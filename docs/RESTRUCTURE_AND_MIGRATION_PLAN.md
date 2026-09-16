# SAJIM HOLDINGS — Restructure, cTrader Migration & Render Go-Live Plan

**Status:** Plan (for founder sign-off before any file moves)
**Date:** 2026-09-16
**Prepared by:** Claude Code (background audit session)

This is the master plan for the second task. It covers three tracks in dependency order:

- **Track A — Restructure & declutter** (merge `SAJIM STRATEGIES` in, collapse three copies of the
  system into one, strip build artifacts, reorganize into a company folder).
- **Track B — cTrader backtest migration** (replace the stub bridge with a real Open API client and
  an adapter that emits the Universal Trade Schema).
- **Track C — Render live processing** (make the code portable, honest, and safe, then deploy).

Everything below is grounded in two already-committed artifacts in this repo:
`claude_thought/` (analysis) and `docs/FOLDER_INVENTORY_REPORT.md` (disk map). This plan does **not**
touch any code or move any file — it is the roadmap for doing so.

---

## 0. Where we are (one picture)

Two source locations exist today:

| Location | What it actually is | Size |
|---|---|---|
| `C:\Users\sajim\OneDrive\SAJIM HOLDINGS` | Main trading system (BEEP, V1/V2 bots, web portal, cTrader stub) | ~740 MB |
| `F:\Tete\SAJIM STRATEGIES` | Benchmarking platform (`sajim_quant`, `sim` leaderboard, `data/`, `tests/`) | ~1.5 GB+ (data) |

**The single most important discovery:** the live trading system exists in **three copies**:

