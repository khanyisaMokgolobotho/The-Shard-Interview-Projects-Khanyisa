from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.customer import Customer, Account
from app.schemas.customer import (
    CustomerCreateRequest, CustomerUpdateRequest,
    CustomerResponse, CustomerListResponse,
    AccountResponse, AccountListResponse,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_PAGE_SIZE = 100


class CustomerService:

    def create_customer(
        self, db: Session, request: CustomerCreateRequest
    ) -> CustomerResponse:
        existing = db.query(Customer).filter(Customer.email == request.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A customer with this email already exists",
            )

        customer = Customer(
            full_name=request.full_name,
            email=request.email,
            phone_number=request.phone_number,
            id_number=request.id_number,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        logger.info("customer_created", customer_id=str(customer.id))
        return CustomerResponse.model_validate(customer)

    def get_customer(self, db: Session, customer_id) -> CustomerResponse:
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.is_active == True,
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return CustomerResponse.model_validate(customer)

    def list_customers(
        self, db: Session, page: int = 1, page_size: int = 20, search: str = None
    ) -> dict:
        page_size = min(page_size, MAX_PAGE_SIZE)
        query = db.query(Customer).filter(Customer.is_active == True)

        if search:
            term = f"%{search}%"
            query = query.filter(
                Customer.full_name.ilike(term) | Customer.email.ilike(term)
            )

        total = query.count()
        customers = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [CustomerListResponse.model_validate(c) for c in customers],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def update_customer(
        self, db: Session, customer_id, request: CustomerUpdateRequest
    ) -> CustomerResponse:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        if request.full_name:
            customer.full_name = request.full_name
        if request.phone_number:
            customer.phone_number = request.phone_number
        if request.email:
            # Check email uniqueness
            existing = db.query(Customer).filter(
                Customer.email == request.email,
                Customer.id != customer_id,
            ).first()
            if existing:
                raise HTTPException(status_code=409, detail="Email already in use")
            customer.email = request.email

        db.commit()
        db.refresh(customer)
        return CustomerResponse.model_validate(customer)

    def get_accounts(self, db: Session, customer_id) -> list[AccountListResponse]:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
        return [AccountListResponse.model_validate(a) for a in accounts]


customer_service = CustomerService()