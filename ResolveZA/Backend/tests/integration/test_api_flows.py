import pytest
from fastapi.testclient import TestClient


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def login(client, email, password):
    """Log in and return the access token."""
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.json()}"
    return resp.json()["access_token"]


def auth(token):
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def seeded(client, db):
    """
    Seed roles and users for integration tests.
    Returns a dict of tokens keyed by role.
    """
    from app.models.user import Role, User
    from app.core.security import hash_password

    roles = {}
    for name in ("admin", "supervisor", "agent"):
        r = db.query(Role).filter(Role.name == name).first()
        if not r:
            r = Role(name=name, description=f"{name} role")
            db.add(r)
            db.flush()
        roles[name] = r

    users = {
        "admin":      ("admin@test.com",      "Admin@123!"),
        "supervisor": ("supervisor@test.com",  "Super@123!"),
        "agent":      ("agent@test.com",       "Agent@123!"),
    }

    for role_name, (email, password) in users.items():
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                full_name=f"Test {role_name.title()}",
                hashed_password=hash_password(password),
                role_id=roles[role_name].id,
                is_active=True,
            )
            db.add(u)
    db.commit()

    tokens = {
        role: login(client, email, password)
        for role, (email, password) in users.items()
    }
    return {"tokens": tokens, "users": users}


# ─── Auth flow ────────────────────────────────────────────────────────────────

