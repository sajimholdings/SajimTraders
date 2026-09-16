# SAJIM HOLDINGS — Company Handover & Operations Handbook

**From inception to present** — the complete story of SAJIM operations, written for
future work as the company scales.

**Founder & Chief Quantitative Architect:** Jimmy Mathu
**Date:** 2026-09-16
**Status:** Post-declutter, pre-migration. Not yet pushed to GitHub.

---

## 0. Read this first

SAJIM Holdings Quant Labs builds scale-invariant algorithmic trading systems that extract
mathematical anomalies from FX and commodities (primary assets: `XAUUSD`, `EURJPY`,
`GBPJPY`, `USDCAD`, `BTCUSD`). The company's core mission is **rapid capital accumulation
and institutional prop-firm qualification through mathematical anomaly extraction**.

This document is the single reference for anyone (human or AI) who needs to operate,
extend, or explain the company. It is deliberately honest — including the parts that are
not yet real — because nothing should be shown to an investor or client that is not backed
by a broker-confirmed result.

---

## 1. The story so far (birth to now)

SAJIM grew through eight documented working sessions, each leaving a mark on the codebase.

| Phase | What happened | Where it lives today |
|---|---|---|
| **Genesis** | The **BEEP** framework was born — four "universal contextual deviation" equations intended to detect market anomalies. The first bot (V1) was built on it. | `core/beep_core.py` (git-ignored private IP), `vault/` |
| **Data & execution** | Historical data pipelines (Dukascopy), MT5 bridge, audio/telemetry capture. | `core/mt5_bridge.py`, `scripts/download_dukascopy.py` |
| **The cockpit** | A Next.js web app + Supabase backend: auth, live signals, account linking. | `frontend/`, `web/`, `supabase/schema.sql` |
| **Deep research** | Chart deep-dives, a 5-year gold (XAUUSD) backtest, and a master architecture report. | `docs/*.md`, `tests/` |
| **The second engine** | **Sajim V2** — two pluggable cartridges (Surge continuation + Exhaustion reversion) plus a coexistence gatekeeper to run V1 and V2 side-by-side. | `v2/` |
| **Institutional surface** | Investor reporting, quant evaluation, a prop-firm challenge bot, and the start of a **cTrader** cloud bridge. | `core/investor_reporting.py`, `core/quant_evaluator.py`, `bots/prop_firm/`, `core/ctrader_bridge.py` |
| **Company formalisation** | Team roles, an operations manual, a capital roadmap, and a prop-challenge acquisition playbook. | `docs/company_operations/` |
| **Benchmarking platform** | A parallel platform (`F:\Tete\SAJIM STRATEGIES`) for evaluating strategies against a "Universal Trade Schema" and ranking them on a leaderboard. | `F:\Tete\SAJIM STRATEGIES` (to be merged) |
| **Now** | Consolidation, a viability audit, secret cleanup, and the three-track migration plan. | this document + `docs/RESTRUCTURE_AND_MIGRATION_PLAN.md` |

The full session-by-session record is preserved in `docs/conversation_history/`
(redacted; see §7) — it is the raw "why" behind the architecture.

---

## 2. The intellectual property: BEEP

BEEP ("Universal Contextual Deviation Protocol") is the core quant idea. It models every
market as a deviation from a dynamic baseline, weighted by momentum, volatility regime,
and order-flow asymmetry.

- **B(t)** — *Dynamic Equilibrium Baseline*: a robust mean (HMA-50) representing fair value.
- **M(t)** — *Kinetic Mass / Institutional Momentum*: acceleration relative to that baseline.
- **Γ (Gamma)** — *Multi-scale volatility gate*: compression/expansion that flags liquidity
  sweeps and squeeze zones.
- **Λ (Lambda)** — *Exponential momentum decay / tick asymmetry*: directional absorption
  versus retail noise.

Signals are **tiered** by confidence: **Diamond ≥ 90**, **Rare ≥ 75**, **Certified ≥ 40**.

> **IP note:** `core/beep_*` is **git-ignored private intellectual property**. It must never
> be force-added or pushed. The licensing terms are in `docs/BEEP_IP_LICENSING_AGREEMENT.md`.

---

## 3. The bot family

| Bot | Identity | What it does |
|---|---|---|
| **Sajim V1** | magic `777999` | Flagship execution bot on the BEEP signal engine. |
| **Sajim V2 Surge** | label `SAJIM_V2_SURGE` | Young-trend continuation (enters when trend maturity ≤ 0.60, targets 1:3.0R). |
| **Sajim V2 Reversion** | label `SAJIM_V2_REVERT` | Exhaustion mean-reversion (fades overextended trends, targets 1:2.0R). |
| **Overnight server** | 24/7 daemon | `bots/sajim_server_overnight.py` — runs the system around the clock. |
| **Prop-firm challenge bot** | — | `bots/prop_firm/` — risk-capped bot for FTMO/FundedNext/Headway challenges. |

