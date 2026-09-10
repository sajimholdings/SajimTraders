/**
 * Sajim Traders — Supabase Client API Helper
 * Provides typed, zero-dependency REST access to Supabase Auth, Profiles, Accounts & Signals.
 */

export const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://oticnkopzmrrzdljyurv.supabase.co";
export const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

class SupabaseClient {
  private url: string;
  private key: string;

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

  // Auth: Sign Up with Email
  async signUp(email: string, password: string, fullName?: string) {
    const res = await fetch(`${this.url}/auth/v1/signup`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        email,
        password,
        data: { full_name: fullName || email.split("@")[0] },
      }),
    });
    return res.json();
  }

  // Auth: Sign In with Password
  async signInWithPassword(email: string, password: string) {
    const res = await fetch(`${this.url}/auth/v1/token?grant_type=password`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ email, password }),
    });
    return res.json();
  }

  // Auth: Sign In with OAuth (Google)
  signInWithOAuth(provider: "google" | "github" = "google", redirectTo?: string) {
    if (typeof window === "undefined") return;
    const targetRedirect = redirectTo || window.location.origin;
    const authUrl = `${this.url}/auth/v1/authorize?provider=${provider}&redirect_to=${encodeURIComponent(targetRedirect)}`;
    window.location.href = authUrl;
  }

  // Auth: Fetch User Info from JWT
  async getUser(token: string) {
    try {
      const res = await fetch(`${this.url}/auth/v1/user`, {
        headers: this.headers(token),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  // Auth: Sign Out
  async signOut(token?: string) {
    try {
      await fetch(`${this.url}/auth/v1/logout`, {
        method: "POST",
        headers: this.headers(token),
      });
    } catch {
      // Ignore
    }
  }

  // Database: Fetch Active Signals
  async getActiveSignals(token?: string) {
    try {
      const res = await fetch(
        `${this.url}/rest/v1/signals?is_active=eq.true&order=created_at.desc&select=*`,
        {
          headers: this.headers(token),
        }
      );
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  }

  // Database: Link / Connect MT5 Account
  async connectTradingAccount(
    userId: string,
    account: {
      account_id: string;
      account_name?: string;
      broker_server: string;
      is_demo?: boolean;
      risk_mode?: string;
    },
    token?: string
  ) {
    const res = await fetch(`${this.url}/rest/v1/trading_accounts`, {
      method: "POST",
      headers: {
        ...this.headers(token),
        Prefer: "return=representation,resolution=merge-duplicates",
      },
      body: JSON.stringify({
        user_id: userId,
        account_id: account.account_id,
        account_name: account.account_name || "Trader Account",
        broker_server: account.broker_server,
        is_demo: Boolean(account.is_demo),
        risk_mode: account.risk_mode || "ULTRA_SAFE",
        autopilot_enabled: true,
      }),
    });
    return res.json();
  }

  // Database: Submit 1-Tap Order to Queue
  async submitOrder(
    userId: string,
    order: {
      account_id: string;
      symbol: string;
      action: "BUY" | "SELL";
      volume: number;
      sl?: number;
      tp?: number;
      comment?: string;
    },
    token?: string
  ) {
    const res = await fetch(`${this.url}/rest/v1/orders_queue`, {
      method: "POST",
      headers: {
        ...this.headers(token),
        Prefer: "return=representation",
      },
      body: JSON.stringify({
        user_id: userId,
        account_id: order.account_id,
        symbol: order.symbol,
        action: order.action,
        volume: order.volume,
        sl: order.sl,
        tp: order.tp,
        comment: order.comment || "Sajim_1Tap",
        status: "PENDING",
      }),
    });
    return res.json();
  }
}

export const supabase = new SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY);
