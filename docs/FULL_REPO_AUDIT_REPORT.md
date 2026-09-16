# SAJIM HOLDINGS — Full Repository Audit Report

**Date:** 2026-09-16
**Auditor:** Claude Code (handoff audit, read-only)
**Scope:** Entire repository — 131 active Python source files across `core/`, `v2/`, `bots/`, `web/`, `config/`, `scripts/`, `tests/`, plus `run.py`, `render.yaml`, `requirements.txt`, and secret-hygiene.
**Method:** Direct line-level review of the cTrader migration path + four parallel read-only audit agents (core engines, bots/strategies, web/config/scripts, test-suite runner) + git secret-hygiene check. No source files were modified.

---

## 0. Verdict

**⛔ NOT PRODUCTION-READY. Do not route live capital (cTrader demo or MT5) through this codebase in its current state.**

The single most important finding is **systemic, not a single bug**: several independent subsystems fabricate success — they report "connected", "filled", "CONFIRMED", or "verified" when no order reached a broker, no data was received, or no real PnL exists. A live handoff built on this would look green on the dashboard while trading nothing or trading wrongly.

---

## 1. Health Scores

| Subsystem | Score /10 | One-line basis |
|---|---|---|
| cTrader Bridge (`core/ctrader_bridge.py`) | **2** | Sandbox stub — no Open API protocol, silent degrade-to-sandbox returns `True` |
| Multi-bot concurrency (`v2/coexistence.py`, orchestrator) | **3** | 50% breaker (not 5%), no cTrader breaker path, cross-broker KeyError, no locks |
| Quant math & sizing (`quant_evaluator`, `lot_calculator`) | **4** | EV/PF correct; Sharpe/Sortino non-standard; cloud lot sizing is a stub |
| Core engines (`core/beep_*`, `api.py`, `backtester`, etc.) | **3** | Correct SMC core, but fabricated telemetry, dead MT5 order path, threshold rewrites |
| Bots & V2 strategies | **3** | Prop-firm bot unimportable + stub live branch; unclosed-bar gates; verified IndexError/UnboundLocalError |
| Web / API gateway | **3** | Auth gaps, cross-tenant trades, fabricated telemetry, CORS `*` |
| Tests | **4** | 7/16 suites pass; stale assertions + missing env keys |
| **Overall** | **~3 / 10** | Pre-production demo state |

---

## 2. Critical findings (must-fix before any live capital)

### 2.1 The cTrader migration is not real
- `core/ctrader_bridge.py` does **not** implement Spotware Open API 2.0. `_authenticate_session()` sleeps and returns `True` (`:205-211`); `_heartbeat_worker`/`_rx_worker` are `pass`/`sleep` (`:213-229`); `send_order()` fabricates a ticket from `time.time()` and never transmits (`:309`); `_reconcile_account_state()` is `pass` (`:446-448`). The `protobuf` + `websockets` deps are never used.
- On **any** auth/connection failure, `connect()` sets `simulation_mode=True` and **returns `True`** (`:193-203`). Callers conclude the broker is connected while nothing can trade.

### 2.2 The execution path is still Windows/MT5-bound
- Unconditional top-level `import MetaTrader5` (crashes on Linux/Render) at **~20 sites**, including every file in the "cloud" execution chain:
  - `v2/execution/order_router.py:13`, `v2/dual_orchestrator.py:33`, `v2/sajim_v2_dual_bot.py:30`, `v2/risk/hummingbird.py:13`, `v2/risk/ratchet.py:18`, `bots/sajim_server_overnight.py:35`, `bots/sajim_v1_bot.py:32`, `bots/sajim_v2_bot.py:39`, `bots/prop_firm/prop_firm_challenge_bot.py:41`
  - `core/beep_signal_engine.py:33`, `core/beep_binary_quant_engine.py:21`, `core/market_digest_generator.py:23`, `core/expectancy_tracker.py:12`, `core/trade_flight_recorder.py:28`, `core/signal_truth_tester.py:23`
- `v2/__init__.py:18` imports `v2.sajim_v2_dual_bot` (which imports MT5), so `import v2.strategies` / `v2.trend_duration_engine` / `v2.api` all fail on Linux even though the strategy files themselves are MT5-free.
- `run.py dual --broker ctrader` imports `dual_orchestrator` (→ MT5) and crashes **before** the cTrader branch runs.

