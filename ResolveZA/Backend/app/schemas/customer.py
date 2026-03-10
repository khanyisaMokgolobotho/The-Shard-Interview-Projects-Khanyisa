from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
from decimal import Decimal
import uuid

from app.schemas.common import AccountType, AccountStatus


# ─── Customer Schemas ────────────────────────────────────────────────────────

class CustomerCreateRequest(BaseModel):
    """
    POST /customers — creates a new customer record.
    id_number is optional (foreign nationals may not have a SA ID).
    """
    full_name: str
    email: EmailStr
    phone_number: str
    id_number: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_sa_phone(cls, v: str) -> str:
        """
        Accepts: 0821234567 or +27821234567
        Rejects: spaces, dashes, letters, wrong length
        """
        cleaned = v.replace(" ", "").replace("-", "")
        if cleaned.startswith("+27"):
            cleaned = "0" + cleaned[3:]
        if not cleaned.startswith("0") or not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError(
                "Phone number must be a valid SA number: 0XXXXXXXXX or +27XXXXXXXXX"
            )
        return cleaned

    @field_validator("id_number")
    @classmethod
    def validate_sa_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.replace(" ", "")
        if not cleaned.isdigit() or len(cleaned) != 13:
            raise ValueError("SA ID number must be exactly 13 digits")
        return cleaned

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class CustomerUpdateRequest(BaseModel):
    """PATCH /customers/{id} — partial update, all fields optional."""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.replace(" ", "").replace("-", "")
        if cleaned.startswith("+27"):
            cleaned = "0" + cleaned[3:]
        if not cleaned.startswith("0") or not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError("Invalid SA phone number")
        return cleaned


class CustomerResponse(BaseModel):
    """
    Full customer detail — used in GET /customers/{id}.
    id_number intentionally excluded — access it via dedicated PII endpoint.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone_number: str
    is_active: bool


class CustomerListResponse(BaseModel):
    """
    Minimal customer view — used in list endpoints and ticket summaries.
    Less data = faster queries, less PII exposure.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


# ─── Account Schemas ─────────────────────────────────────────────────────────

class AccountResponse(BaseModel):
    """
    Account detail.
    balance is Decimal for exact precision — never float for money.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    account_number: str
    account_type: str
    status: str
    balance: Decimal
    currency: str


class AccountListResponse(BaseModel):
    """Minimal account summary for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_number: str
    account_type: str
    status: str
    balance: Decimal
    currency: str