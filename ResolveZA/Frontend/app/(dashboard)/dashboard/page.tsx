"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { getDashboardOverview, listStaffUsers, registerStaffUser } from "@/lib/dashboard";
import { useDashboardSession } from "@/lib/dashboard-session";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type { DashboardOverview, RegisterStaffRequest, StaffUser } from "@/types";

import styles from "../page.module.css";

const initialStaffForm: RegisterStaffRequest = {
  full_name: "",
  email: "",
  password: "",
  role_name: "agent",
};

export default function DashboardPage() {
  const { currentUser } = useDashboardSession();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [staffUsers, setStaffUsers] = useState<StaffUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingStaff, setIsLoadingStaff] = useState(true);
  const [isRegisteringStaff, setIsRegisteringStaff] = useState(false);
  const [staffForm, setStaffForm] = useState<RegisterStaffRequest>(initialStaffForm);
  const [error, setError] = useState<string | null>(null);
  const [staffError, setStaffError] = useState<string | null>(null);
  const [staffFeedback, setStaffFeedback] = useState<string | null>(null);

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

  useEffect(() => {
    let active = true;

    async function loadStaffUsers() {
      try {
        setIsLoadingStaff(true);
        setStaffError(null);

        const nextStaffUsers = await listStaffUsers();
        if (active) {
          setStaffUsers(nextStaffUsers);
        }
      } catch (loadError) {
        if (active) {
          setStaffError(loadError instanceof Error ? loadError.message : "Failed to load staff users.");
        }
      } finally {
        if (active) {
          setIsLoadingStaff(false);
        }
      }
    }

    void loadStaffUsers();

    return () => {
      active = false;
    };
  }, []);

  const displayUser = currentUser ?? overview?.currentUser ?? null;
  const canRegisterStaff = displayUser?.role_name === "admin";
  const tickets = overview?.tickets.slice(0, 6) ?? [];
  const refunds = overview?.refunds.slice(0, 6) ?? [];
  const customers = overview?.customers.slice(0, 6) ?? [];

  async function handleRegisterStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setIsRegisteringStaff(true);
      setStaffError(null);
      setStaffFeedback(null);

      const createdUser = await registerStaffUser({
        email: staffForm.email.trim(),
        password: staffForm.password,
        full_name: staffForm.full_name.trim(),
        role_name: staffForm.role_name,
      });

      setStaffForm(initialStaffForm);
      setStaffFeedback(`Created ${createdUser.full_name} as ${formatStatusLabel(createdUser.role_name ?? "agent")}.`);
      setStaffUsers((current) =>
        [...current, createdUser].sort((left, right) => left.full_name.localeCompare(right.full_name)),
      );
    } catch (submitError) {
      setStaffError(
        submitError instanceof Error ? submitError.message : "Failed to register the staff user.",
      );
    } finally {
      setIsRegisteringStaff(false);
    }
  }

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
              <p className={styles.sectionEyebrow}>Staff directory</p>
              <h2 className={styles.sectionTitle}>Active platform users</h2>
            </div>
          </div>

          {staffError ? <p className={styles.error}>{staffError}</p> : null}

          <div className={styles.list}>
            {isLoadingStaff ? <p className={styles.emptyState}>Loading staff directory...</p> : null}
            {!isLoadingStaff && staffUsers.length === 0 ? (
              <p className={styles.emptyState}>No active staff users were returned by the backend.</p>
            ) : null}
            {staffUsers.map((staffUser) => (
              <article key={staffUser.id} className={styles.messageCard}>
                <p className={styles.listItemTitle}>{staffUser.full_name}</p>
                <p className={styles.listItemMeta}>{staffUser.email}</p>
                <div className={styles.badgeRow}>
                  <span className={styles.badgeWarm}>
                    {formatStatusLabel(staffUser.role_name ?? "agent")}
                  </span>
                  <span className={styles.badge}>{formatCompactId(staffUser.id)}</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.sectionHeader}>
            <div>
              <p className={styles.sectionEyebrow}>Access management</p>
              <h2 className={styles.sectionTitle}>Register staff user</h2>
            </div>
          </div>

          {staffFeedback ? <p className={styles.success}>{staffFeedback}</p> : null}

          {!canRegisterStaff ? (
            <p className={styles.emptyState}>
              Only an admin account should create staff users from the frontend.
            </p>
          ) : (
            <form className={styles.actions} onSubmit={handleRegisterStaff}>
              <div className={styles.detailGrid}>
                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Full name</span>
                  <input
                    className={styles.input}
                    value={staffForm.full_name}
                    onChange={(event) =>
                      setStaffForm((current) => ({ ...current, full_name: event.target.value }))
                    }
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Email</span>
                  <input
                    className={styles.input}
                    type="email"
                    value={staffForm.email}
                    onChange={(event) =>
                      setStaffForm((current) => ({ ...current, email: event.target.value }))
                    }
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Password</span>
                  <input
                    className={styles.input}
                    type="password"
                    value={staffForm.password}
                    onChange={(event) =>
                      setStaffForm((current) => ({ ...current, password: event.target.value }))
                    }
                    minLength={8}
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Role</span>
                  <select
                    className={styles.select}
                    value={staffForm.role_name}
                    onChange={(event) =>
                      setStaffForm((current) => ({
                        ...current,
                        role_name: event.target.value as RegisterStaffRequest["role_name"],
                      }))
                    }
                  >
                    <option value="agent">Agent</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="admin">Admin</option>
                  </select>
                </label>
              </div>

              <button type="submit" className={styles.button} disabled={isRegisteringStaff}>
                {isRegisteringStaff ? "Creating staff user..." : "Create staff user"}
              </button>
            </form>
          )}
        </section>
      </div>

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
