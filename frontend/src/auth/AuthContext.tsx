import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  AuthSessionPayload,
  apiRequest,
  setInMemoryCsrfToken,
} from "../api/client";
import { useI18n } from "../i18n/I18nProvider";

interface AuthContextValue {
  sessionData: AuthSessionPayload | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<AuthSessionPayload>;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessionData, setSessionData] = useState<AuthSessionPayload | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const { setLocale } = useI18n();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const current = await apiRequest<AuthSessionPayload>("/auth/me");
        if (!cancelled) {
          setInMemoryCsrfToken(current.csrf_token);
          setSessionData(current);
          setLocale(current.user.preferred_locale);
        }
      } catch {
        if (!cancelled) {
          setInMemoryCsrfToken(null);
          setSessionData(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setLocale]);

  const login = useCallback(
    async (username: string, password: string): Promise<AuthSessionPayload> => {
      const payload = await apiRequest<AuthSessionPayload>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setInMemoryCsrfToken(payload.csrf_token);
      setSessionData(payload);
      setLocale(payload.user.preferred_locale);
      return payload;
    },
    [setLocale]
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiRequest<{ status: string }>("/auth/logout", { method: "POST" });
    } finally {
      setInMemoryCsrfToken(null);
      setSessionData(null);
    }
  }, []);

  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (!sessionData) return false;
      return sessionData.permissions.includes(permission);
    },
    [sessionData]
  );

  return (
    <AuthContext.Provider value={{ sessionData, isLoading, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
