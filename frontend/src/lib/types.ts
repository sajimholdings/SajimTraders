export interface ClientTrade {
  ticket: number;
  symbol: string;
  type: "BUY" | "SELL";
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
  action: "BUY" | "SELL";
  entry: number;
  sl: number;
  tp: number;
  rr: string;
  strategy: string;
  phase: string;
  win_probability: string;
  gain_estimate_usd: string;
  risk_estimate_usd: string;
  timestamp: string;
  one_tap_ready: boolean;
}

export interface AccountTelemetry {
  account_id: string;
  account_name: string;
  broker_server: string;
  autopilot_enabled: boolean;
  risk_mode: string;
  balance: number;
  equity: number;
  free_margin: number;
  margin_level?: number;
  today_pnl: number;
  today_pnl_percent: number;
  currency: string;
  open_positions: ClientTrade[];
  floating_pnl: number;
  terminal_connected: boolean;
  is_demo: boolean;
}
