export const SIGNAL_SOURCES = [
  "BEEP",
  "PineScript",
  "EMA",
  "price_action",
  "python_algo",
] as const;

export type SignalSource = (typeof SIGNAL_SOURCES)[number];
export type SignalStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "REVIEWING"
  | "VERIFIED"
  | "PUBLISHED"
  | "EXPIRED"
  | "REJECTED"
  | "CANCELLED"
  | "RETRACTED";
export type SignalAction = "BUY" | "SELL";

export interface SignalSubmission {
  id: string;
  symbol: string;
  timeframe: string;
  action: SignalAction;
  entry: number;
  stopLoss: number;
  takeProfit: number;
  source: SignalSource;
  strategyVersion: string;
  screenshotUrl?: string;
  rationale: string;
  submittedBy: string;
  status: SignalStatus;
  expiresAt: string;
  createdAt: string;
  updatedAt: string;
  rejectionReason?: string;
}

export interface SignalSubmissionInput {
  symbol?: unknown;
  timeframe?: unknown;
  action?: unknown;
  entry?: unknown;
  stopLoss?: unknown;
  takeProfit?: unknown;
  source?: unknown;
  strategyVersion?: unknown;
  screenshotUrl?: unknown;
  rationale?: unknown;
  submittedBy?: unknown;
  expiresAt?: unknown;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
  riskReward?: number;
}

const VALID_ACTIONS: SignalAction[] = ["BUY", "SELL"];

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function validateSignalInput(input: SignalSubmissionInput): ValidationResult {
  const errors: string[] = [];
  const symbol = typeof input.symbol === "string" ? input.symbol.trim().toUpperCase() : "";
  const timeframe = typeof input.timeframe === "string" ? input.timeframe.trim().toUpperCase() : "";
  const action = typeof input.action === "string" ? input.action.trim().toUpperCase() : "";
  const source = typeof input.source === "string" ? input.source : "";
  const rationale = typeof input.rationale === "string" ? input.rationale.trim() : "";
  const strategyVersion = typeof input.strategyVersion === "string" ? input.strategyVersion.trim() : "";
  const entry = asNumber(input.entry);
  const stopLoss = asNumber(input.stopLoss);
  const takeProfit = asNumber(input.takeProfit);
  const expiresAt = typeof input.expiresAt === "string" ? new Date(input.expiresAt) : null;

  if (!symbol) errors.push("symbol is required");
  if (!timeframe) errors.push("timeframe is required");
  if (!VALID_ACTIONS.includes(action as SignalAction)) errors.push("action must be BUY or SELL");
  if (!SIGNAL_SOURCES.includes(source as SignalSource)) errors.push("source is not supported");
  if (!strategyVersion) errors.push("strategyVersion is required");
  if (!rationale) errors.push("rationale is required");
  if (entry === null || stopLoss === null || takeProfit === null) {
    errors.push("entry, stopLoss, and takeProfit must be numbers");
  } else {
    if (action === "BUY" && !(stopLoss < entry && takeProfit > entry)) {
      errors.push("BUY requires stopLoss below entry and takeProfit above entry");
    }
    if (action === "SELL" && !(stopLoss > entry && takeProfit < entry)) {
      errors.push("SELL requires stopLoss above entry and takeProfit below entry");
    }
  }
  if (!expiresAt || Number.isNaN(expiresAt.getTime())) errors.push("expiresAt must be a valid timestamp");
  if (expiresAt && expiresAt.getTime() <= Date.now()) errors.push("expiresAt must be in the future");

  let riskReward: number | undefined;
  if (entry !== null && stopLoss !== null && takeProfit !== null) {
    const risk = Math.abs(entry - stopLoss);
    const reward = Math.abs(takeProfit - entry);
    if (risk > 0) {
      riskReward = Number((reward / risk).toFixed(2));
      if (riskReward < 2) errors.push("risk/reward must be at least 1:2");
    }
  }

  return { ok: errors.length === 0, errors, riskReward };
}

export function createSignal(input: SignalSubmissionInput): SignalSubmission {
  const validation = validateSignalInput(input);
  if (!validation.ok) throw new Error(validation.errors.join("; "));

  const now = new Date().toISOString();
  const source = String(input.source) as SignalSource;
  return {
    id: crypto.randomUUID(),
    symbol: String(input.symbol).trim().toUpperCase(),
    timeframe: String(input.timeframe).trim().toUpperCase(),
    action: String(input.action).trim().toUpperCase() as SignalAction,
    entry: Number(input.entry),
    stopLoss: Number(input.stopLoss),
    takeProfit: Number(input.takeProfit),
    source,
    strategyVersion: String(input.strategyVersion).trim(),
    screenshotUrl: typeof input.screenshotUrl === "string" ? input.screenshotUrl.trim() : undefined,
    rationale: String(input.rationale).trim(),
    submittedBy: String(input.submittedBy || "unknown").trim(),
    status: "SUBMITTED",
    expiresAt: new Date(String(input.expiresAt)).toISOString(),
    createdAt: now,
    updatedAt: now,
  };
}
