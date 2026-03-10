import type { ReactNode } from "react";

import styles from "./auth.module.css";

type RootLayoutProps = {
  children: ReactNode;
};

export default function AuthLayout({ children }: RootLayoutProps) {
  return (
    <main className={styles.shell}>
      <div className={styles.brandBlock}>
        <div className={styles.brandMark} aria-hidden="true">
          RZ
        </div>
        <div className={styles.brandText}>
          <p className={styles.kicker}>ResolveZA</p>
          <h1 className={styles.title}>Customer support with sharper triage.</h1>
          <p className={styles.subtitle}>
            Sign in to review disputes, monitor refunds, and keep escalations moving.
          </p>
        </div>
      </div>
      <section className={styles.card}>{children}</section>
    </main>
  );
}
