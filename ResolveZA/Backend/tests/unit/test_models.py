import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from app.models.user import Role, User
from app.models.customer import Customer, Account
from app.models.transaction import Transaction
from app.models.ticket import Ticket, Message, Escalation
from app.models.refund import Refund
from app.models.audit_log import AuditLog


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_role(db, name="agent"):
    role = Role(name=name, description="Test role")
    db.add(role)
    db.flush()
    return role

def make_customer(db):
    customer = Customer(
        full_name="Nomvula Dlamini",
        email=f"nomvula_{uuid.uuid4().hex[:6]}@test.com",
        phone_number="0821234567",
    )
    db.add(customer)
    db.flush()
    return customer

def make_account(db, customer):
    account = Account(
        customer_id=customer.id,
        account_number=f"ACC-{uuid.uuid4().hex[:8]}",
        account_type="PREPAID",
    )
    db.add(account)
    db.flush()
    return account


# ─── Role ───────────────────────────────────────────────────────────────────

class TestRoleModel:
    def test_role_id_is_uuid_after_flush(self, db_session):
        role = make_role(db_session)
        assert isinstance(role.id, uuid.UUID)

    def test_role_name_stored_correctly(self, db_session):
        role = make_role(db_session, "supervisor")
        assert role.name == "supervisor"

    def test_role_repr(self, db_session):
        role = make_role(db_session)
        assert "agent" in repr(role)


# ─── User ────────────────────────────────────────────────────────────────────

class TestUserModel:
    def test_user_is_active_defaults_true(self, db_session):
        role = make_role(db_session)
        user = User(
            email="agent@resolveza.co.za",
            hashed_password="$2b$12$hashed",
            full_name="Thabo Nkosi",
            role_id=role.id,
        )
        db_session.add(user)
        db_session.flush()
        assert user.is_active is True

    def test_user_last_login_defaults_none(self, db_session):
        role = make_role(db_session, "admin")
        user = User(
            email="admin@test.com",
            hashed_password="hash",
            full_name="Admin",
            role_id=role.id,
        )
        db_session.add(user)
        db_session.flush()
        assert user.last_login_at is None

    def test_user_repr(self, db_session):
        role = make_role(db_session)
        user = User(
            email="repr@test.com",
            hashed_password="hash",
            full_name="Test",
            role_id=role.id,
        )
        db_session.add(user)
        db_session.flush()
        assert "repr@test.com" in repr(user)


# ─── Customer ────────────────────────────────────────────────────────────────

class TestCustomerModel:
    def test_customer_is_active_default(self, db_session):
        customer = make_customer(db_session)
        assert customer.is_active is True

    def test_customer_id_number_optional(self, db_session):
        customer = make_customer(db_session)
        assert customer.id_number is None

    def test_customer_repr(self, db_session):
        customer = make_customer(db_session)
        assert "@test.com" in repr(customer)


# ─── Account ─────────────────────────────────────────────────────────────────

