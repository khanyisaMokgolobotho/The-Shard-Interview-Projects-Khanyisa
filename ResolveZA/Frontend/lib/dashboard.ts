import { api } from "@/lib/api";
import type {
  Account,
  ApiListResponse,
  Customer,
  CustomerCreateRequest,
  CustomerFilters,
  CustomerSummary,
  CustomerUpdateRequest,
  CustomerWorkspace,
  DashboardOverview,
  EscalateTicketRequest,
  OverviewRefund,
  OverviewTicket,
  PaginatedCustomers,
  PaginatedTickets,
  Refund,
  RefundCreateRequest,
  RefundFilters,
  RefundListItem,
  RefundSummary,
  RefundWorkspace,
  RegisterStaffRequest,
  StaffUser,
  Ticket,
  TicketAssignRequest,
  TicketCreateRequest,
  TicketFilters,
  TicketMessage,
  TicketSummary,
  TicketWorkspace,
  Transaction,
  User,
} from "@/types";

const DEFAULT_PAGE_SIZE = 24;
const MAX_PAGE_SIZE = 100;

function toQueryString(params: Record<string, string | number | boolean | undefined | null>) {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }

  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

function createIdMap<T extends { id: string }>(items: T[]) {
  return new Map(items.map((item) => [item.id, item]));
}

function groupRefundsByTicket(refunds: RefundSummary[]) {
  const refundMap = new Map<string, RefundSummary[]>();

  for (const refund of refunds) {
    const existing = refundMap.get(refund.ticket_id) ?? [];
    existing.push(refund);
    refundMap.set(refund.ticket_id, existing);
  }

  return refundMap;
}

async function collectAllPages<T>(
  fetchPage: (page: number, pageSize: number) => Promise<ApiListResponse<T>>,
  pageSize = MAX_PAGE_SIZE,
) {
  const firstPage = await fetchPage(1, pageSize);
  const totalPages = Math.ceil(firstPage.total / firstPage.page_size);

  if (totalPages <= 1) {
    return firstPage.items;
  }

  const remainingPages = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) => fetchPage(index + 2, pageSize)),
  );

  return [firstPage, ...remainingPages].flatMap((page) => page.items);
}

export function getCurrentUserProfile() {
  return api.get<User>("/auth/me");
}

export const getCurrentProfile = getCurrentUserProfile;

export function listStaffUsers() {
  return api.get<StaffUser[]>("/auth/users");
}

export function registerStaffUser(payload: RegisterStaffRequest) {
  return api.post<User>("/auth/register", payload);
}

export function listCustomers(filters: CustomerFilters = {}) {
  return api.get<PaginatedCustomers>(
    `/customers${toQueryString({
      search: filters.search,
      page: filters.page ?? 1,
      page_size: filters.pageSize ?? DEFAULT_PAGE_SIZE,
    })}`,
  );
}

export function listAllCustomers(search?: string) {
  return collectAllPages<CustomerSummary>((page, pageSize) =>
    listCustomers({ search, page, pageSize }),
  );
}

export function getCustomer(customerId: string) {
  return api.get<Customer>(`/customers/${customerId}`);
}

export function createCustomer(payload: CustomerCreateRequest) {
  return api.post<Customer>("/customers", payload);
}

export function updateCustomer(customerId: string, payload: CustomerUpdateRequest) {
  return api.patch<Customer>(`/customers/${customerId}`, payload);
}

export function getCustomerAccounts(customerId: string) {
  return api.get<Account[]>(`/customers/${customerId}/accounts`);
}

export function getCustomerTransactions(customerId: string) {
  return api.get<Transaction[]>(`/customers/${customerId}/transactions`);
}

export function listTickets(filters: TicketFilters = {}) {
  return api.get<PaginatedTickets>(
    `/tickets${toQueryString({
      page: filters.page ?? 1,
      page_size: filters.pageSize ?? DEFAULT_PAGE_SIZE,
      status: filters.status,
      priority: filters.priority,
      assigned_to: filters.assignedTo,
    })}`,
  );
}

export function listAllTickets(filters: Omit<TicketFilters, "page" | "pageSize"> = {}) {
  return collectAllPages<TicketSummary>((page, pageSize) =>
    listTickets({ ...filters, page, pageSize }),
  );
}

export function getTicket(ticketId: string) {
  return api.get<Ticket>(`/tickets/${ticketId}`);
}

export function createTicket(payload: TicketCreateRequest) {
  const { customer_id, ...ticketPayload } = payload;
  return api.post<Ticket>(
    `/tickets${toQueryString({ customer_id: customer_id })}`,
    ticketPayload,
  );
}

export function getTicketMessages(ticketId: string, includeInternal = true) {
  return api.get<TicketMessage[]>(
    `/tickets/${ticketId}/messages${toQueryString({ include_internal: includeInternal })}`,
  );
}

export function updateTicketStatus(ticketId: string, status: string, note?: string) {
  return api.patch<Ticket>(`/tickets/${ticketId}/status`, { status, note });
}

