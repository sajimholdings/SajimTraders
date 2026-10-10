import { beforeEach, describe, expect, it } from "vitest";
import { storage } from "../storage";
import { isExpiringSoon, sessionFromHash, sessionFromPayload } from "../session";

describe("storage session helpers", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("round-trips a session", () => {
    const session = { access_token: "a", refresh_token: "r", expires_at: 1000 };
    storage.setSession(session);
    expect(storage.getSession()).toEqual(session);
    expect(storage.getToken()).toBe("a");
  });

  it("ignores malformed stored sessions", () => {
    localStorage.setItem("sajim_supabase_session", "{not json");
    expect(storage.getSession()).toBeNull();
    localStorage.setItem("sajim_supabase_session", JSON.stringify({ access_token: "" }));
    expect(storage.getSession()).toBeNull();
  });

  it("clear() removes session, account and legacy keys", () => {
    localStorage.setItem("sajim_auth", "true");
    localStorage.setItem("sajim_supabase_token", "legacy");
    storage.setSession({ access_token: "a", refresh_token: null, expires_at: null });
    storage.clear();
    expect(storage.getSession()).toBeNull();
    expect(storage.getAccount()).toBeNull();
    expect(localStorage.getItem("sajim_auth")).toBeNull();
    expect(localStorage.getItem("sajim_supabase_token")).toBeNull();
  });

  it("clearSession() keeps the saved account", () => {
    storage.setSession({ access_token: "a", refresh_token: null, expires_at: null });
    localStorage.setItem("sajim_active_account", JSON.stringify({ account_id: "1" }));
    storage.clearSession();
    expect(storage.getSession()).toBeNull();
    expect(storage.getAccount()).toEqual({ account_id: "1" });
  });
});

describe("session parsing", () => {
  it("builds a session from a token payload with expires_at", () => {
    expect(
      sessionFromPayload({ access_token: "a", refresh_token: "r", expires_at: 2000, expires_in: 3600 })
    ).toEqual({ access_token: "a", refresh_token: "r", expires_at: 2000 });
  });

  it("derives expires_at from expires_in", () => {
    expect(sessionFromPayload({ access_token: "a", expires_in: 3600 }, 100)).toEqual({
      access_token: "a",
      refresh_token: null,
      expires_at: 3700,
    });
  });

  it("rejects payloads without an access token", () => {
    expect(sessionFromPayload(null)).toBeNull();
    expect(sessionFromPayload({ refresh_token: "r" })).toBeNull();
  });

  it("parses an OAuth redirect fragment", () => {
    expect(
      sessionFromHash("#access_token=a&refresh_token=r&expires_in=3600&token_type=bearer", 10)
    ).toEqual({ access_token: "a", refresh_token: "r", expires_at: 3610 });
  });

  it("detects sessions that are about to expire", () => {
    const s = { access_token: "a", refresh_token: "r", expires_at: 1000 };
    expect(isExpiringSoon(s, 900, 60)).toBe(false);
    expect(isExpiringSoon(s, 950, 60)).toBe(true);
    expect(isExpiringSoon({ ...s, expires_at: null }, 5000)).toBe(false);
  });
});