class TestAccountModel:
    def test_balance_defaults_zero(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        assert account.balance == Decimal("0.00")

    def test_currency_defaults_zar(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        assert account.currency == "ZAR"

    def test_status_defaults_active(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        assert account.status == "ACTIVE"

    def test_account_repr(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        assert "PREPAID" in repr(account)


# ─── Transaction ─────────────────────────────────────────────────────────────

class TestTransactionModel:
    def test_status_defaults_completed(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        tx = Transaction(
            account_id=account.id,
            transaction_type="DEBIT",
            amount=Decimal("99.00"),
        )
        db_session.add(tx)
        db_session.flush()
        assert tx.status == "COMPLETED"

    def test_amount_is_decimal(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        tx = Transaction(
            account_id=account.id,
            transaction_type="AIRTIME",
            amount=Decimal("10.50"),
        )
        db_session.add(tx)
        db_session.flush()
        # After DB round-trip, still Decimal
        assert isinstance(tx.amount, Decimal)

    def test_transaction_repr(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        tx = Transaction(
            account_id=account.id,
            transaction_type="DATA",
            amount=Decimal("149.00"),
        )
        db_session.add(tx)
        db_session.flush()
        assert "DATA" in repr(tx)


# ─── Ticket ───────────────────────────────────────────────────────────────────

class TestTicketModel:
    def _make_ticket(self, db):
        customer = make_customer(db)
        ticket = Ticket(
            customer_id=customer.id,
            category="DOUBLE_BILLING",
            priority="HIGH",
            subject="Charged twice",
            description="Debited twice on the same day",
            sla_deadline=datetime.now(timezone.utc),
        )
        db.add(ticket)
        db.flush()
        return ticket

    def test_status_defaults_open(self, db_session):
        ticket = self._make_ticket(db_session)
        assert ticket.status == "OPEN"

    def test_sla_not_breached_on_creation(self, db_session):
        ticket = self._make_ticket(db_session)
        assert ticket.sla_breached is False

    def test_resolved_at_defaults_none(self, db_session):
        ticket = self._make_ticket(db_session)
        assert ticket.resolved_at is None

    def test_assigned_to_defaults_none(self, db_session):
        ticket = self._make_ticket(db_session)
        assert ticket.assigned_to is None


# ─── Message ──────────────────────────────────────────────────────────────────

class TestMessageModel:
    def test_is_internal_defaults_false(self, db_session):
        customer = make_customer(db_session)
        ticket = Ticket(
            customer_id=customer.id,
            category="UNAUTHORIZED_DEDUCTION",
            priority="MEDIUM",
            subject="Unexpected charge",
            description="Description",
            sla_deadline=datetime.now(timezone.utc),
        )
        db_session.add(ticket)
        db_session.flush()

        msg = Message(
            ticket_id=ticket.id,
            sender_type="CUSTOMER",
            content="Please help",
        )
        db_session.add(msg)
        db_session.flush()
        assert msg.is_internal is False

    def test_ai_message_has_no_sender_id(self):
        """Pure Python test — no DB needed"""
        msg = Message(
            ticket_id=uuid.uuid4(),
            sender_type="AI_ASSISTANT",
            content="How can I assist you?",
        )
        assert msg.sender_id is None


# ─── Refund ───────────────────────────────────────────────────────────────────

class TestRefundModel:
    def test_status_defaults_pending(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        tx = Transaction(
            account_id=account.id,
            transaction_type="DEBIT",
            amount=Decimal("149.00"),
        )
        db_session.add(tx)
        ticket = Ticket(
            customer_id=customer.id,
            category="DOUBLE_BILLING",
            priority="HIGH",
            subject="Test",
            description="Test",
            sla_deadline=datetime.now(timezone.utc),
        )
        db_session.add(ticket)
        db_session.flush()

        refund = Refund(
            ticket_id=ticket.id,
            transaction_id=tx.id,
            idempotency_key=str(uuid.uuid4()),
            amount=Decimal("149.00"),
            requested_at=datetime.now(timezone.utc),
        )
        db_session.add(refund)
        db_session.flush()
        assert refund.status == "PENDING"

    def test_unique_constraint_on_transaction(self):
        """Schema-level check — no DB session needed"""
        constraints = {c.name for c in Refund.__table__.constraints}
        assert "uq_refund_transaction" in constraints

    def test_approved_at_defaults_none(self, db_session):
        customer = make_customer(db_session)
        account = make_account(db_session, customer)
        tx = Transaction(account_id=account.id, transaction_type="DEBIT", amount=Decimal("50.00"))
        db_session.add(tx)
        ticket = Ticket(
            customer_id=customer.id, category="DOUBLE_BILLING",
            priority="LOW", subject="Test", description="Test",
            sla_deadline=datetime.now(timezone.utc),
        )
        db_session.add(ticket)
        db_session.flush()

        refund = Refund(
            ticket_id=ticket.id, transaction_id=tx.id,
            idempotency_key=str(uuid.uuid4()),
            amount=Decimal("50.00"), requested_at=datetime.now(timezone.utc),
        )
        db_session.add(refund)
        db_session.flush()
        assert refund.approved_at is None


# ─── AuditLog ─────────────────────────────────────────────────────────────────

class TestAuditLogModel:
    def test_audit_log_persists(self, db_session):
        log = AuditLog(
            action="TICKET_CREATED",
            resource_type="ticket",
            resource_id=str(uuid.uuid4()),
            ip_address="10.0.0.1",
        )
        db_session.add(log)
        db_session.flush()
        assert log.id is not None
        assert log.action == "TICKET_CREATED"

    def test_user_id_optional(self, db_session):
        log = AuditLog(
            action="AUTO_ESCALATION",
            resource_type="ticket",
            resource_id=str(uuid.uuid4()),
        )
        db_session.add(log)
        db_session.flush()
        assert log.user_id is None

    def test_no_updated_at_column(self):
        """Audit logs are immutable — no updated_at"""
        columns = {c.name for c in AuditLog.__table__.columns}
        assert "updated_at" not in columns
        assert "created_at" in columns