export type StrategySource = "BEEP" | "PineScript" | "EMA" | "price_action" | "python_algo";

export interface StrategyEvidence {
  evidenceId: string;
  source: StrategySource;
  strategyVersion: string;
  displayName: string;
  sourcePath: string;
  status: "UNTESTED" | "FORWARD_TEST" | "VALIDATED" | "SUSPENDED";
  entryRules: string[];
  riskControls: string[];
  parameters: Record<string, number | boolean | string>;
  claims: string[];
  limitations: string[];
}

export const emaPullbackTrendDurationEvidence: StrategyEvidence = {
  evidenceId: "pine-ema-pullback-trend-duration-v1",
  source: "PineScript",
  strategyVersion: "ema-pullback-trend-duration-v1",
  displayName: "EMA Pullback System + Trend Duration Forecast",
  sourcePath: "strategy-sources/pine/EMA_Pullback_with_TrendDuration.pine",
  status: "UNTESTED",
  entryRules: [
    "H4 EMA 50 above EMA 200 for long bias or below for short bias",
    "Price touches EMA 20 and prints a matching engulfing candle",
    "Optional HMA trend-duration alignment can gate entries",
    "A valid swing low/high must exist for structural stop placement",
  ],
  riskControls: [
    "Configurable risk percentage input",
    "Configurable reward:risk target with room-to-target trimming",
    "Maximum trades per day",
    "One open strategy trade at a time",
    "Optional Friday close rule",
  ],
  parameters: {
    riskPercent: 0.5,
    rrRatio: 2,
    swingLen: 8,
    minRoomRatio: 0.8,
    useRoomFilter: true,
    closeByFriday: true,
    fridayHour: 20,
    maxTradesDay: 2,
    tdLength: 50,
    tdTrendLength: 3,
    tdSamples: 10,
    useHmaFilter: false,
  },
  claims: [],
  limitations: [
    "UNTESTED: no approved out-of-sample or forward-test result is attached",
    "Pine commission_value is zero and must be replaced with realistic costs",
    "Slippage and spread assumptions are not represented in the source strategy",
    "TradingView execution semantics must be reconciled with broker execution",
    "Pivot detection and higher-timeframe security behavior require parity testing",
  ],
};

const requiredMarkers = [
  "strategy(\"EMA Pullback System + Trend Duration Forecast\"",
  "ema50_h4",
  "ema200_h4",
  "ta.pivothigh",
  "ta.pivotlow",
  "bullishEngulf",
  "bearishEngulf",
  "strategy.entry",
  "strategy.exit",
];

export function validatePineSource(source: string): { ok: boolean; missing: string[] } {
  const missing = requiredMarkers.filter((marker) => !source.includes(marker));
  return { ok: missing.length === 0, missing };
}
