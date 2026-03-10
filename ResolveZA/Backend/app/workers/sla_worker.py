from datetime import datetime, timezone
from celery import shared_task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.ticket import Ticket, Escalation
from app.models.audit_log import AuditLog

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.sla_worker.check_sla_breaches",
    max_retries=3,
    default_retry_delay=60,  # retry after 60 seconds on failure
)
def check_sla_breaches(self):
    """
    Find all tickets that have breached their SLA and haven't been
    flagged yet. Mark them breached and auto-escalate if still open.

    Returns a summary dict — useful for monitoring and testing.
    """
    db = SessionLocal()
    breached_count = 0
    escalated_count = 0

    try:
        now = datetime.now(timezone.utc)

        # Find tickets that are past their SLA deadline but not yet flagged
        # Only active tickets (not RESOLVED or CLOSED)
        breached_tickets = db.query(Ticket).filter(
            Ticket.sla_deadline < now,
            Ticket.sla_breached == False,        # noqa: E712
            Ticket.status.notin_(["RESOLVED", "CLOSED"]),
        ).all()

        logger.info(f"SLA check: found {len(breached_tickets)} breached tickets")

        for ticket in breached_tickets:
            # 1. Mark as breached
            ticket.sla_breached = True
            breached_count += 1

            # 2. Auto-escalate if not already escalated
            if ticket.status not in ("ESCALATED",):
                previous_status = ticket.status
                ticket.status = "ESCALATED"
                escalated_count += 1

                # Record the escalation event
                escalation = Escalation(
                    ticket_id=ticket.id,
                    escalated_by=None,       # system-triggered, no human
                    escalated_to=None,       # will be assigned by supervisor
                    reason=f"Auto-escalated: SLA breached. Was {previous_status}.",
                    escalation_type="AUTO_SLA",
                )
                db.add(escalation)

            # 3. Write to audit log
            import json
            audit = AuditLog(
                resource_type="ticket",
                resource_id=str(ticket.id),
                action="sla_breached",
                user_id=None,   # system action — no human user
                extra_data=json.dumps({
                    "ticket_id": str(ticket.id),
                    "sla_deadline": ticket.sla_deadline.isoformat(),
                    "breached_at": now.isoformat(),
                    "status": ticket.status,
                }),
            )
            db.add(audit)

            # 4. Queue a notification (fire-and-forget)
            from app.workers.notification_worker import notify_sla_breach
            notify_sla_breach.delay(str(ticket.id))

        db.commit()

        result = {
            "checked_at": now.isoformat(),
            "breached": breached_count,
            "auto_escalated": escalated_count,
        }
        logger.info(f"SLA check complete: {result}")
        return result

    except Exception as exc:
        db.rollback()
        logger.error(f"SLA check failed: {exc}")
        # Retry the task — Celery will wait default_retry_delay before retrying
        raise self.retry(exc=exc)

    finally:
        db.close()