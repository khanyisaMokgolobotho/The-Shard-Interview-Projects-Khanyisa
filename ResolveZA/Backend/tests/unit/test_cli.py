import uuid
import sys
import pytest
from argparse import Namespace
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.session import Base
from app.models.user import Role, User
from app.core.security import hash_password
from app.cli import cmd_create_admin, cmd_seed, cmd_reset_db


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


def patched_session(session):
    """Context manager that patches SessionLocal to return the test session."""
    return patch("app.cli.SessionLocal", return_value=session)


# ─── create-admin tests ───────────────────────────────────────────────────────

class TestCreateAdmin:

    def test_creates_admin_user(self, db):
        args = Namespace(
            email="admin@test.com",
            name="Test Admin",
            password="SecurePass123!",
        )
        with patched_session(db):
            cmd_create_admin(args)

        user = db.query(User).filter(User.email == "admin@test.com").first()
        assert user is not None
        assert user.full_name == "Test Admin"

    def test_creates_admin_role_if_missing(self, db):
        """Should create the admin role if it doesn't exist yet."""
        args = Namespace(
            email="admin@test.com",
            name="Test Admin",
            password="SecurePass123!",
        )
        with patched_session(db):
            cmd_create_admin(args)

        role = db.query(Role).filter(Role.name == "admin").first()
        assert role is not None

    def test_rejects_duplicate_email(self, db):
        """Creating a second admin with the same email should exit with error."""
        # Create first admin
        role = Role(name="admin", description="Admin")
        db.add(role)
        db.flush()
        user = User(
            email="admin@test.com",
            full_name="Existing Admin",
            hashed_password=hash_password("Password123!"),
            role_id=role.id,
        )
        db.add(user)
        db.commit()

        args = Namespace(
            email="admin@test.com",
            name="Duplicate",
            password="SecurePass123!",
        )
        with patched_session(db):
            with pytest.raises(SystemExit) as exc_info:
                cmd_create_admin(args)
            assert exc_info.value.code == 1

    def test_rejects_short_password(self, db):
        args = Namespace(
            email="admin@test.com",
            name="Test Admin",
            password="short",
        )
        with patched_session(db):
            with pytest.raises(SystemExit) as exc_info:
                cmd_create_admin(args)
            assert exc_info.value.code == 1


# ─── seed tests ───────────────────────────────────────────────────────────────

class TestSeed:

    def test_seed_creates_roles(self, db):
        args = Namespace()
        with patched_session(db):
            cmd_seed(args)

        roles = db.query(Role).all()
        role_names = {r.name for r in roles}
        assert {"admin", "supervisor", "agent"} <= role_names

    def test_seed_creates_users(self, db):
        args = Namespace()
        with patched_session(db):
            cmd_seed(args)

        users = db.query(User).all()
        assert len(users) == 4

    def test_seed_creates_customers(self, db):
        from app.models.customer import Customer
        args = Namespace()
        with patched_session(db):
            cmd_seed(args)

        customers = db.query(Customer).all()
        assert len(customers) == 5

    def test_seed_creates_tickets(self, db):
        from app.models.ticket import Ticket
        args = Namespace()
        with patched_session(db):
            cmd_seed(args)

        tickets = db.query(Ticket).all()
        assert len(tickets) == 8

    def test_seed_is_idempotent(self, db):
        """Running seed twice should not duplicate data."""
        from app.models.customer import Customer
        args = Namespace()
        with patched_session(db):
            cmd_seed(args)
            cmd_seed(args)

        customers = db.query(Customer).all()
        assert len(customers) == 5  # not 10


# ─── reset-db tests ───────────────────────────────────────────────────────────

class TestResetDb:

    def test_blocked_in_production(self):
        args = Namespace(confirm=True, seed=False)
        with patch("app.cli.settings") as mock_settings:
            mock_settings.app_env = "production"
            with pytest.raises(SystemExit) as exc_info:
                cmd_reset_db(args)
            assert exc_info.value.code == 1

    def test_requires_confirm_flag(self):
        args = Namespace(confirm=False, seed=False)
        with patch("app.cli.settings") as mock_settings:
            mock_settings.app_env = "development"
            with pytest.raises(SystemExit) as exc_info:
                cmd_reset_db(args)
            assert exc_info.value.code == 1

    def test_resets_db_with_confirm(self):
        args = Namespace(confirm=True, seed=False)
        with patch("app.cli.settings") as mock_settings, \
             patch("app.cli.Base") as mock_base, \
             patch("app.cli.engine") as mock_engine:
            mock_settings.app_env = "development"
            cmd_reset_db(args)
            mock_base.metadata.drop_all.assert_called_once_with(mock_engine)
            mock_base.metadata.create_all.assert_called_once_with(mock_engine)