from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

from app.schemas.common import (
    TicketStatus, TicketPriority, TicketCategory,
    MessageSenderType, EscalationType
)
from app.schemas.customer import CustomerListResponse


# ─── Ticket Schemas ───────────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    """
    POST /tickets — customer or agent opens a new ticket.
    account_id is optional (customer may not know their account number).
    """
    category: TicketCategory
    priority: TicketPriority = TicketPriority.MEDIUM
    subject: str
    description: str
    account_id: Optional[uuid.UUID] = None

    @field_validator("subject")
    @classmethod
    def subject_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Subject cannot be empty")
        if len(v) > 500:
            raise ValueError("Subject must be 500 characters or fewer")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description cannot be empty")
        return v


class TicketStatusUpdate(BaseModel):
    """
    PATCH /tickets/{id}/status — agent moves a ticket through states.
    Not all transitions are valid — that's enforced in TicketService.
    """
    status: TicketStatus
    note: Optional[str] = None  # optional internal note on why status changed


class TicketAssignRequest(BaseModel):
    """PATCH /tickets/{id}/assign — supervisor assigns a ticket to an agent."""
    agent_id: uuid.UUID


class TicketResponse(BaseModel):
    """
    Full ticket detail — returned by GET /tickets/{id}.
    Includes nested customer summary (not full customer — that's a separate call).
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    priority: str
    status: str
    subject: str
    description: str
    sla_deadline: datetime
    sla_breached: bool
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    customer_id: uuid.UUID
    account_id: Optional[uuid.UUID]
    assigned_to: Optional[uuid.UUID]


class TicketListItem(BaseModel):
    """
    Minimal ticket view for GET /tickets list.
    Omits description (can be long) — agents click in for details.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    priority: str
    status: str
    subject: str
    sla_deadline: datetime
    sla_breached: bool
    created_at: datetime
    customer_id: uuid.UUID
    assigned_to: Optional[uuid.UUID]


class PaginatedTickets(BaseModel):
    """
    Paginated list response for GET /tickets.
    total allows the frontend to build pagination controls.
    """
    items: list[TicketListItem]
    total: int
    page: int
    page_size: int


# ─── Message Schemas ──────────────────────────────────────────────────────────

class MessageCreateRequest(BaseModel):
    """
    POST /tickets/{id}/messages — adds a message to a ticket's thread.

    is_internal is only respected when sent by AGENT or ADMIN roles.
    If a customer sends is_internal=True, the service ignores it.
    Role enforcement is in the service, not the schema.
    """
    content: str
    is_internal: bool = False

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message content cannot be empty")
        return v


class MessageResponse(BaseModel):
    """
    A single message in the ticket thread.
    sender_id is None for AI_ASSISTANT messages.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    sender_type: str
    sender_id: Optional[uuid.UUID]
    content: str
    is_internal: bool
    created_at: datetime


# ─── Escalation Schemas ───────────────────────────────────────────────────────

class EscalateRequest(BaseModel):
    """
    POST /tickets/{id}/escalate — move ticket to Tier-2 human support.
    reason is required — agents must document why they're escalating.
    """
    reason: str
    escalate_to_agent_id: Optional[uuid.UUID] = None  # specific agent, or auto-assign

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Escalation reason cannot be empty")
        if len(v) < 10:
            raise ValueError("Please provide a meaningful escalation reason (min 10 chars)")
        return v


class EscalationResponse(BaseModel):
    """Record of a ticket escalation event."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    escalated_by: Optional[uuid.UUID]
    escalated_to: Optional[uuid.UUID]
    reason: str
    escalation_type: str
    created_at: datetime