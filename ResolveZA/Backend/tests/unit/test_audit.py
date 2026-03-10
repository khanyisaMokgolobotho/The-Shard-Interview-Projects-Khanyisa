import uuid
import json
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.session import Base
from app.models.audit_log import AuditLog
from app.services.audit_service import audit_service, AuditAction


# ─── Test DB setup ────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def get_logs(db, action=None):
    """Helper: fetch audit logs, optionally filtered by action."""
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    return q.all()


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestAuditService:

    def test_log_login_creates_entry(self, db):
        user_id = uuid.uuid4()
        entry = audit_service.log_login(
            db, user_id=user_id, email="agent@test.com", ip_address="192.168.1.1"
        )
        db.commit()

        logs = get_logs(db, AuditAction.USER_LOGIN)
        assert len(logs) == 1
        assert logs[0].action == AuditAction.USER_LOGIN
        assert logs[0].resource_type == "user"
        assert logs[0].ip_address == "192.168.1.1"
        data = json.loads(logs[0].extra_data)
        assert data["email"] == "agent@test.com"

    def test_log_login_failed_has_no_user_id(self, db):
        """Failed login — we don't know who the user is."""
        entry = audit_service.log_login_failed(
            db, email="hacker@evil.com", ip_address="10.0.0.1"
        )
        db.commit()

        logs = get_logs(db, AuditAction.USER_LOGIN_FAILED)
        assert len(logs) == 1
        assert logs[0].user_id is None
        data = json.loads(logs[0].extra_data)
        assert data["email"] == "hacker@evil.com"

    def test_log_customer_created(self, db):
        customer_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        audit_service.log_customer_created(
            db, customer_id=customer_id, performed_by=agent_id
        )
        db.commit()

        logs = get_logs(db, AuditAction.CUSTOMER_CREATED)
        assert len(logs) == 1
        assert logs[0].resource_id == str(customer_id)
        assert logs[0].user_id == agent_id

    def test_log_customer_viewed(self, db):
        """POPIA — every PII access must be logged."""
        customer_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        audit_service.log_customer_viewed(
            db, customer_id=customer_id, performed_by=agent_id,
            ip_address="172.16.0.5"
        )
        db.commit()

        logs = get_logs(db, AuditAction.CUSTOMER_VIEWED)
        assert len(logs) == 1
        assert logs[0].resource_type == "customer"
        assert logs[0].ip_address == "172.16.0.5"

    def test_log_ticket_created(self, db):
        ticket_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        audit_service.log_ticket_created(
            db,
            ticket_id=ticket_id,
            customer_id=customer_id,
            performed_by=agent_id,
            priority="HIGH",
            category="DOUBLE_BILLING",
        )
        db.commit()

        logs = get_logs(db, AuditAction.TICKET_CREATED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["priority"] == "HIGH"
        assert data["category"] == "DOUBLE_BILLING"
        assert data["customer_id"] == str(customer_id)

    def test_log_ticket_status_changed(self, db):
        ticket_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        audit_service.log_ticket_status_changed(
            db,
            ticket_id=ticket_id,
            old_status="OPEN",
            new_status="IN_PROGRESS",
            performed_by=agent_id,
        )
        db.commit()

        logs = get_logs(db, AuditAction.TICKET_STATUS_CHANGED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["from"] == "OPEN"
        assert data["to"] == "IN_PROGRESS"

    def test_log_ticket_assigned(self, db):
        ticket_id = uuid.uuid4()
        agent_id = uuid.uuid4()
        supervisor_id = uuid.uuid4()

        audit_service.log_ticket_assigned(
            db,
            ticket_id=ticket_id,
            assigned_to=agent_id,
            performed_by=supervisor_id,
        )
        db.commit()

        logs = get_logs(db, AuditAction.TICKET_ASSIGNED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["assigned_to"] == str(agent_id)

    def test_log_escalation(self, db):
        ticket_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        audit_service.log_escalation(
            db,
            ticket_id=ticket_id,
            reason="Customer threatened media escalation",
            performed_by=agent_id,
            escalation_type="MANUAL",
        )
        db.commit()

        logs = get_logs(db, AuditAction.TICKET_ESCALATED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["escalation_type"] == "MANUAL"
        assert "media escalation" in data["reason"]

    def test_log_refund_requested(self, db):
        refund_id = uuid.uuid4()
        ticket_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        audit_service.log_refund_requested(
            db,
            refund_id=refund_id,
            ticket_id=ticket_id,
            amount="149.00",
            performed_by=agent_id,
        )
        db.commit()

        logs = get_logs(db, AuditAction.REFUND_REQUESTED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["amount"] == "149.00"

    def test_log_refund_approved(self, db):
        refund_id = uuid.uuid4()
        supervisor_id = uuid.uuid4()

        audit_service.log_refund_approved(
            db,
            refund_id=refund_id,
            amount="149.00",
            approved=True,
            performed_by=supervisor_id,
        )
        db.commit()

        logs = get_logs(db, AuditAction.REFUND_APPROVED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["approved"] is True

    def test_log_refund_rejected_includes_reason(self, db):
        refund_id = uuid.uuid4()
        supervisor_id = uuid.uuid4()

        audit_service.log_refund_approved(
            db,
            refund_id=refund_id,
            amount="149.00",
            approved=False,
            performed_by=supervisor_id,
            rejection_reason="Transaction not found in billing system",
        )
        db.commit()

        logs = get_logs(db, AuditAction.REFUND_REJECTED)
        assert len(logs) == 1
        data = json.loads(logs[0].extra_data)
        assert data["approved"] is False
        assert "billing system" in data["rejection_reason"]

    def test_multiple_logs_accumulate(self, db):
        """Each call adds a new row — audit logs are append-only."""
        agent_id = uuid.uuid4()
        ticket_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        for status in ("IN_PROGRESS", "ESCALATED", "RESOLVED"):
            audit_service.log_ticket_status_changed(
                db, ticket_id=ticket_id,
                old_status="OPEN", new_status=status,
                performed_by=agent_id,
            )
        db.commit()

        logs = get_logs(db, AuditAction.TICKET_STATUS_CHANGED)
        assert len(logs) == 3

    def test_system_action_has_no_user_id(self, db):
        """Celery/system actions have no human user — user_id must be None."""
        ticket_id = uuid.uuid4()

        audit_service.log_escalation(
            db,
            ticket_id=ticket_id,
            reason="Auto-escalated: SLA breached",
            performed_by=None,       # system triggered
            escalation_type="AUTO_SLA",
        )
        db.commit()

        logs = get_logs(db, AuditAction.TICKET_ESCALATED)
        assert logs[0].user_id is None
        data = json.loads(logs[0].extra_data)
        assert data["escalation_type"] == "AUTO_SLA"