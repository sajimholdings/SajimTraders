import type { BackendAccount, ClientSignal } from "./types";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

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

async function requestJson<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const res = await fetch(path, init);
    const data = (await res.json().catch(() => null)) as
      | (T & { error?: string; message?: string })
      | null;
    if (!res.ok) {
      const error = data?.error || data?.message || `Request failed (${res.status})`;
      return { ok: false, error };
    }
    return { ok: true, data: (data ?? {}) as T };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

function post<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  return requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  getStatus: () => requestJson<StatusResponse>("/api/status"),

  getAccount: (accountId: string) =>
    requestJson<BackendAccount>(
      `/api/client/account?account_id=${encodeURIComponent(accountId)}`
    ),

  getSignals: () => requestJson<SignalsResponse>("/api/client/signals"),

  connect: (body: Record<string, unknown>) =>
    post<ConnectResponse>("/api/client/connect", body),

  toggleAutopilot: (accountId: string, enabled: boolean) =>
    post<ToggleAutopilotResponse>("/api/client/toggle-autopilot", {
      account_id: accountId,
      enabled,
    }),

  execute: (body: Record<string, unknown>) =>
    post<ExecuteResponse>("/api/client/execute", body),

  closeTrade: (ticket: number) =>
    post<CloseTradeResponse>("/api/client/close-trade", { ticket }),
};
