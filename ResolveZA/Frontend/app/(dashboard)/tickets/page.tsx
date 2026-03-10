"use client";

import { type FormEvent, useEffect, useState } from "react";

import {
  addTicketMessage,
  getTicketWorkspace,
  listAllTickets,
  updateTicketStatus,
} from "@/lib/dashboard";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type { TicketPriority, TicketStatus, TicketSummary, TicketWorkspace } from "@/types";

import styles from "../page.module.css";

const statusOptions: TicketStatus[] = [
  "OPEN",
  "IN_PROGRESS",
  "ESCALATED",
  "RESOLVED",
  "CLOSED",
];

const priorityOptions: TicketPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function TicketsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<TicketWorkspace | null>(null);
  const [statusDraft, setStatusDraft] = useState<TicketStatus>("OPEN");
  const [statusNote, setStatusNote] = useState("");
  const [messageDraft, setMessageDraft] = useState("");
  const [internalOnly, setInternalOnly] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load ticket detail.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  useEffect(() => {
    void refreshTickets();
  }, [priorityFilter, statusFilter]);

  useEffect(() => {
    if (!selectedId) {
      setWorkspace(null);
      return;
    }

    const ticketId = selectedId;
    void refreshWorkspace(ticketId);
  }, [selectedId]);

  async function handleStatusSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId) {
      return;
    }

    try {
      await updateTicketStatus(selectedId, statusDraft, statusNote.trim() || undefined);
      setFeedback(`Ticket moved to ${formatStatusLabel(statusDraft)}.`);
      setStatusNote("");
      await Promise.all([refreshTickets(selectedId), refreshWorkspace(selectedId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update ticket status.");
    }
  }

  async function handleMessageSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId || !messageDraft.trim()) {
      return;
    }

    try {
      await addTicketMessage(selectedId, messageDraft.trim(), internalOnly);
      setFeedback("Ticket message added.");
      setMessageDraft("");
      setInternalOnly(false);
      await refreshWorkspace(selectedId);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to add a ticket message.");
    }
  }

  return (
    <section className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Ticket workflow</p>
        <h1 className={styles.heroTitle}>Queue management with live customer context</h1>
        <p className={styles.heroText}>
          Filter the support queue, inspect the selected ticket, and work its linked customer,
          account, transactions, refunds, and message history from one screen.
        </p>
      </section>

      <div className={styles.grid}>
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
              <button type="submit" className={styles.button} disabled={!workspace}>
                Update status
              </button>
            </form>
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
              <button type="submit" className={styles.button} disabled={!workspace}>
                Add message
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
        </section>
      </div>
    </section>
  );
}
