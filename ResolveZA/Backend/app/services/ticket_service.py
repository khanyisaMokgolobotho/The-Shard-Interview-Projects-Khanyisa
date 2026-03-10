from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.ticket import Ticket, Message, Escalation
from app.models.customer import Customer
from app.models.user import User
from app.schemas.ticket import (
    TicketCreateRequest, TicketStatusUpdate, TicketAssignRequest,
    TicketResponse, TicketListItem, PaginatedTickets,
    MessageCreateRequest, MessageResponse,
    EscalateRequest, EscalationResponse,
)
from app.schemas.common import TicketStatus, TicketPriority
from app.core.logging import get_logger

logger = get_logger(__name__)

# SLA deadlines by priority
SLA_HOURS = {
    TicketPriority.CRITICAL: 2,
    TicketPriority.HIGH: 8,
    TicketPriority.MEDIUM: 24,
    TicketPriority.LOW: 72,
}

# Valid state transitions: current_status → set of allowed next statuses
VALID_TRANSITIONS: dict[str, set[str]] = {
    "OPEN":        {"IN_PROGRESS", "ESCALATED", "CLOSED"},
    "IN_PROGRESS": {"ESCALATED", "RESOLVED", "CLOSED"},
    "ESCALATED":   {"IN_PROGRESS", "RESOLVED", "CLOSED"},
    "RESOLVED":    {"CLOSED"},
    "CLOSED":      set(),  # terminal
}

MAX_PAGE_SIZE = 100


def _calculate_sla_deadline(priority: str) -> datetime:
    """Calculate SLA deadline from now based on ticket priority."""
    hours = SLA_HOURS.get(TicketPriority(priority), 24)
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def _get_ticket_or_404(db: Session, ticket_id) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


class TicketService:

    def create_ticket(
        self,
        db: Session,
        request: TicketCreateRequest,
        customer_id,
    ) -> TicketResponse:
        """
        Create a new support ticket for a customer.
        Sets SLA deadline based on priority.
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        ticket = Ticket(
            customer_id=customer_id,
            account_id=request.account_id,
            category=request.category.value,
            priority=request.priority.value,
            subject=request.subject,
            description=request.description,
            sla_deadline=_calculate_sla_deadline(request.priority.value),
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        logger.info(
            "ticket_created",
            ticket_id=str(ticket.id),
            customer_id=str(customer_id),
            priority=ticket.priority,
        )
        return TicketResponse.model_validate(ticket)

    def list_tickets(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status_filter: str = None,
        priority_filter: str = None,
        assigned_to: str = None,
    ) -> PaginatedTickets:
        page_size = min(page_size, MAX_PAGE_SIZE)
        query = db.query(Ticket)

        if status_filter:
            query = query.filter(Ticket.status == status_filter)
        if priority_filter:
            query = query.filter(Ticket.priority == priority_filter)
        if assigned_to:
            query = query.filter(Ticket.assigned_to == assigned_to)

        # Always show newest first
        query = query.order_by(Ticket.created_at.desc())

        total = query.count()
        tickets = query.offset((page - 1) * page_size).limit(page_size).all()

        return PaginatedTickets(
            items=[TicketListItem.model_validate(t) for t in tickets],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_ticket(self, db: Session, ticket_id) -> TicketResponse:
        ticket = _get_ticket_or_404(db, ticket_id)
        return TicketResponse.model_validate(ticket)

    def update_status(
        self,
        db: Session,
        ticket_id,
        request: TicketStatusUpdate,
        current_user: User,
    ) -> TicketResponse:
        """
        Transition a ticket to a new status.
        Enforces the state machine — invalid transitions are rejected.
        """
        ticket = _get_ticket_or_404(db, ticket_id)
        new_status = request.status.value
        current_status = ticket.status

        # Check the transition is valid
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot transition from {current_status} to {new_status}. "
                    f"Allowed transitions: {', '.join(allowed) or 'none (terminal state)'}"
                ),
            )

        ticket.status = new_status

        # Set resolved_at when resolving
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(timezone.utc)

        # Optionally add an internal note
        if request.note:
            note = Message(
                ticket_id=ticket.id,
                sender_type="AGENT",
                sender_id=current_user.id,
                content=request.note,
                is_internal=True,
            )
            db.add(note)

        db.commit()
        db.refresh(ticket)

        logger.info(
            "ticket_status_changed",
            ticket_id=str(ticket.id),
            from_status=current_status,
            to_status=new_status,
            changed_by=str(current_user.id),
        )
        return TicketResponse.model_validate(ticket)

    def assign_ticket(
        self,
        db: Session,
        ticket_id,
        request: TicketAssignRequest,
        current_user: User,
    ) -> TicketResponse:
        ticket = _get_ticket_or_404(db, ticket_id)

        agent = db.query(User).filter(
            User.id == request.agent_id,
            User.is_active == True,
        ).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        ticket.assigned_to = agent.id
        if ticket.status == "OPEN":
            ticket.status = "IN_PROGRESS"

        db.commit()
        db.refresh(ticket)
        return TicketResponse.model_validate(ticket)

    def add_message(
        self,
        db: Session,
        ticket_id,
        request: MessageCreateRequest,
        sender_type: str,
        sender_id=None,
    ) -> MessageResponse:
        """
        Add a message to a ticket's thread.
        is_internal is only honoured for AGENT sender_type.
        Customers cannot post internal messages.
        """
        ticket = _get_ticket_or_404(db, ticket_id)

        # Customers cannot write internal messages
        is_internal = request.is_internal and sender_type == "AGENT"

        message = Message(
            ticket_id=ticket.id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=request.content,
            is_internal=is_internal,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        return MessageResponse.model_validate(message)

    def get_messages(
        self,
        db: Session,
        ticket_id,
        include_internal: bool = False,
    ) -> list[MessageResponse]:
        """
        Get all messages for a ticket.
        include_internal=False hides agent notes from customers.
        include_internal=True shows all messages to agents/admins.
        """
        _get_ticket_or_404(db, ticket_id)

        query = db.query(Message).filter(Message.ticket_id == ticket_id)
        if not include_internal:
            query = query.filter(Message.is_internal == False)  # noqa: E712

        messages = query.order_by(Message.created_at.asc()).all()
        return [MessageResponse.model_validate(m) for m in messages]

    def escalate(
        self,
        db: Session,
        ticket_id,
        request: EscalateRequest,
        escalated_by_user: User,
    ) -> EscalationResponse:
        """
        Escalate a ticket to Tier-2 support.
        Changes ticket status to ESCALATED and records the escalation event.
        """
        ticket = _get_ticket_or_404(db, ticket_id)

        if ticket.status in ("RESOLVED", "CLOSED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot escalate a {ticket.status} ticket",
            )

        ticket.status = "ESCALATED"
        if request.escalate_to_agent_id:
            ticket.assigned_to = request.escalate_to_agent_id

        escalation = Escalation(
            ticket_id=ticket.id,
            escalated_by=escalated_by_user.id,
            escalated_to=request.escalate_to_agent_id,
            reason=request.reason,
            escalation_type="MANUAL",
        )
        db.add(escalation)
        db.commit()
        db.refresh(escalation)

        logger.info(
            "ticket_escalated",
            ticket_id=str(ticket.id),
            escalated_by=str(escalated_by_user.id),
            reason=request.reason[:50],
        )
        return EscalationResponse.model_validate(escalation)


ticket_service = TicketService()