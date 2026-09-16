# 04 — Audit Findings

This summarizes and organizes the findings from `docs/FULL_REPO_AUDIT_REPORT.md` (a line-level,
read-only audit performed the same day). Subsystem health scores are out of 10.

| Subsystem | Score | One-line basis |
|---|---|---|
| cTrader bridge | **2** | Sandbox stub — no Open API protocol; silent degrade-to-sandbox returns `True` |
| Multi-bot concurrency | **3** | 50% breaker (not 5%), no cTrader breaker path, cross-broker KeyError, no locks |
| Quant math & sizing | **4** | EV/PF correct; Sharpe/Sortino non-standard; cloud lot sizing is a stub |
| Core engines | **3** | Correct SMC core, but fabricated telemetry, dead MT5 order path, threshold rewrites |
| Bots & V2 strategies | **3** | Prop-firm bot unimportable + stub live branch; unclosed-bar gates; verified crashes |
| Web / API | **3** | Auth gaps, cross-tenant trades, fabricated telemetry, CORS `*` |
| Tests | **4** | 7/16 suites pass; stale assertions + missing env keys |
| **Overall** | **~3 / 10** | Pre-production demo state |

## 1. The cTrader migration is not real

`core/ctrader_bridge.py` does **not** implement Spotware Open API 2.0:

- `_authenticate_session()` sleeps and returns `True`; the heartbeat and receive workers are
  `pass`/`sleep`; `send_order()` fabricates a ticket from `time.time()` and never transmits;
  `_reconcile_account_state()` is `pass`.
- On **any** auth/connection failure, `connect()` sets `simulation_mode=True` and **returns `True`**,
  so callers believe the broker is connected while nothing can trade.

## 2. The execution path is still Windows/MT5-bound

- Unconditional top-level `import MetaTrader5` (crashes on Linux/Render) at ~20 sites, including the
  entire "cloud" chain: `v2/execution/order_router.py`, `v2/dual_orchestrator.py`, the bots, and
  several `core/` engines.
- `v2/__init__.py` imports the MT5-bound `sajim_v2_dual_bot`, so importing `v2.strategies` fails on
  Linux even though the strategy files themselves are MT5-free.
- `run.py dual --broker ctrader` imports the orchestrator (→ MT5) and crashes **before** the cTrader
  branch runs.

## 3. Fabricated success / fabricated data (systemic)

This is the most important theme: several subsystems report success when nothing real happened.

- `core/api.py` uses a non-existent `mt5.ORDER_BUY`, swallows the `AttributeError`, and returns HTTP
  200 `"SIMULATED_ORDER_CONFIRMED"` for every order — live execution can never place a trade and
  never reports failure.
- `core/investor_reporting.py` seeds **five hardcoded fake deals** when no real ledger exists, and
  `web/app.py` serves them publicly as "verified" equity/expectancy.
- `core/multi_account_manager.py` hardcodes `today_pnl=4.35` / `20.7%` for a specific account.
- `web/routes/admin.py` returns fabricated balance/equity/win-rates and a hardcoded
  `"terminal_bridge": "CONNECTED"`.
- `core/beep_broadcast.py` hardcodes `"92%"/"89%"/"86%"` win probabilities.
- `core/mt5_bridge.py` returns a **hardcoded 14-price fake series** when MT5 is absent.
- `core/beep_processor.py` silently rewrites its own documented thresholds (e.g. `min_snipe_score`
  55→48, `min_relative_volume` 1.20→0.65).
- `core/backtester.py` generates synthetic data and writes it as if real, with a hardcoded gold
  price for all FX pairs and a shared seed that makes "uncorrelated" pairs identical.

## 4. Risk controls are broken or self-contradictory

- Circuit breaker is **50%, not 5%** (`v2/coexistence.py` `MAX_DAILY_DRAWDOWN_PCT = 0.50`).
- The cTrader path never evaluates the breaker (only the MT5 `refresh()` does).
- Prop-firm bot measures total drawdown from current balance, not the challenge high-water mark.
- Prop-firm `--live` branch is a `print()` stub; the bot cannot import at all.
- V1 treats any `.c` symbol or "Headway" server as a cent account → 5% equity risk/trade vs the
  documented 2% cap, plus a concurrency bonus exposing up to 8×5% at once.

## 5. Verified correctness bugs (crashes / wrong output)

- `v2/execution/order_router.py` — `order_type` referenced but never assigned → `NameError`.
- `core/dealer_state_space.py` — `delta_p` is identically 0.0 every tick (subtracts the same mid).
- `core/confluence_engine.py` — `is_bear_exhausted` never read; the ternary makes `action` BUY
  unconditionally.
- `bots/sajim_v1_bot.py` — `spread_cost` read before assignment → `UnboundLocalError` (swallowed).
- `bots/sajim_v2_bot.py` + `v2/risk/hummingbird.py` — guard `len(rates) < 10` but indexes
  `rates[-14..-1]` → `IndexError` on 10–14 bar feeds.
- `bots/prop_firm/prop_firm_challenge_bot.py` — `mt5.positions_get(magic=...)` invalid → `TypeError`.
- `scripts/bridge_supervisor.py` — calls a `Logger` object as a function → `TypeError` at startup.

## 6. Quant math & sizing issues

- Expectancy is numerically correct, but the documented formula ignores scratch/breakeven trades.
- Sharpe/Sortino computed on per-trade dollar PnL (not returns, un-annualized, no risk-free rate);
  Sortino divides by N instead of the downside count.
- MDD computed in list order, not time-sorted.
- `core/lot_calculator.py` non-MT5 fallback assumes point value = $1/lot → meaningless cloud sizing.

## 7. Web / API security gaps

- `web/app.py` `/api/client/execute` and `/close-trade` authenticate the user but **never verify
  `account_id` ownership** → cross-tenant trade placement.
- Investor + cTrader telemetry endpoints are public (no auth).
- `web/routes/client.py` `handle_bridge_sync` is unauthenticated and writes attacker-supplied signals.
- CORS `*`; non-constant-time admin compare; bare `dict` POST bodies → unhandled 500s.

## 8. Security hygiene

- **Good:** secret files are git-ignored; no committed credentials; no `eval/exec/pickle`/`shell=True`;
  no password logging.
- **Bad:** hardcoded API key (`core/app.py:21`), hardcoded demo-password bypass
  (`multi_account_manager.py:122`), plaintext MT5 password passed via child env / `--password` CLI,
  Supabase query-string injection, and a Fernet key derived from `SUPABASE_SERVICE_ROLE_KEY` (rotating
  that key silently undecrypts all stored MT5 passwords).

## 9. Test suite baseline

| Result | Count |
|---|---|
| PASS | 7 |
| FAIL | 7 |
| ERROR | 1 (auth) |
| SKIPPED (live MT5) | 1 |

Root causes: stale assertions after refactors, a new V1 edge-filter gate rejecting old fixtures,
missing `BEEP_MASTER_KEY`/`BEEP_API_KEY` in `.env`, and genuine drift in the Hummingbird order path.

---

### My notes

The single biggest issue is not any one bug — it is the **fabricated-success pattern**: the system
tells you it is connected, filled, profitable, and "verified" when it is not. That is the first
thing to fix, because it makes every other bug invisible. The concrete crash bugs are real but
mechanical and mostly one-line fixes.
