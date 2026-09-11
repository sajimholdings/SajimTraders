// Domain types for the Sajim Traders client portal.

export type TradeType = "BUY" | "SELL";
export type RiskMode = "ULTRA_SAFE" | "PRO_SCALP" | "MAX_YIELD";
export type ConnectorTab = "demo" | "real";
export type AuthMode = "signup" | "signin";

export interface ClientTrade {
  ticket: number;
  symbol: string;
  type: TradeType;
  volume: number;
  open_price: number;
  current_price: number;
  sl?: number;
  tp?: number;
  pnl: number;
  time?: string;
  comment?: string;
}

export interface ClientSignal {
  id: string;
  symbol: string;
  timeframe: string;
  action: TradeType;
  entry: number;
  sl: number;
  tp: number;
  rr: string;
  strategy: string;
  phase: string;
  win_probability: string;
  gain_estimate_usd: string;
  risk_estimate_usd: string;
  expected_duration?: string;
  expected_bars?: string;
  trade_health_pct?: number;
  trade_health_status?: string;
  trade_explainer?: string;
  timestamp: string;
  one_tap_ready: boolean;
}

// Shape returned by GET /api/client/account (server-owned fields only).
export interface BackendAccount {
  account_id: string;
  account_name: string;
  broker_server: string;
  autopilot_enabled: boolean;
  risk_mode: string;
  balance: number;
  equity: number;
  free_margin: number;
  margin_level?: number;
  currency: string;
  open_positions: ClientTrade[];
  floating_pnl: number;
  terminal_connected: boolean;
}

// Client-side account state: server fields plus locally-managed fields.
export interface AccountTelemetry extends BackendAccount {
  today_pnl: number;
  today_pnl_percent: number;
  is_demo: boolean;
}

export interface GateStats {
  today_pnl: number | null;
  active_trades: number | null;
  system_online: boolean;
}

export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
}
