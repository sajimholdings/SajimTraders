# What Was Done — Declutter, Viability Audit & Merge Map

**Date:** 2026-09-16
**Status:** Local changes only — **nothing has been pushed.** Awaiting your authorization.

This report tells you exactly what I changed on `C:\Users\sajim\OneDrive\SAJIM HOLDINGS` and what I
found, so you can review before authorizing a push to GitHub.

---

## TL;DR — three things you need to know

1. **Main folder decluttered** — deleted ~400 MB of regenerable build artifacts, archived unneeded
   dumps, expanded `.gitignore`, and untracked 5 runtime telemetry files from git.
2. **Your three copies of the trading system are resolved** — `C:\…\SAJIM HOLDINGS` is canonical (a
   strict superset); the two copies inside `F:\Tete\SAJIM STRATEGIES` are stale snapshots.
3. **Viability audit (your "is it a scam?" question):** the strategy *engines* are largely **real**,
   but the **reporting/analytics layer fabricates favourable numbers**. That layer is what must be
   fixed before any number is shown to an investor or client.

---

## 1. Declutter — what changed on the main folder

| Action | Items | Effect |
|---|---|---|
| Deleted build artifacts | `frontend/node_modules`, `frontend/.next`, all `__pycache__/` | ~400 MB freed; regenerable via `npm install` / `npm build` |
| Archived (kept on disk, git-ignored) | `COMPLETE_CONVERSATION_HISTORY.md` (root + docs), `HFM FREE CLASSES 1.zip`, `mirage_pine_script_raw.txt` | moved to `archives/` (recoverable, not deleted) |
| Moved to `scripts/` | `scratch/screen_universe_friction.py`, `scratch/test_universe_lot_sizing.py` | consolidated |
| Untracked from git (kept on disk) | `broadcast_active.json`, `broadcast_stream.jsonl` (33 MB), `overnight_status.json`, `edge_matrix_status.json`, `v2/coexistence_status.json` | `git rm --cached` — runtime state no longer tracked |
| `.gitignore` additions | `.claude/`, `data/`, `download/`, `scratch/`, runtime telemetry, `archives/` | prevents re-adding clutter |

Left in place on purpose: the `test` symlink (→ `tests/`), and the runtime telemetry files on disk
(the running system still writes them — they are just no longer in git).

---

## 2. Canonical copy decision (3 → 1)

The live trading system exists in three places:

