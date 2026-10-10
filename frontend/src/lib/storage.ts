import type { AccountTelemetry } from "./types";

const ACCOUNT_KEY = "sajim_active_account";
const SESSION_KEY = "sajim_supabase_session";
// Legacy keys from older builds (boolean auth flag, bare access token).
const LEGACY_AUTH_KEY = "sajim_auth";
const LEGACY_TOKEN_KEY = "sajim_supabase_token";

/** Persisted Supabase session. `expires_at` is epoch seconds (Supabase convention). */
export interface StoredSession {
  access_token: string;
  refresh_token: string | null;
  expires_at: number | null;
}

function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

function isStoredSession(value: unknown): value is StoredSession {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.access_token === "string" &&
    v.access_token.length > 0 &&
    (v.refresh_token === null || typeof v.refresh_token === "string") &&
    (v.expires_at === null || typeof v.expires_at === "number")
  );
}

export const storage = {
  getAccount(): Partial<AccountTelemetry> | null {
    return safe(() => {
      const raw = localStorage.getItem(ACCOUNT_KEY);
      return raw ? (JSON.parse(raw) as Partial<AccountTelemetry>) : null;
    }, null);
  },

  setAccount(account: AccountTelemetry): void {
    safe(() => localStorage.setItem(ACCOUNT_KEY, JSON.stringify(account)), undefined);
  },

  getSession(): StoredSession | null {
    return safe(() => {
      const raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      const parsed: unknown = JSON.parse(raw);
      return isStoredSession(parsed) ? parsed : null;
    }, null);
  },

  setSession(session: StoredSession): void {
    safe(() => {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      localStorage.removeItem(LEGACY_TOKEN_KEY);
    }, undefined);
  },

  clearSession(): void {
    safe(() => {
      localStorage.removeItem(SESSION_KEY);
      localStorage.removeItem(LEGACY_TOKEN_KEY);
    }, undefined);
  },

  /** Current access token (may be expired — use session.getValidAccessToken for requests). */
  getToken(): string | null {
    return storage.getSession()?.access_token ?? null;
  },

  clear(): void {
    safe(() => {
      localStorage.removeItem(ACCOUNT_KEY);
      localStorage.removeItem(SESSION_KEY);
      localStorage.removeItem(LEGACY_AUTH_KEY);
      localStorage.removeItem(LEGACY_TOKEN_KEY);
    }, undefined);
  },
};
