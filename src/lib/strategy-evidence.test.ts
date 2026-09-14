import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { emaPullbackTrendDurationEvidence, validatePineSource } from "./strategy-evidence";

const source = `
strategy("EMA Pullback System + Trend Duration Forecast")
ema50_h4 = request.security(syminfo.tickerid, "240", ta.ema(close, 50))
ema200_h4 = request.security(syminfo.tickerid, "240", ta.ema(close, 200))
swingHigh = ta.pivothigh(high, 8, 8)
swingLow = ta.pivotlow(low, 8, 8)
bullishEngulf = close > open
bearishEngulf = close < open
strategy.entry("Long", strategy.long)
strategy.exit("Long Exit", "Long", stop = 1, limit = 2)
`;

describe("Pine strategy evidence", () => {
  it("registers the source as untested until evidence is attached", () => {
    expect(emaPullbackTrendDurationEvidence.source).toBe("PineScript");
    expect(emaPullbackTrendDurationEvidence.status).toBe("UNTESTED");
    expect(emaPullbackTrendDurationEvidence.claims).toEqual([]);
  });

  it("recognizes the required strategy structure", () => {
    expect(validatePineSource(source)).toEqual({ ok: true, missing: [] });
  });

  it("reports missing source markers instead of silently accepting an incomplete file", () => {
    const result = validatePineSource("strategy(\"partial\")");
    expect(result.ok).toBe(false);
    expect(result.missing).toContain("strategy.entry");
    expect(result.missing).toContain("ta.pivothigh");
  });

  it("validates the checked-in Pine artifact", () => {
    const path = resolve(process.cwd(), emaPullbackTrendDurationEvidence.sourcePath);
    const result = validatePineSource(readFileSync(path, "utf8"));
    expect(result).toEqual({ ok: true, missing: [] });
  });
});
