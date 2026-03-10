"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getDashboardOverview } from "@/lib/dashboard";
import { useDashboardSession } from "@/lib/dashboard-session";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type { DashboardOverview } from "@/types";

import styles from "../page.module.css";

export default function DashboardPage() {
  const { currentUser } = useDashboardSession();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      try {
        setIsLoading(true);
        setError(null);

        const nextOverview = await getDashboardOverview();
        if (active) {
          setOverview(nextOverview);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load the dashboard.");
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, []);

  const displayUser = currentUser ?? overview?.currentUser ?? null;
  const tickets = overview?.tickets.slice(0, 6) ?? [];
  const refunds = overview?.refunds.slice(0, 6) ?? [];
  const customers = overview?.customers.slice(0, 6) ?? [];

  return (
    <section className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Operations overview</p>
        <h1 className={styles.heroTitle}>
          {displayUser ? `Welcome back, ${displayUser.full_name}.` : "ResolveZA dashboard"}
        </h1>
        <p className={styles.heroText}>
          The frontend is now pulling live dashboard state from the backend for users, customers,
          tickets, refunds, accounts, and transactions. Use the shell to move between the linked
          support models.
        </p>
      </section>

      <div className={styles.metrics}>
        <article className={styles.metricCard}>
          <p className={styles.metricLabel}>Customers</p>
          <p className={styles.metricValue}>{isLoading ? "..." : overview?.customerTotal ?? 0}</p>
          <p className={styles.metricNote}>Active customer records indexed from the backend.</p>
        </article>
        <article className={styles.metricCard}>
          <p className={styles.metricLabel}>Open tickets</p>
          <p className={styles.metricValue}>{isLoading ? "..." : overview?.totals.openTickets ?? 0}</p>
          <p className={styles.metricNote}>Tickets still waiting for active work.</p>
        </article>
        <article className={styles.metricCard}>
          <p className={styles.metricLabel}>Escalated</p>
          <p className={styles.metricValue}>
            {isLoading ? "..." : overview?.totals.escalatedTickets ?? 0}
          </p>
          <p className={styles.metricNote}>Cases already pushed beyond the initial queue.</p>
        </article>
        <article className={styles.metricCard}>
          <p className={styles.metricLabel}>Pending refunds</p>
          <p className={styles.metricValue}>
            {isLoading ? "..." : overview?.totals.pendingRefunds ?? 0}
          </p>
          <p className={styles.metricNote}>Requests still waiting on a supervisor decision.</p>
        </article>
        <article className={styles.metricCard}>
          <p className={styles.metricLabel}>Refund exposure</p>
          <p className={styles.metricValue}>
            {isLoading
              ? "..."
              : formatCurrency(String(overview?.totals.pendingRefundAmount ?? 0), "ZAR")}
          </p>
          <p className={styles.metricNote}>Total value of refunds that are still pending.</p>
        </article>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.gridCompact}>
        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.sectionEyebrow}>Support queue</p>
              <h2 className={styles.sectionTitle}>Latest tickets</h2>
            </div>
            <Link href="/tickets" className={styles.secondaryButton}>
              Open tickets
            </Link>
          </div>

          <div className={styles.list}>
            {isLoading ? <p className={styles.emptyState}>Loading ticket activity...</p> : null}
            {!isLoading && tickets.length === 0 ? (
              <p className={styles.emptyState}>No tickets are available yet.</p>
            ) : null}
            {tickets.map(({ ticket, customer, refundCount }) => (
              <article key={ticket.id} className={styles.messageCard}>
                <p className={styles.listItemTitle}>{ticket.subject}</p>
                <p className={styles.listItemMeta}>
                  {customer?.full_name ?? `Customer ${formatCompactId(ticket.customer_id)}`} |{" "}
                  {formatStatusLabel(ticket.status)} | {formatStatusLabel(ticket.priority)}
                </p>
                <div className={styles.badgeRow}>
                  <span className={styles.badge}>{formatStatusLabel(ticket.category)}</span>
                  <span className={styles.badgeWarm}>Due {formatDateTime(ticket.sla_deadline)}</span>
                  <span className={styles.badgeSuccess}>{refundCount} linked refunds</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.sectionEyebrow}>Approval queue</p>
              <h2 className={styles.sectionTitle}>Latest refunds</h2>
            </div>
            <Link href="/refunds" className={styles.secondaryButton}>
              Open refunds
            </Link>
          </div>

          <div className={styles.list}>
            {isLoading ? <p className={styles.emptyState}>Loading refund activity...</p> : null}
            {!isLoading && refunds.length === 0 ? (
              <p className={styles.emptyState}>No refund records are available yet.</p>
            ) : null}
            {refunds.map(({ refund, ticket, customer }) => (
              <article key={refund.id} className={styles.messageCard}>
                <p className={styles.listItemTitle}>{formatCurrency(refund.amount)}</p>
                <p className={styles.listItemMeta}>
                  {customer?.full_name ?? "Customer unavailable"} |{" "}
                  {ticket?.subject ?? `Ticket ${formatCompactId(refund.ticket_id)}`}
                </p>
                <div className={styles.badgeRow}>
                  <span className={styles.badgeWarm}>{formatStatusLabel(refund.status)}</span>
                  <span className={styles.badge}>
                    Requested {formatDateTime(refund.requested_at)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className={styles.panel}>
        <div className={styles.sectionHeader}>
          <div>
            <p className={styles.sectionEyebrow}>Customer base</p>
            <h2 className={styles.sectionTitle}>Recent customer records</h2>
          </div>
          <Link href="/customers" className={styles.secondaryButton}>
            Open customers
          </Link>
        </div>

        <div className={styles.list}>
          {isLoading ? <p className={styles.emptyState}>Loading customers...</p> : null}
          {!isLoading && customers.length === 0 ? (
            <p className={styles.emptyState}>No customers have been returned by the backend yet.</p>
          ) : null}
          {customers.map((customer) => (
            <article key={customer.id} className={styles.messageCard}>
              <p className={styles.listItemTitle}>{customer.full_name}</p>
              <p className={styles.listItemMeta}>{customer.email}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
