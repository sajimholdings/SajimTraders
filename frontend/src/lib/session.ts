/**
 * Sajim Traders — Supabase session lifecycle.
 *
 * Persists access + refresh tokens, refreshes before expiry (and on demand
 * after a 401), validates restored sessions, and notifies subscribers when a
 * session can no longer be recovered so the UI can show a "sign in again" state.
 */

import { storage, type StoredSession } from "./storage";
import { supabaseAuth, type SupabaseSessionPayload, type SupabaseUser } from "./supabase";

/** Refresh when the access token has less than this many seconds left. */
export const REFRESH_SKEW_SECONDS = 60;

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

/** Normalise a Supabase token payload (or OAuth hash params) into a StoredSession. */
export function sessionFromPayload(
  payload: SupabaseSessionPayload | null | undefined,
  now: number = nowSeconds()
): StoredSession | null {
  if (!payload || typeof payload.access_token !== "string" || !payload.access_token) return null;
  const expiresAt = Number(payload.expires_at);
  const expiresIn = Number(payload.expires_in);
  let expires_at: number | null = null;
  if (Number.isFinite(expiresAt) && expiresAt > 0) expires_at = expiresAt;
  else if (Number.isFinite(expiresIn) && expiresIn > 0) expires_at = now + expiresIn;
  return {
    access_token: payload.access_token,
    refresh_token: payload.refresh_token || null,
    expires_at,
  };
}

/** Parse the `#access_token=...&refresh_token=...` fragment of an OAuth redirect. */
export function sessionFromHash(hash: string, now: number = nowSeconds()): StoredSession | null {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  return sessionFromPayload(
    {
      access_token: params.get("access_token") || undefined,
      refresh_token: params.get("refresh_token") || undefined,
      expires_at: params.get("expires_at") ? Number(params.get("expires_at")) : undefined,
      expires_in: params.get("expires_in") ? Number(params.get("expires_in")) : undefined,
    },
    now
  );
}

export function isExpiringSoon(
  session: StoredSession,
  now: number = nowSeconds(),
  skew: number = REFRESH_SKEW_SECONDS
): boolean {
  if (session.expires_at === null) return false;
  return session.expires_at - now <= skew;
}

// ---- expiry notifications -------------------------------------------------

type ExpiredListener = () => void;
const expiredListeners = new Set<ExpiredListener>();

export function onSessionExpired(listener: ExpiredListener): () => void {
  expiredListeners.add(listener);
  return () => {
    expiredListeners.delete(listener);
  };
}

/** Clear the stored session and tell the UI it has to ask for a new sign-in. */
export function expireSession(): void {
  storage.clearSession();
  expiredListeners.forEach((l) => {
    try {
      l();
    } catch {
      // Listener errors must not break the auth flow.
    }
  });
}

// ---- refresh --------------------------------------------------------------

let refreshInFlight: Promise<StoredSession | null> | null = null;

/**
 * Refresh the stored session using its refresh token. Concurrent callers share
 * one request. Resolves to the new session, or null when refresh is impossible
 * (no refresh token / rejected) — in which case the session is expired.
 */
export function refreshSession(): Promise<StoredSession | null> {
  if (refreshInFlight) return refreshInFlight;
  const current = storage.getSession();
  if (!current?.refresh_token) {
    if (current) expireSession();
    return Promise.resolve(null);
  }
  const refreshToken = current.refresh_token;
  refreshInFlight = (async () => {
    try {
      const res = await supabaseAuth.refreshSession(refreshToken);
      // Offline: keep the current session so a later attempt can still refresh it.
      if (res.networkError) return storage.getSession();
      const next = sessionFromPayload(res.session);
      // Another tab/sign-out may have replaced the session meanwhile.
      if (storage.getSession()?.refresh_token !== refreshToken) {
        return storage.getSession();
      }
      if (!next) {
        expireSession();
        return null;
      }
      storage.setSession({ ...next, refresh_token: next.refresh_token || refreshToken });
      return storage.getSession();
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/** Access token for an outgoing request, refreshed first if it is about to expire. */
export async function getValidAccessToken(): Promise<string | null> {
  const current = storage.getSession();
  if (!current) return null;
  if (!isExpiringSoon(current)) return current.access_token;
  const next = await refreshSession();
  return next?.access_token ?? null;
}

export type RestoreResult =
  | { status: "none" }
  | { status: "valid"; user: SupabaseUser }
  | { status: "expired" }
  | { status: "offline" };

/**
 * Validate a persisted session against /auth/v1/user, refreshing once if the
 * token is rejected. "offline" means the auth server could not be reached —
 * the session is kept so a later request can retry.
 */
export async function restoreSession(): Promise<RestoreResult> {
  if (!storage.getSession()) return { status: "none" };
  try {
    let token = await getValidAccessToken();
    if (!token) return { status: "expired" };
    let user = await supabaseAuth.getUser(token);
    if (!user) {
      const refreshed = await refreshSession();
      token = refreshed?.access_token ?? null;
      user = token ? await supabaseAuth.getUser(token) : null;
    }
    if (!user) {
      expireSession();
      return { status: "expired" };
    }
    return { status: "valid", user };
  } catch {
    return { status: "offline" };
  }
}

/** Revoke the session server-side (best effort) and clear it locally. */
export async function signOutSession(): Promise<void> {
  const current = storage.getSession();
  storage.clearSession();
  if (current) await supabaseAuth.signOut(current.access_token);
}
