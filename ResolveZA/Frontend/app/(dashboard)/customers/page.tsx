"use client";

import { type FormEvent, useEffect, useState } from "react";

import {
  createCustomer,
  getCustomerWorkspace,
  listAllCustomers,
  updateCustomer,
} from "@/lib/dashboard";
import { formatCompactId, formatCurrency, formatDateTime, formatStatusLabel } from "@/lib/format";
import type { CustomerSummary, CustomerUpdateRequest, CustomerWorkspace } from "@/types";

import styles from "../page.module.css";

const initialCreateForm = {
  full_name: "",
  email: "",
  phone_number: "",
  id_number: "",
};

const initialUpdateForm: CustomerUpdateRequest = {
  full_name: "",
  email: "",
  phone_number: "",
};

export default function CustomersPage() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<CustomerWorkspace | null>(null);
  const [createForm, setCreateForm] = useState(initialCreateForm);
  const [updateForm, setUpdateForm] = useState<CustomerUpdateRequest>(initialUpdateForm);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshCustomers(nextSelectedId?: string | null, nextSearch = search) {
    try {
      setIsLoadingList(true);
      setError(null);

      const nextCustomers = await listAllCustomers(nextSearch || undefined);
      setCustomers(nextCustomers);
      setSelectedId((currentSelectedId) => {
        const desiredId = nextSelectedId ?? currentSelectedId;
        if (desiredId && nextCustomers.some((customer) => customer.id === desiredId)) {
          return desiredId;
        }
        return nextCustomers[0]?.id ?? null;
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load customers.");
    } finally {
      setIsLoadingList(false);
    }
  }

  async function refreshWorkspace(customerId: string) {
    try {
      setIsLoadingDetail(true);
      setError(null);

      const nextWorkspace = await getCustomerWorkspace(customerId);
      setWorkspace(nextWorkspace);
      setUpdateForm({
        full_name: nextWorkspace.customer.full_name,
        email: nextWorkspace.customer.email,
        phone_number: nextWorkspace.customer.phone_number,
      });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load customer detail.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  useEffect(() => {
    void refreshCustomers();
  }, [search]);

  useEffect(() => {
    if (!selectedId) {
      setWorkspace(null);
      setUpdateForm(initialUpdateForm);
      return;
    }

    void refreshWorkspace(selectedId);
  }, [selectedId]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    setSearch(query.trim());
  }

  async function handleCreateCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setIsCreating(true);
      setError(null);
      setFeedback(null);

      const customer = await createCustomer({
        full_name: createForm.full_name.trim(),
        email: createForm.email.trim(),
        phone_number: createForm.phone_number.trim(),
        id_number: createForm.id_number.trim() || undefined,
      });

      setCreateForm(initialCreateForm);
      setQuery("");
      setSearch("");
      setFeedback(`Created customer ${customer.full_name}.`);
      await refreshCustomers(customer.id, "");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to create customer.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleUpdateCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedId) {
      return;
    }

    try {
      setIsUpdating(true);
      setError(null);
      setFeedback(null);

      await updateCustomer(selectedId, {
        full_name: updateForm.full_name?.trim() || undefined,
        email: updateForm.email?.trim() || undefined,
        phone_number: updateForm.phone_number?.trim() || undefined,
      });

      setFeedback("Customer details updated.");
      await Promise.all([refreshCustomers(selectedId), refreshWorkspace(selectedId)]);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update customer.");
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <section className={styles.stack}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Customer data</p>
        <h1 className={styles.heroTitle}>Customers, accounts, transactions, and linked cases</h1>
        <p className={styles.heroText}>
          The customer workspace now supports both read and write workflows. Use it to register a
          customer, edit their primary contact detail, and inspect the accounts, transactions,
          tickets, and refunds that sit underneath support operations.
        </p>
      </section>

      <div className={styles.grid}>
        <div className={styles.detailStack}>
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
            {feedback ? <p className={styles.success}>{feedback}</p> : null}

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

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Create</p>
              <h2 className={styles.cardTitle}>Register a customer</h2>
            </div>

            <form className={styles.actions} onSubmit={handleCreateCustomer}>
              <div className={styles.detailGrid}>
                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Full name</span>
                  <input
                    className={styles.input}
                    value={createForm.full_name}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, full_name: event.target.value }))
                    }
                    placeholder="Nomsa Zulu"
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Email</span>
                  <input
                    className={styles.input}
                    type="email"
                    value={createForm.email}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, email: event.target.value }))
                    }
                    placeholder="nomsa@example.com"
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>Phone</span>
                  <input
                    className={styles.input}
                    value={createForm.phone_number}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, phone_number: event.target.value }))
                    }
                    placeholder="0821234567"
                    required
                  />
                </label>

                <label className={styles.actions}>
                  <span className={styles.metaLabel}>SA ID number</span>
                  <input
                    className={styles.input}
                    value={createForm.id_number}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, id_number: event.target.value }))
                    }
                    placeholder="Optional, 13 digits"
                  />
                </label>
              </div>

              <button type="submit" className={styles.button} disabled={isCreating}>
                {isCreating ? "Creating customer..." : "Create customer"}
              </button>
            </form>
          </section>
        </div>

        <div className={styles.detailStack}>
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

          <section className={styles.actionCard}>
            <div>
              <p className={styles.sectionEyebrow}>Edit</p>
              <h2 className={styles.cardTitle}>Update customer</h2>
            </div>

            {!workspace ? (
              <p className={styles.emptyState}>Select a customer to update their contact details.</p>
            ) : (
              <form className={styles.actions} onSubmit={handleUpdateCustomer}>
                <div className={styles.detailGrid}>
                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Full name</span>
                    <input
                      className={styles.input}
                      value={updateForm.full_name ?? ""}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, full_name: event.target.value }))
                      }
                      required
                    />
                  </label>

                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Email</span>
                    <input
                      className={styles.input}
                      type="email"
                      value={updateForm.email ?? ""}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, email: event.target.value }))
                      }
                      required
                    />
                  </label>

                  <label className={styles.actions}>
                    <span className={styles.metaLabel}>Phone</span>
                    <input
                      className={styles.input}
                      value={updateForm.phone_number ?? ""}
                      onChange={(event) =>
                        setUpdateForm((current) => ({
                          ...current,
                          phone_number: event.target.value,
                        }))
                      }
                      required
                    />
                  </label>
                </div>

                <button type="submit" className={styles.button} disabled={isUpdating}>
                  {isUpdating ? "Saving changes..." : "Save changes"}
                </button>
              </form>
            )}
          </section>
        </div>
      </div>
    </section>
  );
}