class TestAuthFlow:

    def test_login_success(self, client, seeded):
        resp = client.post("/auth/login", json={
            "email": "admin@test.com",
            "password": "Admin@123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, seeded):
        resp = client.post("/auth/login", json={
            "email": "admin@test.com",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client, seeded):
        resp = client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "Password@123!",
        })
        assert resp.status_code == 401

    def test_get_me(self, client, seeded):
        token = seeded["tokens"]["agent"]
        resp = client.get("/auth/me", headers=auth(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "agent@test.com"

    def test_unauthenticated_request_rejected(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, client):
        resp = client.get("/auth/me", headers=auth("not.a.real.token"))
        assert resp.status_code == 401

    def test_refresh_token(self, client, seeded):
        # Login to get tokens
        resp = client.post("/auth/login", json={
            "email": "agent@test.com",
            "password": "Agent@123!",
        })
        refresh_token = resp.json()["refresh_token"]

        # Use refresh token to get new access token
        resp2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp2.status_code == 200
        assert "access_token" in resp2.json()


# ─── Customer flow ────────────────────────────────────────────────────────────

class TestCustomerFlow:

    def test_create_customer(self, client, seeded):
        token = seeded["tokens"]["agent"]
        resp = client.post("/customers", headers=auth(token), json={
            "full_name": "Nomsa Dlamini",
            "email": "nomsa@test.com",
            "phone_number": "0821234567",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["full_name"] == "Nomsa Dlamini"
        assert data["email"] == "nomsa@test.com"
        assert "id_number" not in data  # POPIA — excluded from response

    def test_get_customer(self, client, seeded):
        token = seeded["tokens"]["agent"]

        # Create first
        create_resp = client.post("/customers", headers=auth(token), json={
            "full_name": "Kagiso Sithole",
            "email": "kagiso@test.com",
            "phone_number": "0731234567",
        })
        customer_id = create_resp.json()["id"]

        # Then fetch
        resp = client.get(f"/customers/{customer_id}", headers=auth(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == customer_id

    def test_list_customers(self, client, seeded):
        token = seeded["tokens"]["agent"]

        # Create two customers
        for i in range(2):
            client.post("/customers", headers=auth(token), json={
                "full_name": f"Customer {i}",
                "email": f"customer{i}@test.com",
                "phone_number": "0821234567",
            })

        resp = client.get("/customers", headers=auth(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_update_customer(self, client, seeded):
        token = seeded["tokens"]["agent"]

        create_resp = client.post("/customers", headers=auth(token), json={
            "full_name": "Old Name",
            "email": "update@test.com",
            "phone_number": "0821234567",
        })
        customer_id = create_resp.json()["id"]

        resp = client.patch(f"/customers/{customer_id}", headers=auth(token), json={
            "full_name": "New Name",
        })
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "New Name"

    def test_unauthenticated_cannot_list_customers(self, client):
        resp = client.get("/customers")
        assert resp.status_code == 401


# ─── Ticket flow ──────────────────────────────────────────────────────────────

class TestTicketFlow:

    def _create_customer(self, client, token):
        resp = client.post("/customers", headers=auth(token), json={
            "full_name": "Test Customer",
            "email": f"tc_{id(self)}@test.com",
            "phone_number": "0821234567",
        })
        return resp.json()["id"]

    def test_create_ticket(self, client, seeded):
        token = seeded["tokens"]["agent"]
        customer_id = self._create_customer(client, token)

        resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(token),
            json={
                "category": "DOUBLE_BILLING",
                "priority": "HIGH",
                "subject": "Charged twice for data bundle",
                "description": "Customer was billed R149 twice on 1 June.",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "OPEN"
        assert data["subject"] == "Charged twice for data bundle"
        assert "sla_deadline" in data

    def test_get_ticket(self, client, seeded):
        token = seeded["tokens"]["agent"]
        customer_id = self._create_customer(client, token)

        create_resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(token),
            json={
                "category": "OTHER",
                "priority": "CRITICAL",
                "subject": "No signal",
                "description": "No signal for 2 days.",
            },
        )
        ticket_id = create_resp.json()["id"]

        resp = client.get(f"/tickets/{ticket_id}", headers=auth(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == ticket_id

    def test_list_tickets(self, client, seeded):
        token = seeded["tokens"]["agent"]
        resp = client.get("/tickets", headers=auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_update_ticket_status(self, client, seeded):
        token = seeded["tokens"]["agent"]
        customer_id = self._create_customer(client, token)

        create_resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(token),
            json={
                "category": "DOUBLE_BILLING",
                "priority": "MEDIUM",
                "subject": "Status change test",
                "description": "Testing status transition.",
            },
        )
        ticket_id = create_resp.json()["id"]

        resp = client.patch(
            f"/tickets/{ticket_id}/status",
            headers=auth(token),
            json={"status": "IN_PROGRESS"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "IN_PROGRESS"

    def test_assign_ticket(self, client, seeded, db):
        sup_token = seeded["tokens"]["supervisor"]
        agent_token = seeded["tokens"]["agent"]
        customer_id = self._create_customer(client, sup_token)

        create_resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(agent_token),
            json={
                "category": "DOUBLE_BILLING",
                "priority": "LOW",
                "subject": "Assign test",
                "description": "Testing assignment.",
            },
        )
        ticket_id = create_resp.json()["id"]

        # Get the agent's user ID
        from app.models.user import User
        agent = db.query(User).filter(User.email == "agent@test.com").first()

        resp = client.patch(
            f"/tickets/{ticket_id}/assign",
            headers=auth(sup_token),
            json={"agent_id": str(agent.id)},
        )
        assert resp.status_code == 200
        assert resp.json()["assigned_to"] == str(agent.id)

    def test_add_message_to_ticket(self, client, seeded):
        token = seeded["tokens"]["agent"]
        customer_id = self._create_customer(client, token)

        create_resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(token),
            json={
                "category": "DOUBLE_BILLING",
                "priority": "LOW",
                "subject": "Message test",
                "description": "Testing messages.",
            },
        )
        ticket_id = create_resp.json()["id"]

        resp = client.post(
            f"/tickets/{ticket_id}/messages",
            headers=auth(token),
            json={"content": "We are investigating this issue."},
        )
        assert resp.status_code == 201

        # Fetch messages
        msgs_resp = client.get(f"/tickets/{ticket_id}/messages", headers=auth(token))
        assert msgs_resp.status_code == 200
        assert len(msgs_resp.json()) == 1

    def test_escalate_ticket(self, client, seeded):
        token = seeded["tokens"]["agent"]
        customer_id = self._create_customer(client, token)

        create_resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(token),
            json={
                "category": "INCORRECT_CHARGE",
                "priority": "HIGH",
                "subject": "Escalation test",
                "description": "Customer demanding escalation.",
            },
        )
        ticket_id = create_resp.json()["id"]

        resp = client.post(
            f"/tickets/{ticket_id}/escalate",
            headers=auth(token),
            json={"reason": "Customer threatening media escalation"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "ticket_id" in data
        assert "reason" in data


# ─── RBAC enforcement ─────────────────────────────────────────────────────────

class TestRBAC:

    def _legacy_open_registration_reference(self, client, seeded):
        """
        Register is open — but only admins can assign roles like 'admin'.
        We verify the endpoint is reachable but an agent creating another
        user doesn't grant elevated access.
        This test verifies that a registered user gets default/agent role.
        """
        # Anyone can register — this is by design (open registration)
        resp = client.post("/auth/register", json={
            "email": "selfregister@test.com",
            "password": "Password@123!",
            "full_name": "Self Registered",
            "role_name": "agent",
        })
        # Register succeeds (open) — user gets agent role
        assert resp.status_code == 201

    def test_agent_cannot_register_users(self, client, seeded):
        token = seeded["tokens"]["agent"]
        resp = client.post("/auth/register", headers=auth(token), json={
            "email": "selfregister-blocked@test.com",
            "password": "Password@123!",
            "full_name": "Self Registered",
            "role_name": "agent",
        })
        assert resp.status_code == 403

    def test_admin_can_register_users(self, client, seeded):
        token = seeded["tokens"]["admin"]
        resp = client.post("/auth/register", headers=auth(token), json={
            "email": "newagent@test.com",
            "password": "Password@123!",
            "full_name": "New Agent",
            "role_name": "agent",
        })
        assert resp.status_code == 201

    def test_staff_can_list_users(self, client, seeded):
        token = seeded["tokens"]["agent"]
        resp = client.get("/auth/users", headers=auth(token))
        assert resp.status_code == 200
        emails = [user["email"] for user in resp.json()]
        assert "admin@test.com" in emails
        assert "agent@test.com" in emails

    def test_agent_cannot_assign_tickets(self, client, seeded, db):
        """Only supervisors and admins can assign tickets."""
        agent_token = seeded["tokens"]["agent"]

        # Create a customer and ticket
        cust_resp = client.post("/customers", headers=auth(agent_token), json={
            "full_name": "RBAC Customer",
            "email": "rbac@test.com",
            "phone_number": "0821234567",
        })
        customer_id = cust_resp.json()["id"]

        ticket_resp = client.post(
            f"/tickets?customer_id={customer_id}",
            headers=auth(agent_token),
            json={
                "category": "DOUBLE_BILLING",
                "priority": "LOW",
                "subject": "RBAC test ticket",
                "description": "Testing RBAC.",
            },
        )
        ticket_id = ticket_resp.json()["id"]

        from app.models.user import User
        agent = db.query(User).filter(User.email == "agent@test.com").first()

        resp = client.patch(
            f"/tickets/{ticket_id}/assign",
            headers=auth(agent_token),
            json={"agent_id": str(agent.id)},
        )
        assert resp.status_code == 403
