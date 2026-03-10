"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import styles from "./login.module.css";
import { api, ApiError } from "@/lib/api";
import { setTokens } from "@/lib/auth";
import type { LoginRequest, TokenResponse } from "@/types";

const initialForm: LoginRequest = {
  email: "",
  password: "",
};

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState<LoginRequest>(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const tokens = await api.post<TokenResponse>("/auth/login", form, {
        auth: false,
        retryOn401: false,
      });
      setTokens(tokens.access_token, tokens.refresh_token);
      router.push("/dashboard");
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        if (caughtError.status === 401) {
          setError("Incorrect email or password");
        } else if (caughtError.status === 429) {
          setError("Too many attempts. Wait a minute.");
        } else {
          setError("Unable to sign in right now. Please try again.");
        }
      } else {
        setError("Unable to sign in right now. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.heading}>Sign in</h2>
        <p className={styles.copy}>
          Use your staff account to access queues, ticket history, and refund workflows.
        </p>
      </div>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.field}>
          <span className={styles.label}>Email</span>
          <input
            className={styles.input}
            type="email"
            autoComplete="email"
            value={form.email}
            disabled={isSubmitting}
            onChange={(event) =>
              setForm((current) => ({ ...current, email: event.target.value }))
            }
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Password</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="current-password"
            value={form.password}
            disabled={isSubmitting}
            onChange={(event) =>
              setForm((current) => ({ ...current, password: event.target.value }))
            }
            required
          />
        </label>

        {error ? <p className={styles.error}>{error}</p> : null}

        <button className={styles.submitButton} type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <span className={styles.loading}>
              <span className={styles.spinner} aria-hidden="true" />
              Signing in...
            </span>
          ) : (
            "Sign in"
          )}
        </button>
      </form>
    </div>
  );
}
