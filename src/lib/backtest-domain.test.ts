import { describe, expect, it } from "vitest";
import { createBacktestJob, validateBacktestJobInput, validateStrategyManifest } from "./backtest-domain";

const manifest = {
  strategyId: "ema-pullback",
  displayName: "EMA Pullback",
  version: "v1",
  runtime: "pine",
  entrypoint: "EMA_Pullback_with_TrendDuration.pine",
  sourceFiles: ["EMA_Pullback_with_TrendDuration.pine"],
  parameters: { rrRatio: 2, useHmaFilter: false },
  datasetRequirements: { symbols: ["XAUUSD"], timeframes: ["M15"], start: "2020-01-01", end: "2024-01-01" },
};

const jobInput = {
  manifest,
  datasetId: "xauusd-m15-2020-2024-v1",
  executionModel: "bar-close-next-open",
  spreadPoints: 25,
  commissionPerOrder: 0.5,
  slippagePoints: 2,
  seed: 42,
};

describe("backtest contracts", () => {
  it("accepts a controlled strategy manifest", () => {
    expect(validateStrategyManifest(manifest)).toEqual({ ok: true, errors: [] });
  });

  it("rejects missing runtime and invalid date range", () => {
    const result = validateStrategyManifest({ ...manifest, runtime: "shell", datasetRequirements: { ...manifest.datasetRequirements, start: "2025-01-01", end: "2024-01-01" } });
    expect(result.ok).toBe(false);
    expect(result.errors).toContain("manifest.runtime must be python, pine, or mt5");
    expect(result.errors).toContain("datasetRequirements.end must be after start");
  });

  it("requires explicit costs, execution model, and deterministic seed", () => {
    const result = validateBacktestJobInput({ manifest, datasetId: "data", executionModel: "bar-close", spreadPoints: 0, commissionPerOrder: 0, slippagePoints: 0, seed: 1 });
    expect(result).toEqual({ ok: true, errors: [] });
  });

  it("creates a queued-only job without executing source code", () => {
    const job = createBacktestJob(jobInput);
    expect(job.status).toBe("QUEUED");
    expect(job.runtime).toBe("pine");
    expect(job.costModel).toEqual({ spreadPoints: 25, commissionPerOrder: 0.5, slippagePoints: 2 });
  });

  it("accepts an MT5 EA package for queued Strategy Tester execution", () => {
    const mt5Job = createBacktestJob({
      ...jobInput,
      manifest: { ...manifest, runtime: "mt5", entrypoint: "EMA_Pullback_TrendDuration_EA.mq5" },
    });
    expect(mt5Job.runtime).toBe("mt5");
    expect(mt5Job.status).toBe("QUEUED");
  });
});
