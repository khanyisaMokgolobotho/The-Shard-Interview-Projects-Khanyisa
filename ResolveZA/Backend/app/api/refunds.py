from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User
from app.schemas.refund import (
    RefundCreateRequest, RefundApproveRequest,
    RefundResponse, RefundListItem,
)
from app.services.refund_service import refund_service

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.post("", response_model=RefundResponse, status_code=201, summary="Request a refund")
def create_refund(
    request: RefundCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    """
    Request a refund for a transaction on behalf of a customer.
    Include a client-generated idempotency_key to safely retry on network failure.
    """
    return refund_service.create_refund(db, request, current_user)


@router.get("", response_model=list[RefundListItem], summary="List refunds")
def list_refunds(
    ticket_id: Optional[uuid.UUID] = Query(None, description="Filter by ticket"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    return refund_service.list_refunds(db, ticket_id, status)


@router.get("/{refund_id}", response_model=RefundResponse, summary="Get refund detail")
def get_refund(
    refund_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "supervisor", "admin")),
):
    from fastapi import HTTPException
    from app.models.refund import Refund
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return RefundResponse.model_validate(refund)


@router.patch(
    "/{refund_id}/approve",
    response_model=RefundResponse,
    summary="Approve or reject a refund",
)
def approve_refund(
    refund_id: uuid.UUID,
    request: RefundApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("supervisor", "admin")),
):
    """
    Approve or reject a PENDING refund. Supervisor or admin only.
    Rejection requires a reason. Approved refunds queue for processing.
    """
    return refund_service.approve_refund(db, refund_id, request, current_user)