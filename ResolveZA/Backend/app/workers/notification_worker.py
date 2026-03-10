import uuid
from celery.utils.log import get_task_logger
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.ticket import Ticket
from app.models.user import User

logger = get_task_logger(__name__)


def _send_email(to: str, subject: str, body: str):
    """
    Email sending stub.
    Replace with real SMTP / SendGrid / AWS SES call in production.
    """
    logger.info(f"EMAIL (stub) → to={to} subject={subject} body={body[:80]}")


@celery_app.task(
    name="app.workers.notification_worker.notify_sla_breach",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def notify_sla_breach(ticket_id: str):
    """
    Notify the assigned agent (and supervisors) that a ticket has
    breached its SLA and been auto-escalated.
    """
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(
            Ticket.id == uuid.UUID(ticket_id)
        ).first()

        if not ticket:
            logger.warning(f"notify_sla_breach: ticket {ticket_id} not found")
            return

        subject = f"[ResolveZA] SLA Breach — Ticket #{str(ticket.id)[:8]}"
        body = (
            f"Ticket has breached its SLA deadline.\n\n"
            f"Subject: {ticket.subject}\n"
            f"Priority: {ticket.priority}\n"
            f"Category: {ticket.category}\n"
            f"SLA Deadline: {ticket.sla_deadline}\n"
            f"Status: {ticket.status}\n\n"
            f"This ticket has been automatically escalated."
        )

        # Notify assigned agent if there is one
        if ticket.assigned_to:
            agent = db.query(User).filter(
                User.id == uuid.UUID(str(ticket.assigned_to))
            ).first()
            if agent:
                _send_email(agent.email, subject, body)

        # Also notify all supervisors
        supervisors = (
            db.query(User)
            .join(User.role)
            .filter(User.role.has(name="supervisor"))
            .all()
        )
        for supervisor in supervisors:
            _send_email(supervisor.email, subject, body)

        logger.info(f"SLA breach notifications sent for ticket {ticket_id}")

    finally:
        db.close()


@celery_app.task(
    name="app.workers.notification_worker.notify_ticket_assigned",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def notify_ticket_assigned(ticket_id: str, agent_id: str):
    """Notify an agent that a ticket has been assigned to them."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(
            Ticket.id == uuid.UUID(ticket_id)
        ).first()
        agent = db.query(User).filter(
            User.id == uuid.UUID(agent_id)
        ).first()

        if not ticket or not agent:
            logger.warning(
                f"notify_ticket_assigned: ticket={ticket_id} or agent={agent_id} not found"
            )
            return

        subject = f"[ResolveZA] Ticket Assigned — #{str(ticket.id)[:8]}"
        body = (
            f"A ticket has been assigned to you.\n\n"
            f"Subject: {ticket.subject}\n"
            f"Priority: {ticket.priority}\n"
            f"Category: {ticket.category}\n"
            f"SLA Deadline: {ticket.sla_deadline}\n\n"
            f"Please log in to ResolveZA to review."
        )
        _send_email(agent.email, subject, body)
        logger.info(f"Assignment notification sent to {agent.email} for ticket {ticket_id}")

    finally:
        db.close()


@celery_app.task(
    name="app.workers.notification_worker.notify_escalation",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def notify_escalation(ticket_id: str, escalated_to_agent_id: str = None):
    """Notify relevant parties when a ticket is manually escalated."""
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(
            Ticket.id == uuid.UUID(ticket_id)
        ).first()
        if not ticket:
            return

        subject = f"[ResolveZA] Ticket Escalated — #{str(ticket.id)[:8]}"
        body = (
            f"A ticket has been escalated and requires your attention.\n\n"
            f"Subject: {ticket.subject}\n"
            f"Priority: {ticket.priority}\n"
            f"Category: {ticket.category}\n\n"
            f"Please log in to ResolveZA to review."
        )

        if escalated_to_agent_id:
            agent = db.query(User).filter(
                User.id == uuid.UUID(escalated_to_agent_id)
            ).first()
            if agent:
                _send_email(agent.email, subject, body)

        supervisors = (
            db.query(User)
            .join(User.role)
            .filter(User.role.has(name="supervisor"))
            .all()
        )
        for supervisor in supervisors:
            _send_email(supervisor.email, subject, body)

    finally:
        db.close()