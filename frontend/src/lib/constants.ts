import type { AccountTelemetry, ClientSignal, RiskMode } from "./types";

export const AFFILIATE_URL =
  process.env.NEXT_PUBLIC_HEADWAY_AFFILIATE_URL || "https://headway.partners/user/signup?hwp=b158cc";

export const RISK_MODES: { id: RiskMode; title: string; subtitle: string }[] = [
  {
    id: "ULTRA_SAFE",
    title: "Ultra Safe",
    subtitle: "0.01 Micro lot fixed • 1% maximum portfolio risk",
  },
  {
    id: "PRO_SCALP",
    title: "Pro Scalp",
    subtitle: "Dynamic 0.02 - 0.05 lot • 2% target compound risk",
  },
  {
    id: "MAX_YIELD",
    title: "Max Yield",
    subtitle: "High-velocity momentum scaling • 5% max risk",
  },
];

export const DEMO_TELEMETRY: AccountTelemetry = {
  account_id: "DEMO-884920",
  account_name: "Demo Trader",
  broker_server: "Headway-Demo",
  autopilot_enabled: true,
  risk_mode: "PRO_SCALP",
  balance: 10000,
  equity: 10000,
  free_margin: 10000,
  today_pnl: 0,
  today_pnl_percent: 0,
  currency: "USD",
  open_positions: [],
  floating_pnl: 0,
  terminal_connected: true,
  is_demo: true,
};

export const EMPTY_TELEMETRY: AccountTelemetry = {
  account_id: "NEW",
  account_name: "Trader",
  broker_server: "None",
  autopilot_enabled: false,
  risk_mode: "ULTRA_SAFE",
  balance: 0,
  equity: 0,
  free_margin: 0,
  today_pnl: 0,
  today_pnl_percent: 0,
  currency: "USD",
  open_positions: [],
  floating_pnl: 0,
  terminal_connected: false,
  is_demo: false,
};

/**
 * Static sample signals shown in demo mode. Demo users are not signed in, so
 * the authenticated /api/client/signals feed is never called for them; these
 * are illustrative only and are clearly labelled "DEMO" in the UI.
 */
export const DEMO_SIGNALS: ClientSignal[] = [
  {
    id: "demo-xauusd",
    symbol: "XAUUSD",
    timeframe: "M15",
    action: "BUY",
    entry: 2350.0,
    sl: 2342.5,
    tp: 2365.0,
    rr: "1:2",
    strategy: "DEMO SAMPLE",
    phase: "DEMO",
    win_probability: "DEMO",
    gain_estimate_usd: "+$75.00",
    risk_estimate_usd: "-$37.50",
    expected_duration: "~45 min",
    trade_health_status: "DEMO",
    trade_explainer: "Sample signal for the demo cockpit — not live market data.",
    timestamp: "1970-01-01T00:00:00Z",
    one_tap_ready: true,
  },
  {
    id: "demo-eurusd",
    symbol: "EURUSD",
    timeframe: "H1",
    action: "SELL",
    entry: 1.085,
    sl: 1.0875,
    tp: 1.08,
    rr: "1:2",
    strategy: "DEMO SAMPLE",
    phase: "DEMO",
    win_probability: "DEMO",
    gain_estimate_usd: "+$50.00",
    risk_estimate_usd: "-$25.00",
    expected_duration: "~3 h",
    trade_health_status: "DEMO",
    trade_explainer: "Sample signal for the demo cockpit — not live market data.",
    timestamp: "1970-01-01T00:00:00Z",
    one_tap_ready: true,
  },
];
