from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User
from app.schemas.ticket import (
    TicketCreateRequest, TicketStatusUpdate, TicketAssignRequest,
    TicketResponse, PaginatedTickets,
    MessageCreateRequest, MessageResponse,
    EscalateRequest, EscalationResponse,
)
from app.services.ticket_service import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201, summary="Open a ticket")
def create_ticket(
    request: TicketCreateRequest,
    customer_id: uuid.UUID = Query(..., description="ID of the customer this ticket is for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Open a new support ticket on behalf of a customer.
    SLA deadline is automatically calculated from priority.
    """
    return ticket_service.create_ticket(db, request, customer_id)


@router.get("", response_model=PaginatedTickets, summary="List tickets")
def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assigned_to: Optional[uuid.UUID] = Query(None, description="Filter by assigned agent"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """Paginated list of tickets. Newest first. Filter by status, priority, or agent."""
    return ticket_service.list_tickets(
        db, page, page_size,
        status_filter=status,
        priority_filter=priority,
        assigned_to=str(assigned_to) if assigned_to else None,
    )


@router.get("/{ticket_id}", response_model=TicketResponse, summary="Get ticket detail")
def get_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    return ticket_service.get_ticket(db, ticket_id)


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Update ticket status",
)
def update_status(
    ticket_id: uuid.UUID,
    request: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Transition a ticket through the state machine.
    Invalid transitions return 400 with a clear error message.
    """
    return ticket_service.update_status(db, ticket_id, request, current_user)


@router.patch(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
    summary="Assign ticket to agent",
)
def assign_ticket(
    ticket_id: uuid.UUID,
    request: TicketAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("supervisor", "admin")),
):
    """Assign a ticket to a specific agent. Supervisor or admin only."""
    return ticket_service.assign_ticket(db, ticket_id, request, current_user)


@router.post(
    "/{ticket_id}/messages",
    response_model=MessageResponse,
    status_code=201,
    summary="Add message to ticket thread",
)
def add_message(
    ticket_id: uuid.UUID,
    request: MessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Add a message or internal note to a ticket thread.
    is_internal=true creates an agent-only note, invisible to customers.
    """
    return ticket_service.add_message(
        db, ticket_id, request,
        sender_type="AGENT",
        sender_id=current_user.id,
    )


@router.get(
    "/{ticket_id}/messages",
    response_model=list[MessageResponse],
    summary="Get ticket message thread",
)
def get_messages(
    ticket_id: uuid.UUID,
    include_internal: bool = Query(False, description="Include agent-only notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Fetch the full conversation thread for a ticket.
    include_internal=true shows agent notes (not visible to customers).
    """
    return ticket_service.get_messages(db, ticket_id, include_internal)


@router.post(
    "/{ticket_id}/escalate",
    response_model=EscalationResponse,
    status_code=201,
    summary="Escalate ticket to Tier-2",
)
def escalate_ticket(
    ticket_id: uuid.UUID,
    request: EscalateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Escalate a ticket to Tier-2 support.
    Requires a documented reason. Status changes to ESCALATED.
    """
    return ticket_service.escalate(db, ticket_id, request, current_user)