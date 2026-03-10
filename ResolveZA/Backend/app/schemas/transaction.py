from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid

from app.schemas.common import TransactionType


class TransactionResponse(BaseModel):
    """
    Full transaction detail.
    Used in GET /customers/{id}/transactions and ticket context.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    transaction_type: str
    amount: Decimal
    description: Optional[str]
    reference_number: Optional[str]
    status: str
    transacted_at: datetime


class TransactionListResponse(BaseModel):
    """Minimal transaction view for list endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_type: str
    amount: Decimal
    status: str
    transacted_at: datetime
    description: Optional[str] = None