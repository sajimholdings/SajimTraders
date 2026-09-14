import { describe, expect, it } from "vitest";
import { createSignal, validateSignalInput } from "./signal-domain";

const future = "2099-01-01T00:00:00.000Z";

function validInput(overrides: Record<string, unknown> = {}) {
  return {
    symbol: "xauusd",
    timeframe: "m15",
    action: "BUY",
    entry: 100,
    stopLoss: 99,
    takeProfit: 103,
    source: "BEEP",
    strategyVersion: "beep-test-v1",
    rationale: "Structured setup for review",
    submittedBy: "00000000-0000-0000-0000-000000000001",
    expiresAt: future,
    ...overrides,
  };
}

describe("signal validation", () => {
  it("accepts a valid BUY setup and calculates risk/reward", () => {
    const result = validateSignalInput(validInput());
    expect(result).toEqual({ ok: true, errors: [], riskReward: 3 });
  });

  it("accepts a valid SELL setup", () => {
    const result = validateSignalInput(validInput({ action: "SELL", entry: 100, stopLoss: 101, takeProfit: 97 }));
    expect(result.ok).toBe(true);
    expect(result.riskReward).toBe(3);
  });

  it("rejects a BUY with invalid price ordering", () => {
    const result = validateSignalInput(validInput({ stopLoss: 101 }));
    expect(result.ok).toBe(false);
    expect(result.errors).toContain("BUY requires stopLoss below entry and takeProfit above entry");
  });

  it("rejects insufficient risk/reward", () => {
    const result = validateSignalInput(validInput({ takeProfit: 100.5 }));
    expect(result.ok).toBe(false);
    expect(result.errors).toContain("risk/reward must be at least 1:2");
  });

  it("rejects unsupported sources and expired signals", () => {
    const result = validateSignalInput(validInput({ source: "unknown", expiresAt: "2020-01-01T00:00:00.000Z" }));
    expect(result.ok).toBe(false);
    expect(result.errors).toContain("source is not supported");
    expect(result.errors).toContain("expiresAt must be in the future");
  });

  it("normalizes a valid submission into the internal contract", () => {
    const signal = createSignal(validInput());
    expect(signal.symbol).toBe("XAUUSD");
    expect(signal.timeframe).toBe("M15");
    expect(signal.status).toBe("SUBMITTED");
    expect(signal.submittedBy).toBe("00000000-0000-0000-0000-000000000001");
  });
});