### 2.3 Fabricated success / fabricated data (systemic)
- `core/api.py:542` uses `mt5.ORDER_BUY` (not a real attribute) → `AttributeError` swallowed at `:566-567` → `/v1/mt5/order` **always** returns HTTP 200 `"SIMULATED_ORDER_CONFIRMED"`. Live execution can never place a trade and never reports failure.
- `core/investor_reporting.py:62-70` seeds five **hardcoded fake deals** when there is no real ledger; `web/app.py:323-354` serves them publicly as "verified" equity/expectancy.
- `core/multi_account_manager.py:579-581` hardcodes `today_pnl=4.35`, `today_pnl_pct=20.7` for a specific account; `:496` defaults balance to a magic `20.98`.
- `web/routes/admin.py` returns fabricated `balance=99.0`, `equity=94.04`, `v1_count=5`, and hardcoded `"92.6%"`/`"87.1%"` win rates with `"system_online": True` and `"terminal_bridge": "CONNECTED"`.
- `core/beep_broadcast.py:735-745` hardcodes `"92%"/"89%"/"86%"` win probabilities.
- `core/mt5_bridge.py:76-82` returns a **hardcoded 14-price fake series** when MT5 is absent, which `run_live_cycle` then trades on.
- `core/beep_processor.py:474-477` silently rewrites its own documented thresholds (`min_snipe_score 55→48`, `min_relative_volume 1.20→0.65`, `min_kinetic_mass 35→30`).
- `core/backtester.py:77-82` generates synthetic data (`generate_benchmark_market_data`) and writes it to `report.md` as if real, with a hardcoded gold price (2320.0) for all FX pairs and a shared `random.seed(42)` that makes "uncorrelated" pairs identical.

### 2.4 Risk controls are broken or self-contradictory
- Circuit breaker is **50%, not 5%**: `v2/coexistence.py:47` `MAX_DAILY_DRAWDOWN_PCT = 0.50`, while the docstring/handover/branding say 5%; the cTrader path never evaluates the breaker at all (`refresh_account_state` `:109-151` lacks the logic that only lives in `refresh()`).
- `bots/prop_firm/prop_firm_challenge_bot.py:139` measures total drawdown from **current balance** (not challenge high-water mark) → after +10% profit the account can lose ~15% before the breaker fires, breaching the 10% prop rule. `peak_equity` (`:82-83`) is computed but never read.
- `bots/prop_firm/prop_firm_challenge_bot.py:240-241` — the `--live` branch is a `print()` stub; no `order_send`.
- `bots/prop_firm/prop_firm_challenge_bot.py:43` — `from sajim_omniverse_bot import UniversalLotCalculator` → **ModuleNotFoundError** (verified); the bot cannot import at all.
- `bots/sajim_v1_bot.py:199-205` — `is_cent` is true for any `.c` symbol or "Headway" server, giving a **5% equity risk ceiling per trade** vs the documented 2% cap, with a `+3` concurrency bonus exposing up to 8×5% at once.

### 2.5 Verified correctness bugs
- `v2/execution/order_router.py:130` — `order_type` is referenced but never assigned → **NameError** in the MT5 branch.
- `core/dealer_state_space.py:251-253` — `delta_p` is identically 0.0 every tick (subtracts `last_mid` set to the same `mid` one line earlier) → flow classifier permanently degenerate.
- `core/confluence_engine.py:321-326` — `is_bear_exhausted` is never read; the ternary makes `action` **BUY unconditionally**, emitting a buy for a mean-reversion short.
- `bots/sajim_v1_bot.py:652` — `spread_cost` read before assignment → **UnboundLocalError** swallowed by `except: pass` → the Dealer particle filter is never fed a tick (verified).
- `bots/sajim_v2_bot.py:295` + `v2/risk/hummingbird.py:29` — guard is `len(rates) < 10` but code indexes `rates[-14..-1]` → **IndexError** on 10–14 bar feeds.
- `bots/prop_firm/prop_firm_challenge_bot.py:207` — `mt5.positions_get(magic=...)` is not a valid API arg → **TypeError** every iteration (verified against installed MT5).
- `scripts/bridge_supervisor.py:58` — calls a `Logger` object as a function → **TypeError** at startup; supervisor never manages a worker.

---

## 3. Findings by subsystem

### 3.1 cTrader bridge (`core/ctrader_bridge.py`)
- Stub protocol (no Protobuf, no heartbeat, no reconnect) — see 2.1.
- `send_order` ticket collision `% 100000000`; open-position floating PnL always 0 (never marked-to-market); `close_position` PnL ignores pip value/account currency.

### 3.2 Concurrency (`v2/coexistence.py`, `v2/dual_orchestrator.py`, `v2/execution/order_router.py`)
- 50% breaker; no cTrader breaker; `net_daily_pnl = closed + min(0, floating)` ignores floating profits.
- Cross-broker schema mismatch: `check_pre_entry_clearance` reads `pos["type"]`/`pos["magic"]`, which cTrader dicts lack → **KeyError** with ≥1 open position.
- No lock anywhere in the gatekeeper despite concurrent V1/V2 signals; `save_status` remove-then-rename is non-atomic.
- Docstring vs constants all disagree (6 vs 2 positions, 500% vs 200% margin, 2 vs 1 cluster, 5% vs 50% DD).
- `protected_capital_floor` hardcoded dollar tiers, only ratcheted in the MT5 `refresh()`.

