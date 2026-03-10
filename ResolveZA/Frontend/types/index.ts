export type LoginRequest = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type UserResponse = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role_name: string | null;
};

export type TicketStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "ESCALATED"
  | "RESOLVED"
  | "CLOSED";

export type TicketPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type TicketCategory =
  | "DOUBLE_BILLING"
  | "UNAUTHORIZED_DEDUCTION"
  | "FAILED_PURCHASE"
  | "DELAYED_REFUND"
  | "INCORRECT_CHARGE"
  | "OTHER";

export type RefundStatus = "PENDING" | "APPROVED" | "REJECTED" | "PROCESSED";

export type Customer = {
  id: string;
  full_name: string;
  email: string;
  phone_number?: string;
  is_active?: boolean;
};

export type Ticket = {
  id: string;
  category: TicketCategory | string;
  priority: TicketPriority | string;
  status: TicketStatus | string;
  subject: string;
  description: string;
  sla_deadline: string;
  sla_breached: boolean;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  customer_id: string;
  account_id: string | null;
  assigned_to: string | null;
};

export type PaginatedTickets = {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
};

export type TicketMessage = {
  id: string;
  ticket_id: string;
  sender_type: string;
  sender_id: string | null;
  content: string;
  is_internal: boolean;
  created_at: string;
};

export type Refund = {
  id: string;
  ticket_id: string;
  transaction_id: string;
  idempotency_key: string;
  amount: string;
  status: RefundStatus | string;
  rejection_reason: string | null;
  requested_at: string;
  approved_at: string | null;
  processed_at: string | null;
  created_at: string;
};
