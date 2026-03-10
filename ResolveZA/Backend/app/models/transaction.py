import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import Uuid

from app.db.session import Base
from app.models.base import TimestampMixin


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )

    # DEBIT | CREDIT | REFUND | AIRTIME | DATA | SUBSCRIPTION
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # DECIMAL not FLOAT — exact precision for money
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(500))

    # External reference from the telecom billing system
    # Used for deduplication and dispute matching
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # COMPLETED | FAILED | REVERSED
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED", nullable=False)

    # When the transaction actually occurred (may differ from created_at)
    transacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")  # type: ignore[name-defined]  # noqa: F821
    refund: Mapped[Optional["Refund"]] = relationship("Refund", back_populates="transaction")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type} {self.amount} {self.status}>"