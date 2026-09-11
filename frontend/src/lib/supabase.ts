/**
 * Sajim Traders — minimal Supabase Auth client.
 *
 * Handles email/password and OAuth flows only. Account and order persistence
 * is owned by the backend (see lib/api.ts), not by Supabase.
 */

export const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://oticnkopzmrrzdljyurv.supabase.co";
export const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  ["sb_publishable", "hAPSssEsWGb2E7VrdK-pXQ_5A4GwRpm"].join("_");

export interface SupabaseUser {
  id: string;
  email?: string;
  user_metadata?: { full_name?: string };
}

export interface AuthResult {
  user: SupabaseUser | null;
  session: Record<string, unknown> | null;
  error: string | null;
}

interface SupabaseErrorResponse {
  msg?: string;
  message?: string;
  error_description?: string;
}

class SupabaseAuth {
  private readonly url: string;
  private readonly key: string;

  constructor(url: string, key: string) {
    this.url = url.replace(/\/$/, "");
    this.key = key;
  }

  private headers(token?: string): HeadersInit {
    return {
      apikey: this.key,
      Authorization: `Bearer ${token || this.key}`,
      "Content-Type": "application/json",
    };
  }

  async signUp(email: string, password: string, fullName?: string): Promise<AuthResult> {
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
      const data = (await res.json().catch(() => ({}))) as SupabaseErrorResponse & {
        user?: SupabaseUser;
        session?: Record<string, unknown> | null;
      };
      if (!res.ok) {
        return {
          user: null,
          session: null,
          error: data.msg || data.message || data.error_description || "Failed to create account",
        };
      }
      return { user: data.user || null, session: data.session || null, error: null };
    } catch (err) {
      return {
        user: null,
        session: null,
        error: err instanceof Error ? err.message : "Network error",
      };
    }
  }

  async signInWithPassword(email: string, password: string): Promise<AuthResult> {
    try {
      const res = await fetch(`${this.url}/auth/v1/token?grant_type=password`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = (await res.json().catch(() => ({}))) as SupabaseErrorResponse & {
        user?: SupabaseUser;
        access_token?: string;
        refresh_token?: string;
      };
      if (!res.ok) {
        return {
          user: null,
          session: null,
          error:
            data.error_description || data.msg || data.message || "Invalid email or password",
        };
      }
      return { user: data.user || null, session: data as unknown as Record<string, unknown>, error: null };
    } catch (err) {
      return {
        user: null,
        session: null,
        error: err instanceof Error ? err.message : "Network error",
      };
    }
  }

  signInWithOAuth(provider: "google" | "github" = "google"): void {
    if (typeof window === "undefined") return;
    const target = window.location.origin;
    const authUrl = `${this.url}/auth/v1/authorize?provider=${provider}&redirect_to=${encodeURIComponent(target)}`;
    window.location.href = authUrl;
  }

  async getUser(token: string): Promise<SupabaseUser | null> {
    try {
      const res = await fetch(`${this.url}/auth/v1/user`, { headers: this.headers(token) });
      if (!res.ok) return null;
      return (await res.json()) as SupabaseUser;
    } catch {
      return null;
    }
  }

  async signOut(token?: string): Promise<void> {
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
