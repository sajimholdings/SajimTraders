import type { BackendAccount, ClientSignal } from "./types";
import { expireSession, getValidAccessToken, refreshSession } from "./session";

/**
 * `status` is the HTTP status (0 for network errors / aborted requests).
 * `aborted` is set when the caller cancelled the request via AbortSignal.
 */
export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status: number; aborted?: boolean };

function authHeaders(token: string | null, extra?: HeadersInit): HeadersInit {
  return {
    ...(extra || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

interface FastApiValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

/**
 * Extract a human-readable error from a backend error body. Handles FastAPI's
 * `{detail: "..."}` and `{detail: [{loc, msg}, ...]}` (422 validation) shapes
 * as well as `{error}` / `{message}`.
 */
export function extractErrorMessage(body: unknown, status: number): string {
  const fallback = `Request failed (${status})`;
  if (!body || typeof body !== "object") return fallback;
  const b = body as { error?: unknown; message?: unknown; detail?: unknown };
  if (typeof b.error === "string" && b.error) return b.error;
  if (typeof b.message === "string" && b.message) return b.message;
  const detail = b.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const parts = detail
      .map((item: FastApiValidationItem | string) => {
        if (typeof item === "string") return item;
        if (!item || typeof item.msg !== "string") return null;
        const field = Array.isArray(item.loc)
          ? item.loc.filter((p) => p !== "body" && p !== "query").join(".")
          : "";
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .filter((p): p is string => Boolean(p));
    if (parts.length > 0) return parts.join("; ");
  }
  if (detail && typeof detail === "object") {
    const d = detail as { error?: unknown; message?: unknown; msg?: unknown };
    for (const v of [d.error, d.message, d.msg]) {
      if (typeof v === "string" && v) return v;
    }
  }
  return fallback;
}

export interface StatusResponse {
  system_online?: boolean;
  pnl?: { combined_daily_net?: number };
  concurrency?: { total_open?: number };
}

export interface SignalsResponse {
  count: number;
  signals: ClientSignal[];
}

export interface ConnectResponse {
  success: boolean;
  account?: Partial<BackendAccount>;
  error?: string;
}

export interface ToggleAutopilotResponse {
  success: boolean;
  account_id?: string;
  autopilot_enabled?: boolean;
  error?: string;
}

export interface ExecuteResponse {
  success: boolean;
  status?: string;
  order_id?: string;
  ticket?: number;
  volume?: number;
  price?: number;
  error?: string;
}

export interface CloseTradeResponse {
  success: boolean;
  ticket?: number;
  closed_at?: number;
  error?: string;
}

export const SESSION_EXPIRED_MESSAGE = "Session expired, please sign in again.";

async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    let token = await getValidAccessToken();
    let res = await fetch(path, { ...init, headers: authHeaders(token, init?.headers) });

    // Access token rejected: refresh once and retry, otherwise expire the session.
    if (res.status === 401 && token) {
      const refreshed = await refreshSession();
      if (refreshed && refreshed.access_token !== token) {
        token = refreshed.access_token;
        res = await fetch(path, { ...init, headers: authHeaders(token, init?.headers) });
      }
      if (res.status === 401) {
        expireSession();
        return { ok: false, error: SESSION_EXPIRED_MESSAGE, status: 401 };
      }
    }

    const data: unknown = await res.json().catch(() => null);
    if (!res.ok) {
      return { ok: false, error: extractErrorMessage(data, res.status), status: res.status };
    }
    return { ok: true, data: (data ?? {}) as T };
  } catch (err) {
    if ((err as { name?: string } | null)?.name === "AbortError") {
      return { ok: false, error: "Request cancelled", status: 0, aborted: true };
    }
    return {
      ok: false,
      error: err instanceof Error ? err.message : "Network error",
      status: 0,
    };
  }
}

function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<ApiResult<T>> {
  return requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export const api = {
  getStatus: () => requestJson<StatusResponse>("/api/status"),

  getAccount: (accountId: string, signal?: AbortSignal) =>
    requestJson<BackendAccount>(
      `/api/client/account?account_id=${encodeURIComponent(accountId)}`,
      { signal }
    ),

  getAccounts: (signal?: AbortSignal) =>
    requestJson<{ accounts: BackendAccount[] }>("/api/client/accounts", { signal }),

  getSignals: (signal?: AbortSignal) =>
    requestJson<SignalsResponse>("/api/client/signals", { signal }),

  connect: (body: Record<string, unknown>) =>
    post<ConnectResponse>("/api/client/connect", body),

  toggleAutopilot: (accountId: string, enabled: boolean) =>
    post<ToggleAutopilotResponse>("/api/client/toggle-autopilot", {
      account_id: accountId,
      enabled,
    }),

  execute: (body: Record<string, unknown>) =>
    post<ExecuteResponse>("/api/client/execute", body),

  closeTrade: (ticket: number, accountId?: string, symbol?: string) =>
    post<CloseTradeResponse>("/api/client/close-trade", {
      ticket,
      account_id: accountId,
      symbol,
    }),
};
