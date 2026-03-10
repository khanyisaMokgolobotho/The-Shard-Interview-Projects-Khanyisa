"use client";

import { type FormEvent, useEffect, useState } from "react";

import {
  addTicketMessage,
  assignTicket,
  createRefund,
  createTicket,
  escalateTicket,
  getCustomerAccounts,
  getTicketWorkspace,
  listAllCustomers,
  listAllTickets,
  listStaffUsers,
  updateTicketStatus,
} from "@/lib/dashboard";
import { useDashboardSession } from "@/lib/dashboard-session";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type {
  Account,
  CustomerSummary,
  StaffUser,
  TicketCategory,
  TicketPriority,
  TicketStatus,
  TicketSummary,
  TicketWorkspace,
} from "@/types";

import styles from "../page.module.css";

const statusOptions: TicketStatus[] = [
  "OPEN",
  "IN_PROGRESS",
  "ESCALATED",
  "RESOLVED",
  "CLOSED",
];

const priorityOptions: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

const categoryOptions: TicketCategory[] = [
  "DOUBLE_BILLING",
  "UNAUTHORIZED_DEDUCTION",
  "FAILED_PURCHASE",
  "DELAYED_REFUND",
  "INCORRECT_CHARGE",
  "OTHER",
];

const initialTicketForm = {
  customer_id: "",
  account_id: "",
  category: "DOUBLE_BILLING" as TicketCategory,
  priority: "MEDIUM" as TicketPriority,
  subject: "",
  description: "",
};

