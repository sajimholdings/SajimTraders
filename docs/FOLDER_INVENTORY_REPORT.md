# SAJIM HOLDINGS — Full Folder Inventory

**Date:** 2026-09-16
**Auditor:** Claude Code (read-only inventory)
**Scope:** Entire `C:\Users\sajim\OneDrive\SAJIM HOLDINGS` folder on disk — not just the git-tracked repo. Every top-level file and directory, with file counts, sizes, and a one-line purpose per area.
**Method:** Directory listings, bounded `du`/`find` sizing, and light reads of config/README/docstrings to infer purpose. **No source files were modified. No secret values are reproduced in this report.**

> This is a *grounding pass* — "what is actually here." It does not re-verify the code bugs in
> `docs/FULL_REPO_AUDIT_REPORT.md` and does not render a security or data-integrity verdict. It does
> *flag* where sensitive files live (Section 5), with values redacted.

---

## 0. Top-level map

| Path | Size | Files | Purpose |
|---|---|---|---|
| `frontend/` | 396 MB | ~21,900 | Next.js 14 web app ("sajim-traders-portal") + `node_modules` (364 MB) + `.next` build (32 MB) |
| `data/` | 277 MB | 45 | Dukascopy XAUUSD historical bid CSVs (5 years, D1→M1) |
| `docs/` | 4.5 MB | 54 | Audit reports, playbooks, legal, ops manuals, conversation transcripts |
| `web/` | 1.2 MB | 49 | FastAPI gateway (`app.py`) + routes + a static frontend export |
| `core/` | 1.1 MB | 62 | Foundational quant & execution engines |
| `tests/` (also `test` symlink) | 990 KB | 98 | Backtest artifacts + pytest suites |
| `scripts/` | 668 KB | 57 | Audit, backtest, download, eval, and ops scripts |
| `vault/` | 592 KB | 36 | Git-ignored: research, archived bots, investor reports, flight recorder |
| `scratch/` | 417 KB | 5 | Throwaway test/screening scripts |
| `v2/` | 391 KB | 40 | Sajim V2 institutional quant framework |
| `bots/` | 297 KB | 15 | Production trading bots |
| `config/` | 44 KB | 7 | Credentials + trading whitelist (see Section 5) |
| `supabase/` | 16 KB | 1 | `schema.sql` — Postgres schema for the web backend |
| `download/` | 1 KB | 1 | Single D1 CSV sample |
| `.git/`, `__pycache__/` | 28 KB | — | VCS + Python bytecode cache |

**Root files** (not in any subdirectory):

| File | Size | Purpose |
|---|---|---|
| `broadcast_stream.jsonl` | 33 MB | Append-only JSONL telemetry stream (signal + deal events) |
| `overnight_execution.log` | 23 MB | 24/7 daemon execution log |
| `COMPLETE_CONVERSATION_HISTORY.md` | 2.1 MB | Full conversation-history dump (duplicated in `docs/`) |
| `run.py` | 20 KB | Master CLI operational cockpit |
| `mirage_pine_script_raw.txt` | 19 KB | Raw Pine Script for the "Mirage" strategy |
| `CLAUDE_CODE_HANDOVER.md` | 10 KB | Handover + code-audit brief for Claude Code |
| `README.md` | 7 KB | Repository overview |
| `HFM FREE CLASSES 1.zip` | 17 KB | Zip archive (course material) |
| `edge_matrix_status.json` | 1.5 KB | Edge-matrix scan status snapshot |
| `overnight_status.json` | 426 B | Overnight daemon status snapshot |
| `broadcast_active.json` | 164 KB | Active broadcast signals cache |
| `.env` / `.env.example` | 314 B / 739 B | Environment config (see Section 5) |
| `render.yaml` / `vercel.json` | 785 B / 198 B | Render (cloud) + Vercel deploy config |
| `requirements.txt` / `requirements-windows.txt` | 486 B / 212 B | Python dependencies |

---

## 1. Code — engines, framework, web, bots

### 1.1 `core/` (62 files) — foundational quant & execution engines
- **Bridges:** `mt5_bridge.py` (legacy MT5 terminal IPC), `ctrader_bridge.py` (cTrader Open API bridge), `supabase_bridge.py` (DB sync), `telegram_broadcaster.py` (Telegram).
- **BEEP quant:** `beep_core.py` (4 equations), `beep_signal_engine.py`, `beep_processor.py`, `beep_narrative.py`, `beep_broadcast.py`, `beep_matrix_scanner.py`, `beep_binary_quant_engine.py`, `tick_beep_engine.py`.
- **Math/risk:** `quant_evaluator.py` (expectancy/Sharpe/Sortino/DD), `lot_calculator.py`, `expectancy_tracker.py`, `confluence_engine.py`, `dealer_state_space.py` (particle filter), `sajim_regime_algos.py`, `trade_flight_recorder.py`, `signal_truth_tester.py`, `whitelist_manager.py`, `market_digest_generator.py`.
- **Ops/accounts:** `multi_account_manager.py`, `credential_vault.py` (Fernet-encrypted credential store), `mt5_login.py` (auto-login), `api.py` + `app.py` (gateway/bridge), `backtester.py`, `sajim_community_concierge.py`, `investor_reporting.py`.