V2's magic is `888222`. Multi-bot harmony is enforced by the **CoexistenceGatekeeper**
(`v2/coexistence.py`): opposing-trade shield, max 12 concurrent positions, max 2 per
cluster, and a daily-loss circuit breaker.

---

## 4. Systems & architecture

```
core/            # quant engines: BEEP, quant_evaluator, investor_reporting,
                 #   ctrader_bridge, mt5_bridge, supabase_bridge, lot_calculator
v2/              # V2 framework: coexistence, dual_orchestrator, order_router, strategies/
bots/            # production bots (V1, V2, overnight, prop_firm)
web/             # FastAPI gateway + routes
frontend/        # Next.js 14 cockpit (deployed on Vercel)
supabase/        # Postgres schema (RLS, triggers)
scripts/         # ops + audit + backtest utilities
config/          # broker/telegram/client config (git-ignored secrets)
data/            # Dukascopy CSVs + Parquet (git-ignored, large)
tests/           # backtest artifacts + verification suite
vault/           # git-ignored: investor reports, flight recorder, original BEEP archive
```

**The key architectural decision** (from the benchmarking platform): *normalise at the
results layer, not the execution layer.* Every engine adapter (MT5, cTrader, Backtrader,
Pine) must emit a **frozen Universal Trade Schema** — a `Trade` record with snake_case
fields (`trade_id`, `strategy_name`, `engine`, `symbol`, `timeframe`, `direction`,
`entry/exit`, `gross_pnl`, `net_pnl`, `mae`, `mfe`, `duration_seconds`, `custom_fields`).
This is what lets the leaderboard compare strategies across engines honestly.

---

## 5. Where the code lives (canonical layout)

There are **three copies** of the trading system. Only one is canonical:

| Copy | Verdict |
|---|---|
| `C:\Users\sajim\OneDrive\SAJIM HOLDINGS` (git, `main`) | **CANONICAL** — strict superset |
| `F:\Tete\SAJIM STRATEGIES\sajim_holdings_sandbox\` | stale snapshot — delete after preserving unique items |
| `F:\Tete\SAJIM STRATEGIES\strategies\SajimTraders\` | stale snapshot — delete after preserving unique items |

The benchmarking platform (`F:\Tete\SAJIM STRATEGIES`) will be merged into this monorepo.
The full target architecture and the exact merge map are in
`docs/RESTRUCTURE_AND_MIGRATION_PLAN.md` §1 and §2 (Track A).

---

## 6. Credentials & secrets (security posture)

**One git-ignored `.env` file** at the repo root is now the single source of truth for all
credentials. It is never committed, never printed, never shared. The committed
`.env.example` documents every key (with empty placeholders).

| Group | Keys | Status |
|---|---|---|
| Supabase | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | live |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_CHANNEL_USERNAME` | live |
| MT5 / broker | `MT5_LOGIN/PASSWORD/SERVER`, `BROKER_ACCOUNTS_JSON` (3 accounts: 2 demo, 1 live cent) | live |
| cTrader | `CTRADER_CLIENT_ID/SECRET/ACCESS_TOKEN/ACCOUNT_ID` | **not yet issued** (Track B) |
| BEEP gateway | `BEEP_CLIENT_KEY`, `BEEP_SAMMY_KEY`, `BEEP_MASTER_KEY` | not yet issued |

**Rotation required:** a live Telegram bot token and the Supabase service-role key were
found sitting in plaintext in the session-history transcripts. They have been redacted from
those files, but because they existed in plaintext they should be **rotated** before the
repo goes public. The same applies to the plaintext MT5 credentials historically embedded
in `sajim_quant/adapters/mql5/mt5_adapter.py` (in the F: platform).

---

## 7. What is real vs. what is fabricated — the honest status

This is the single most important section for anyone building on this codebase.

**The strategy *engines* are largely real.** The BEEP math, the V1/V2 bots, the Dukascopy
5-year backtest (which honestly publishes losses), the Parquet/analytics layer, and the
Monte Carlo engine are genuine.

**The *reporting* layer fabricates favourable numbers.** Specific offenders:

| File | Problem |
|---|---|
| `core/ctrader_bridge.py` | Stub — `connect()` silently returns `True` in simulation mode |
| `v2/execution/order_router.py` | `order_type` never assigned — `NameError` (cannot place an order) |
| `core/api.py` | returns `SIMULATED_ORDER_CONFIRMED` for every order |
| `core/investor_reporting.py` | seeds 5 hardcoded fake deals when no real ledger exists |
| `core/beep_broadcast.py` / `web/routes/client.py` | hardcoded 86/89/92% win probabilities |
| `universe_matrix.py` | hardcodes base Sharpe/win-rate/PF and feeds a *synthetic* `np.random` (seed 42) trade sequence into the Monte Carlo engine |
| `timeframe_matrix.py` | hardcodes 4 of 6 evaluators; the leaderboard is a literal string |
| `smc_daemon_project` | scripted always-win simulator |

