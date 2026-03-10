"use client";

import { type FormEvent, useEffect, useState } from "react";

import { getCustomerWorkspace, listAllCustomers } from "@/lib/dashboard";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type { CustomerSummary, CustomerWorkspace } from "@/types";

import styles from "../page.module.css";

export default function CustomersPage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<CustomerWorkspace | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadCustomers() {
      try {
        setIsLoadingList(true);
        setError(null);

        const nextCustomers = await listAllCustomers(search || undefined);
        if (!active) {
          return;
        }

        setCustomers(nextCustomers);
        setSelectedId((currentSelectedId) => {
          if (currentSelectedId && nextCustomers.some((customer) => customer.id === currentSelectedId)) {
            return currentSelectedId;
          }
          return nextCustomers[0]?.id ?? null;
        });
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load customers.");
        }
      } finally {
        if (active) {
          setIsLoadingList(false);
        }
      }
    }

    void loadCustomers();

    return () => {
      active = false;
    };
  }, [search]);

  useEffect(() => {
    if (!selectedId) {
      setWorkspace(null);
      return;
    }

    let active = true;
    const customerId = selectedId;

    async function loadWorkspace() {
      try {
        setIsLoadingDetail(true);
        setError(null);

        const nextWorkspace = await getCustomerWorkspace(customerId);
        if (active) {
          setWorkspace(nextWorkspace);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load customer detail.");
        }
      } finally {
        if (active) {
          setIsLoadingDetail(false);
        }
      }
    }

    void loadWorkspace();

    return () => {
      active = false;
    };
  }, [selectedId]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(query.trim());
  }

  return (
    <section className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Customer data</p>
        <h1 className={styles.heroTitle}>Customers, accounts, transactions, and linked cases</h1>
        <p className={styles.heroText}>
          Select a customer to inspect the backend relationships that sit underneath support work:
          active accounts, billing transactions, tickets, and any related refunds.
        </p>
      </section>

      <div className={styles.grid}>
        <section className={styles.listCard}>
          <div className={styles.listHeader}>
            <div>
              <p className={styles.sectionEyebrow}>Directory</p>
              <h2 className={styles.cardTitle}>Customer list</h2>
            </div>
            <form className={styles.searchForm} onSubmit={handleSearch}>
              <input
                className={styles.input}
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by name or email"
              />
              <button type="submit" className={styles.button}>
                Search
              </button>
            </form>
          </div>

          {error ? <p className={styles.error}>{error}</p> : null}

          <div className={styles.list}>
            {isLoadingList ? <p className={styles.emptyState}>Loading customer records...</p> : null}
            {!isLoadingList && customers.length === 0 ? (
              <p className={styles.emptyState}>No customers matched the current search.</p>
            ) : null}
            {customers.map((customer) => (
              <button
                key={customer.id}
                type="button"
                onClick={() => setSelectedId(customer.id)}
                className={`${styles.listItemButton} ${
                  selectedId === customer.id ? styles.listItemActive : ""
                }`}
              >
                <p className={styles.listItemTitle}>{customer.full_name}</p>
                <p className={styles.listItemMeta}>{customer.email}</p>
              </button>
            ))}
          </div>
        </section>

        <section className={styles.detailCard}>
          {!selectedId ? (
            <p className={styles.emptyState}>Select a customer to inspect related backend records.</p>
          ) : isLoadingDetail ? (
            <p className={styles.emptyState}>Loading customer workspace...</p>
          ) : workspace ? (
            <div className={styles.detailStack}>
              <div className={styles.sectionHeader}>
                <div>
                  <p className={styles.sectionEyebrow}>Customer detail</p>
                  <h2 className={styles.detailTitle}>{workspace.customer.full_name}</h2>
                </div>
                <div className={styles.badgeRow}>
                  <span className={styles.badgeWarm}>
                    {workspace.customer.is_active ? "Active" : "Inactive"}
                  </span>
                  <span className={styles.badge}>{formatCompactId(workspace.customer.id)}</span>
                </div>
              </div>

              <div className={styles.detailGrid}>
                <div>
                  <p className={styles.metaLabel}>Email</p>
                  <p className={styles.detailRow}>{workspace.customer.email}</p>
                </div>
                <div>
                  <p className={styles.metaLabel}>Phone</p>
                  <p className={styles.detailRow}>{workspace.customer.phone_number}</p>
                </div>
              </div>

              <div className={styles.summaryStrip}>
                <article className={styles.summaryCard}>
                  <p className={styles.summaryLabel}>Accounts</p>
                  <p className={styles.summaryValue}>{workspace.accounts.length}</p>
                </article>
                <article className={styles.summaryCard}>
                  <p className={styles.summaryLabel}>Transactions</p>
                  <p className={styles.summaryValue}>{workspace.transactions.length}</p>
                </article>
                <article className={styles.summaryCard}>
                  <p className={styles.summaryLabel}>Tickets</p>
                  <p className={styles.summaryValue}>{workspace.tickets.length}</p>
                </article>
                <article className={styles.summaryCard}>
                  <p className={styles.summaryLabel}>Refunds</p>
                  <p className={styles.summaryValue}>{workspace.refunds.length}</p>
                </article>
              </div>

              <section className={styles.tableStack}>
                <div>
                  <p className={styles.sectionEyebrow}>Accounts</p>
                  <h3 className={styles.cardTitle}>Service accounts</h3>
                </div>

                {workspace.accounts.length === 0 ? (
                  <p className={styles.emptyState}>No accounts were returned for this customer.</p>
                ) : (
                  <div className={styles.tableWrapper}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Account</th>
                          <th>Type</th>
                          <th>Status</th>
                          <th>Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {workspace.accounts.map((account) => (
                          <tr key={account.id}>
                            <td>{account.account_number}</td>
                            <td>{formatStatusLabel(account.account_type)}</td>
                            <td>{formatStatusLabel(account.status)}</td>
                            <td>{formatCurrency(account.balance, account.currency)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <section className={styles.tableStack}>
                <div>
                  <p className={styles.sectionEyebrow}>Transactions</p>
                  <h3 className={styles.cardTitle}>Latest billing activity</h3>
                </div>

                {workspace.transactions.length === 0 ? (
                  <p className={styles.emptyState}>No transactions were returned for this customer.</p>
                ) : (
                  <div className={styles.tableWrapper}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Type</th>
                          <th>Status</th>
                          <th>Amount</th>
                          <th>When</th>
                        </tr>
                      </thead>
                      <tbody>
                        {workspace.transactions.slice(0, 10).map((transaction) => (
                          <tr key={transaction.id}>
                            <td>{formatStatusLabel(transaction.transaction_type)}</td>
                            <td>{formatStatusLabel(transaction.status)}</td>
                            <td>{formatCurrency(transaction.amount)}</td>
                            <td>{formatDateTime(transaction.transacted_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              <div className={styles.embeddedGrid}>
                <section className={styles.embeddedPanel}>
                  <div>
                    <p className={styles.sectionEyebrow}>Tickets</p>
                    <h3 className={styles.cardTitle}>Support cases</h3>
                  </div>

                  <div className={styles.list}>
                    {workspace.tickets.length === 0 ? (
                      <p className={styles.emptyState}>No tickets are linked to this customer.</p>
                    ) : (
                      workspace.tickets.map((ticket) => (
                        <article key={ticket.id} className={styles.messageCard}>
                          <p className={styles.listItemTitle}>{ticket.subject}</p>
                          <p className={styles.listItemMeta}>
                            {formatStatusLabel(ticket.status)} | {formatStatusLabel(ticket.priority)}
                          </p>
                          <div className={styles.badgeRow}>
                            <span className={styles.badge}>{formatStatusLabel(ticket.category)}</span>
                            <span className={styles.badgeWarm}>
                              Due {formatDateTime(ticket.sla_deadline)}
                            </span>
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                </section>

                <section className={styles.embeddedPanel}>
                  <div>
                    <p className={styles.sectionEyebrow}>Refunds</p>
                    <h3 className={styles.cardTitle}>Linked refund requests</h3>
                  </div>

                  <div className={styles.list}>
                    {workspace.refunds.length === 0 ? (
                      <p className={styles.emptyState}>No refunds are linked to this customer yet.</p>
                    ) : (
                      workspace.refunds.map((refund) => (
                        <article key={refund.id} className={styles.messageCard}>
                          <p className={styles.listItemTitle}>{formatCurrency(refund.amount)}</p>
                          <p className={styles.listItemMeta}>
                            Ticket {formatCompactId(refund.ticket_id)} |{" "}
                            {formatDateTime(refund.requested_at)}
                          </p>
                          <div className={styles.badgeRow}>
                            <span className={styles.badgeWarm}>{formatStatusLabel(refund.status)}</span>
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                </section>
              </div>
            </div>
          ) : (
            <p className={styles.emptyState}>Customer detail is unavailable.</p>
          )}
        </section>
      </div>
    </section>
  );
}