1. `C:\Users\sajim\OneDrive\SAJIM HOLDINGS` (git, on `main`) — the canonical source.
2. `F:\Tete\SAJIM STRATEGIES\sajim_holdings_sandbox\` — a full copy (`bots/`, `core/`, `config/`,
   `vault/`, `run.py`, `overnight_execution.log`), **not** a git repo, files dated today 11:00.
3. `F:\Tete\SAJIM STRATEGIES\strategies\SajimTraders\` — a full copy with its own `.git`,
   `broadcast_stream.jsonl` (33 MB), `frontend/`, `supabase/`, dated today 13:45.

Copies #2 and #3 are **not stale** — their timestamps are today's. They must be diffed against #1
before anything is deleted (Track A, Phase A1). This is both the biggest clutter and the biggest
data-loss risk in the whole engagement.

**Where the "clutter" is** (measured, `SAJIM STRATEGIES`):

- 39 × `node_modules`, 2 × `.next`, 1,845 × `__pycache__`, 174 × `dist`, 10 × `build`, 2 × venvs.
- 6 nested standalone `.git` repos inside `strategies/` (vendored bots: `backtrader-pullback-window-xauusd`,
  `Deriv trading`, `GoldOrb`, `SajimTraders`, `Scalper1`, `XAUUSD_TRADING_ASISTENT_AI`).
- `strategies/` = 45,744 files, mostly a Node/SST/Rust build from the three `Deriv*` dirs + `SajimTraders`.
- `files/` (21k) and `data_downloader/` (7.7k) are two small Dukascopy download utilities whose file
  counts are almost entirely their own `.venv`/`__pycache__`.
- `data/` = 1.5 GB of Dukascopy CSVs + Parquet + edge matrices (`strategy_universe_matrix.json` 2.9 MB).

**The system itself is not production-ready** (audit score ~3/10): cTrader bridge is a stub, several
subsystems report fabricated success, the daily breaker is 50% not 5%, and ~20 sites unconditionally
`import MetaTrader5` (crashes on Linux/Render). See `claude_thought/04_audit_findings.md`.

---

## 1. Target architecture (the "company folder")

One canonical monorepo, no nested repos, no build artifacts under version control, secrets only as
git-ignored files / env vars:

```
SAJIM HOLDINGS/
├── README.md                      # company + system overview, quickstart
├── pyproject.toml                 # one package: `sajim`
├── requirements.txt               # linux (Render) deps
├── requirements-windows.txt       # + MetaTrader5 extras (local only)
├── .env.example                   # template; real .env git-ignored
├── docs/
│   ├── audits/                    # FULL_REPO_AUDIT, FOLDER_INVENTORY, past reports
│   ├── architecture/              # system architecture, BEEP framework, benchmarking methodology
│   ├── plans/                     # this plan + per-track detailed plans
│   ├── operations/                # company_operations, playbooks, legal
│   └── claude_thought/            # analysis notes (kept as the "why" record)
├── core/                          # shared quant: BEEP engine, metrics, lot sizing, regime algos
├── strategies/                    # the bots — one dir each, NO nested .git
│   ├── beep/                      # BEEP_MASTER_PACKAGE
│   ├── sajim_v1/                  # flagship V1 bot
│   ├── sajim_v2/                  # Surge + Reversion cartridges
│   ├── prop_firm/                 # challenge bot
│   ├── overnight/                 # 24/7 daemon
│   └── research/                  # backtrader-pullback, smc_daemon, GoldOrb, Scalper1,
│                                  # Deriv*, XAUUSD assistant (benchmark candidates)
├── adapters/                      # engine adapters → Universal Trade Schema
│   ├── mt5/                       # MT5 headless adapter + SajimLogger.mqh
│   ├── ctrader/                   # cTrader Open API client + adapter (Track B)
│   ├── backtrader/                # python reference adapter
│   ├── vectorbt/
│   └── pine/                      # TradingView CSV importer
├── execution/                     # order_router, dual_orchestrator, coexistence gatekeeper
├── backtest/                      # the benchmarking engine (formerly sajim_quant)
│   ├── schema/                    # frozen Universal Trade Schema (Pydantic)
│   ├── metrics/                   # Sharpe, Sortino, Calmar, MaxDD, MAE/MFE, PF, WR
│   ├── universe/                  # universe matrix + discovery scanner
│   ├── data/                      # dukascopy downloader + parquet cache (files/ + data_downloader merged)
│   └── sim/                       # Next.js leaderboard (formerly sim/)
├── web/                           # trading portal: FastAPI (app.py, routes) + frontend/
├── services/                      # daemons, overnight server, supervisors
├── scripts/                       # ops/utility scripts
├── config/                        # broker/telegram/client config (secrets — git-ignored)
├── data/                          # historical CSVs/Parquet (git-ignored, on disk only)
├── tests/                         # unified suite: unit + phase1/2/3 + strategy
├── infra/                         # render.yaml, Dockerfile, vercel.json, supabase/schema.sql
└── vault/                         # git-ignored: investor reports, flight recorder, archived bots
```

Guiding rules for the structure:

1. **One repo, one source of truth.** No more mirror copies, no nested `.git`.
2. **Build artifacts never committed.** `node_modules/`, `.next/`, `__pycache__/`, `venv/`, `dist/`,
   `build/` are git-ignored and deleted from disk during the merge.
3. **Secrets never committed and never duplicated.** One `config/` + `.env`; everything else reads
   from env vars on Render.
4. **Large data is data, not code.** `data/` (1.5 GB) stays on disk, git-ignored; a `data/README.md`
   documents how to regenerate it.

---

## 2. Track A — Restructure & declutter

**Goal:** a single lightweight repo that imports cleanly on both Windows and Linux, with no build
artifacts, no duplicate copies, and a documented layout.

### A0. Freeze & snapshot
- Commit the current `main` state of both repos as a known merge point.
- Record a short `docs/plans/merge_snapshot.md` listing the exact commit SHAs.

### A1. Collapse three copies → one canonical (DECISION GATE)
- `diff -r` the three trading-system copies against each other. They are **not** identical
  (timestamps today, one has a `frontend/`, one has a 33 MB `broadcast_stream.jsonl`).
- Determine the newest truthful copy of each directory (`core/`, `bots/`, `config/`, `web/`,
  `scripts/`, `vault/`) and merge into canonical.
- **Decision needed:** confirm which copy is source-of-truth, or authorize "take newest file per
  path, preserving secrets only from the canonical `config/`".

### A2. Strip build artifacts
- Delete all `node_modules/` (39), `.next/` (2), `__pycache__/` (1,845+), `venv/`/`.venv/`,
  `dist/` (174), `build/` (10) from both trees.
- Add a comprehensive `.gitignore` so they never return.
- Expected result: the 45k-file `strategies/` and 30k-file `sim/` collapse to a few hundred source files.

### A3. Flatten the nested git repos
- For each of the 6 vendored bots, keep the **working tree**, drop the `.git` (flatten into the monorepo).
- **Decision needed:** flatten (recommended, lighter) vs promote to git submodules (keeps their history,
  adds operational overhead).

### A4. Merge `SAJIM STRATEGIES` into the canonical tree
Move by domain (not by copy):

| From (`SAJIM STRATEGIES`) | To (monorepo) |
|---|---|
| `sajim_quant/` | `backtest/` (schema, metrics, universe, adapters) |
| `sim/` | `backtest/sim/` |
| `strategies/{research bots}` | `strategies/research/` |
| `strategies/BEEP_MASTER_PACKAGE` | `strategies/beep/` |
| `data/dukascopy`, `data/parquet` | `data/` |
| `data/*.json` (matrices, leaderboard) | `backtest/universe/` (or `data/`) |
| `data_downloader/` + `files/` | `backtest/data/` (merge the two downloaders) |
| `tests/` | `tests/` (merge with existing) |
| `docs/`, `temp_reports/` | `docs/` |
| `sajim_holdings_sandbox/`, `strategies/SajimTraders/` | **resolve in A1, then delete** |

### A5. Deduplicate
- Remove `sajim_holdings_sandbox/` and `strategies/SajimTraders/` once canonical is established.
- Merge `files/` + `data_downloader/` into one `backtest/data/` downloader.
- Remove the two large PDFs from the repo root (or move to an `archives/` outside the repo).
- Delete `files.zip` and any redundant `HFM FREE CLASSES 1.zip`-style artifacts (confirm first).

### A6. Reorganize & rewire
- Move code into the target tree; update all `import` paths and `run.py` entrypoints.
- One `pyproject.toml` (package `sajim`) so `sajim.core`, `sajim.strategies`, `sajim.backtest` etc.
  resolve consistently.
- Update `run.py` to accept the new layout (`run.py bot`, `run.py backtest`, `run.py web`).

### A7. Verify (Track A "done")
- Import smoke test on **both** Windows (with MT5) and Linux (without MT5).
- Run the unified test suite; record the green/fail baseline.
- Report disk size before → after (expect 4–5 GB → under ~1 GB source + 1.5 GB git-ignored data).

---

## 3. Track B — cTrader backtest migration

**Goal:** route backtest/forward-test execution through cTrader and emit schema-compliant trades —
replacing the current stub so the "cTrader" claims become real.

### B0. Stop the false confidence
- Rename `core/ctrader_bridge.py` → `core/ctrader_bridge_stub.py` (per the audit) and make
  `connect()` fail loudly instead of silently degrading to `simulation_mode=True`.

### B1. Implement the real Open API client
- Build `adapters/ctrader/open_api_client.py` implementing Spotware Open API 2.0:
  Protobuf `ProtoOAApplicationAuthReq` → `ProtoOAHeartbeatEvent` → order/deal requests →
  reconnect with backoff. Testable offline against a recorded-protobuf mock.

### B2. Decide what "backtest on cTrader" means (DECISION GATE)
cTrader's native historical backtest runs **inside cTrader Automate as a C# cBot** — a different
runtime from our Python. The honest, Python-friendly path is:

- **(Recommended)** Use the cTrader Open API against a **demo/paper account** as the execution layer
  for forward-tests and parameter sweeps, harvesting every fill into the Universal Trade Schema for
  the leaderboard — while historical *replay* stays in Python/backtrader.
- (Alternative) Write cBots in C# for in-terminal historical backtests, exporting `sajim_trades.csv`.

**Decision needed:** confirm the recommended path, or specify C# cBots.

### B3. Add a cTrader adapter to the benchmarking engine
- `backtest/adapters/ctrader_adapter.py`: `run(strategy, symbol, timeframe, params) -> list[Trade]`
  conforming to the frozen schema, with `Assumptions = {spread_model, slippage_pips}` tags.

### B4. Wire cTrader into governance
- Fix the coexistence gatekeeper's cTrader path: normalize positions (`type`/`magic`/`ticket` →
  cTrader `label`), and move the daily circuit-breaker + high-watermark logic into
  `refresh_account_state()` so it is enforced on the cTrader path.

---

## 4. Track C — Render live processing

**Goal:** run the web service + a worker daemon on Render (Linux), with MT5 fully decoupled and
cTrader as the live execution path.

### C0. Decouple MT5
- Make `import MetaTrader5` lazy/optional at ~20 sites; fix `v2/__init__.py` / `core/__init__.py` so
  strategy/API modules import cleanly on Linux.

### C1. Fix the verified crashes (mostly one-liners)
`order_router` `order_type` NameError; `dealer_state_space` `delta_p`; `confluence_engine` inverted
action; V1 `UnboundLocalError`; hummingbird/V2 short-feed `IndexError`; `bridge_supervisor` Logger
`TypeError`.

### C2. Fix risk controls before any capital
- `MAX_DAILY_DRAWDOWN_PCT` 0.50 → 0.05 (5%) on **both** MT5 and cTrader paths.
- Prop-firm drawdown measured from high-water mark, not current balance.

### C3. Kill fabricated success
- Remove hardcoded PnL / win-rates / investor seeds; make `mt5_bridge` and `ctrader_bridge` fail
  loudly; `investor_reporting.py` consumes a real ledger only.

### C4. Secrets → env vars
- Move Supabase/Telegram/broker credentials to Render environment variables; rotate exposed creds;
  re-derive the Fernet key independently of the Supabase key.

### C5. Web auth
- Add `user_id` ownership checks to execute/close; require auth on investor/ctrader endpoints;
  `hmac.compare_digest`; fixed CORS; typed request models.

### C6. Containerize & deploy
- `infra/Dockerfile` + `infra/render.yaml`: one web service (FastAPI + frontend) and one worker
  daemon (overnight + cTrader heartbeat). Supabase as managed service.

### C7. Go-live gate (Track C "done")
- Green tests; breaker verified on both paths; no code path reports success without a
  broker-confirmed fill; every number on the investor deck traces to a real trade.

---

## 5. Sequencing & dependencies

```
Track A (restructure) ──▶ Stabilize core ──▶ Track B (cTrader) ──▶ Track C go-live
                           (C0, C1, C2, C3)
```

- **Track A first** — everything else assumes one canonical, portable repo.
- **Stabilize core** (decouple MT5, fix crashes, fix breaker, kill fabricated success) is the shared
  prerequisite for both the cTrader migration and Render.
- **Track B** builds the cTrader client/adapter — which is also the live execution layer Render will use.
- **Track C** containerizes and deploys on top of a stabilized, cTrader-wired codebase.

---

## 6. Decisions I need from you (gated — no action taken until answered)

| # | Decision | My recommendation |
|---|---|---|
| D1 | Which of the 3 trading-system copies is canonical? | `C:\…\SAJIM HOLDINGS` (main), then merge in any newer files from the two F: copies after a diff |
| D2 | Merge git history of `SAJIM STRATEGIES`? | Flat move into the monorepo; archive the F: repo (lighter) |
| D3 | Nested `.git` repos (6 vendored bots)? | Flatten (drop history), keep working tree |
| D4 | "Backtest on cTrader" = ? | cTrader Open API demo/paper forward-test → Universal Schema (Python), keep Python replay for historical backtests |
| D5 | Keep `claude_thought/` as-is or fold into `docs/`? | Keep as its own folder (it's the "why" record) |
| D6 | 1.5 GB Dukascopy data handling | Keep on disk, git-ignored; document regeneration |
| D7 | Delete the two PDFs / `files.zip` / HFM zip? | Move out of repo to an `archives/` outside the repo |

---

## 7. Definition of done (whole engagement)

- **One** canonical git repo, one source tree, no build artifacts committed, no duplicate system copies.
- Imports and the test suite are green on **both** Windows and Linux.
- The daily 5% breaker fires on **both** MT5 and cTrader paths.
- The cTrader adapter emits schema-compliant trades into the leaderboard.
- Render runs web + worker; MT5 is fully decoupled from the cloud path.
- No code path reports success without a broker-confirmed result.
