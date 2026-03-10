import uuid
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

import app.models  # noqa: F401 — must be before Base.metadata.create_all
from app.db.session import Base, SessionLocal
from app.models.user import Role, User
from app.models.customer import Customer
from app.models.ticket import Ticket, Escalation
from app.core.security import hash_password


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

    # Patch SessionLocal to return our test session.
    # We wrap it so the worker's db.close() call is a no-op —
    # otherwise the worker closes the shared session and our
    # assertions fail with DetachedInstanceError.
    class NoCloseSession:
        """Proxy that delegates everything to the real session except close()."""
        def __init__(self, session):
            self._session = session
        def close(self):
            pass  # intentionally do nothing
        def __getattr__(self, name):
            return getattr(self._session, name)

    with patch("app.workers.sla_worker.SessionLocal", return_value=NoCloseSession(session)), \
         patch("app.workers.notification_worker.SessionLocal", return_value=NoCloseSession(session)):
        yield session

    session.close()
    Base.metadata.drop_all(engine)


# ─── Seed helpers ─────────────────────────────────────────────────────────────

def seed_roles(db):
    roles = {}
    for name in ("admin", "supervisor", "agent"):
        r = Role(name=name, description=f"{name} role")
        db.add(r)
        db.flush()
        roles[name] = r
    return roles


def make_ticket(db, customer_id, priority="MEDIUM", status="OPEN",
                sla_breached=False, hours_overdue=1):
    """Create a ticket with an SLA deadline in the past by default."""
    ticket = Ticket(
        customer_id=customer_id,
        category="DOUBLE_BILLING",
        priority=priority,
        status=status,
        subject="Test ticket",
        description="Test description",
        sla_deadline=datetime.now(timezone.utc) - timedelta(hours=hours_overdue),
        sla_breached=sla_breached,
    )
    db.add(ticket)
    db.flush()
    return ticket


def make_customer(db):
    customer = Customer(
        full_name="Test Customer",
        email=f"test_{uuid.uuid4().hex[:6]}@test.com",
        phone_number="0821234567",
    )
    db.add(customer)
    db.flush()
    return customer


# ─── SLA Worker tests ─────────────────────────────────────────────────────────

class TestSLAWorker:

    def test_breached_ticket_is_flagged(self, db):
        """
        A ticket past its SLA deadline should have sla_breached set to True.
        """
        customer = make_customer(db)
        ticket = make_ticket(db, customer.id)
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        refreshed = db.query(Ticket).filter(Ticket.id == ticket.id).first()
        assert refreshed.sla_breached is True
        assert result["breached"] == 1

    def test_breached_ticket_is_auto_escalated(self, db):
        """
        An OPEN ticket that breaches SLA should be moved to ESCALATED.
        An Escalation record should be created with type AUTO_SLA.
        """
        customer = make_customer(db)
        ticket = make_ticket(db, customer.id, status="OPEN")
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        refreshed = db.query(Ticket).filter(Ticket.id == ticket.id).first()
        assert refreshed.status == "ESCALATED"
        assert result["auto_escalated"] == 1

        escalation = db.query(Escalation).filter(
            Escalation.ticket_id == ticket.id
        ).first()
        assert escalation is not None
        assert escalation.escalation_type == "AUTO_SLA"

    def test_already_breached_ticket_is_skipped(self, db):
        """
        A ticket already marked sla_breached=True should not be processed again.
        Idempotency check.
        """
        customer = make_customer(db)
        # Already breached — should be skipped
        make_ticket(db, customer.id, sla_breached=True)
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        assert result["breached"] == 0

    def test_resolved_ticket_is_skipped(self, db):
        """
        RESOLVED and CLOSED tickets should never be auto-escalated,
        even if their SLA deadline has passed.
        """
        customer = make_customer(db)
        make_ticket(db, customer.id, status="RESOLVED")
        make_ticket(db, customer.id, status="CLOSED")
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        assert result["breached"] == 0
        assert result["auto_escalated"] == 0

    def test_future_sla_ticket_is_skipped(self, db):
        """
        A ticket whose SLA deadline is in the future should not be touched.
        """
        customer = make_customer(db)
        ticket = Ticket(
            customer_id=customer.id,
            category="DOUBLE_BILLING",
            priority="HIGH",
            status="OPEN",
            subject="Future ticket",
            description="Not breached yet",
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=5),
            sla_breached=False,
        )
        db.add(ticket)
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        assert result["breached"] == 0

    def test_multiple_breached_tickets(self, db):
        """All breached tickets in one run should be processed."""
        customer = make_customer(db)
        for _ in range(4):
            make_ticket(db, customer.id)
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        assert result["breached"] == 4
        assert result["auto_escalated"] == 4

    def test_already_escalated_ticket_not_double_escalated(self, db):
        """
        A ticket already in ESCALATED status should be flagged as breached
        but NOT have another escalation record created.
        """
        customer = make_customer(db)
        make_ticket(db, customer.id, status="ESCALATED")
        db.commit()

        from app.workers.sla_worker import check_sla_breaches
        with patch("app.workers.notification_worker.notify_sla_breach.delay"):
            result = check_sla_breaches()

        assert result["breached"] == 1
        assert result["auto_escalated"] == 0  # already escalated, don't re-escalate


# ─── Notification Worker tests ────────────────────────────────────────────────

class TestNotificationWorker:

    def test_notify_sla_breach_missing_ticket(self, db):
        """
        If the ticket doesn't exist, the task should log and return
        gracefully — not raise an exception.
        """
        db.commit()

        from app.workers.notification_worker import notify_sla_breach
        # Should not raise — just logs a warning
        notify_sla_breach(str(uuid.uuid4()))

    def test_notify_sla_breach_sends_email(self, db):
        """
        When a breached ticket exists, _send_email should be called
        at least once (for supervisors or assigned agent).
        """
        roles = seed_roles(db)
        supervisor = User(
            email="supervisor@test.com",
            hashed_password=hash_password("Password123"),
            full_name="Test Supervisor",
            role_id=roles["supervisor"].id,
        )
        db.add(supervisor)

        customer = make_customer(db)
        ticket = make_ticket(db, customer.id)
        db.commit()

        from app.workers.notification_worker import notify_sla_breach
        with patch("app.workers.notification_worker._send_email") as mock_send:
            notify_sla_breach(str(ticket.id))
            # Supervisor should have received a notification
            assert mock_send.called