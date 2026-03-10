import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Boolean, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import Uuid

from app.db.session import Base
from app.models.base import TimestampMixin


class Customer(TimestampMixin, Base):
    """
    A telecom subscriber. Stored separately from User (agents).

    Separation rationale:
      Customers authenticate differently (lighter flow, no RBAC roles).
      Mixing customers and staff in one table leads to complex permission logic.
    """
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # POPIA: SA ID number — encrypted at rest in production
    # Access to this field must be logged in audit_logs
    id_number: Mapped[Optional[str]] = mapped_column(String(20))

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)

    # Relationships
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="customer")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="customer")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Customer {self.email}>"


class Account(TimestampMixin, Base):
    """
    A single telecom service line belonging to a customer.

    account_type options: PREPAID | POSTPAID | FIBRE | BUSINESS
    status options:       ACTIVE | SUSPENDED | CLOSED

    balance is stored as DECIMAL(10,2) — never FLOAT for money.
    WHY: Floating point arithmetic has rounding errors.
         DECIMAL is exact. e.g. 0.1 + 0.2 = 0.3, not 0.30000000000000004.
    """
    __tablename__ = "accounts"

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
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)   # PREPAID | POSTPAID | FIBRE
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ZAR", nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Transaction", back_populates="account"
    )
    tickets: Mapped[list["Ticket"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Ticket", back_populates="account"
    )

    def __repr__(self) -> str:
        return f"<Account {self.account_number} ({self.account_type})>"