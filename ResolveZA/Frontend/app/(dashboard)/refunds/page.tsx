"use client";

import { type FormEvent, useEffect, useState } from "react";

import { approveRefund, getRefundWorkspace, listRefunds } from "@/lib/dashboard";
import { useDashboardSession } from "@/lib/dashboard-session";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type { RefundListItem, RefundStatus, RefundWorkspace } from "@/types";

import styles from "../page.module.css";

const statusOptions: RefundStatus[] = ["PENDING", "APPROVED", "REJECTED", "PROCESSED"];

export default function RefundsPage() {
  const { currentUser } = useDashboardSession();
  const [statusFilter, setStatusFilter] = useState("");
  const [refunds, setRefunds] = useState<RefundListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<RefundWorkspace | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canApprove =
    currentUser?.role_name === "admin" || currentUser?.role_name === "supervisor";

  async function refreshRefunds(nextSelectedId?: string | null) {
    try {
      setIsLoadingList(true);
      setError(null);

      const nextRefunds = await listRefunds({ status: statusFilter || undefined });
      setRefunds(nextRefunds);
      setSelectedId((currentSelectedId) => {
        const desiredId = nextSelectedId ?? currentSelectedId;
        if (desiredId && nextRefunds.some((refund) => refund.id === desiredId)) {
          return desiredId;
        }
        return nextRefunds[0]?.id ?? null;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load refunds.");
    } finally {
      setIsLoadingList(false);
    }
  }

  async function refreshWorkspace(refundId: string) {
    try {
      setIsLoadingDetail(true);
      setError(null);

      const nextWorkspace = await getRefundWorkspace(refundId);
      setWorkspace(nextWorkspace);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load refund detail.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  useEffect(() => {
    void refreshRefunds();
  }, [statusFilter]);

  useEffect(() => {
    if (!selectedId) {
      setWorkspace(null);
      return;
    }

    const refundId = selectedId;
    void refreshWorkspace(refundId);
  }, [selectedId]);

  async function handleApprove(approved: boolean) {
    if (!workspace || !canApprove) {
      return;
    }

    if (!approved && !rejectionReason.trim()) {
      setError("A rejection reason is required when rejecting a refund.");
      return;
    }

    try {
      await approveRefund(
        workspace.refund.id,
        approved,
        approved ? undefined : rejectionReason.trim(),
      );
      setFeedback(approved ? "Refund approved." : "Refund rejected.");
      setRejectionReason("");
      await Promise.all([refreshRefunds(workspace.refund.id), refreshWorkspace(workspace.refund.id)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update refund.");
    }
  }

  function handleReject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void handleApprove(false);
  }

  return (
    <section className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Refund workflow</p>
        <h1 className={styles.heroTitle}>Refund decisions with full dispute context</h1>
        <p className={styles.heroText}>
          Review refund records from the backend alongside the ticket, customer, account, and
          transaction data connected to each request.
        </p>
      </section>

      <div className={styles.grid}>
        <section className={styles.listCard}>
          <div className={styles.toolbar}>
            <div>
              <p className={styles.sectionEyebrow}>Queue</p>
              <h2 className={styles.cardTitle}>Refund requests</h2>
            </div>
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
          </div>

          {error ? <p className={styles.error}>{error}</p> : null}
          {feedback ? <p className={styles.success}>{feedback}</p> : null}

          <div className={styles.list}>
            {isLoadingList ? <p className={styles.emptyState}>Loading refund queue...</p> : null}
            {!isLoadingList && refunds.length === 0 ? (
              <p className={styles.emptyState}>No refunds matched the current filter.</p>
            ) : null}
            {refunds.map((refund) => (
              <button
                key={refund.id}
                type="button"
                onClick={() => setSelectedId(refund.id)}
                className={`${styles.listItemButton} ${
                  selectedId === refund.id ? styles.listItemActive : ""
                }`}
              >
                <p className={styles.listItemTitle}>{formatCurrency(refund.amount)}</p>
                <p className={styles.listItemMeta}>
                  {formatStatusLabel(refund.status)} | ticket {formatCompactId(refund.ticket_id)}
                </p>
              </button>
            ))}
          </div>
        </section>

        <section className={styles.detailStack}>
          <section className={styles.detailCard}>
            {!selectedId ? (
              <p className={styles.emptyState}>Select a refund to inspect its related records.</p>
            ) : isLoadingDetail ? (
              <p className={styles.emptyState}>Loading refund workspace...</p>
            ) : workspace ? (
              <div className={styles.detailStack}>
                <div className={styles.sectionHeader}>
                  <div>
                    <p className={styles.sectionEyebrow}>Refund detail</p>
                    <h2 className={styles.detailTitle}>Refund {formatCompactId(workspace.refund.id)}</h2>
                  </div>
                  <div className={styles.badgeRow}>
                    <span className={styles.badgeWarm}>
                      {formatStatusLabel(workspace.refund.status)}
                    </span>
                    <span className={styles.badge}>
                      {formatCurrency(workspace.refund.amount)}
                    </span>
                  </div>
                </div>

                <div className={styles.detailGrid}>
                  <div>
                    <p className={styles.metaLabel}>Requested</p>
                    <p className={styles.detailRow}>{formatDateTime(workspace.refund.requested_at)}</p>
                  </div>
                  <div>
                    <p className={styles.metaLabel}>Approved</p>
                    <p className={styles.detailRow}>{formatDateTime(workspace.refund.approved_at)}</p>
                  </div>
                  <div>
                    <p className={styles.metaLabel}>Processed</p>
                    <p className={styles.detailRow}>{formatDateTime(workspace.refund.processed_at)}</p>
                  </div>
                  <div>
                    <p className={styles.metaLabel}>Rejection reason</p>
                    <p className={styles.detailRow}>
                      {workspace.refund.rejection_reason ?? "No rejection recorded"}
                    </p>
                  </div>
                </div>

                <div className={styles.embeddedGrid}>
                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Ticket</p>
                      <h3 className={styles.cardTitle}>Source dispute</h3>
                    </div>
                    {workspace.ticket ? (
                      <div className={styles.contentStack}>
                        <p className={styles.listItemTitle}>{workspace.ticket.subject}</p>
                        <p className={styles.userFacingValue}>
                          {formatStatusLabel(workspace.ticket.status)} |{" "}
                          {formatStatusLabel(workspace.ticket.priority)}
                        </p>
                        <p className={styles.userFacingValue}>
                          SLA {formatDateTime(workspace.ticket.sla_deadline)}
                        </p>
                      </div>
                    ) : (
                      <p className={styles.emptyState}>The linked ticket could not be loaded.</p>
                    )}
                  </section>

                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Customer</p>
                      <h3 className={styles.cardTitle}>Customer record</h3>
                    </div>
                    {workspace.customer ? (
                      <div className={styles.contentStack}>
                        <p className={styles.listItemTitle}>{workspace.customer.full_name}</p>
                        <p className={styles.userFacingValue}>{workspace.customer.email}</p>
                        <p className={styles.userFacingValue}>{workspace.customer.phone_number}</p>
                      </div>
                    ) : (
                      <p className={styles.emptyState}>The linked customer could not be loaded.</p>
                    )}
                  </section>
                </div>

                <div className={styles.embeddedGrid}>
                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Transaction</p>
                      <h3 className={styles.cardTitle}>Refund source transaction</h3>
                    </div>
                    {workspace.transaction ? (
                      <div className={styles.contentStack}>
                        <p className={styles.listItemTitle}>
                          {formatStatusLabel(workspace.transaction.transaction_type)}
                        </p>
                        <p className={styles.userFacingValue}>
                          {formatCurrency(workspace.transaction.amount)} |{" "}
                          {formatStatusLabel(workspace.transaction.status)}
                        </p>
                        <p className={styles.userFacingValue}>
                          {formatDateTime(workspace.transaction.transacted_at)}
                        </p>
                        <p className={styles.userFacingValue}>
                          {workspace.transaction.description ?? "No transaction description"}
                        </p>
                      </div>
                    ) : (
                      <p className={styles.emptyState}>
                        The linked transaction is not exposed by the selected customer history.
                      </p>
                    )}
                  </section>

                  <section className={styles.embeddedPanel}>
                    <div>
                      <p className={styles.sectionEyebrow}>Account</p>
                      <h3 className={styles.cardTitle}>Service account context</h3>
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
                      <p className={styles.emptyState}>No account is linked to the source ticket.</p>
                    )}
                  </section>
                </div>
              </div>
            ) : (
              <p className={styles.emptyState}>Refund detail is unavailable.</p>
            )}
          </section>

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Approvals</p>
              <h2 className={styles.cardTitle}>Review decision</h2>
            </div>

            {!workspace ? (
              <p className={styles.emptyState}>Load a refund to review approval options.</p>
            ) : !canApprove ? (
              <p className={styles.emptyState}>
                Your role is {currentUser?.role_name ?? "unknown"}, so this queue is read-only.
              </p>
            ) : workspace.refund.status !== "PENDING" ? (
              <p className={styles.emptyState}>Only pending refunds can be approved or rejected.</p>
            ) : (
              <div className={styles.actions}>
                <button type="button" className={styles.button} onClick={() => void handleApprove(true)}>
                  Approve refund
                </button>

                <form className={styles.actions} onSubmit={handleReject}>
                  <textarea
                    className={styles.textarea}
                    value={rejectionReason}
                    onChange={(event) => setRejectionReason(event.target.value)}
                    placeholder="Required when rejecting a refund"
                  />
                  <button type="submit" className={styles.secondaryButton}>
                    Reject refund
                  </button>
                </form>
              </div>
            )}
          </section>
        </section>
      </div>
    </section>
  );
}