### 1.2 `v2/` (40 files) — Sajim V2 framework
- Orchestration: `dual_orchestrator.py`, `sajim_v2_dual_bot.py`, `coexistence.py` (multi-bot gatekeeper), `coexistence_status.json`.
- `strategies/`: `young_surge_continuation.py`, `exhaustion_mean_reversion.py`, `mirage_liquidity_sweep.py`.
- `risk/`: `hummingbird.py` (peak harvest), `ratchet.py` (SL ratchet). `engine/`: `liquidity_sweep_engine.py`. `execution/`: `order_router.py`. `api/`: `telemetry_bridge.py`. `trend_duration_engine.py`, `strategy_base.py`.

### 1.3 `web/` (49 files) — API gateway
- `app.py` (FastAPI gateway), `server.py` (latent), `routes/admin.py`, `routes/base.py`, `routes/client.py`.
- `static/` — a built/exported frontend (`index.html`, `app.js`, `styles.css`, `_next/`, `assets/`, `404.html`).

### 1.4 `bots/` (15 files)
- `sajim_v1_bot.py`, `sajim_v2_bot.py`, `sajim_server_overnight.py`, `prop_firm/prop_firm_challenge_bot.py`.

### 1.5 `scripts/` (57 files)
- Audits: `audit_flight_recorder.py`, `audit_indices.py`, `audit_overnight_deals.py`, `audit_strict_overnight.py`, `audit_grand_confluence.py`.
- Backtests/data: `dukascopy_backtest_5y.py`, `dukascopy_backtest_pipeline.py`, `backtest_instant_kinetic_scalp.py`, `run_edge_matrix_backtest.py`, `download_dukascopy.py`.
- Eval/scan: `eval_m1_candidates.py`, `scan_m1_broker_spreads.py`, `check_additional_m1.py`, `evaluate_mirage_*.py`, `evaluate_trinity_confluence.py`.
- Ops: `bridge_supervisor.py`, `signal_generator.py`, `connect_headway.py`, `inspect_positions.py`, `purge_all_positions.py`, `local_mt5_bridge.py`, `hostinger_vps_setup.bat`, plus Telegram/EV-tester scripts.

### 1.6 `tests/` (98 files)
- Backtest dirs `test_001` … `test_010` (each with trades/metrics artifacts), `run_test_005.py`, `run_test_010.py`.
- `test_*.py` pytest suites (snipe filter, dealer state space, hummingbird, coexistence, system, etc.), `TEST_INDEX.md`, benchmark JSONs.

---

## 2. Frontend (`frontend/`, 396 MB)

- **Package:** `sajim-traders-portal` v2.1.0 — Next.js 14.2.5, React 18.3.1, Tailwind, lucide-react, `@vercel/analytics`.
- **Source (`src/`, 27 files):** `app/` (layout, page, globals.css), 14 components (`CockpitHeader`, `MetricHeroCard`, `ActiveTradeCard`, `SignalsQuickGrid`, `AuthModal`, `AccountConnectorModal`, `RiskModeSheet`, `GateScreen`, …), 2 hooks (`useCockpit`, `usePolling`), 9 lib modules (`api`, `supabase`, `storage`, `format`, `types`, …).
- **Bulk:** `node_modules/` 364 MB, `.next/` 32 MB (build artifacts — not source).

---

## 3. Data (`data/`, 277 MB; `download/`, 1 KB)

- **`data/dukascopy/`** — XAUUSD historical bid data (Dukascopy), 5-year span 2021-09-13 → 2026-09-12, per-year files at **D1, H1, H4, M5, M15, MN1**, plus consolidated `*_5y.csv` for each timeframe.
  - Largest: `xauusd_m1_5y.csv` (114 MB), `xauusd_m1-bid-*` (~22 MB/yr), `xauusd_m5_5y.csv` (20 MB).
  - Only **gold (XAUUSD)** is present — no FX-pair data despite multi-pair bots.
- **`download/`** — one sample file `xauusd-d1-bid-2026-09-01-2026-09-10.csv`.

---

## 4. Docs & Vault

