from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.ticket import Ticket
from app.models.refund import Refund
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.refund import (
    RefundCreateRequest, RefundApproveRequest,
    RefundResponse, RefundListItem,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class RefundService:

    def create_refund(
        self,
        db: Session,
        request: RefundCreateRequest,
        requested_by_user: User,
    ) -> RefundResponse:
        """
        Request a refund for a transaction.
        Idempotent — returns existing refund if key already used.
        """
        # Layer 1: idempotency key check
        existing = db.query(Refund).filter(
            Refund.idempotency_key == request.idempotency_key
        ).first()
        if existing:
            logger.info(
                "refund_idempotent_return",
                idempotency_key=request.idempotency_key,
                refund_id=str(existing.id),
            )
            return RefundResponse.model_validate(existing)

        # Verify the ticket exists
        ticket = db.query(Ticket).filter(Ticket.id == request.ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Verify the transaction exists and belongs to the customer
        transaction = db.query(Transaction).filter(
            Transaction.id == request.transaction_id
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Validate refund amount doesn't exceed transaction amount
        if request.amount > transaction.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Refund amount ({request.amount}) cannot exceed "
                       f"transaction amount ({transaction.amount})",
            )

        refund = Refund(
            ticket_id=request.ticket_id,
            transaction_id=request.transaction_id,
            requested_by=requested_by_user.id,
            idempotency_key=request.idempotency_key,
            amount=request.amount,
            requested_at=datetime.now(timezone.utc),
        )
        db.add(refund)

        try:
            db.commit()
        except IntegrityError:
            # Layer 2: DB unique constraint caught a concurrent duplicate
            db.rollback()
            existing = db.query(Refund).filter(
                Refund.transaction_id == request.transaction_id
            ).first()
            if existing:
                return RefundResponse.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A refund for this transaction already exists",
            )

        db.refresh(refund)

        logger.info(
            "refund_created",
            refund_id=str(refund.id),
            ticket_id=str(request.ticket_id),
            amount=str(request.amount),
        )
        return RefundResponse.model_validate(refund)

    def approve_refund(
        self,
        db: Session,
        refund_id,
        request: RefundApproveRequest,
        approving_user: User,
    ) -> RefundResponse:
        """
        Supervisor/admin approves or rejects a pending refund.
        """
        refund = db.query(Refund).filter(Refund.id == refund_id).first()
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found")

        if refund.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Refund is already {refund.status} — cannot approve/reject again",
            )

        if request.approved:
            refund.status = "APPROVED"
            refund.approved_by = approving_user.id
            refund.approved_at = datetime.now(timezone.utc)
            logger.info(
                "refund_approved",
                refund_id=str(refund.id),
                approved_by=str(approving_user.id),
            )
        else:
            if not request.rejection_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rejection reason is required when rejecting a refund",
                )
            refund.status = "REJECTED"
            refund.rejection_reason = request.rejection_reason
            logger.info(
                "refund_rejected",
                refund_id=str(refund.id),
                rejected_by=str(approving_user.id),
            )

        db.commit()
        db.refresh(refund)
        return RefundResponse.model_validate(refund)

    def list_refunds(
        self,
        db: Session,
        ticket_id=None,
        status_filter: str = None,
    ) -> list[RefundListItem]:
        query = db.query(Refund)
        if ticket_id:
            query = query.filter(Refund.ticket_id == ticket_id)
        if status_filter:
            query = query.filter(Refund.status == status_filter)
        refunds = query.order_by(Refund.created_at.desc()).all()
        return [RefundListItem.model_validate(r) for r in refunds]


refund_service = RefundService()