export function addTicketMessage(ticketId: string, content: string, isInternal: boolean) {
  return api.post<TicketMessage>(`/tickets/${ticketId}/messages`, {
    content,
    is_internal: isInternal,
  });
}

export function assignTicket(ticketId: string, payload: TicketAssignRequest) {
  return api.patch<Ticket>(`/tickets/${ticketId}/assign`, payload);
}

export function escalateTicket(ticketId: string, payload: EscalateTicketRequest) {
  return api.post(`/tickets/${ticketId}/escalate`, payload);
}

export function listRefunds(filters: RefundFilters = {}) {
  return api.get<RefundListItem[]>(
    `/refunds${toQueryString({ status: filters.status, ticket_id: filters.ticketId })}`,
  );
}

export function getRefund(refundId: string) {
  return api.get<Refund>(`/refunds/${refundId}`);
}

export function createRefund(payload: RefundCreateRequest) {
  return api.post<Refund>("/refunds", payload);
}

export function approveRefund(refundId: string, approved: boolean, rejectionReason?: string) {
  return api.patch<Refund>(`/refunds/${refundId}/approve`, {
    approved,
    rejection_reason: rejectionReason,
  });
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const [currentUser, customers, tickets, refunds] = await Promise.all([
    getCurrentUserProfile(),
    listAllCustomers(),
    listAllTickets(),
    listRefunds(),
  ]);

  const customerMap = createIdMap(customers);
  const ticketMap = createIdMap(tickets);
  const refundsByTicket = groupRefundsByTicket(refunds);

  const overviewTickets: OverviewTicket[] = tickets.map((ticket) => ({
    ticket,
    customer: customerMap.get(ticket.customer_id) ?? null,
    refundCount: refundsByTicket.get(ticket.id)?.length ?? 0,
  }));

  const overviewRefunds: OverviewRefund[] = refunds.map((refund) => {
    const ticket = ticketMap.get(refund.ticket_id) ?? null;
    return {
      refund,
      ticket,
      customer: ticket ? customerMap.get(ticket.customer_id) ?? null : null,
    };
  });

  const pendingRefundAmount = refunds
    .filter((refund) => refund.status === "PENDING")
    .reduce((total, refund) => total + Number(refund.amount), 0);

  return {
    currentUser,
    customers,
    customerTotal: customers.length,
    tickets: overviewTickets,
    refunds: overviewRefunds,
    totals: {
      openTickets: tickets.filter((ticket) => ticket.status === "OPEN").length,
      escalatedTickets: tickets.filter((ticket) => ticket.status === "ESCALATED").length,
      pendingRefunds: refunds.filter((refund) => refund.status === "PENDING").length,
      pendingRefundAmount,
    },
  };
}

export async function getCustomerWorkspace(customerId: string): Promise<CustomerWorkspace> {
  const [customer, accounts, transactions, tickets, refunds] = await Promise.all([
    getCustomer(customerId),
    getCustomerAccounts(customerId),
    getCustomerTransactions(customerId),
    listAllTickets(),
    listRefunds(),
  ]);

  const customerTickets = tickets.filter((ticket) => ticket.customer_id === customerId);
  const customerTicketIds = new Set(customerTickets.map((ticket) => ticket.id));
  const customerRefunds = refunds.filter((refund) => customerTicketIds.has(refund.ticket_id));

  return {
    customer,
    accounts,
    transactions,
    tickets: customerTickets,
    refunds: customerRefunds,
  };
}

export async function getTicketWorkspace(ticketId: string): Promise<TicketWorkspace> {
  const [ticket, messages, refunds] = await Promise.all([
    getTicket(ticketId),
    getTicketMessages(ticketId, true),
    listRefunds({ ticketId }),
  ]);

  const [customer, accounts, transactions] = await Promise.all([
    getCustomer(ticket.customer_id).catch(() => null),
    getCustomerAccounts(ticket.customer_id).catch(() => []),
    getCustomerTransactions(ticket.customer_id).catch(() => []),
  ]);

  const account = ticket.account_id
    ? accounts.find((customerAccount) => customerAccount.id === ticket.account_id) ?? null
    : null;

  return {
    ticket,
    customer,
    account,
    messages,
    refunds,
    customerTransactions: transactions,
  };
}

export async function getRefundWorkspace(refundId: string): Promise<RefundWorkspace> {
  const refund = await getRefund(refundId);
  const ticket = await getTicket(refund.ticket_id).catch(() => null);

  if (!ticket) {
    return {
      refund,
      ticket: null,
      customer: null,
      account: null,
      transaction: null,
    };
  }

  const [customer, accounts, transactions] = await Promise.all([
    getCustomer(ticket.customer_id).catch(() => null),
    getCustomerAccounts(ticket.customer_id).catch(() => []),
    getCustomerTransactions(ticket.customer_id).catch(() => []),
  ]);

  const account = ticket.account_id
    ? accounts.find((customerAccount) => customerAccount.id === ticket.account_id) ?? null
    : null;
  const transaction = transactions.find((item) => item.id === refund.transaction_id) ?? null;

  return {
    refund,
    ticket,
    customer,
    account,
    transaction,
  };
}
