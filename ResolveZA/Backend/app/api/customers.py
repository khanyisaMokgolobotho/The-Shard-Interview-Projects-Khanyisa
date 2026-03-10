from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.customer import (
    CustomerCreateRequest, CustomerUpdateRequest,
    CustomerResponse, CustomerListResponse,
    AccountListResponse,
)
from app.schemas.transaction import TransactionListResponse
from app.services.customer_service import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", summary="List customers")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Paginated list of customers.
    Optional search filters by name or email (case-insensitive).
    """
    return customer_service.list_customers(db, page, page_size, search)


@router.post("", response_model=CustomerResponse, status_code=201, summary="Create customer")
def create_customer(
    request: CustomerCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """Create a new customer record. Validates SA phone number format."""
    return customer_service.create_customer(db, request)


@router.get("/{customer_id}", response_model=CustomerResponse, summary="Get customer")
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    return customer_service.get_customer(db, customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse, summary="Update customer")
def update_customer(
    customer_id: uuid.UUID,
    request: CustomerUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """Partial update — only send fields you want to change."""
    return customer_service.update_customer(db, customer_id, request)


@router.get(
    "/{customer_id}/accounts",
    response_model=list[AccountListResponse],
    summary="List customer accounts",
)
def get_customer_accounts(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """All service accounts (prepaid, postpaid, fibre) for a customer."""
    return customer_service.get_accounts(db, customer_id)


@router.get(
    "/{customer_id}/transactions",
    response_model=list[TransactionListResponse],
    summary="List customer transactions",
)
def get_customer_transactions(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    All transactions across all accounts belonging to this customer.
    Read-only — transactions are created by the billing system, not this API.
    """
    # Collect all account IDs for this customer, then fetch transactions
    accounts = customer_service.get_accounts(db, customer_id)
    if not accounts:
        return []

    account_ids = [a.id for a in accounts]
    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids))
        .order_by(Transaction.transacted_at.desc())
        .limit(200)
        .all()
    )
    return [TransactionListResponse.model_validate(t) for t in transactions]