import type { AccountTelemetry } from "./types";

const AUTH_KEY = "sajim_auth";
const ACCOUNT_KEY = "sajim_active_account";
const TOKEN_KEY = "sajim_supabase_token";

function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

export const storage = {
  isAuthenticated(): boolean {
    return safe(() => localStorage.getItem(AUTH_KEY) === "true", false);
  },

  setAuthenticated(value: boolean): void {
    safe(() => {
      if (value) localStorage.setItem(AUTH_KEY, "true");
      else localStorage.removeItem(AUTH_KEY);
    }, undefined);
  },

  getAccount(): Partial<AccountTelemetry> | null {
    return safe(() => {
      const raw = localStorage.getItem(ACCOUNT_KEY);
      return raw ? (JSON.parse(raw) as Partial<AccountTelemetry>) : null;
    }, null);
  },

  setAccount(account: AccountTelemetry): void {
    safe(() => localStorage.setItem(ACCOUNT_KEY, JSON.stringify(account)), undefined);
  },

  getToken(): string | null {
    return safe(() => localStorage.getItem(TOKEN_KEY), null);
  },

  setToken(token: string): void {
    safe(() => localStorage.setItem(TOKEN_KEY, token), undefined);
  },

  clear(): void {
    safe(() => {
      localStorage.removeItem(AUTH_KEY);
      localStorage.removeItem(ACCOUNT_KEY);
      localStorage.removeItem(TOKEN_KEY);
    }, undefined);
  },
};
