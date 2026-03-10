import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# ⚠️  Import app.models FIRST — this registers all ORM classes on
# Base.metadata. create_all() below only creates tables it knows about.
# If models are imported after create_all(), you get "no such table".
import app.models  # noqa: F401

from app.main import app as fastapi_app
from app.db.session import Base, get_db
from app.models.user import Role, User
from app.models.customer import Customer, Account
from app.models.transaction import Transaction
from app.core.security import hash_password


# ─── Test DB setup ────────────────────────────────────────────────────────────

def make_test_engine():
    """
    StaticPool is REQUIRED for SQLite :memory: tests.

    WHY:
      A normal SQLite :memory: database exists only for a single connection.
      When SQLAlchemy opens a second connection (which happens inside FastAPI's
      request handling), it gets a brand-new, empty database — "no such table".

      StaticPool forces SQLAlchemy to reuse the same connection for every
      checkout, so create_all() and the test session share the same DB.
    """
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db():
    engine = make_test_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db):
    """TestClient wired to the in-memory DB."""
    fastapi_app.dependency_overrides[get_db] = lambda: db
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# ─── Seed helpers ─────────────────────────────────────────────────────────────

def seed_roles(db):
    roles = {}
    for name in ("admin", "supervisor", "agent"):
        r = Role(name=name, description=f"{name} role")
        db.add(r)
        db.flush()
        roles[name] = r
    return roles


def seed_user(db, roles, role_name="agent", email=None):
    email = email or f"{role_name}_{uuid.uuid4().hex[:6]}@test.com"
    user = User(
        email=email,
        hashed_password=hash_password("Password123"),
        full_name=f"Test {role_name.title()}",
        role_id=roles[role_name].id,
    )
    db.add(user)
    db.flush()
    return user


def get_token(client, email, password="Password123"):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(client, email, password="Password123"):
    return {"Authorization": f"Bearer {get_token(client, email, password)}"}


# ─── Auth tests ───────────────────────────────────────────────────────────────

