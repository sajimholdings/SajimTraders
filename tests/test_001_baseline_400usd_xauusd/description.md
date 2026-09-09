# TEST LOG: TEST_001_BASELINE_400USD_XAUUSD

**Execution Date:** 2026-09-08 02:06:01
**Target Instrument:** XAUUSD
**Trading Style:** SWING
**Initial Capital:** $400.00 USD
**Fixed Lot Size:** 0.01 Lot (Sammy Gatekeeper Certified)

## Hypothesis & Scope
Baseline stress-test of BEEP Universal Protocol starting on a $400 USD starter account. Evaluates XAUUSD (Gold) across 1-month hourly data, enforcing Sammy's 4-Check Gatekeeper (M(t) > 40, SL beyond B(t), strict 0.01 lot size, Lambda > 10%) and Lambda optimal stopping time exits.

## Enforced Risk Constraints
- Sammy's 4-Check Gatekeeper active (M(t) > 40, SL beyond B(t), Lot 0.01, Lambda > 10%)
- Lambda optimal stopping time exit (Lambda < 35%)
- Realistic spread modeled at $0.35/oz
