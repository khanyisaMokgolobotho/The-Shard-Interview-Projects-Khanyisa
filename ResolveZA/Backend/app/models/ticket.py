import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import Uuid

from app.db.session import Base
from app.models.base import TimestampMixin


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("customers.id"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("accounts.id"),
    )
    # The agent currently handling this ticket
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
    )

    # DOUBLE_BILLING | UNAUTHORIZED_DEDUCTION | FAILED_PURCHASE
    # DELAYED_REFUND | INCORRECT_CHARGE | OTHER
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # LOW | MEDIUM | HIGH | CRITICAL
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)

    # OPEN | IN_PROGRESS | ESCALATED | RESOLVED | CLOSED
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False, index=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # SLA tracking
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="tickets")  # type: ignore[name-defined]  # noqa: F821
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="tickets")  # type: ignore[name-defined]  # noqa: F821
    assigned_agent: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="assigned_tickets", foreign_keys=[assigned_to]
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="ticket", order_by="Message.created_at"
    )
    escalations: Mapped[list["Escalation"]] = relationship("Escalation", back_populates="ticket")
    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="ticket")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Ticket {self.id} [{self.status}] {self.category}>"


class Message(Base):
    """
    A single message in a ticket's conversation thread.
    No TimestampMixin — messages are immutable, only created_at matters.
    """
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("tickets.id"),
        nullable=False,
        index=True,
    )

    # CUSTOMER | AGENT | AI_ASSISTANT
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # NULL for AI_ASSISTANT messages (no user row)
    sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid())

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Internal agent notes — never shown to customers
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    from sqlalchemy import func
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.sender_type} on ticket {self.ticket_id}>"


class Escalation(Base):
    """
    Records each time a ticket was escalated.
    Stored separately so we can track escalation history —
    a ticket might be escalated, resolved at Tier-2, then re-opened.
    """
    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("tickets.id"),
        nullable=False,
    )
    escalated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
    )
    escalated_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)

    # MANUAL | AUTO_SLA | AUTO_AI
    escalation_type: Mapped[str] = mapped_column(String(20), default="MANUAL", nullable=False)

    from sqlalchemy import func
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="escalations")

    def __repr__(self) -> str:
        return f"<Escalation {self.escalation_type} on ticket {self.ticket_id}>"