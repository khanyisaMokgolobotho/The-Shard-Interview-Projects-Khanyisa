import uuid
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import Uuid
from typing import Optional
from datetime import datetime

from app.db.session import Base
from app.models.base import TimestampMixin


class Role(TimestampMixin, Base):
    """
    Defines permission groups for RBAC.
    Seeded with: admin, supervisor, agent, customer
    """
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    # Reverse relationship — Role.users gives all users with this role
    users: Mapped[list["User"]] = relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("roles.id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    assigned_tickets: Mapped[list["Ticket"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Ticket", back_populates="assigned_agent", foreign_keys="Ticket.assigned_to"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"