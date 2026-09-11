import type { AccountTelemetry, RiskMode } from "./types";

export const AFFILIATE_URL = "https://headway.partners/user/signup?hwp=b158cc";

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

// Pre-filled demo credentials for the free demo tab.
export const DEMO_ACCOUNT_ID = "1200442972";
export const DEMO_PASSWORD = "demo1234";