### 4.1 `docs/` (54 files, 4.5 MB)
- **Audit/report markdown:** `FULL_REPO_AUDIT_REPORT.md`, `SYSTEM_ARCHITECTURE_AND_CODEBASE_REPORT.md`, `DUKASCOPY_5Y_BACKTEST_REPORT.md`, `GRAND_CONFLUENCE_AUDIT_REPORT.md`, `OVERNIGHT_QUANT_EXPECTANCY_REPORT.md`, `MIRAGE_*`, `M1_EDGE_AUDIT_REPORT.md`, `TREND_DURATION_FORECAST_ANALYSIS.md`, `EDGE_MATRIX_REPORT.md`, and others.
- **Governance/legal:** `SAJIM_QUANT_TRADING_PLAYBOOK.md`, `SAJIM_HOLDINGS_AGREEMENT.md`, `SAMMYS_4_CHECK_RISK_POLICY.md`, `BEEP_IP_LICENSING_AGREEMENT.md`, `BEEP_API_INTEGRATION_GUIDE.md`.
- **`company_operations/` (14 files):** ops manual, team roles, business roadmap, Hostinger VPS runbook, FTMO/prop acquisition playbook, central signal hub, and per-person cards (Sammy, Alu, Arnold, Tete, Val).
- **`conversation_history/` (18 files):** session/subagent transcripts (largest ~914 KB).

### 4.2 `vault/` (git-ignored, 592 KB, 36 files)
- `investor_reports/` — `investor_audit_summary.json` + `trade_ledger.csv` (4 deals).
- `flight_recorder/` — currently **empty**.
- `archived_bots/` — `sajim_omniverse_bot.py`, `live_quant_cent_executor.py`, `market_milker.py`, `prop_firm/`.
- `vault_original_beep/` — `ORIGINAL_BEEP_SPECIFICATION_v1.0.md`, `raw_beep_equations.py`.
- Research markdown (`BEEP_MATHEMATICAL_FOUNDATION…`, `THE_MATH_OF_COLLAPSE…`), `Meta AI/` + `Meta AI.zip`, and audit-result JSONs (`grand_confluence_audit_results.json`, `signal_truth_vault.json`, etc.).

---

## 5. Sensitive-file index (values redacted)

These files hold real credentials or personal data. Listed by path + purpose only — **contents not reproduced**.

| Path | Contains |
|---|---|
| `.env` | Supabase URL, anon key, **service-role key** (real values) + Headway affiliate URL |
| `config/broker_config.json` | **Plaintext MT5 passwords** for 3 accounts (2 Headway-Demo, 1 Headway-Real "cent") + terminal path |
| `config/telegram_config.json` | **Telegram bot token** + channel IDs |
| `config/client_accounts.json` | MT5 account IDs, owner names, balances, broker server, one pending-order record |
| `frontend/.env.local` | Next.js env (affiliate/URL vars) |
| `config/master_trading_whitelist.json` | Trading whitelist/blacklist (not secret, but operational config) |
| `vault/investor_reports/` | Trade ledger + investor summary (financial records) |

Git-hygiene note: `config/broker_config.json`, `config/telegram_config.json`, `config/client_accounts.json`, and `vault/` are in `.gitignore` and currently untracked; `.env` is git-ignored. These secrets are **on disk in plaintext** and sync via OneDrive, but are not committed to git.

---

## 6. Runtime state (currently DRY_RUN / simulated)

- `overnight_status.json` — `mode: "DRY_RUN"`, `account: 0`, `equity/balance/free_margin: 0.0`, no open positions.
- `v2/coexistence_status.json` — default `balance/equity = 10000.0` (USD), zero positions, breaker inactive.
- `edge_matrix_status.json` — a completed 204-front edge scan (last run 2026-09-09).
- `broadcast_stream.jsonl` (33 MB) — append-only JSONL of `SIGNAL_GENERATED` / `DEAL_WIN` / `DEAL_LOSS` events, including broadcast text. Contains synthetic-looking deal tickets (e.g. `999888777`, `999111`).
- `overnight_execution.log` (23 MB) — daemon log; latest entries show whitelist hot-reloads, edge-filter skips, and a simulated `LOSS DETECTED` on `Deal #999111`.

---

## 7. Totals

| Category | Approx size |
|---|---|
| Frontend deps/build (`node_modules` + `.next`) | 396 MB |
| Historical market data (`data/dukascopy`) | 277 MB |
| Runtime logs/streams (root JSONL + log) | ~57 MB |
| Docs + conversation transcripts | ~6.5 MB |
| Source code (core, v2, web, bots, scripts, tests) | ~5 MB |
| Vault + config + scratch + supabase + download | ~1.1 MB |

**Bottom line:** the "real" codebase is small (~5 MB across ~300 Python/TS files); most of the ~740 MB on disk is frontend dependencies, five years of XAUUSD historical data, and telemetry/log output.

---

*Report ends. Read-only inventory; no files were modified and no secret values were copied.*
