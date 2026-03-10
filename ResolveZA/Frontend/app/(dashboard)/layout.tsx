"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { DashboardSessionProvider, useDashboardSession } from "@/lib/dashboard-session";
import { formatStatusLabel } from "@/lib/format";

import styles from "./layout.module.css";

type DashboardLayoutProps = {
  children: ReactNode;
};

const navItems = [
  {
    href: "/dashboard",
    label: "Overview",
    eyebrow: "Dashboard overview",
    description: "Track customer load, live ticket flow, and refund pressure from one place.",
  },
  {
    href: "/customers",
    label: "Customers",
    eyebrow: "Customer relationships",
    description: "Inspect customers alongside the accounts, transactions, tickets, and refunds tied to them.",
  },
  {
    href: "/tickets",
    label: "Tickets",
    eyebrow: "Ticket operations",
    description: "Work the support queue with status updates, messages, and linked customer context.",
  },
  {
    href: "/refunds",
    label: "Refund workflow",
    description: "Review refund decisions with the ticket, customer, and transaction relationship in view.",
  },
];

function DashboardShell({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const { currentUser, isLoadingUser, userError, logout } = useDashboardSession();

  const activeSection =
    navItems.find(
      (item) => pathname === item.href || (item.href !== "/" && pathname.startsWith(`${item.href}/`)),
    ) ?? navItems[0];

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandMark} aria-hidden="true">
            RZ
          </div>
          <div>
            <p className={styles.kicker}>ResolveZA</p>
            <h1 className={styles.brandTitle}>Operations Console</h1>
          </div>
        </div>

        <nav className={styles.nav}>
          {navItems.map((item) => {
            const isActive =
              pathname === item.href || (item.href !== "/" && pathname.startsWith(`${item.href}/`));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={isActive ? styles.navLinkActive : styles.navLink}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          <p className={styles.footerLabel}>Current user</p>
          <p className={styles.footerValue}>
            {isLoadingUser ? "Loading profile..." : currentUser?.full_name ?? "Profile unavailable"}
          </p>
          <p className={styles.footerMeta}>{currentUser?.email ?? "Backend user session required"}</p>
          <p className={styles.footerRole}>
            {currentUser?.role_name ? formatStatusLabel(currentUser.role_name) : "Role pending"}
          </p>
          {userError ? <p className={styles.footerError}>{userError}</p> : null}
        </div>
      </aside>

      <div className={styles.content}>
        <header className={styles.header}>
          <div className={styles.headerCopy}>
            <p className={styles.headerEyebrow}>{activeSection.eyebrow}</p>
            <h2 className={styles.headerTitle}>{activeSection.label}</h2>
            <p className={styles.headerText}>{activeSection.description}</p>
          </div>

          <div className={styles.headerActions}>
            <div className={styles.userCard}>
              <p className={styles.userLabel}>Signed in as</p>
              <p className={styles.userName}>
                {isLoadingUser ? "Loading profile..." : currentUser?.full_name ?? "Unknown user"}
              </p>
              <p className={styles.userMeta}>
                {currentUser?.email ?? "Session expired"}{" "}
                {currentUser?.role_name ? `| ${formatStatusLabel(currentUser.role_name)}` : ""}
              </p>
            </div>
            <button type="button" className={styles.logoutButton} onClick={logout}>
              Log out
            </button>
          </div>
        </header>

        <main className={styles.main}>{children}</main>
      </div>
    </div>
  );
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <DashboardSessionProvider>
      <DashboardShell>{children}</DashboardShell>
    </DashboardSessionProvider>
  );
}