class TestAuthEndpoints:

    def test_login_success(self, client, db):
        roles = seed_roles(db)
        user = seed_user(db, roles, "agent")
        db.commit()

        resp = client.post("/auth/login", json={
            "email": user.email,
            "password": "Password123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client, db):
        roles = seed_roles(db)
        user = seed_user(db, roles, "agent")
        db.commit()

        resp = client.post("/auth/login", json={
            "email": user.email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client, db):
        seed_roles(db)
        db.commit()

        resp = client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "Password123",
        })
        assert resp.status_code == 401

    def test_register_creates_user(self, client, db):
        roles = seed_roles(db)
        db.commit()

        resp = client.post("/auth/register", json={
            "email": "newagent@test.com",
            "password": "Password123",
            "full_name": "New Agent",
            "role_name": "agent",
        })
        assert resp.status_code == 201
        assert resp.json()["email"] == "newagent@test.com"
        assert "hashed_password" not in resp.json()

    def test_register_duplicate_email_is_409(self, client, db):
        roles = seed_roles(db)
        user = seed_user(db, roles, email="dup@test.com")
        db.commit()

        resp = client.post("/auth/register", json={
            "email": "dup@test.com",
            "password": "Password123",
            "full_name": "Dup",
            "role_name": "agent",
        })
        assert resp.status_code == 409

    def test_me_returns_current_user(self, client, db):
        roles = seed_roles(db)
        user = seed_user(db, roles, "agent")
        db.commit()

        headers = auth_headers(client, user.email)
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email

    def test_me_requires_auth(self, client, db):
        resp = client.get("/auth/me")
        assert resp.status_code == 401  # no bearer token → 401 Unauthorized

    def test_short_password_rejected(self, client, db):
        seed_roles(db)
        db.commit()

        resp = client.post("/auth/register", json={
            "email": "short@test.com",
            "password": "abc",  # < 8 chars
            "full_name": "Short",
            "role_name": "agent",
        })
        assert resp.status_code == 422  # Pydantic validation error


# ─── Customer tests ───────────────────────────────────────────────────────────

class TestCustomerEndpoints:

    def _setup(self, db):
        roles = seed_roles(db)
        agent = seed_user(db, roles, "agent")
        supervisor = seed_user(db, roles, "supervisor")
        db.commit()
        return agent, supervisor

    def test_create_customer(self, client, db):
        agent, _ = self._setup(db)
        headers = auth_headers(client, agent.email)

        resp = client.post("/customers", json={
            "full_name": "Nomvula Dlamini",
            "email": "nomvula@test.com",
            "phone_number": "0821234567",
        }, headers=headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["full_name"] == "Nomvula Dlamini"
        assert body["phone_number"] == "0821234567"
        assert "id" in body

    def test_invalid_phone_rejected(self, client, db):
        agent, _ = self._setup(db)
        headers = auth_headers(client, agent.email)

        resp = client.post("/customers", json={
            "full_name": "Test",
            "email": "test@test.com",
            "phone_number": "12345",  # invalid
        }, headers=headers)
        assert resp.status_code == 422

    def test_duplicate_email_is_409(self, client, db):
        agent, _ = self._setup(db)
        headers = auth_headers(client, agent.email)

        payload = {
            "full_name": "Test", "email": "dup@test.com", "phone_number": "0821234567"
        }
        client.post("/customers", json=payload, headers=headers)
        resp = client.post("/customers", json=payload, headers=headers)
        assert resp.status_code == 409

    def test_get_customer(self, client, db):
        agent, _ = self._setup(db)
        headers = auth_headers(client, agent.email)

        created = client.post("/customers", json={
            "full_name": "Thabo Nkosi",
            "email": "thabo@test.com",
            "phone_number": "0731234567",
        }, headers=headers).json()

        resp = client.get(f"/customers/{created['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "thabo@test.com"

    def test_list_customers_paginated(self, client, db):
        agent, _ = self._setup(db)
        headers = auth_headers(client, agent.email)

        for i in range(5):
            client.post("/customers", json={
                "full_name": f"Customer {i}",
                "email": f"cust{i}@test.com",
                "phone_number": "0821234567",
            }, headers=headers)

        resp = client.get("/customers?page=1&page_size=3", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 3
        assert body["total"] == 5

    def test_search_customers(self, client, db):
        agent, _ = self._setup(db)
        headers = auth_headers(client, agent.email)

        client.post("/customers", json={
            "full_name": "Zanele Mokoena",
            "email": "zanele@test.com",
            "phone_number": "0821234567",
        }, headers=headers)

        resp = client.get("/customers?search=zanele", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_unauthenticated_request_rejected(self, client, db):
        resp = client.get("/customers")
        assert resp.status_code == 401


# ─── Ticket tests ─────────────────────────────────────────────────────────────

class TestTicketEndpoints:

    def _setup(self, client, db):
        roles = seed_roles(db)
        agent = seed_user(db, roles, "agent")
        supervisor = seed_user(db, roles, "supervisor")
        db.commit()

        # Create a customer to attach tickets to
        headers = auth_headers(client, agent.email)
        customer = client.post("/customers", json={
            "full_name": "Sipho Mokoena",
            "email": "sipho@test.com",
            "phone_number": "0821234567",
        }, headers=headers).json()

        return agent, supervisor, customer, headers

    def test_create_ticket(self, client, db):
        agent, _, customer, headers = self._setup(client, db)

        resp = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "DOUBLE_BILLING",
                "priority": "HIGH",
                "subject": "Charged twice in May",
                "description": "I was debited R149 twice on 15 May.",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "OPEN"
        assert body["sla_breached"] is False
        assert "sla_deadline" in body

    def test_ticket_status_transitions(self, client, db):
        agent, _, customer, headers = self._setup(client, db)

        ticket = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "UNAUTHORIZED_DEDUCTION",
                "priority": "MEDIUM",
                "subject": "Unexpected charge",
                "description": "R50 deducted without my consent.",
            },
            headers=headers,
        ).json()

        # OPEN → IN_PROGRESS
        resp = client.patch(
            f"/tickets/{ticket['id']}/status",
            json={"status": "IN_PROGRESS"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_PROGRESS"

    def test_invalid_status_transition_rejected(self, client, db):
        agent, _, customer, headers = self._setup(client, db)

        ticket = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "OTHER",
                "priority": "LOW",
                "subject": "Test",
                "description": "Test description here.",
            },
            headers=headers,
        ).json()

        # OPEN → RESOLVED is invalid (must go through IN_PROGRESS first)
        resp = client.patch(
            f"/tickets/{ticket['id']}/status",
            json={"status": "RESOLVED"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "Cannot transition" in resp.json()["detail"]

    def test_assign_ticket_requires_supervisor(self, client, db):
        agent, supervisor, customer, agent_headers = self._setup(client, db)
        db.commit()

        ticket = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "DOUBLE_BILLING",
                "priority": "HIGH",
                "subject": "Test ticket",
                "description": "Test description here.",
            },
            headers=agent_headers,
        ).json()

        # Agent cannot assign
        resp = client.patch(
            f"/tickets/{ticket['id']}/assign",
            json={"agent_id": str(agent.id)},
            headers=agent_headers,
        )
        assert resp.status_code == 403

        # Supervisor can assign
        supervisor_headers = auth_headers(client, supervisor.email)
        resp = client.patch(
            f"/tickets/{ticket['id']}/assign",
            json={"agent_id": str(agent.id)},
            headers=supervisor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_to"] == str(agent.id)

    def test_add_and_get_messages(self, client, db):
        agent, _, customer, headers = self._setup(client, db)

        ticket = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "DELAYED_REFUND",
                "priority": "MEDIUM",
                "subject": "Refund not received",
                "description": "Requested refund 30 days ago, still waiting.",
            },
            headers=headers,
        ).json()

        # Add a public message
        client.post(
            f"/tickets/{ticket['id']}/messages",
            json={"content": "We are investigating your case.", "is_internal": False},
            headers=headers,
        )
        # Add an internal note
        client.post(
            f"/tickets/{ticket['id']}/messages",
            json={"content": "Customer called in twice already.", "is_internal": True},
            headers=headers,
        )

        # Without internal: 1 message
        resp = client.get(f"/tickets/{ticket['id']}/messages", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # With internal: 2 messages
        resp = client.get(
            f"/tickets/{ticket['id']}/messages?include_internal=true",
            headers=headers,
        )
        assert len(resp.json()) == 2

    def test_escalate_ticket(self, client, db):
        agent, _, customer, headers = self._setup(client, db)

        ticket = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "INCORRECT_CHARGE",
                "priority": "HIGH",
                "subject": "Wrong amount charged",
                "description": "Charged R299 instead of R149.",
            },
            headers=headers,
        ).json()

        resp = client.post(
            f"/tickets/{ticket['id']}/escalate",
            json={"reason": "Customer threatening media escalation, requires senior attention."},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["escalation_type"] == "MANUAL"

    def test_empty_subject_rejected(self, client, db):
        agent, _, customer, headers = self._setup(client, db)

        resp = client.post(
            f"/tickets?customer_id={customer['id']}",
            json={
                "category": "OTHER",
                "priority": "LOW",
                "subject": "",  # invalid
                "description": "Some description.",
            },
            headers=headers,
        )
        assert resp.status_code == 422


# ─── Refund tests ─────────────────────────────────────────────────────────────

class TestRefundEndpoints:

    def _setup(self, client, db):
        roles = seed_roles(db)
        agent = seed_user(db, roles, "agent")
        supervisor = seed_user(db, roles, "supervisor")

        customer = Customer(
            full_name="Refund Test Customer",
            email="refund@test.com",
            phone_number="0821234567",
        )
        db.add(customer)
        db.flush()

        account = Account(
            customer_id=customer.id,
            account_number="ACC-REFUND-001",
            account_type="PREPAID",
        )
        db.add(account)
        db.flush()

        transaction = Transaction(
            account_id=account.id,
            transaction_type="DEBIT",
            amount=Decimal("149.00"),
            transacted_at=datetime.now(timezone.utc),
        )
        db.add(transaction)
        db.flush()

        ticket = client.post(
            f"/tickets?customer_id={customer.id}",
            json={
                "category": "DOUBLE_BILLING",
                "priority": "HIGH",
                "subject": "Double charged",
                "description": "Charged twice for the same transaction.",
            },
            headers=auth_headers(client, agent.email),
        ).json()

        db.commit()
        return agent, supervisor, ticket, transaction

    def test_create_refund(self, client, db):
        agent, _, ticket, transaction = self._setup(client, db)
        headers = auth_headers(client, agent.email)
        idempotency_key = str(uuid.uuid4())

        resp = client.post("/refunds", json={
            "ticket_id": ticket["id"],
            "transaction_id": str(transaction.id),
            "amount": "149.00",
            "idempotency_key": idempotency_key,
        }, headers=headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "PENDING"
        assert body["amount"] == "149.00"

    def test_idempotent_refund_request(self, client, db):
        """Same idempotency key twice returns same refund, no duplicate."""
        agent, _, ticket, transaction = self._setup(client, db)
        headers = auth_headers(client, agent.email)
        key = str(uuid.uuid4())

        payload = {
            "ticket_id": ticket["id"],
            "transaction_id": str(transaction.id),
            "amount": "149.00",
            "idempotency_key": key,
        }
        r1 = client.post("/refunds", json=payload, headers=headers)
        r2 = client.post("/refunds", json=payload, headers=headers)

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]  # same refund returned

    def test_agent_cannot_approve_refund(self, client, db):
        agent, _, ticket, transaction = self._setup(client, db)
        headers = auth_headers(client, agent.email)

        refund = client.post("/refunds", json={
            "ticket_id": ticket["id"],
            "transaction_id": str(transaction.id),
            "amount": "149.00",
            "idempotency_key": str(uuid.uuid4()),
        }, headers=headers).json()

        # Agent tries to approve — must be rejected
        resp = client.patch(
            f"/refunds/{refund['id']}/approve",
            json={"approved": True},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_supervisor_approves_refund(self, client, db):
        agent, supervisor, ticket, transaction = self._setup(client, db)
        agent_headers = auth_headers(client, agent.email)
        supervisor_headers = auth_headers(client, supervisor.email)

        refund = client.post("/refunds", json={
            "ticket_id": ticket["id"],
            "transaction_id": str(transaction.id),
            "amount": "149.00",
            "idempotency_key": str(uuid.uuid4()),
        }, headers=agent_headers).json()

        resp = client.patch(
            f"/refunds/{refund['id']}/approve",
            json={"approved": True},
            headers=supervisor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"

    def test_rejection_requires_reason(self, client, db):
        agent, supervisor, ticket, transaction = self._setup(client, db)
        agent_headers = auth_headers(client, agent.email)
        supervisor_headers = auth_headers(client, supervisor.email)

        refund = client.post("/refunds", json={
            "ticket_id": ticket["id"],
            "transaction_id": str(transaction.id),
            "amount": "149.00",
            "idempotency_key": str(uuid.uuid4()),
        }, headers=agent_headers).json()

        # Reject without reason → service raises 400
        resp = client.patch(
            f"/refunds/{refund['id']}/approve",
            json={"approved": False},  # no rejection_reason
            headers=supervisor_headers,
        )
        assert resp.status_code == 400

    def test_refund_exceeds_transaction_amount(self, client, db):
        agent, _, ticket, transaction = self._setup(client, db)
        headers = auth_headers(client, agent.email)

        resp = client.post("/refunds", json={
            "ticket_id": ticket["id"],
            "transaction_id": str(transaction.id),
            "amount": "9999.00",  # more than the R149 transaction
            "idempotency_key": str(uuid.uuid4()),
        }, headers=headers)
        assert resp.status_code == 400