The published numbers are systematically **more favourable than the measured runs**
(e.g. `GoldOrb_ORB`: 0 real trades shown as 2 trades / 50% WR / +$160; `GoldPullbackAI`
Sharpe 0.24 shown as 0.84). The committed leaderboard was hand-edited beyond even the
hardcoded generator.

**Bottom line:** the engines are real; the numbers shown to investors are not. Fixing this
is a bounded set of file edits, enumerated in `docs/RESTRUCTURE_AND_MIGRATION_PLAN.md`
Track C3. **No number may be shown to an investor or client until it traces to a
broker-confirmed fill.**

---

## 8. The three-track plan (what happens next)

The master roadmap is `docs/RESTRUCTURE_AND_MIGRATION_PLAN.md`. In dependency order:

- **Track A — Restructure & declutter.** Collapse the three copies into one monorepo,
  strip build artifacts, flatten nested `.git` repos, merge `SAJIM STRATEGIES` in.
- **Track B — cTrader backtest migration.** Replace the stub bridge with a real Spotware
  Open API 2.0 client (Protobuf/WebSockets), and add a cTrader adapter that emits the
  Universal Trade Schema. Recommended path: cTrader Open API against a **demo/paper**
  account as the execution layer for forward-tests; historical replay stays in Python.
- **Track C — Render live processing.** Decouple MT5 (make `import MetaTrader5` optional at
  ~20 sites), fix the verified one-liner crashes, fix the daily breaker (0.50 → 0.05 = 5%),
  kill fabricated success, move secrets to env vars, containerize, deploy.

**Seven gated decisions (D1–D7)** await the founder (canonical copy, git-history merge,
nested-repo flattening, "backtest on cTrader" definition, `claude_thought/` disposition,
1.5 GB data handling, archive cleanup). Full detail in the plan's §6.

---

## 9. Team & operations

From `docs/company_operations/`:

- **Jimmy Mathu** — founder, final decision-maker.
- **Sammy** — risk gatekeeper; owns "Sammy's 4-Check Risk Policy" (`docs/SAMMYS_4_CHECK_RISK_POLICY.md`).
- **Tete** — tech / platform (the F: benchmarking work is under this role).
- **Val** — client messaging templates.
- **Arnold** — money ledger tracking.
- **Alu** — daily trading card.

Every trade must pass **Sammy's 4 checks**: (1) spread ≤ 15% of expected edge,
(2) kinetic-mass gate, (3) multi-scale (Gamma) alignment, (4) capital-preservation
(daily-loss) gate.

Operational docs: `docs/company_operations/README.md` is the index; the operations manual,
team charter, capital roadmap, and prop-challenge playbook are alongside it.

---

## 10. Day-to-day operations (run.py cockpit)

```bash
python run.py omniverse                       # universal anomaly scanner (dry run)
python run.py omniverse --live --loop --interval 15 --risk 0.05
python run.py propfirm --size 100000          # prop challenge bot
python run.py cent --symbol XAUUSD --timeframe M15 --flips 3
python run.py scanner                          # 20+ cross-asset matrix scanner
python run.py server                           # 24/7 overnight daemon
python run.py backtest --test_id 002
python run.py test                             # end-to-end verification suite
python run.py investor                         # investor audit deck (see §7 warning)
python run.py ctrader --test                   # cTrader bridge test (stub — see §7)
```

Environment: Python 3.12+, MetaTrader 5 terminal (Windows host only; Linux/Render uses
cTrader), and the packages in `requirements.txt` (Linux) / `requirements-windows.txt`.

---

## 11. Immediate next actions (the queue)

1. **Commit the session transcripts** (`docs/conversation_history/`) — redacted, but held
   out of the last commit pending explicit authorization (they are the sensitive tier).
2. **Push to GitHub** — local `main` is ahead of `origin`; push is intentionally waiting on
   the founder's go-ahead.
3. **Merge `F:\Tete\SAJIM STRATEGIES` → monorepo** (Track A), after preserving the unique
   items: `sajim_holdings_sandbox/tests/*.py`, `MT5_Sajim/MQL5/`, and `sajim_strategy.yaml`.
4. **Fix the fabricated reporting layer** (Track C3) before any investor communication.
5. **Rotate the exposed credentials** (§6).

---

## 12. Definition of done (whole engagement)

- One canonical git repo, one source tree, no build artifacts committed, no duplicate copies.
- Imports and the test suite green on **both** Windows and Linux.
- The daily 5% breaker fires on **both** MT5 and cTrader paths.
- The cTrader adapter emits schema-compliant trades into the leaderboard.
- Render runs web + worker; MT5 is fully decoupled from the cloud path.
- **No code path reports success without a broker-confirmed result.**

---

*Prepared by Claude Code (background audit session). Cross-references:
`docs/RESTRUCTURE_AND_MIGRATION_PLAN.md`, `docs/WHAT_WAS_DONE.md`,
`docs/FULL_REPO_AUDIT_REPORT.md`, `docs/FOLDER_INVENTORY_REPORT.md`,
`docs/company_operations/README.md`, `docs/conversation_history/`.*
