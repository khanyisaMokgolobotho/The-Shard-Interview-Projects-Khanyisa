"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useEffectEvent,
  useState,
  type ReactNode,
} from "react";

import { clearTokens, isAuthenticated } from "@/lib/auth";
import { getCurrentUserProfile } from "@/lib/dashboard";
import type { User } from "@/types";

type DashboardSessionValue = {
  currentUser: User | null;
  isLoadingUser: boolean;
  userError: string | null;
  refreshCurrentUser: () => Promise<void>;
  logout: () => void;
};

const DashboardSessionContext = createContext<DashboardSessionValue | null>(null);

type DashboardSessionProviderProps = {
  children: ReactNode;
};

export function DashboardSessionProvider({ children }: DashboardSessionProviderProps) {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoadingUser, setIsLoadingUser] = useState(true);
  const [userError, setUserError] = useState<string | null>(null);

  const loadCurrentUser = useEffectEvent(async () => {
    setIsLoadingUser(true);
    setUserError(null);

    try {
      const user = await getCurrentUserProfile();
      setCurrentUser(user);
    } catch (error) {
      setCurrentUser(null);
      setUserError(error instanceof Error ? error.message : "Failed to load your profile.");
    } finally {
      setIsLoadingUser(false);
    }
  });

  useEffect(() => {
    if (!isAuthenticated()) {
      setIsLoadingUser(false);
      startTransition(() => {
        router.replace("/login");
      });
      return;
    }

    void loadCurrentUser();
  }, [router]);

  async function refreshCurrentUser() {
    await loadCurrentUser();
  }

  function logout() {
    clearTokens();
    setCurrentUser(null);
    startTransition(() => {
      router.push("/login");
    });
  }

  return (
    <DashboardSessionContext.Provider
      value={{
        currentUser,
        isLoadingUser,
        userError,
        refreshCurrentUser,
        logout,
      }}
    >
      {children}
    </DashboardSessionContext.Provider>
  );
}

export function useDashboardSession() {
  const value = useContext(DashboardSessionContext);

  if (!value) {
    throw new Error("useDashboardSession must be used within a DashboardSessionProvider.");
  }

  return value;
}
