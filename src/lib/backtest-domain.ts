export const BACKTEST_RUNTIMES = ["python", "pine", "mt5"] as const;
export type BacktestRuntime = (typeof BACKTEST_RUNTIMES)[number];

export type BacktestJobStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface StrategyPackageManifest {
  strategyId: string;
  displayName: string;
  version: string;
  runtime: BacktestRuntime;
  entrypoint: string;
  sourceFiles: string[];
  parameters: Record<string, number | boolean | string>;
  datasetRequirements: {
    symbols: string[];
    timeframes: string[];
    start: string;
    end: string;
  };
}

export interface BacktestJobInput {
  manifest?: unknown;
  datasetId?: unknown;
  executionModel?: unknown;
  spreadPoints?: unknown;
  commissionPerOrder?: unknown;
  slippagePoints?: unknown;
  seed?: unknown;
}

export interface BacktestJob {
  runId: string;
  strategyId: string;
  strategyVersion: string;
  runtime: BacktestRuntime;
  status: BacktestJobStatus;
  datasetId: string;
  executionModel: string;
  costModel: {
    spreadPoints: number;
    commissionPerOrder: number;
    slippagePoints: number;
  };
  seed: number;
  createdAt: string;
  updatedAt: string;
  error?: string;
}

export interface ValidationResult {
  ok: boolean;
  errors: string[];
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function isDateString(value: unknown): boolean {
  return isNonEmptyString(value) && !Number.isNaN(new Date(value).getTime());
}

export function validateStrategyManifest(value: unknown): ValidationResult {
  const errors: string[] = [];
  if (!value || typeof value !== "object") return { ok: false, errors: ["manifest must be an object"] };
  const manifest = value as Partial<StrategyPackageManifest>;

  if (!isNonEmptyString(manifest.strategyId)) errors.push("manifest.strategyId is required");
  if (!isNonEmptyString(manifest.displayName)) errors.push("manifest.displayName is required");
  if (!isNonEmptyString(manifest.version)) errors.push("manifest.version is required");
  if (!BACKTEST_RUNTIMES.includes(manifest.runtime as BacktestRuntime)) errors.push("manifest.runtime must be python, pine, or mt5");
  if (!isNonEmptyString(manifest.entrypoint)) errors.push("manifest.entrypoint is required");
  if (!Array.isArray(manifest.sourceFiles) || manifest.sourceFiles.length === 0) errors.push("manifest.sourceFiles must contain at least one file");
  if (!manifest.parameters || typeof manifest.parameters !== "object" || Array.isArray(manifest.parameters)) errors.push("manifest.parameters must be an object");

  const requirements = manifest.datasetRequirements;
  if (!requirements || typeof requirements !== "object") {
    errors.push("manifest.datasetRequirements is required");
  } else {
    if (!Array.isArray(requirements.symbols) || requirements.symbols.length === 0) errors.push("datasetRequirements.symbols is required");
    if (!Array.isArray(requirements.timeframes) || requirements.timeframes.length === 0) errors.push("datasetRequirements.timeframes is required");
    if (!isDateString(requirements.start) || !isDateString(requirements.end)) errors.push("datasetRequirements.start and end must be valid dates");
    if (isDateString(requirements.start) && isDateString(requirements.end) && new Date(requirements.start).getTime() >= new Date(requirements.end).getTime()) errors.push("datasetRequirements.end must be after start");
  }

  return { ok: errors.length === 0, errors };
}

export function validateBacktestJobInput(input: BacktestJobInput): ValidationResult {
  const errors: string[] = [];
  const manifestResult = validateStrategyManifest(input.manifest);
  errors.push(...manifestResult.errors);
  if (!isNonEmptyString(input.datasetId)) errors.push("datasetId is required");
  if (!isNonEmptyString(input.executionModel)) errors.push("executionModel is required");
  if (!isFiniteNumber(input.spreadPoints)) errors.push("spreadPoints must be a non-negative number");
  if (!isFiniteNumber(input.commissionPerOrder)) errors.push("commissionPerOrder must be a non-negative number");
  if (!isFiniteNumber(input.slippagePoints)) errors.push("slippagePoints must be a non-negative number");
  if (typeof input.seed !== "number" || !Number.isInteger(input.seed) || input.seed < 0) errors.push("seed must be a non-negative integer");
  return { ok: errors.length === 0, errors };
}

export function createBacktestJob(input: BacktestJobInput): BacktestJob {
  const validation = validateBacktestJobInput(input);
  if (!validation.ok) throw new Error(validation.errors.join("; "));
  const manifest = input.manifest as StrategyPackageManifest;
  const now = new Date().toISOString();
  return {
    runId: crypto.randomUUID(),
    strategyId: manifest.strategyId,
    strategyVersion: manifest.version,
    runtime: manifest.runtime,
    status: "QUEUED",
    datasetId: String(input.datasetId),
    executionModel: String(input.executionModel),
    costModel: {
      spreadPoints: Number(input.spreadPoints),
      commissionPerOrder: Number(input.commissionPerOrder),
      slippagePoints: Number(input.slippagePoints),
    },
    seed: Number(input.seed),
    createdAt: now,
    updatedAt: now,
  };
}
