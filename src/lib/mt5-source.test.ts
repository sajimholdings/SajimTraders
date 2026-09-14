import { describe, expect, it } from "vitest";
import { validateMql5Source } from "./mt5-source";

const eaSource = `
#include <Trade\\Trade.mqh>
CTrade trade;
input int magicNumber = 20260914;
int OnInit() { return(INIT_SUCCEEDED); }
void OnTick() { CopyBuffer(handle, 0, 1, 1, buffer); trade.Buy(0.1); trade.Sell(0.1); }
// strategy
`;

describe("MQL5 source validation", () => {
  it("recognizes an EA with the required execution structure", () => {
    expect(validateMql5Source(eaSource)).toEqual({ ok: true, missing: [] });
  });

  it("rejects incomplete source instead of queueing it silently", () => {
    const result = validateMql5Source("void OnTick() {}");
    expect(result.ok).toBe(false);
    expect(result.missing).toContain("trade.Buy");
    expect(result.missing).toContain("magicNumber");
  });
});