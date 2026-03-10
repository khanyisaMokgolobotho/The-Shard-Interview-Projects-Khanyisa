export type UUID = string;
export type ISODateString = string;
export type CurrencyAmount = string;

export type ApiListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterStaffRequest = {
  email: string;
  password: string;
  full_name: string;
  role_name: UserRole;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type UserRole = "agent" | "supervisor" | "admin" | string;

export type User = {
  id: UUID;
  email: string;
  full_name: string;
  is_active: boolean;
  role_name: UserRole | null;
};

export type UserResponse = User;
export type StaffUser = User;

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

export type AccountType = "PREPAID" | "POSTPAID" | "FIBRE" | "BUSINESS";

export type AccountStatus = "ACTIVE" | "SUSPENDED" | "CLOSED";

export type TransactionType =
  | "DEBIT"
  | "CREDIT"
  | "REFUND"
  | "AIRTIME"
  | "DATA"
  | "SUBSCRIPTION";

export type CustomerSummary = {
  id: UUID;
  full_name: string;
  email: string;
};

export type Customer = CustomerSummary & {
  phone_number: string;
  is_active: boolean;
};

export type CustomerCreateRequest = {
  full_name: string;
  email: string;
  phone_number: string;
  id_number?: string;
};

export type CustomerUpdateRequest = {
  full_name?: string;
  email?: string;
  phone_number?: string;
};

export type Account = {
  id: UUID;
  account_number: string;
  account_type: AccountType | string;
  status: AccountStatus | string;
  balance: CurrencyAmount;
  currency: string;
};

export type Transaction = {
  id: UUID;
  transaction_type: TransactionType | string;
  amount: CurrencyAmount;
  status: string;
  transacted_at: ISODateString;
  description?: string | null;
};

export type PaginatedCustomers = ApiListResponse<CustomerSummary>;

export type TicketSummary = {
  id: UUID;
  category: TicketCategory | string;
  priority: TicketPriority | string;
  status: TicketStatus | string;
  subject: string;
  sla_deadline: ISODateString;
  sla_breached: boolean;
  created_at: ISODateString;
  customer_id: UUID;
  assigned_to?: UUID | null;
};

export type Ticket = TicketSummary & {
  description: string;
  resolved_at?: ISODateString | null;
  updated_at: ISODateString;
  account_id?: UUID | null;
};

export type TicketCreateRequest = {
  customer_id: UUID;
  category: TicketCategory | string;
  priority: TicketPriority | string;
  subject: string;
  description: string;
  account_id?: UUID | null;
};

export type TicketAssignRequest = {
  agent_id: UUID;
};

export type EscalateTicketRequest = {
  reason: string;
  escalate_to_agent_id?: UUID | null;
};

export type PaginatedTickets = ApiListResponse<TicketSummary>;

export type TicketMessageSender = "CUSTOMER" | "AGENT" | "AI_ASSISTANT" | string;

export type TicketMessage = {
  id: UUID;
  ticket_id: UUID;
  sender_type: TicketMessageSender;
  sender_id: UUID | null;
  content: string;
  is_internal: boolean;
  created_at: ISODateString;
};

export type RefundSummary = {
  id: UUID;
  ticket_id: UUID;
  amount: CurrencyAmount;
  status: RefundStatus | string;
  requested_at: ISODateString;
};

export type Refund = RefundSummary & {
  transaction_id: UUID;
  idempotency_key: string;
  rejection_reason?: string | null;
  approved_at?: ISODateString | null;
  processed_at?: ISODateString | null;
  created_at: ISODateString;
};

export type RefundCreateRequest = {
  ticket_id: UUID;
  transaction_id: UUID;
  amount: CurrencyAmount;
  idempotency_key: string;
};

export type RefundListItem = RefundSummary;

export type CustomerFilters = {
  search?: string;
  page?: number;
  pageSize?: number;
};

export type TicketFilters = {
  page?: number;
  pageSize?: number;
  status?: TicketStatus | string;
  priority?: TicketPriority | string;
  assignedTo?: UUID;
};

export type RefundFilters = {
  status?: RefundStatus | string;
  ticketId?: UUID;
};

export type OverviewTicket = {
  ticket: TicketSummary;
  customer: CustomerSummary | null;
  refundCount: number;
};

export type OverviewRefund = {
  refund: RefundSummary;
  ticket: TicketSummary | null;
  customer: CustomerSummary | null;
};

export type DashboardOverview = {
  currentUser: User;
  customers: CustomerSummary[];
  customerTotal: number;
  tickets: OverviewTicket[];
  refunds: OverviewRefund[];
  totals: {
    openTickets: number;
    escalatedTickets: number;
    pendingRefunds: number;
    pendingRefundAmount: number;
  };
};

export type CustomerWorkspace = {
  customer: Customer;
  accounts: Account[];
  transactions: Transaction[];
  tickets: TicketSummary[];
  refunds: RefundSummary[];
};

export type TicketWorkspace = {
  ticket: Ticket;
  customer: Customer | null;
  account: Account | null;
  messages: TicketMessage[];
  refunds: RefundSummary[];
  customerTransactions: Transaction[];
};

export type RefundWorkspace = {
  refund: Refund;
  ticket: Ticket | null;
  customer: Customer | null;
  account: Account | null;
  transaction: Transaction | null;
};
