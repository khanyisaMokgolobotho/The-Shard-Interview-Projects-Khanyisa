import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, func
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Uuid

from app.db.session import Base


class AuditLog(Base):
    """
    Immutable audit trail. Never update or delete rows.
    Uses BIGINT primary key for fast sequential inserts.
    """
    __tablename__ = "audit_logs"

    # BIGINT auto-increment — fast sequential inserts, simpler than UUID here
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)

    # NULL for system-initiated actions (Celery workers, AI assistant)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(),
        index=True,
    )

    # e.g. TICKET_CREATED | REFUND_APPROVED | CUSTOMER_VIEWED
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    # e.g. ticket | refund | customer | user
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # The UUID of the affected record (stored as string for flexibility)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Request metadata for security forensics
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))   # Supports IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))

    # JSON: {"before": {...}, "after": {...}} or {"context": {...}}
    extra_data: Mapped[Optional[str]] = mapped_column("metadata", Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.resource_type}:{self.resource_id}>"