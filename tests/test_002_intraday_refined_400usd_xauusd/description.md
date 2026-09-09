# TEST LOG: TEST_002_INTRADAY_REFINED_400USD_XAUUSD

**Execution Date:** 2026-09-08 02:06:33
**Target Instrument:** XAUUSD
**Trading Style:** INTRADAY
**Initial Capital:** $400.00 USD
**Fixed Lot Size:** 0.01 Lot (Sammy Gatekeeper Certified)

## Hypothesis & Scope
Iterative refinement of Baseline Test 001. Tests BEEP in INTRADAY mode with tighter baseline support buffers (1.618x ATR) and faster Lambda decay (0.03). Evaluates whether tighter duration risk reduces maximum drawdown on a $400 account.

## Enforced Risk Constraints
- Sammy's 4-Check Gatekeeper active (M(t) > 40, SL beyond B(t), Lot 0.01, Lambda > 10%)
- Lambda optimal stopping time exit (Lambda < 35%)
- Realistic spread modeled at $0.35/oz
