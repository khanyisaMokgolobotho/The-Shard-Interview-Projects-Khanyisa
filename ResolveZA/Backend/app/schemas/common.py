from enum import Enum


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketCategory(str, Enum):
    DOUBLE_BILLING = "DOUBLE_BILLING"
    UNAUTHORIZED_DEDUCTION = "UNAUTHORIZED_DEDUCTION"
    FAILED_PURCHASE = "FAILED_PURCHASE"
    DELAYED_REFUND = "DELAYED_REFUND"
    INCORRECT_CHARGE = "INCORRECT_CHARGE"
    OTHER = "OTHER"


class RefundStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSED = "PROCESSED"


class TransactionType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    REFUND = "REFUND"
    AIRTIME = "AIRTIME"
    DATA = "DATA"
    SUBSCRIPTION = "SUBSCRIPTION"


class AccountType(str, Enum):
    PREPAID = "PREPAID"
    POSTPAID = "POSTPAID"
    FIBRE = "FIBRE"
    BUSINESS = "BUSINESS"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class MessageSenderType(str, Enum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    AI_ASSISTANT = "AI_ASSISTANT"


class EscalationType(str, Enum):
    MANUAL = "MANUAL"
    AUTO_SLA = "AUTO_SLA"
    AUTO_AI = "AUTO_AI"


class UserRole(str, Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENT = "agent"
    CUSTOMER = "customer"