### 3.3 Quant math & sizing (`core/quant_evaluator.py`, `core/lot_calculator.py`)
- Expectancy is numerically correct (= net/total) but doc formula `(1−W)×AvgLoss` ignores scratches.
- Sharpe/Sortino computed on per-trade dollar PnL (not returns, un-annualized, no risk-free rate); Sortino divides by N not downside count.
- MDD computed in list order, not time-sorted.
- `lot_calculator.py:43-60` non-MT5 fallback assumes point value = $1/lot → **meaningless cloud sizing** (this is the path that runs on Linux).
- `evaluate_multi_bot_breakdown` divides capital by 3 → inflated per-bot DD%.

### 3.4 Bots & strategies (`bots/`, `v2/strategies/`)
- Prop-firm bot: unimportable, stub live branch, wrong DD baseline, `positions_get(magic=)` TypeError (2.4/2.5).
- Unclosed-bar gates: `mirage_liquidity_sweep`, `young_surge_continuation`, `exhaustion_mean_reversion` and `core/beep_signal_engine.py` all evaluate `bars[-1]` (the forming candle) → repaint + repeated re-emission; entry price is a live close sent as a market deal.
- Whitelist bypass: `is_pair_approved` wrapped in `try/except: pass`; `whitelist_manager` never enforces timeframe-scoped blacklist entries (9 of 16 carry `_M15` etc. but callers pass plain symbols) — verified against `config/master_trading_whitelist.json`.
- `trend_duration_engine.py` maturity ratio is a function of feed length; `memory` never used; `calculate_hma` is a Python loop, not "vectorized".
- `liquidity_sweep_engine.py` re-simulates 150 bars per evaluate() per symbol×tf×cycle; no dedupe → same sweep re-emitted each cycle.
- `sajim_v2_bot.py:501-502` — 6-hour deal window with no startup seed → restart replays prior deals and pollutes the streak→lot multiplier.
- SL/TP copied into orders with no `sl < entry < tp` validation and no spread/min-distance check (V1 and V2).

### 3.5 Core engines (`core/`)
- `api.py`: dead live-order path (2.3), binds 0.0.0.0 despite "localhost" banner, CORS `*`, unguarded `float()` casts, returns `LIVE_MT5_EXECUTED` without checking `retcode == DONE`.
- `beep_signal_engine.py`: signal from `rates[-1]` (repaint), cached by un-finalized bar timestamp; `phi_energy` divides by raw-price spread → FX outranks gold ~10,000×; `htf_map["D1"]` makes the D1 macro gate compare D1 to itself (no-op).
- `sajim_regime_algos.py:232,237` — "True Range" uses current close so it collapses to plain bar range; `:247-250` `kappa` threshold is unreachable with realistic H4/M15 ATR ratios → `RANGE_COMPRESSION`/HUMMINGBIRD params dead.
- `beep_processor.py` — Wilder ATR is a simple mean; `k_base` EMA includes `k_cur` (self-referential, decay rarely triggers); low-volume chop filter fully disabled when volume has no variance.
- `beep_core.py:216,220` — advertised R:R not achieved (SWING real R:R ~0.80); `statistics.mean` with no empty guard.
- `beep_binary_quant_engine.py:147-176` — PnL applied with no lot/contract multiplier, added to a balance defined as cents.
- `dealer_state_space.py:448-470` — confirmation gate fails **open** on missing data (`rates=None` → `candle_confirmed=True`).
- `multi_account_manager.py` — fabricated PnL (2.3); `:122` hardcoded `"demo1234"` bypass; unguarded read-modify-write on one JSON from concurrent endpoints; `:338` hardcodes a 100-unit contract (under-sizes FX by 1000×).
- `core/app.py:21` — live gateway API key hardcoded (`sajim-tete-live-key-9921`) and published in `docs/BEEP_API_INTEGRATION_GUIDE.md:69`.
- `core/__init__.py:31-87` — 13 `except Exception: X = None` blocks turn failures into `None` while `__all__` still advertises names; importing any core module runs `api.py` engine construction as an import side effect.

### 3.6 Web / API (`web/app.py`, `web/routes/`, `web/server.py`)
- `web/server.py` (latent, not the deployed entrypoint): **zero auth** on trade/close/delete/toggle routes; CORS `*`.
- `web/app.py` (live): `/api/client/execute` and `/close-trade` authenticate the user but **never verify `account_id` ownership** → cross-tenant trade placement/closing. Investor + cTrader telemetry endpoints (`:323-354`) are **public** (no `get_current_user`).
- `web/routes/client.py` — unauthenticated `handle_bridge_sync` writes attacker-supplied signals into the file `/api/client/signals` serves as tradeable; `ResilientAccountManager` fallback fabricates `success: True, ticket: 777123`; `win_probability`/`gain_estimate` invented from symbol-name heuristics.
- `web/routes/base.py:21-29` — state paths point at a non-existent `logs/` dir; endpoints serve hardcoded defaults.
- `web/app.py` — CORS `*`, non-constant-time admin compare, bare `dict` POST bodies → unhandled `AttributeError`/`ValueError` 500s.