export default function TicketsPage() {
  const { currentUser } = useDashboardSession();
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<StaffUser[]>([]);
  const [createTicketAccounts, setCreateTicketAccounts] = useState<Account[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<TicketWorkspace | null>(null);
  const [ticketForm, setTicketForm] = useState(initialTicketForm);
  const [statusDraft, setStatusDraft] = useState<TicketStatus>("OPEN");
  const [statusNote, setStatusNote] = useState("");
  const [messageDraft, setMessageDraft] = useState("");
  const [internalOnly, setInternalOnly] = useState(false);
  const [assignAgentId, setAssignAgentId] = useState("");
  const [escalateReason, setEscalateReason] = useState("");
  const [escalateToAgentId, setEscalateToAgentId] = useState("");
  const [refundTransactionId, setRefundTransactionId] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isLoadingSupportData, setIsLoadingSupportData] = useState(true);
  const [isCreatingTicket, setIsCreatingTicket] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isAssigningTicket, setIsAssigningTicket] = useState(false);
  const [isEscalatingTicket, setIsEscalatingTicket] = useState(false);
  const [isCreatingRefund, setIsCreatingRefund] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canAssign = currentUser?.role_name === "admin" || currentUser?.role_name === "supervisor";

  async function refreshTickets(nextSelectedId?: string | null) {
    try {
      setIsLoadingList(true);
      setError(null);

      const nextTickets = await listAllTickets({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      });

      setTickets(nextTickets);
      setSelectedId((currentSelectedId) => {
        const desiredId = nextSelectedId ?? currentSelectedId;
        if (desiredId && nextTickets.some((ticket) => ticket.id === desiredId)) {
          return desiredId;
        }
        return nextTickets[0]?.id ?? null;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load tickets.");
    } finally {
      setIsLoadingList(false);
    }
  }

  async function refreshWorkspace(ticketId: string) {
    try {
      setIsLoadingDetail(true);
      setError(null);

      const nextWorkspace = await getTicketWorkspace(ticketId);
      setWorkspace(nextWorkspace);
      setStatusDraft(nextWorkspace.ticket.status as TicketStatus);
      setAssignAgentId(nextWorkspace.ticket.assigned_to ?? "");
      setRefundTransactionId("");
      setRefundAmount("");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load ticket detail.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function refreshSupportData() {
    try {
      setIsLoadingSupportData(true);
      const [nextCustomers, nextStaffUsers] = await Promise.all([listAllCustomers(), listStaffUsers()]);
      setCustomers(nextCustomers);
      setAssignableUsers(
        nextStaffUsers.filter((user) => user.role_name === "agent" || user.role_name === "supervisor"),
      );
      setTicketForm((current) => {
        if (current.customer_id && nextCustomers.some((customer) => customer.id === current.customer_id)) {
          return current;
        }

        return {
          ...current,
          customer_id: nextCustomers[0]?.id ?? "",
          account_id: "",
        };
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load support data.");
    } finally {
      setIsLoadingSupportData(false);
    }
  }

  useEffect(() => {
    void refreshSupportData();
  }, []);

  useEffect(() => {
    void refreshTickets();
  }, [priorityFilter, statusFilter]);

  useEffect(() => {
    if (!selectedId) {
      setWorkspace(null);
      return;
    }

    void refreshWorkspace(selectedId);
  }, [selectedId]);

  useEffect(() => {
    if (!ticketForm.customer_id) {
      setCreateTicketAccounts([]);
      return;
    }

    let active = true;

    async function loadCreateAccounts() {
      try {
        const accounts = await getCustomerAccounts(ticketForm.customer_id);
        if (!active) {
          return;
        }

        setCreateTicketAccounts(accounts);
        setTicketForm((current) => {
          if (current.customer_id !== ticketForm.customer_id) {
            return current;
          }

          const hasSelectedAccount = current.account_id
            ? accounts.some((account) => account.id === current.account_id)
            : false;

          return {
            ...current,
            account_id: hasSelectedAccount ? current.account_id : "",
          };
        });
      } catch {
        if (active) {
          setCreateTicketAccounts([]);
        }
      }
    }

    void loadCreateAccounts();

    return () => {
      active = false;
    };
  }, [ticketForm.customer_id]);

  async function handleCreateTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!ticketForm.customer_id) {
      setError("Create a customer first before opening a ticket.");
      return;
    }

    try {
      setIsCreatingTicket(true);
      setError(null);
      setFeedback(null);

      const ticket = await createTicket({
        customer_id: ticketForm.customer_id,
        account_id: ticketForm.account_id || undefined,
        category: ticketForm.category,
        priority: ticketForm.priority,
        subject: ticketForm.subject.trim(),
        description: ticketForm.description.trim(),
      });

      setFeedback(`Ticket ${formatCompactId(ticket.id)} created.`);
      setTicketForm((current) => ({
        ...current,
        account_id: "",
        category: "DOUBLE_BILLING",
        priority: "MEDIUM",
        subject: "",
        description: "",
      }));
      await refreshTickets(ticket.id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to create ticket.");
    } finally {
      setIsCreatingTicket(false);
    }
  }

  async function handleStatusSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId) {
      return;
    }

    try {
      setIsUpdatingStatus(true);
      await updateTicketStatus(selectedId, statusDraft, statusNote.trim() || undefined);
      setFeedback(`Ticket moved to ${formatStatusLabel(statusDraft)}.`);
      setStatusNote("");
      await Promise.all([refreshTickets(selectedId), refreshWorkspace(selectedId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update ticket status.");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  async function handleMessageSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId || !messageDraft.trim()) {
      return;
    }

    try {
      setIsSendingMessage(true);
      await addTicketMessage(selectedId, messageDraft.trim(), internalOnly);
      setFeedback("Ticket message added.");
      setMessageDraft("");
      setInternalOnly(false);
      await refreshWorkspace(selectedId);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to add a ticket message.");
    } finally {
      setIsSendingMessage(false);
    }
  }

  async function handleAssignTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId || !assignAgentId) {
      return;
    }

    try {
      setIsAssigningTicket(true);
      await assignTicket(selectedId, { agent_id: assignAgentId });
      setFeedback("Ticket assignment updated.");
      await Promise.all([refreshTickets(selectedId), refreshWorkspace(selectedId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to assign the ticket.");
    } finally {
      setIsAssigningTicket(false);
    }
  }

  async function handleEscalateTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId) {
      return;
    }

    try {
      setIsEscalatingTicket(true);
      await escalateTicket(selectedId, {
        reason: escalateReason.trim(),
        escalate_to_agent_id: escalateToAgentId || undefined,
      });
      setFeedback("Ticket escalated.");
      setEscalateReason("");
      setEscalateToAgentId("");
      await Promise.all([refreshTickets(selectedId), refreshWorkspace(selectedId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to escalate the ticket.");
    } finally {
      setIsEscalatingTicket(false);
    }
  }

  async function handleCreateRefund(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!workspace || !refundTransactionId || !refundAmount.trim()) {
      return;
    }

    try {
      setIsCreatingRefund(true);
      await createRefund({
        ticket_id: workspace.ticket.id,
        transaction_id: refundTransactionId,
        amount: refundAmount.trim(),
        idempotency_key: globalThis.crypto?.randomUUID?.() ?? `refund-${Date.now()}`,
      });
      setFeedback("Refund request created.");
      setRefundTransactionId("");
      setRefundAmount("");
      await refreshWorkspace(workspace.ticket.id);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to request a refund.");
    } finally {
      setIsCreatingRefund(false);
    }
  }

  return (
    <section className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Ticket workflow</p>
        <h1 className={styles.heroTitle}>Queue management with full dispute operations</h1>
        <p className={styles.heroText}>
          The ticket console now covers the full backend workflow: open a ticket, assign it,
          escalate it, move it through the state machine, add thread messages, and request a refund
          against one of the customer&apos;s transactions.
        </p>
      </section>

      <div className={styles.grid}>
        <div className={styles.detailStack}>
          <section className={styles.listCard}>
            <div className={styles.toolbar}>
              <div>
                <p className={styles.sectionEyebrow}>Queue</p>
                <h2 className={styles.cardTitle}>Support tickets</h2>
              </div>
              <div className={styles.inlineForm}>
                <select
                  className={styles.select}
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                >
                  <option value="">All statuses</option>
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
                <select
                  className={styles.select}
                  value={priorityFilter}
                  onChange={(event) => setPriorityFilter(event.target.value)}
                >
                  <option value="">All priorities</option>
                  {priorityOptions.map((priority) => (
                    <option key={priority} value={priority}>
                      {priority}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {error ? <p className={styles.error}>{error}</p> : null}
            {feedback ? <p className={styles.success}>{feedback}</p> : null}

            <div className={styles.list}>
              {isLoadingList ? <p className={styles.emptyState}>Loading ticket queue...</p> : null}
              {!isLoadingList && tickets.length === 0 ? (
                <p className={styles.emptyState}>No tickets matched the selected filters.</p>
              ) : null}
              {tickets.map((ticket) => (
                <button
                  key={ticket.id}
                  type="button"
                  onClick={() => setSelectedId(ticket.id)}
                  className={`${styles.listItemButton} ${
                    selectedId === ticket.id ? styles.listItemActive : ""
                  }`}
                >
                  <p className={styles.listItemTitle}>{ticket.subject}</p>
                  <p className={styles.listItemMeta}>
                    {formatStatusLabel(ticket.status)} | {formatStatusLabel(ticket.priority)} | customer{" "}
                    {formatCompactId(ticket.customer_id)}
                  </p>
                </button>
              ))}
            </div>
          </section>

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Create</p>
              <h2 className={styles.cardTitle}>Open a ticket</h2>
            </div>

            {isLoadingSupportData ? (
              <p className={styles.emptyState}>Loading customers and staff context...</p>
            ) : customers.length === 0 ? (
              <p className={styles.emptyState}>Create a customer first before opening a ticket.</p>
            ) : (
              <form className={styles.actions} onSubmit={handleCreateTicket}>
                <div className={styles.detailGrid}>
                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Customer</span>
                    <select
                      className={styles.select}
                      value={ticketForm.customer_id}
                      onChange={(event) =>
                        setTicketForm((current) => ({
                          ...current,
                          customer_id: event.target.value,
                          account_id: "",
                        }))
                      }
                      required
                    >
                      <option value="" disabled>
                        Select customer
                      </option>
                      {customers.map((customer) => (
                        <option key={customer.id} value={customer.id}>
                          {customer.full_name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Account</span>
                    <select
                      className={styles.select}
                      value={ticketForm.account_id}
                      onChange={(event) =>
                        setTicketForm((current) => ({ ...current, account_id: event.target.value }))
                      }
                    >
                      <option value="">No linked account</option>
                      {createTicketAccounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.account_number}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Category</span>
                    <select
                      className={styles.select}
                      value={ticketForm.category}
                      onChange={(event) =>
                        setTicketForm((current) => ({
                          ...current,
                          category: event.target.value as TicketCategory,
                        }))
                      }
                    >
                      {categoryOptions.map((category) => (
                        <option key={category} value={category}>
                          {formatStatusLabel(category)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Priority</span>
                    <select
                      className={styles.select}
                      value={ticketForm.priority}
                      onChange={(event) =>
                        setTicketForm((current) => ({
                          ...current,
                          priority: event.target.value as TicketPriority,
                        }))
                      }
                    >
                      {priorityOptions.map((priority) => (
                        <option key={priority} value={priority}>
                          {priority}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Subject</span>
                  <input
                    className={styles.input}
                    value={ticketForm.subject}
                    onChange={(event) =>
                      setTicketForm((current) => ({ ...current, subject: event.target.value }))
                    }
                    placeholder="Charged twice for June data bundle"
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Description</span>
                  <textarea
                    className={styles.textarea}
                    value={ticketForm.description}
                    onChange={(event) =>
                      setTicketForm((current) => ({ ...current, description: event.target.value }))
                    }
                    placeholder="Describe the dispute and what the customer reported."
                    required
                  />
                </label>

                <button type="submit" className={styles.button} disabled={isCreatingTicket}>
                  {isCreatingTicket ? "Opening ticket..." : "Create ticket"}
                </button>
              </form>
            )}
          </section>
        </div>

        <section className={styles.detailStack}>
          <section className={styles.detailCard}>
            {!selectedId ? (
              <p className={styles.emptyState}>Select a ticket to inspect its relationships.</p>
            ) : isLoadingDetail ? (
              <p className={styles.emptyState}>Loading ticket workspace...</p>
            ) : workspace ? (
              <div className={styles.detailStack}>
                <div className={styles.sectionHeader}>
                  <div>
                    <p className={styles.sectionEyebrow}>Ticket detail</p>
                    <h2 className={styles.detailTitle}>{workspace.ticket.subject}</h2>
                  </div>
                  <div className={styles.badgeRow}>
                    <span className={styles.badgeWarm}>
                      {formatStatusLabel(workspace.ticket.status)}
                    </span>
                    <span className={styles.badge}>
                      {formatStatusLabel(workspace.ticket.priority)}
                    </span>
                    {workspace.ticket.sla_breached ? (
                      <span className={styles.badgeAlert}>SLA breached</span>
                    ) : null}
                  </div>
                </div>

                <p className={styles.sectionText}>{workspace.ticket.description}</p>

                <div className={styles.detailGrid}>
                  <div>
                    <p className={styles.metaLabel}>Category</p>
                    <p className={styles.detailRow}>{formatStatusLabel(workspace.ticket.category)}</p>
                  </div>
                  <div>
                    <p className={styles.metaLabel}>SLA deadline</p>
                    <p className={styles.detailRow}>{formatDateTime(workspace.ticket.sla_deadline)}</p>
                  </div>
                  <div>
                    <p className={styles.metaLabel}>Resolved at</p>
                    <p className={styles.detailRow}>{formatDateTime(workspace.ticket.resolved_at)}</p>
                  </div>
                  <div>
                    <p className={styles.metaLabel}>Assigned agent</p>
                    <p className={styles.detailRow}>
                      {workspace.ticket.assigned_to
                        ? formatCompactId(workspace.ticket.assigned_to)
                        : "Unassigned"}
                    </p>
                  </div>
                </div>
                <div className={styles.embeddedGrid}>
                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Customer</p>
                      <h3 className={styles.cardTitle}>Linked customer</h3>
                    </div>
                    {workspace.customer ? (
                      <div className={styles.contentStack}>
                        <p className={styles.listItemTitle}>{workspace.customer.full_name}</p>
                        <p className={styles.userFacingValue}>{workspace.customer.email}</p>
                        <p className={styles.userFacingValue}>{workspace.customer.phone_number}</p>
                      </div>
                    ) : (
                      <p className={styles.emptyState}>Customer detail could not be loaded.</p>
                    )}
                  </section>

                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Account</p>
                      <h3 className={styles.cardTitle}>Linked service account</h3>
                    </div>
                    {workspace.account ? (
                      <div className={styles.contentStack}>
                        <p className={styles.listItemTitle}>{workspace.account.account_number}</p>
                        <p className={styles.userFacingValue}>
                          {formatStatusLabel(workspace.account.account_type)} |{" "}
                          {formatStatusLabel(workspace.account.status)}
                        </p>
                        <p className={styles.userFacingValue}>
                          {formatCurrency(workspace.account.balance, workspace.account.currency)}
                        </p>
                      </div>
                    ) : (
                      <p className={styles.emptyState}>No account is linked to this ticket.</p>
                    )}
                  </section>
                </div>

                <div className={styles.embeddedGrid}>
                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Refunds</p>
                      <h3 className={styles.cardTitle}>Linked refund requests</h3>
                    </div>
                    <div className={styles.list}>
                      {workspace.refunds.length === 0 ? (
                        <p className={styles.emptyState}>No refunds are attached to this ticket.</p>
                      ) : (
                        workspace.refunds.map((refund) => (
                          <article key={refund.id} className={styles.messageCard}>
                            <p className={styles.listItemTitle}>{formatCurrency(refund.amount)}</p>
                            <p className={styles.listItemMeta}>
                              Requested {formatDateTime(refund.requested_at)}
                            </p>
                            <div className={styles.badgeRow}>
                              <span className={styles.badgeWarm}>
                                {formatStatusLabel(refund.status)}
                              </span>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                  </section>

                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Transactions</p>
                      <h3 className={styles.cardTitle}>Recent customer activity</h3>
                    </div>
                    <div className={styles.list}>
                      {workspace.customerTransactions.length === 0 ? (
                        <p className={styles.emptyState}>No customer transactions were returned.</p>
                      ) : (
                        workspace.customerTransactions.slice(0, 6).map((transaction) => (
                          <article key={transaction.id} className={styles.messageCard}>
                            <p className={styles.listItemTitle}>
                              {formatStatusLabel(transaction.transaction_type)}
                            </p>
                            <p className={styles.listItemMeta}>
                              {formatCurrency(transaction.amount)} |{" "}
                              {formatStatusLabel(transaction.status)}
                            </p>
                            <p className={styles.userFacingValue}>
                              {formatDateTime(transaction.transacted_at)}
                            </p>
                          </article>
                        ))
                      )}
                    </div>
                  </section>
                </div>
              </div>
            ) : (
              <p className={styles.emptyState}>Ticket detail is unavailable.</p>
            )}
          </section>

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Status</p>
              <h2 className={styles.cardTitle}>Move the ticket</h2>
            </div>
            <form className={styles.actions} onSubmit={handleStatusSubmit}>
              <select
                className={styles.select}
                value={statusDraft}
                onChange={(event) => setStatusDraft(event.target.value as TicketStatus)}
                disabled={!workspace}
              >
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
              <textarea
                className={styles.textarea}
                value={statusNote}
                onChange={(event) => setStatusNote(event.target.value)}
                placeholder="Optional internal note for this transition"
                disabled={!workspace}
              />
              <button type="submit" className={styles.button} disabled={!workspace || isUpdatingStatus}>
                {isUpdatingStatus ? "Updating status..." : "Update status"}
              </button>
            </form>
          </section>

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Assignment</p>
              <h2 className={styles.cardTitle}>Assign or escalate</h2>
            </div>

            {!workspace ? (
              <p className={styles.emptyState}>Load a ticket to manage assignment and escalation.</p>
            ) : (
              <div className={styles.actions}>
                {!canAssign ? (
                  <p className={styles.emptyState}>
                    Your role is {currentUser?.role_name ?? "unknown"}, so assignment remains read-only.
                  </p>
                ) : (
                  <form className={styles.actions} onSubmit={handleAssignTicket}>
                    <label className={styles.actions}>
                      <span className={styles.metaLabel}>Assign to agent</span>
                      <select
                        className={styles.select}
                        value={assignAgentId}
                        onChange={(event) => setAssignAgentId(event.target.value)}
                      >
                        <option value="" disabled>
                          Select an agent
                        </option>
                        {assignableUsers.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.full_name} ({formatStatusLabel(user.role_name ?? "agent")})
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      type="submit"
                      className={styles.button}
                      disabled={!assignAgentId || isAssigningTicket}
                    >
                      {isAssigningTicket ? "Assigning ticket..." : "Assign ticket"}
                    </button>
                  </form>
                )}

                <form className={styles.actions} onSubmit={handleEscalateTicket}>
                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Escalation reason</span>
                    <textarea
                      className={styles.textarea}
                      value={escalateReason}
                      onChange={(event) => setEscalateReason(event.target.value)}
                      placeholder="Explain why this needs Tier-2 attention."
                      required
                    />
                  </label>

                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Escalate to</span>
                    <select
                      className={styles.select}
                      value={escalateToAgentId}
                      onChange={(event) => setEscalateToAgentId(event.target.value)}
                    >
                      <option value="">Let supervisor queue it</option>
                      {assignableUsers.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.full_name} ({formatStatusLabel(user.role_name ?? "agent")})
                        </option>
                      ))}
                    </select>
                  </label>

                  <button type="submit" className={styles.secondaryButton} disabled={isEscalatingTicket}>
                    {isEscalatingTicket ? "Escalating ticket..." : "Escalate ticket"}
                  </button>
                </form>
              </div>
            )}
          </section>

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Messages</p>
              <h2 className={styles.cardTitle}>Ticket thread</h2>
            </div>

            <form className={styles.actions} onSubmit={handleMessageSubmit}>
              <textarea
                className={styles.textarea}
                value={messageDraft}
                onChange={(event) => setMessageDraft(event.target.value)}
                placeholder="Add a customer-facing update or an internal note"
                disabled={!workspace}
              />
              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={internalOnly}
                  onChange={(event) => setInternalOnly(event.target.checked)}
                  disabled={!workspace}
                />
                Internal note only
              </label>
              <button type="submit" className={styles.button} disabled={!workspace || isSendingMessage}>
                {isSendingMessage ? "Adding message..." : "Add message"}
              </button>
            </form>

            <div className={styles.messageList}>
              {!workspace ? (
                <p className={styles.emptyState}>Load a ticket to review its message thread.</p>
              ) : workspace.messages.length === 0 ? (
                <p className={styles.emptyState}>No messages are attached to this ticket yet.</p>
              ) : (
                workspace.messages.map((message) => (
                  <article key={message.id} className={styles.messageCard}>
                    <p className={styles.messageContent}>{message.content}</p>
                    <p className={styles.messageMeta}>
                      {formatStatusLabel(message.sender_type)} |{" "}
                      {message.is_internal ? "Internal note" : "Customer visible"} |{" "}
                      {formatDateTime(message.created_at)}
                    </p>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Refund request</p>
              <h2 className={styles.cardTitle}>Create refund from transaction</h2>
            </div>

            {!workspace ? (
              <p className={styles.emptyState}>Load a ticket to request a refund.</p>
            ) : workspace.customerTransactions.length === 0 ? (
              <p className={styles.emptyState}>
                Refunds require an existing billing transaction for this customer.
              </p>
            ) : (
              <form className={styles.actions} onSubmit={handleCreateRefund}>
                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Source transaction</span>
                  <select
                    className={styles.select}
                    value={refundTransactionId}
                    onChange={(event) => {
                      const nextTransactionId = event.target.value;
                      const selectedTransaction = workspace.customerTransactions.find(
                        (transaction) => transaction.id === nextTransactionId,
                      );

                      setRefundTransactionId(nextTransactionId);
                      setRefundAmount(selectedTransaction?.amount ?? "");
                    }}
                    required
                  >
                    <option value="" disabled>
                      Select transaction
                    </option>
                    {workspace.customerTransactions.map((transaction) => (
                      <option key={transaction.id} value={transaction.id}>
                        {formatStatusLabel(transaction.transaction_type)} |{" "}
                        {formatCurrency(transaction.amount)} |{" "}
                        {formatDateTime(transaction.transacted_at)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Refund amount</span>
                  <input
                    className={styles.input}
                    value={refundAmount}
                    onChange={(event) => setRefundAmount(event.target.value)}
                    placeholder="149.00"
                    required
                  />
                </label>

                <button type="submit" className={styles.button} disabled={isCreatingRefund}>
                  {isCreatingRefund ? "Requesting refund..." : "Create refund request"}
                </button>
              </form>
            )}
          </section>
        </section>
      </div>
    </section>
  );
}
