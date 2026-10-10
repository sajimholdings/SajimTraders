/**
 * Sajim Traders — minimal Supabase Auth client.
 *
 * Handles email/password and OAuth flows only. Account and order persistence
 * is owned by the backend (see lib/api.ts), not by Supabase.
 *
 * Configuration comes exclusively from NEXT_PUBLIC_SUPABASE_URL and
 * NEXT_PUBLIC_SUPABASE_ANON_KEY (inlined at build time). There are no
 * hardcoded fallbacks: when either is missing, every auth call fails with
 * SUPABASE_CONFIG_ERROR so the UI can surface a configuration problem.
 */

export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export const SUPABASE_CONFIG_ERROR =
  "Sign-in is unavailable: Supabase is not configured (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY missing).";

export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

export interface SupabaseUser {
  id: string;
  email?: string;
  user_metadata?: { full_name?: string };
  identities?: unknown[];
}

/** Raw token payload returned by /auth/v1/token and (auto-confirmed) /auth/v1/signup. */
export interface SupabaseSessionPayload {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  expires_at?: number;
  token_type?: string;
  user?: SupabaseUser;
}

export interface AuthResult {
  user: SupabaseUser | null;
  session: SupabaseSessionPayload | null;
  error: string | null;
  /** True when the auth server could not be reached (vs. rejecting the request). */
  networkError?: boolean;
}

interface SupabaseErrorResponse {
  msg?: string;
  message?: string;
  error_description?: string;
}

function failure(error: string, networkError = false): AuthResult {
  return { user: null, session: null, error, networkError };
}

function networkFailure(err: unknown): AuthResult {
  return failure(err instanceof Error ? err.message : "Network error", true);
}

class SupabaseAuth {
  private readonly url: string;
  private readonly key: string;

  constructor(url: string, key: string) {
    this.url = url.replace(/\/$/, "");
    this.key = key;
  }

  get configured(): boolean {
    return Boolean(this.url && this.key);
  }

  private headers(token?: string): HeadersInit {
    return {
      apikey: this.key,
      Authorization: `Bearer ${token || this.key}`,
      "Content-Type": "application/json",
    };
  }

  async signUp(email: string, password: string, fullName?: string): Promise<AuthResult> {
    if (!this.configured) return failure(SUPABASE_CONFIG_ERROR);
    try {
      const redirectUrl = typeof window !== "undefined" ? window.location.origin : "";
      const endpoint = redirectUrl
        ? `${this.url}/auth/v1/signup?redirect_to=${encodeURIComponent(redirectUrl)}`
        : `${this.url}/auth/v1/signup`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({
          email: email.trim(),
          password,
          data: { full_name: fullName?.trim() || email.split("@")[0] },
        }),
      });
      const data = (await res.json().catch(() => ({}))) as SupabaseErrorResponse &
        SupabaseSessionPayload &
        Partial<SupabaseUser>;
      if (!res.ok) {
        return failure(
          data.msg || data.message || data.error_description || "Failed to create account"
        );
      }
      // Auto-confirmed projects return a session ({access_token, user, ...});
      // projects requiring email confirmation return the bare user object.
      if (data.access_token) {
        return { user: data.user || null, session: data, error: null };
      }
      const user = data.user || (data.id ? (data as SupabaseUser) : null);
      return { user, session: null, error: null };
    } catch (err) {
      return networkFailure(err);
    }
  }

  async signInWithPassword(email: string, password: string): Promise<AuthResult> {
    if (!this.configured) return failure(SUPABASE_CONFIG_ERROR);
    try {
      const res = await fetch(`${this.url}/auth/v1/token?grant_type=password`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = (await res.json().catch(() => ({}))) as SupabaseErrorResponse &
        SupabaseSessionPayload & { error?: string; error_code?: string };
      if (!res.ok) {
        return failure(
          data.error_description || data.msg || data.message || "Invalid email or password"
        );
      }
      return { user: data.user || null, session: data, error: null };
    } catch (err) {
      return networkFailure(err);
    }
  }

  /** Exchange a refresh token for a fresh session. */
  async refreshSession(refreshToken: string): Promise<AuthResult> {
    if (!this.configured) return failure(SUPABASE_CONFIG_ERROR);
    try {
      const res = await fetch(`${this.url}/auth/v1/token?grant_type=refresh_token`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      const data = (await res.json().catch(() => ({}))) as SupabaseErrorResponse &
        SupabaseSessionPayload;
      if (!res.ok || !data.access_token) {
        return failure(
          data.error_description || data.msg || data.message || "Session refresh failed"
        );
      }
      return { user: data.user || null, session: data, error: null };
    } catch (err) {
      return networkFailure(err);
    }
  }

  signInWithOAuth(provider: "google" | "github" = "google"): boolean {
    if (typeof window === "undefined" || !this.configured) return false;
    const target = window.location.origin;
    const authUrl = `${this.url}/auth/v1/authorize?provider=${provider}&redirect_to=${encodeURIComponent(target)}`;
    window.location.href = authUrl;
    return true;
  }

  /**
   * Validate an access token. Returns the user, `null` when the token was
   * rejected (401/403), or throws on network failure so callers can tell
   * "invalid session" apart from "offline".
   */
  async getUser(token: string): Promise<SupabaseUser | null> {
    if (!this.configured) return null;
    const res = await fetch(`${this.url}/auth/v1/user`, { headers: this.headers(token) });
    if (res.status === 401 || res.status === 403) return null;
    if (!res.ok) throw new Error(`Auth server error (${res.status})`);
    return (await res.json()) as SupabaseUser;
  }

  async signOut(token?: string): Promise<void> {
    if (!this.configured || !token) return;
    try {
      await fetch(`${this.url}/auth/v1/logout`, {
        method: "POST",
        headers: this.headers(token),
      });
    } catch {
      // Best-effort logout; local state is cleared regardless.
    }
  }
}

export const supabaseAuth = new SupabaseAuth(SUPABASE_URL, SUPABASE_ANON_KEY);
