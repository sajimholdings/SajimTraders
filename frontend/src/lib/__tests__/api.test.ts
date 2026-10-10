import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, extractErrorMessage, SESSION_EXPIRED_MESSAGE } from "../api";
import { storage } from "../storage";
import { onSessionExpired } from "../session";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("extractErrorMessage", () => {
  it("reads FastAPI string detail", () => {
    expect(extractErrorMessage({ detail: "Account not found" }, 404)).toBe("Account not found");
  });

  it("reads FastAPI validation detail arrays", () => {
    const body = {
      detail: [
        { loc: ["body", "account_id"], msg: "field required", type: "missing" },
        { loc: ["query", "limit"], msg: "must be positive" },
      ],
    };
    expect(extractErrorMessage(body, 422)).toBe("account_id: field required; limit: must be positive");
  });

  it("prefers error / message fields", () => {
    expect(extractErrorMessage({ error: "boom", detail: "x" }, 500)).toBe("boom");
    expect(extractErrorMessage({ message: "nope" }, 400)).toBe("nope");
  });

  it("reads object detail", () => {
    expect(extractErrorMessage({ detail: { error: "bad broker" } }, 400)).toBe("bad broker");
  });

  it("falls back to the status code", () => {
    expect(extractErrorMessage(null, 503)).toBe("Request failed (503)");
    expect(extractErrorMessage({ detail: [] }, 500)).toBe("Request failed (500)");
  });
});

describe("api request handling", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns detail from a failed FastAPI response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(400, { detail: "Invalid account" }));
    vi.stubGlobal("fetch", fetchMock);
    const res = await api.getAccount("123");
    expect(res).toEqual({ ok: false, error: "Invalid account", status: 400 });
  });

  it("sends the bearer token and returns data", async () => {
    storage.setSession({ access_token: "tok", refresh_token: "ref", expires_at: null });
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { count: 0, signals: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const res = await api.getSignals();
    expect(res).toEqual({ ok: true, data: { count: 0, signals: [] } });
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok");
  });

  it("expires the session when 401 persists after a failed refresh", async () => {
    storage.setSession({ access_token: "old", refresh_token: "ref", expires_at: null });
    const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
      if (url.includes("grant_type=refresh_token")) return jsonResponse(400, { msg: "invalid" });
      return jsonResponse(401, { detail: "Not authenticated" });
    });
    vi.stubGlobal("fetch", fetchMock);
    const listener = vi.fn();
    const unsubscribe = onSessionExpired(listener);
    const res = await api.getSignals();
    unsubscribe();
    expect(res).toEqual({ ok: false, error: SESSION_EXPIRED_MESSAGE, status: 401 });
    expect(storage.getSession()).toBeNull();
    // Without Supabase env in tests the refresh short-circuits; either way the
    // session ends up expired and listeners are notified.
    expect(listener).toHaveBeenCalled();
  });

  it("reports network failures with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const res = await api.getStatus();
    expect(res).toEqual({ ok: false, error: "Failed to fetch", status: 0 });
  });

  it("flags aborted requests", async () => {
    const abortErr = Object.assign(new Error("aborted"), { name: "AbortError" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortErr));
    const res = await api.getSignals(new AbortController().signal);
    expect(res).toMatchObject({ ok: false, aborted: true });
  });
});

describe("api token refresh (Supabase configured)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("refreshes on 401 and retries once with the new token", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon");
    vi.resetModules();
    const { api: freshApi } = await import("../api");
    const { storage: freshStorage } = await import("../storage");
    localStorage.clear();
    freshStorage.setSession({ access_token: "old", refresh_token: "ref", expires_at: null });

    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("grant_type=refresh_token")) {
        return jsonResponse(200, { access_token: "new", refresh_token: "ref2", expires_in: 3600 });
      }
      const auth = (init?.headers as Record<string, string>).Authorization;
      return auth === "Bearer new"
        ? jsonResponse(200, { count: 1, signals: [] })
        : jsonResponse(401, { detail: "expired" });
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await freshApi.getSignals();
    expect(res).toEqual({ ok: true, data: { count: 1, signals: [] } });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(freshStorage.getSession()).toMatchObject({ access_token: "new", refresh_token: "ref2" });
  });

  it("refreshes proactively when the token is about to expire", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon");
    vi.resetModules();
    const { api: freshApi } = await import("../api");
    const { storage: freshStorage } = await import("../storage");
    localStorage.clear();
    freshStorage.setSession({
      access_token: "old",
      refresh_token: "ref",
      expires_at: Math.floor(Date.now() / 1000) + 10,
    });

    const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
      if (url.includes("grant_type=refresh_token")) {
        return jsonResponse(200, { access_token: "new", expires_in: 3600 });
      }
      return jsonResponse(200, { count: 0, signals: [] });
    });
    vi.stubGlobal("fetch", fetchMock);

    await freshApi.getSignals();
    const dataCall = fetchMock.mock.calls.find(([u]) => String(u).startsWith("/api/"));
    expect((dataCall?.[1]?.headers as Record<string, string>).Authorization).toBe("Bearer new");
    // Refresh token is kept when the response omits a new one.
    expect(freshStorage.getSession()?.refresh_token).toBe("ref");
  });
});
