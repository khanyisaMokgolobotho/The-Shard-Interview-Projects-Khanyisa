import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import Uuid

from app.db.session import Base
from app.models.base import TimestampMixin


class Refund(TimestampMixin, Base):
    __tablename__ = "refunds"

    # Table-level constraints (can reference multiple columns)
    __table_args__ = (
        # Prevents two refunds for the same transaction
        UniqueConstraint("transaction_id", name="uq_refund_transaction"),
    )

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
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("transactions.id"),
        nullable=False,
        # unique=True here is redundant with the table constraint above,
        # but makes the intent clear when reading this column definition
        unique=True,
    )
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        ForeignKey("users.id"),
    )

    # Client-generated unique key for safe retries (see module docstring)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # PENDING | APPROVED | REJECTED | PROCESSED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500))

    # Separate timestamps for the two-stage workflow
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="refunds")  # type: ignore[name-defined]  # noqa: F821
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="refund")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Refund {self.amount} ZAR [{self.status}]>"