| Copy | What it is | Verdict |
|---|---|---|
| `C:\…\SAJIM HOLDINGS` | main repo, on `main` | **CANONICAL** — superset of the other two |
| `F:\…\sajim_holdings_sandbox\` | full copy, no git | stale snapshot (subset) |
| `F:\…\strategies\SajimTraders\` | full copy + own git | stale snapshot (subset) |

Evidence: main's `core/` has three files the others lack (`ctrader_bridge.py`, `investor_reporting.py`,
`quant_evaluator.py` — the newest work), while neither F: copy has any `core/` file main lacks.

**Before the two F: copies can be deleted**, these unique items must be preserved:
- `sajim_holdings_sandbox/tests/*.py` — 16 benchmark test scripts not in main's `tests/`.
- `sajim_holdings_sandbox/MT5_Sajim/MQL5/` — the MQL5 EA source (the rest of `MT5_Sajim/` is a 260 MB
  MT5 terminal install — runtime, not source).
- `strategies/SajimTraders/sajim_strategy.yaml` — the only strategy manifest.

---

## 3. Viability audit — real vs fabricated

You asked: *are the strategies we're pushing viable, or "just any scam"?* Short answer: **the strategy
engines are largely real; the reporting layer is not.**

### Genuinely viable — carry forward

- **Live bots** — V1 / V2, and the **BEEP** core / signal / processor math.
- **Dukascopy 5-year backtest** — real; it honestly publishes losses.
- **Platform data + analytics core** — Parquet layer, `metrics.py`, the real Monte Carlo *engine*, and
  the MT5 / Backtrader / Pine adapters (no synthetic fallback).
- **Real research strategies** — `Deriv UpDown`, `BTC data collector`, `GoldOrb`, `Scalper1` (MQL5 EA),
  `SunriseOgle` (Backtrader), `BEEP_MASTER_PACKAGE`.

### Quarantine as fabricated — the "scam" signature

| File | What is wrong |
|---|---|
| `core/ctrader_bridge.py` | Stub — `connect()` silently returns `True` in simulation mode; `render.yaml` points production at it |
| `v2/execution/order_router.py` | `order_type` never assigned → `NameError` (cannot actually place an order) |
| `core/api.py` | Returns `SIMULATED_ORDER_CONFIRMED` for every order — live execution can never trade |
| `core/investor_reporting.py` | Seeds 5 hardcoded fake deals when no real ledger exists |
| `core/beep_broadcast.py` / `web/routes/client.py` | Hardcoded 86 / 89 / 92% win probabilities |
| `smc_daemon_project` | Scripted always-win simulator |

### Most severe — the ranking layer invents its numbers

`universe_matrix.py` hardcodes base Sharpe / win-rate / PF and generates a **synthetic trade sequence**
(`np.random`, seed 42) that feeds the Monte Carlo engine — so the "720-node" matrix, fragility index,
and risk-of-ruin are computed over *invented* trades, not real ones. `timeframe_matrix.py` hardcodes 4 of
6 evaluators, and the leaderboard is a literal string.

The published numbers are systematically **more favourable than the measured runs** — losses deflated,
drawdowns halved (e.g. `GoldOrb_ORB`: **0 real trades** shown as 2 trades / 50% WR / +$160;
`GoldPullbackAI` Sharpe 0.24 shown as 0.84).

**Bottom line:** the engines are real; the numbers shown to investors are not. Fixing this is a bounded
set of file edits — listed in `docs/RESTRUCTURE_AND_MIGRATION_PLAN.md` (Track C3).

---

## 4. Security note

`F:\Tete\SAJIM STRATEGIES\sajim_quant\adapters\mql5\mt5_adapter.py:101-104` embeds a **plaintext MT5
login + password** written into the generated tester `.ini`. This joins the plaintext credentials
already flagged (`.env`, `config/broker_config.json`, `config/telegram_config.json`). Recommend rotating
all of these and moving them to a secret store / env vars before any public push.

---

## 5. Merge map (target company architecture)

`SAJIM STRATEGIES` content maps into the monorepo as follows (full detail in the plan doc):

| Source | Destination |
|---|---|
| `sajim_quant/` | `backtest/` (schema, adapters, analytics, data) |
| `sim/` (Next.js dashboard) | `backtest/sim/` |
| `data/*.json` matrices | `data/matrices/` |
| `data_downloader/` | `tools/dukascopy_downloader/` |
| research strategies | `strategies/research/…` |
| `GoldOrb` (MQL5 EA) | `strategies/ea/gold_orb/` |
| `files/` (Deriv edge detector) | `research/deriv_edge_detector/` |
| `SajimTraders/` + `sandbox/` | dedupe into the top-level app, then delete |

**Important correction from the map:** `files/` is *not* a Dukascopy downloader — it is a Deriv
synthetic-indices edge detector, and `files/.venv/` is the interpreter the platform README tells you to
run. Only 2 of 12 strategy dirs have the `sajim_strategy.yaml` manifest that the discovery scanner needs.

---

## 6. What is NOT done yet (deliberately)

- **The actual F: → monorepo merge** (moving `sajim_quant/`, `sim/`, strategies; deleting the 2 stale
  copies). This is a large cross-drive move — I'll do it in the next step, after you've seen this report.
- **Fixing the fabricated reporting layer** (`universe_matrix.py`, `timeframe_matrix.py`, leaderboard,
  `ctrader_bridge`, `order_router`, `api.py`).
- **The cTrader migration and Render go-live** (Tracks B & C in the plan).

---

## 7. Before you authorize the push

On your go-ahead I will, in order:
1. Stage only my changes (`.gitignore`, the untracked runtime files, the moved `mirage_pine_script_raw.txt`, this report).
2. Commit with a clear message.
3. `git push origin main` — local `main` is currently 5 commits ahead of `origin`, plus these uncommitted changes.

**Nothing has been pushed.** Note: the 33 MB `broadcast_stream.jsonl` and other runtime files will no
longer be in future pushes, but their old copies remain in git *history* (removing them from history
would require a rewrite — not recommended).