### 3.7 Security hygiene (supplementary check)
- **Good:** `.env`, `config/broker_config.json`, `config/telegram_config.json`, `config/client_accounts.json` are all git-ignored and untracked; `.env.example` has placeholders only; no `eval/exec/pickle/shell=True` in `core/`; no password logging.
- **Bad:** hardcoded API key (`core/app.py:21`), hardcoded demo-password bypass (`multi_account_manager.py:122`), plaintext MT5 password passed via child env / `--password` CLI (`scripts/bridge_supervisor.py:94,99`), Supabase query-string filter injection (ids not URL-encoded, `core/supabase_bridge.py`), Fernet key derived from `SUPABASE_SERVICE_ROLE_KEY` (rotating it silently undecrypts all stored MT5 passwords).

### 3.8 Test suite (baseline)
| Result | Count | Files |
|---|---|---|
| PASS | 7 | snipe_filter, dealer_state_space, dynamic_opportunist, kinetic_baseline_exit, mirage_sweep, range_boundary_harvester, v2_exclusive_and_sanitizer |
| FAIL | 7 | beep_multi_mode, chameleon_dual_regime, clean_plate_and_dynamic_milker, v2_hummingbird_harvest, v1_v2_coexistence, web_server, system |
| ERROR | 1 | test_beep_stamp_api (401 auth) |
| SKIPPED (live MT5) | 1 | test_audit_fixes |

Root causes: (1) stale assertions after refactors (copy text `"Take Profit Reached"`, `tp_rr_ratio` 1.2, `Hummingbird_Peak` comment, `styles.css` split); (2) new V1 edge-filter gate rejecting old fixtures (EURUSD/M15, GBPNZD.c) — arguably correct behavior; (3) missing `BEEP_MASTER_KEY`/`BEEP_API_KEY` in `.env`; (4) genuine drift in the Hummingbird ratchet order path.

---

## 4. Recommended fixes (priority order)

1. **Stop fabricating success.** Fix `core/api.py` (`mt5.ORDER_TYPE_BUY/SELL` + check `retcode`), remove the silent sandbox-`return True` in `ctrader_bridge`, remove fabricated PnL/win-rates/investor seeds, and make `mt5_bridge` fail loudly instead of returning a fake price series.
2. **Make MT5 imports lazy/optional** across the ~20 sites and fix `v2/__init__.py`/`core/__init__.py` so the strategy/API modules import cleanly on Linux.
3. **Fix the circuit breaker** to 5%, move breaker + high-watermark logic into `refresh_account_state()` so cTrader enforces it, and normalize cTrader positions to `type`/`magic`.
4. **Fix or quarantine the prop-firm bot** — repair the import, `positions_get()` call, live branch, and DD baseline; it is currently non-functional.
5. **Fix verified crashes:** `order_type` (NameError), `dealer_state_space` `delta_p`, `confluence_engine` inverted action, V1 `UnboundLocalError`, `hummingbird`/V2 short-feed `IndexError`, `bridge_supervisor` Logger call.
6. **Fix the sizing path:** replace `lot_calculator`'s $1/lot fallback with real point-value math and stop the near-zero-stop → max-lot edge in the prop-firm bot.
7. **Web auth:** add `user_id` ownership checks to execute/close, require auth on investor/ctrader endpoints, add Pydantic models, fix CORS and use `hmac.compare_digest`.
8. **Real cTrader Open API implementation** (Protobuf auth → heartbeat → order/deal messages → reconnect) as a separate scoped task, or rename the stub so it cannot be mistaken for a live bridge.
9. **Bring the tests green** by updating stale assertions, injecting the BEEP keys into the test env, and adding fixtures for the edge-filter gate.

---

## 5. What was verified clean

- Secret files are git-ignored; no committed credentials; no `eval/exec/pickle`/`shell=True`/`yaml.load`; no password logging.
- `core/dealer_state_space.py` particle-filter core (likelihood, weight normalization, `n_eff`, resampling) is a correct SMC bootstrap filter.
- `core/backtester.py` `run_backtest` has no look-ahead and tests SL before TP on same-bar ambiguity; `core/confluence_engine.py` Wilder-ATR recursion is correct.
- `pre_entry_hook` wiring (V1 → `check_pre_entry_clearance`) is signature-correct.
- 7 test suites (41 methods) pass with MT5 mocked.

---

*Report ends. This is a read-only audit; no source files were modified.*
