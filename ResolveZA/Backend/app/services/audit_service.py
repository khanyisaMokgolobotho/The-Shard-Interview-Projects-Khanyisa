import json
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


# ---------------------------------------------------------------------------
# Action constants — use these instead of raw strings to avoid typos
# ---------------------------------------------------------------------------
class AuditAction:
    # Auth
    USER_LOGIN          = "USER_LOGIN"
    USER_LOGIN_FAILED   = "USER_LOGIN_FAILED"
    USER_REGISTERED     = "USER_REGISTERED"

    # Customers (POPIA — log all PII access)
    CUSTOMER_CREATED    = "CUSTOMER_CREATED"
    CUSTOMER_UPDATED    = "CUSTOMER_UPDATED"
    CUSTOMER_VIEWED     = "CUSTOMER_VIEWED"

    # Tickets
    TICKET_CREATED          = "TICKET_CREATED"
    TICKET_STATUS_CHANGED   = "TICKET_STATUS_CHANGED"
    TICKET_ASSIGNED         = "TICKET_ASSIGNED"
    TICKET_ESCALATED        = "TICKET_ESCALATED"
    TICKET_MESSAGE_ADDED    = "TICKET_MESSAGE_ADDED"

    # Refunds (financial — must be thorough)
    REFUND_REQUESTED    = "REFUND_REQUESTED"
    REFUND_APPROVED     = "REFUND_APPROVED"
    REFUND_REJECTED     = "REFUND_REJECTED"

    # SLA (system-triggered)
    SLA_BREACHED        = "SLA_BREACHED"


class AuditService:
    """
    Writes immutable audit log entries.
    Call from service layer, not from routes.
    """

    def log(
        self,
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> AuditLog:
        """
        Write a single audit log entry.

        This is the core method — all the helpers below call this.
        Returns the created AuditLog so callers can inspect it in tests.
        """
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            extra_data=json.dumps(extra_data) if extra_data else None,
        )
        db.add(entry)
        # We flush (not commit) — the caller's transaction owns the commit.
        # This keeps the audit log entry and the main operation atomic:
        # if the main operation rolls back, the audit log rolls back too.
        db.flush()
        return entry

    # -------------------------------------------------------------------------
    # Auth helpers
    # -------------------------------------------------------------------------

    def log_login(
        self,
        db: Session,
        user_id: uuid.UUID,
        email: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.USER_LOGIN,
            resource_type="user",
            resource_id=str(user_id),
            user_id=user_id,
            ip_address=ip_address,
            extra_data={"email": email},
        )

    def log_login_failed(
        self,
        db: Session,
        email: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log a failed login attempt — no user_id since auth failed."""
        return self.log(
            db,
            action=AuditAction.USER_LOGIN_FAILED,
            resource_type="user",
            resource_id=None,
            user_id=None,
            ip_address=ip_address,
            extra_data={"email": email},
        )

    def log_register(
        self,
        db: Session,
        new_user_id: uuid.UUID,
        email: str,
        role: str,
        performed_by: Optional[uuid.UUID] = None,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.USER_REGISTERED,
            resource_type="user",
            resource_id=str(new_user_id),
            user_id=performed_by,
            extra_data={"email": email, "role": role},
        )

    # -------------------------------------------------------------------------
    # Customer helpers
    # -------------------------------------------------------------------------

    def log_customer_created(
        self,
        db: Session,
        customer_id: uuid.UUID,
        performed_by: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.CUSTOMER_CREATED,
            resource_type="customer",
            resource_id=str(customer_id),
            user_id=performed_by,
            ip_address=ip_address,
        )

    def log_customer_viewed(
        self,
        db: Session,
        customer_id: uuid.UUID,
        performed_by: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        POPIA: Log every time a customer's PII is accessed.
        Call this from GET /customers/{id}.
        """
        return self.log(
            db,
            action=AuditAction.CUSTOMER_VIEWED,
            resource_type="customer",
            resource_id=str(customer_id),
            user_id=performed_by,
            ip_address=ip_address,
        )

    # -------------------------------------------------------------------------
    # Ticket helpers
    # -------------------------------------------------------------------------

    def log_ticket_created(
        self,
        db: Session,
        ticket_id: uuid.UUID,
        customer_id: uuid.UUID,
        performed_by: uuid.UUID,
        priority: str,
        category: str,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.TICKET_CREATED,
            resource_type="ticket",
            resource_id=str(ticket_id),
            user_id=performed_by,
            extra_data={
                "customer_id": str(customer_id),
                "priority": priority,
                "category": category,
            },
        )

    def log_ticket_status_changed(
        self,
        db: Session,
        ticket_id: uuid.UUID,
        old_status: str,
        new_status: str,
        performed_by: uuid.UUID,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.TICKET_STATUS_CHANGED,
            resource_type="ticket",
            resource_id=str(ticket_id),
            user_id=performed_by,
            extra_data={"from": old_status, "to": new_status},
        )

    def log_ticket_assigned(
        self,
        db: Session,
        ticket_id: uuid.UUID,
        assigned_to: uuid.UUID,
        performed_by: uuid.UUID,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.TICKET_ASSIGNED,
            resource_type="ticket",
            resource_id=str(ticket_id),
            user_id=performed_by,
            extra_data={"assigned_to": str(assigned_to)},
        )

    def log_escalation(
        self,
        db: Session,
        ticket_id: uuid.UUID,
        reason: str,
        performed_by: Optional[uuid.UUID] = None,
        escalation_type: str = "MANUAL",
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.TICKET_ESCALATED,
            resource_type="ticket",
            resource_id=str(ticket_id),
            user_id=performed_by,
            extra_data={"reason": reason, "escalation_type": escalation_type},
        )

    # -------------------------------------------------------------------------
    # Refund helpers
    # -------------------------------------------------------------------------

    def log_refund_requested(
        self,
        db: Session,
        refund_id: uuid.UUID,
        ticket_id: uuid.UUID,
        amount: str,
        performed_by: uuid.UUID,
    ) -> AuditLog:
        return self.log(
            db,
            action=AuditAction.REFUND_REQUESTED,
            resource_type="refund",
            resource_id=str(refund_id),
            user_id=performed_by,
            extra_data={"ticket_id": str(ticket_id), "amount": amount},
        )

    def log_refund_approved(
        self,
        db: Session,
        refund_id: uuid.UUID,
        amount: str,
        approved: bool,
        performed_by: uuid.UUID,
        rejection_reason: Optional[str] = None,
    ) -> AuditLog:
        action = AuditAction.REFUND_APPROVED if approved else AuditAction.REFUND_REJECTED
        extra: dict = {"amount": amount, "approved": approved}
        if rejection_reason:
            extra["rejection_reason"] = rejection_reason

        return self.log(
            db,
            action=action,
            resource_type="refund",
            resource_id=str(refund_id),
            user_id=performed_by,
            extra_data=extra,
        )


# Singleton — import and use this everywhere
audit_service = AuditService()