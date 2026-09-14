import { describe, expect, it } from "vitest";
import { createSignal } from "./signal-domain";
import { insertSignal, listSignals, transitionSignal } from "./signal-store";

describe("development signal store", () => {
  it("persists and transitions a signal through the local adapter", async () => {
    const signal = createSignal({
      symbol: "EURUSD",
      timeframe: "H1",
      action: "SELL",
      entry: 1.1,
      stopLoss: 1.11,
      takeProfit: 1.07,
      source: "python_algo",
      strategyVersion: "python-test-v1",
      rationale: "Store lifecycle test",
      submittedBy: "00000000-0000-0000-0000-000000000002",
      expiresAt: "2099-01-01T00:00:00.000Z",
    });

    await insertSignal(signal);
    expect((await listSignals()).some((candidate) => candidate.id === signal.id)).toBe(true);

    const transitioned = await transitionSignal(signal.id, "REVIEWING");
    expect(transitioned?.status).toBe("REVIEWING");
    expect(transitioned?.updatedAt).not.toBe(signal.createdAt);
  });
});