# 02 — The BEEP Framework

**Source:** `core/beep_core.py` (class `BeepCoreEngine`, "Universal Contextual Deviation Protocol").

BEEP is a signal engine that scores a price series and emits a directional call with a lot size,
SL/TP, and a confidence "tier." It rests on four equations plus a risk gate and a portfolio-level
circuit breaker.

## Equation 1 — B(t): Asymptotic Baseline (robust location)

`calculate_asymptotic_baseline(prices, trim_z=2.0)`

- Computes the raw mean and population standard deviation of the window.
- **Prunes outliers** whose z-score exceeds `trim_z` (default 2.0) — intended to strip panic wicks
  and retail noise.
- Returns the trimmed mean (the "institutional equilibrium" baseline) and the trimmed sigma.
- Needs ≥ 5 points; otherwise it falls back to the plain mean.

This is essentially a one-pass **Huber/Tukey-style robust mean**, not the Hull Moving Average the
marketing text sometimes claims — it is a location estimator, not a trend smoother.

## Equation 2 — M(t): Kinetic Mass (sign-persistence detector)

`calculate_kinetic_mass(prices, robust_mean, robust_sigma)`

- Converts the **last 12** prices to z-scores against the robust baseline.
- Walks the z-scores; when two consecutive scores share a sign, it **accumulates mass**:
  `mass += |z| * (1.0 + 0.1*i) * 7.5` (later steps weigh more).
- When the sign flips, mass is **damped** `mass *= 0.60`.
- Returns `min(100, mass)`; short series (< 5) return a neutral `20.0`.

In plain English: M(t) rewards *sustained directional pressure* and punishes chop. The code's
docstring asserts M > 40 ≈ 6+ aligned steps ≈ "P(noise) < 1.56%", and M > 55 is used by the risk
narrative as "Rare."

## Equation 3 — Γ (Gamma): Multi-Scale Gate (tri-timeframe alignment)

`evaluate_multiscale_gate(velocity_m1, velocity_m5, velocity_m15)`

- Takes the sign of three velocities (M1, M5, M15).
- Gate passes only when **all three signs match and are non-zero**.
- Emits `direction = BUY/SELL/HOLD` accordingly.

The docstring asserts that combining the gate with M > 40 yields a **0.195%** theoretical
false-positive rate. That number is a hand-computed probability claim, not something measured in
the code — treat it as an assertion, not an empirical result.

## Equation 4 — Λ (Lambda): Exponential Momentum Decay (time stop)

`calculate_lambda_decay(elapsed_bars, style, initial_lambda=1.0)`

- `Lambda(t) = Lambda_0 * exp(-lambda_rate * elapsed_bars)`, returned as a percentage.
- Intended exit signal: when Lambda decays below **0.35** (35%), momentum is considered exhausted
  and the trade should be stopped.
- `lambda_rate` is per style (see below).

## Style calibration

| Style | Timeframes | W_dev | W_mom | W_vol | ATR mult | lambda_rate |
|---|---|---|---|---|---|---|
| SCALP | M1/M5 | 0.35 | 0.35 | 0.30 | 1.2 | 0.08 |
| INTRADAY | M15/H1 | 0.30 | 0.30 | 0.40 | 1.618 | 0.03 |
| SWING | H4/D1 | 0.25 | 0.25 | 0.50 | 2.618 | 0.01 |

(The `W_dev`/`W_mom`/`W_vol` weights are declared but not obviously consumed by the four equations
in the file — the ATR multiplier and lambda rate are the fields that actually drive behavior.)

## Signal certification tiers

Based on M(t):

| M(t) | Tier |
|---|---|
| ≥ 90 | Diamond Beep (Legendary) |
| ≥ 75 | Rare Beep (Extraordinary) |
| ≥ 40 | Certified Beep (Exceptional) |
| < 40 | Uncertified (Normal Range) |

## Sammy's 4-Check Risk Gate

`evaluate_sammy_4check(...)` gates a signal before execution:

1. **Momentum** — `M(t) > 40`.
2. **SL vs baseline** — for BUY, SL must be below B(t); for SELL, above.
3. **Lot size** — within `0.01 … 5.0`.
4. **Lambda energy** — `Lambda > 10%`.

All four must pass → "GO", otherwise "STOP."

## Position sizing

`calculate_dynamic_lotsize(...)`

- **Starter mode** (`balance <= 500`, default on) hard-locks to **0.01 lots**.
- Scaled mode sizes proportionally to risk, then clamps to `0.01 … 10.0` lots.

## Portfolio theorem (cross-asset circuit breaker)

`evaluate_portfolio(...)`

- Scores every asset, averages their Lambda values, and if the **portfolio Lambda < 35%**, trips a
  collective circuit breaker (`CIRCUIT_BREAKER_HALT`).
- Reports a joint false-positive probability `(0.002)^k` for `k` high-conviction assets.

---

### My notes on BEEP

- The **math is internally coherent and reasonably careful** for a personal project: robust mean,
  sign-persistence momentum, a multi-timeframe agreement gate, and exponential time decay are all
  legitimate ideas.
- The **weak points are empirical, not mathematical**: the probability claims (1.56%, 0.195%) and
  the "institutional" language are asserted, not validated against the historical data in `data/`.
- The engine's *outputs* (tier, noise-rejection string) are used downstream for display and
  marketing-flavored messaging; the real execution value is the M(t)/Gamma/direction trio and the
  SL/TP distances, which are simple and auditable.
