# SAJIM HOLDINGS — QUANTITATIVE TRADING INFRASTRUCTURE
## Comprehensive System Architecture, Codebase Topography & Operational Engineering Report

---

**Document Version:** 2.4.0 (Production Release)  
**Classification:** Proprietary Enterprise Architecture Documentation  
**Primary Architect & Founder:** Jimmy Mathu  
**Core Mission:** Rapid capital accumulation, automated scale-invariant account compounding, institutional prop firm qualification, and commercial algorithmic trading infrastructure.  
**Notice:** *In strict compliance with governance directives, all references to proprietary signal equations, formulas, and specific mathematical naming conventions have been completely excised from this document. The signal generation layer is documented solely as an abstract quantitative anomaly detection and scoring engine.*

---

## TABLE OF CONTENTS

1. [Executive Overview & Operational Philosophy](#1-executive-overview--operational-philosophy)
2. [End-to-End System Architecture & Data Topology](#2-end-to-end-system-architecture--data-topology)
3. [Repository Directory Topography](#3-repository-directory-topography)
4. [Master Operational Command Cockpit (`run.py`)](#4-master-operational-command-cockpit-runpy)
5. [Core Quantitative Engine Framework (`core/`)](#5-core-quantitative-engine-framework-core)
   - 5.1 Low-Latency MetaTrader 5 Bridge (`mt5_bridge.py`, `mt5_login.py`)
   - 5.2 Multi-Account Management & Virtual Portfolio Routing (`multi_account_manager.py`)
   - 5.3 Scale-Invariant Universal Lot Calculator (`lot_calculator.py`)
   - 5.4 Sub-Second Trade Flight Recorder & Post-Exit Blackbox (`trade_flight_recorder.py`)
   - 5.5 Master Whitelist Controller & Paper Watchlist (`whitelist_manager.py`)
   - 5.6 Grand Confluence Ensemble Engine (`confluence_engine.py`)
   - 5.7 Dealer State Space & Microstructure Engine (`dealer_state_space.py`)
   - 5.8 Dynamic Regime Classifier (`sajim_regime_algos.py`)
   - 5.9 Expectancy Tracker & Mathematical Win-Rate Auditor (`expectancy_tracker.py`)
   - 5.10 Signal Truth Tester & Forward Evaluation Engine (`signal_truth_tester.py`)
   - 5.11 Supabase Cloud Event Bus Bridge (`supabase_bridge.py`)
   - 5.12 High-Speed Telegram Notification Bus (`telegram_broadcaster.py`)
   - 5.13 24/7 Community Concierge AI & Conversion Bot (`sajim_community_concierge.py`)
   - 5.14 Daily Market & Pair Health Digest Generator (`market_digest_generator.py`)
   - 5.15 Commercial API & Verification Gateway (`api.py`)
   - 5.16 Local Client Bridge & Sammy Compliance Auditor (`app.py`)
   - 5.17 Cryptographic Credential Vault (`credential_vault.py`)
6. [Autonomous Bot Engines (`bots/` & `v2/`)](#6-autonomous-bot-engines-bots--v2)
   - 6.1 Flagship Sajim V1 Bot: Multi-Pair Portfolio Engine (`bots/sajim_v1_bot.py`)
   - 6.2 Flagship Sajim V2 Bot: Edge-Driven Asymmetric Engine (`bots/sajim_v2_bot.py`)
   - 6.3 24/7 Overnight Dedicated Quant Server Daemon (`bots/sajim_server_overnight.py`)
   - 6.4 Prop Firm Challenge Qualification Suite (`bots/prop_firm/prop_firm_challenge_bot.py`)
   - 6.5 Dynamic Compounding Cent Account Flipper (`bots/live_quant_cent_executor.py`)
   - 6.6 Reverse-FOMO Crowd Liquidity Milker (`bots/market_milker.py`)
7. [The V2 Subsystem: Next-Generation Trading Architecture (`v2/`)](#7-the-v2-subsystem-next-generation-trading-architecture-v2)
   - 7.1 Dual Coexistence & Harmony Gatekeeper (`v2/coexistence.py`)
   - 7.2 Master Dual Orchestrator (`v2/dual_orchestrator.py`)
   - 7.3 Liquidity Sweep Pro Engine (`v2/engine/liquidity_sweep_engine.py`)
   - 7.4 Hummingbird Peak Momentum Harvester (`v2/risk/hummingbird.py`)
   - 7.5 Multi-Stage Trailing Ratchet & Capital Defense Shields (`v2/risk/ratchet.py`)
   - 7.6 Trend Duration Lifecycle Engine (`v2/trend_duration_engine.py`)
   - 7.7 Concrete Strategies (`v2/strategies/`)
   - 7.8 Order Routing & Execution Dispatch (`v2/execution/order_router.py`)
   - 7.9 Telemetry Bridge (`v2/api/telemetry_bridge.py`)
8. [Risk Governance: Sammy's 4-Check Gatekeeper](#8-risk-governance-sammys-4-check-gatekeeper)
9. [Cloud Persistence, Database Schema & Security (`supabase/`)](#9-cloud-persistence-database-schema--security-supabase)
   - 9.1 Relational Schema & Entity Roles
   - 9.2 Row-Level Security (RLS) & Multi-Tenant Scoping
   - 9.3 Database Triggers & Automated User Provisioning
   - 9.4 Supabase Realtime Replication Pipeline
10. [Web Application & Client Portal Infrastructure (`web/` & `frontend/`)](#10-web-application--client-portal-infrastructure-web--frontend)
    - 10.1 FastAPI Gateway & REST Architecture (`web/app.py`, `web/routes/`)
    - 10.2 Next.js 14 Frontend Cockpit (`frontend/src/`)
    - 10.3 1-Tap Execution Model & Auto-Pilot Trade Mirroring
    - 10.4 Freemium Onboarding & Broker Affiliate Conversion Funnel
11. [Data Pipelines, Diagnostics & Empirical Research (`scripts/` & `docs/`)](#11-data-pipelines-diagnostics--empirical-research-scripts--docs)
    - 11.1 Dukascopy High-Fidelity Historical Tick Pipeline (`scripts/download_dukascopy.py`)
    - 11.2 Multi-Asset Edge Matrix Backtesting Suite (`scripts/run_edge_matrix_backtest.py`)
    - 11.3 Broker Spread & Friction Scanner (`scripts/scan_m1_broker_spreads.py`)
    - 11.4 Post-Exit Ground-Truth Audit (`scripts/audit_flight_recorder.py`)
12. [Iterative Verification Suites & Benchmarks (`tests/`)](#12-iterative-verification-suites--benchmarks-tests)
13. [Complete File-by-File Repository Reference Index](#13-complete-file-by-file-repository-reference-index)
14. [Deployment, Environment Setup & Operational Runbook](#14-deployment-environment-setup--operational-runbook)

---

## 1. EXECUTIVE OVERVIEW & OPERATIONAL PHILOSOPHY

The **Sajim Holdings (`SajimTraders`)** workspace represents a production-ready, institutionally designed algorithmic trading ecosystem. Engineered primarily in Python (3.12+), TypeScript (Next.js 14), and PostgreSQL (Supabase), the architecture provides end-to-end capabilities spanning historical tick ingestion, high-frequency signal extraction, risk-constrained order execution, multi-account terminal management, and client-facing web portals.

### The Problem Space
In contemporary electronic financial markets, retail trading methodologies relying on conventional lagging indicators (moving average crossovers, RSI divergences, standard candlestick patterns) consistently fail due to non-stationary price dynamics, broker spread friction, and institutional liquidity hunting. 

Sajim Holdings addresses these challenges through a modular engineering architecture predicated on five core operational axioms:

1. **Scale Invariance:** Mathematical risk models and position-sizing engines operate identically whether compounding a micro-cent account ($4.00 starter capital = 400 USC) or managing a $200,000 institutional prop firm challenge.
2. **Defensive Precedence:** Risk management is an active pre-filter and continuous in-flight watchdog, not an afterthought. Capital preservation takes absolute priority over trade frequency.
3. **Empirical Whitelisting:** Execution is restricted strictly to currency pairs, commodities, and timeframes that demonstrate statistically verified positive expectancy ($EV > 0$, Profit Factor $\ge 1.20$) in multi-year historical audits.
4. **Friction Immunity:** Orders are filtered dynamically against real-time broker bid-ask spreads and liquidity depths to prevent structural profit erosion.
5. **Architectural Separation of Concerns:** Core analytics, live bot execution, terminal hardware bridges, cloud database persistence, and client interfaces are strictly decoupled into independent layers.

---

## 2. END-TO-END SYSTEM ARCHITECTURE & DATA TOPOLOGY

The trading ecosystem operates across six functional layers, forming a closed-loop reactive pipeline:

```
+-----------------------------------------------------------------------------------------+
|                              1. MARKET DATA & TERMINAL LAYER                            |
|  - MetaTrader 5 Desktop Terminals (Headway, JustMarkets, Exness)                        |
|  - Dukascopy Swiss Tick Feeds (Multi-Year Historical L2 Data)                           |
+--------------------------------------------+--------------------------------------------+
                                             | Raw Ticks & OHLCV Bars (IPC / Binary)
                                             v
+-----------------------------------------------------------------------------------------+
|                                2. BRIDGE & HARDWARE LAYER                               |
|  - core/mt5_bridge.py          : Native C-API IPC terminal connector                    |
|  - core/multi_account_manager.py: Virtual session coordinator across client accounts    |
|  - core/lot_calculator.py      : Scale-invariant broker constraint volume engine        |
+--------------------------------------------+--------------------------------------------+
                                             | Normalized Feed / Order Commands
                                             v
+-----------------------------------------------------------------------------------------+
|                          3. QUANTITATIVE ANALYSIS & ENGINES                             |
|  - Anomaly Detection Core      : Velocity, volume commitment, and structural shifts    |
|  - v2/engine/liquidity_sweep.py: Institutional liquidity grab & CHoCH detector         |
|  - v2/trend_duration_engine.py : Statistical trend lifecycle maturity model             |
|  - core/confluence_engine.py   : Multi-pillar ensemble scoring                         |
+--------------------------------------------+--------------------------------------------+
                                             | Candidate Setups & Signals
                                             v
+-----------------------------------------------------------------------------------------+
|                             4. RISK GOVERNANCE & EXECUTION                              |
|  - Sammy's 4-Check Gatekeeper  : Spread, Microstructure, HTF Alignment, Drawdown       |
|  - v2/coexistence.py           : Magic number isolation, directional conflict shield    |
|  - v2/risk/hummingbird.py      : Peak momentum exhaustion harvesting                    |
|  - v2/risk/ratchet.py          : +0.35R BE Shield, +1.5R Lock, +2.2R Lock               |
|  - bots/sajim_v1_bot.py        : Multi-pair diversified overnight server                |
|  - bots/sajim_v2_bot.py        : Edge-driven asymmetric execution engine                |
+---------------------+--------------------------------------+----------------------------+
                      |                                      |
                      v Order Commands                       v Telemetry / State
+---------------------+------------------+  +-----------------+----------------------------+
|        5. METATRADER 5 TERMINAL         |  |             6. PERSISTENCE & CLIENT        |
|  - Real Market Order Routing           |  |  - Supabase PostgreSQL (schema.sql)        |
|  - Position Tracking                   |  |  - core/supabase_bridge.py                 |
|  - In-Terminal Execution Reports       |  |  - vault/flight_recorder/ (Blackbox)       |
+----------------------------------------+  |  - FastAPI Gateway (web/app.py)            |
                                            |  - Next.js 14 Frontend Cockpit             |
                                            |  - 24/7 Telegram Concierge AI              |
                                            +--------------------------------------------+
```

---

## 3. REPOSITORY DIRECTORY TOPOGRAPHY

The root filesystem is partitioned into specialized modules, establishing clear boundaries between live production software, statistical research archives, cloud persistence, and customer portals:

```
SAJIM HOLDINGS/
├── bots/                          # Production Live Automated Trading Bots
│   ├── prop_firm/                 # Institutional Prop Firm Challenge Suite
│   │   ├── __init__.py
│   │   └── prop_firm_challenge_bot.py # 5.0% Total / 3.5% Daily Drawdown Protected Bot
│   ├── __init__.py
│   ├── sajim_v1_bot.py            # Flagship V1 Multi-Pair Diversified Engine
│   ├── sajim_v2_bot.py            # Flagship V2 Edge-Driven Asymmetric Engine
│   ├── sajim_server_overnight.py  # 24/7 Dedicated Quant Server Daemon
│   ├── sajim_omniverse_bot.py     # Universal Multi-Asset Multi-TF Live Scanner
│   ├── live_quant_cent_executor.py# Dynamic Compounding Cent Account Flipper
│   └── market_milker.py           # Reverse-FOMO Crowd Liquidity Milker
│
├── core/                          # Foundational Quantitative & Operational Engines
│   ├── __init__.py                # Package exports
│   ├── mt5_bridge.py              # Low-latency MetaTrader 5 Terminal IPC Bridge
│   ├── mt5_login.py               # Terminal authentication & session supervisor
│   ├── multi_account_manager.py   # Multi-tenant account routing & state manager
│   ├── lot_calculator.py          # Scale-invariant universal position sizing engine
│   ├── trade_flight_recorder.py   # Sub-second blackbox flight recorder & audit logger
│   ├── whitelist_manager.py       # Master trading whitelist controller
│   ├── confluence_engine.py       # Grand Confluence multi-pillar ensemble engine
│   ├── dealer_state_space.py      # Dealer microstructure, absorption & state evaluator
│   ├── sajim_regime_algos.py      # Dynamic regime classifier (trending, ranging, chop)
│   ├── expectancy_tracker.py      # Running mathematical expectancy ($EV$) tracker
│   ├── signal_truth_tester.py     # Forward signal verification auditor
│   ├── supabase_bridge.py         # Cloud database REST client & queue synchronizer
│   ├── telegram_broadcaster.py    # Telegram push notification bus
│   ├── sajim_community_concierge.py # 24/7 Autonomous Telegram onboarding & conversion AI
│   ├── market_digest_generator.py # Daily volatility & pair health digest compiler
│   ├── api.py                     # High-performance commercial REST API gateway
│   ├── app.py                     # Local client bridge & Sammy risk compliance auditor
│   ├── backtester.py              # Historical simulation runner
│   ├── credential_vault.py        # Fernet-based cryptographic local credential vault
│   └── ... (proprietary signal evaluators treated abstractly)
│
├── v2/                            # Next-Generation Asymmetric Trading Subsystem
│   ├── __init__.py
│   ├── coexistence.py             # Harmony & zero-conflict portfolio gatekeeper
│   ├── coexistence_status.json    # Live combined telemetry status file
│   ├── dual_orchestrator.py       # Concurrent V1 + V2 scheduler daemon
│   ├── sajim_v2_dual_bot.py       # Coexistence-adapted V2 bot instance
│   ├── strategy_base.py           # Abstract base class for quantitative strategies
│   ├── trend_duration_engine.py   # Statistical trend lifecycle & runway forecaster
│   ├── engine/                    # Structural physics engines
│   │   ├── __init__.py
│   │   └── liquidity_sweep_engine.py # Buy/Sell liquidity sweep & CHoCH detector
│   ├── execution/                 # Order lifecycle & execution
│   │   ├── __init__.py
│   │   └── order_router.py        # Thread-safe MT5 order dispatch router
│   ├── risk/                      # Dynamic capital defense shields
│   │   ├── __init__.py
│   │   ├── hummingbird.py         # Microsecond peak momentum exhaustion harvester
│   │   └── ratchet.py             # Multi-stage trailing ratchet & breakeven defense
│   ├── strategies/                # Concrete strategy implementations
│   │   ├── __init__.py
│   │   ├── young_surge_continuation.py # Momentum surge continuation model
│   │   ├── mirage_liquidity_sweep.py   # Institutional liquidity sweep reversal model
│   │   └── exhaustion_mean_reversion.py# Overextended equilibrium snapback model
│   └── api/
│       ├── __init__.py
│       └── telemetry_bridge.py    # V2 state exporter for external web consumers
│
├── config/                        # Static & Dynamic System Configuration Files
│   ├── master_trading_whitelist.json # Verified positive-expectancy asset whitelist
│   ├── broker_config.json         # Supported broker server endpoints & parameters
│   ├── client_accounts.json       # Registry of linked client accounts
│   ├── telegram_config.json       # Telegram bot credentials & channel bindings
│   ├── v1_edge_filter.json        # Empirical filter parameters for V1 engine
│   └── v1_edge_filter.py          # Dynamic filter evaluator
│
├── web/                           # Backend API Gateway & REST Server
│   ├── app.py                     # FastAPI production server with JWT authentication
│   ├── server.py                  # Standalone fallback HTTP server
│   ├── routes/                    # Scoped REST API routing modules
│   │   ├── __init__.py
│   │   ├── base.py                # Shared utilities & cross-cutting helpers
│   │   ├── client.py              # Client account telemetry, signals, 1-tap orders
│   │   └── admin.py               # Administrative overrides, diagnostics, force-close
│   └── static/                    # Embedded web assets & landing pages
│
├── frontend/                      # Next.js 14 Production Web Application
│   ├── package.json               # Node dependencies (Next.js, React, Tailwind CSS)
│   ├── tsconfig.json              # TypeScript compilation configuration
│   ├── tailwind.config.ts         # Dark-mode institutional theme configuration
│   └── src/
│       ├── app/                   # Next.js App Router entrypoints
│       │   ├── globals.css        # Global styles & animations
│       │   ├── layout.tsx         # Root HTML layout & fonts
│       │   └── page.tsx           # Institutional trading cockpit HUD
│       ├── components/            # UI components
│       │   ├── CockpitHeader.tsx  # Balance/equity status & account selector
│       │   ├── MetricHeroCard.tsx # Real-time PnL, margin, equity hero card
│       │   ├── ActionButtonsRow.tsx # AutoPilot toggle, risk mode, refresh
│       │   ├── ActiveTradeCard.tsx# Live position monitor with 1-click close
│       │   ├── SignalsQuickGrid.tsx # High-conviction signal grid with 1-tap buy/sell
│       │   ├── GateScreen.tsx     # Onboarding screen with live stats & sandbox demo
│       │   ├── RiskModeSheet.tsx  # Risk mode selector (Ultra-Safe, Scalp, Max-Yield)
│       │   ├── AccountConnectorModal.tsx # MT5 credential connection modal
│       │   ├── AuthModal.tsx      # Supabase authentication modal
│       │   └── FreemiumBanner.tsx # Broker partner affiliate conversion banner
│       ├── hooks/
│       │   └── useCockpit.ts      # React hook coordinating Supabase, state & telemetry
│       └── lib/
│           ├── api.ts             # REST client for FastAPI endpoints
│           ├── supabase.ts        # Client-side Supabase client initialization
│           ├── types.ts           # Shared TypeScript interfaces
│           └── constants.ts       # Broker affiliate links & global constants
│
├── supabase/                      # Cloud Relational Database
│   └── schema.sql                 # PostgreSQL 15+ DDL, RLS security policies, triggers
│
├── scripts/                       # Maintenance, Backtesting & Diagnostic Utilities
│   ├── download_dukascopy.py      # Direct binary tick downloader from Dukascopy
│   ├── dukascopy_backtest_5y.py   # 5-year simulation pipeline
│   ├── run_edge_matrix_backtest.py# Empirical multi-asset edge verification harness
│   ├── scan_m1_broker_spreads.py  # Live spread & liquidity friction scanner
│   ├── audit_flight_recorder.py   # Post-exit blackbox efficiency auditor
│   ├── connect_headway.py         # Headway terminal verification utility
│   ├── bridge_supervisor.py       # Watchdog supervisor for background bridges
│   ├── purge_all_positions.py     # Emergency script to flatten all open MT5 orders
│   ├── test_telegram_connection.py# Verifies Telegram Bot API delivery
│   └── hostinger_vps_setup.bat    # Automated environment setup script for VPS
│
├── docs/                          # Institutional Documentation, Playbooks & Audits
│   ├── SAJIM_QUANT_TRADING_PLAYBOOK.md # Official quantitative trading manual
│   ├── SAMMYS_4_CHECK_RISK_POLICY.md   # Sammy's 4-Check Risk Gatekeeper rulebook
│   ├── EDGE_MATRIX_REPORT.md      # Statistical edge verification report
│   ├── edge_matrix_results.json   # Machine-readable backtest metrics by symbol/TF
│   ├── DUKASCOPY_5Y_BACKTEST_REPORT.md # Multi-year Swiss data backtest findings
│   ├── GRAND_CONFLUENCE_AUDIT_REPORT.md# Ensemble model performance report
│   ├── SAJIM_HOLDINGS_AGREEMENT.md# Corporate partnership agreement
│   └── company_operations/        # Corporate governance records
│
├── tests/                         # Iterative Backtest Artifacts & Verification Suites
│   ├── TEST_INDEX.md              # Chronological changelog of Tests 001 through 010
│   ├── test_001_baseline_400usd_xauusd/ # Baseline single-asset benchmark
│   ├── test_002_intraday_refined_400usd_xauusd/
│   ├── test_003_collective_portfolio_5pairs/
│   ├── test_004_market_milker_account_flip/
│   ├── test_005_narrative_asymmetric_flip/
│   ├── test_006_real_mt5_cent_flip_4usd/
│   ├── test_007_tri_timeframe_protected_cent/
│   ├── test_008_binary_quant_state_inversion/
│   ├── test_009_pure_raw_independent_h1/
│   ├── test_010_layered_cent_flip_real_mt5/ # 4-layer dynamic compounding flip
│   ├── test_system.py             # End-to-end integration test runner
│   ├── test_v1_v2_coexistence.py  # Validation of multi-bot harmony & conflict guards
│   ├── test_v2_hummingbird_harvest.py # Unit tests for peak momentum extraction
│   └── test_web_server.py         # Integration tests for FastAPI endpoints
│
├── vault/                         # Deep R&D Storage & Blackbox Flight Logs
│   ├── flight_recorder/           # Per-ticket JSON flight records & post-exit audits
│   ├── signal_truth_vault.json    # Historical signal accuracy registry
│   └── signal_truth_scoreboard.json # Running aggregate scorecard
│
├── data/                          # Data Store
│   └── dukascopy/                 # Downloaded raw tick files (.bi5) and CSV candles
│
├── scratch/                       # Temporary scratch scripts & universe screening
├── run.py                         # Master Command Cockpit CLI
├── requirements.txt               # Production Python package manifest
├── render.yaml                    # Cloud deployment specification for Render.com
└── vercel.json                    # Edge deployment configuration for Vercel
```

---

## 4. MASTER OPERATIONAL COMMAND COCKPIT (`run.py`)

All systems across the platform are operated through the centralized CLI dispatcher [`run.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/run.py). This master script eliminates environment discrepancies, handles bootstrap paths, and exposes high-level sub-commands for every operational mode.

```
================================================================================
                    SAJIM HOLDINGS QUANTITATIVE LABS
                Scale-Invariant Institutional Trading Systems
================================================================================
```

### CLI Command Reference Table

| Subcommand | Description | Primary CLI Arguments |
| :--- | :--- | :--- |
| `python run.py web` | Launches the FastAPI REST Gateway and Web App backend. | `--port 8080` |
| `python run.py v1` | Launches the Flagship Sajim V1 Multi-Pair Production Engine. | `--live`, `--interval 30`, `--risk 0.02`, `--max-positions 34`, `--account <LOGIN>` |
| `python run.py v2` | Launches the Flagship Sajim V2 Edge-Driven Asymmetric Bot. | `--live`, `--loop`, `--interval 15`, `--risk 0.012`, `--max-positions 5`, `--account <LOGIN>` |
| `python run.py dual` | Launches V1 and V2 concurrently side-by-side on the same MT5 account. | `--live`, `--interval 15`, `--max-combined 12`, `--max-v1 6`, `--max-v2 6`, `--risk-v1 0.012`, `--risk-v2 0.012` |
| `python run.py propfirm`| Launches the Prop Firm Challenge Bot ($50k-$200k DD-Preserved). | `--size 100000`, `--live` |
| `python run.py cent` | Runs the Live Quant Cent Executor ($4.00 compounding ladder). | `--symbol XAUUSD`, `--timeframe M15`, `--flips 3`, `--live` |
| `python run.py scanner` | Runs the 20+ Cross-Asset Institutional Matrix Scanner. | *(None; scans all fronts)* |
| `python run.py edge` | Runs the Quantitative Edge Verification Matrix across 5-year data. | *(Executes `scripts/run_edge_matrix_backtest.py`)* |
| `python run.py concierge` | Starts the 24/7 Community Telegram Concierge AI Daemon. | *(Background long-polling)* |
| `python run.py digest` | Generates and broadcasts the Daily Market & Pair Health Digest. | `--no-broadcast` |
| `python run.py server` | Starts the 24/7 dedicated overnight server daemon. | `--live`, `--interval 30`, `--risk 0.02` |
| `python run.py backtest`| Runs quantitative simulation iterations. | `--test_id 001` (or 002, 003) |
| `python run.py test` | Runs the end-to-end integration and verification suite. | *(Executes `tests/test_system.py`)* |

### Bootstrap Implementation Rationale
In enterprise Python projects with sibling packages (`core`, `bots`, `v2`, `web`), running individual scripts from nested directories often leads to `ModuleNotFoundError` exceptions. [`run.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/run.py#L19-L35) programmatically inspects the filesystem and inserts all required roots onto `sys.path` prior to importing any module:

```python
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (
    ROOT_DIR,
    os.path.join(ROOT_DIR, "core"),
    os.path.join(ROOT_DIR, "bots"),
    os.path.join(ROOT_DIR, "bots", "prop_firm"),
    os.path.join(ROOT_DIR, "vault"),
    os.path.join(ROOT_DIR, "tests"),
):
    if p not in sys.path:
        sys.path.insert(0, p)
```

---

## 5. CORE QUANTITATIVE ENGINE FRAMEWORK (`core/`)

The `core/` package provides hardware bridges, risk calculators, cloud synchronizers, and analytical modules.

### 5.1 Low-Latency MetaTrader 5 Bridge (`mt5_bridge.py`, `mt5_login.py`)
- **Direct Terminal IPC:** Interacts with MetaTrader 5 via its native C-API extension, bypassing slow socket-based or FIX adapters.
- **Dynamic Path Detection:** Automatically searches standard Windows binary paths:
  - `C:\Program Files\MetaTrader 5\terminal64.exe`
  - `C:\Program Files\Headway MT5 Terminal\terminal64.exe`
- **Execution Policy Resolution:** Broker symbols enforce distinct trade filling requirements. The bridge queries `symbol_info.filling_mode` and automatically formats requests using `SYMBOL_FILLING_IOC`, `SYMBOL_FILLING_FOK`, or `SYMBOL_FILLING_RETURN`, preventing execution rejections.

### 5.2 Multi-Account Management & Virtual Portfolio Routing (`multi_account_manager.py`)
- **Multi-Tenant State Coordinator:** Allows a single process to maintain state, monitor positions, and route orders across multiple client trading accounts configured in [`config/client_accounts.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/client_accounts.json).
- **Concurrency Protection:** Injects mutex locks around native terminal switching to ensure trade commands intended for Account A are never dispatched to Account B during switching intervals.

### 5.3 Scale-Invariant Universal Lot Calculator (`lot_calculator.py`)
- **Deterministic Risk Sizing:** Calculates broker-compliant volume based strictly on user-defined risk capital:
  $$\text{Cash at Risk} = \text{Account Equity} \times \text{Risk Fraction}$$
  $$\text{Point Value} = \frac{\text{trade\_tick\_value}}{\text{trade\_tick\_size}}$$
  $$\text{Calculated Volume} = \frac{\text{Cash at Risk}}{\text{Stop Loss Distance in Points} \times \text{Point Value}}$$
- **Cent Account Normalization:** Detects Cent account instruments (suffix `.c`) where $1.00\text{ USD} = 100\text{ USC}$ and adjusts contract multipliers accordingly.
- **Broker Constraint Clamping:** Applies mathematical modulo rounding against broker `volume_step` while clamping strictly within `[volume_min, volume_max]`.

### 5.4 Sub-Second Trade Flight Recorder & Post-Exit Blackbox (`trade_flight_recorder.py`)
- **Sub-Second Telemetry Logging:** Records real-time flight metrics for every active order, updating Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE).
- **Post-Exit Ground-Truth Audit:** Upon position closure, the recorder queues the trade for a 10-minute post-exit inspection. It monitors the subsequent 10 M1 bars to evaluate whether the exit was optimal (price immediately reversed) or sub-optimal (price continued moving favorably).
- **Audit Persistence:** Writes structured JSON records to [`vault/flight_recorder/<ticket>_flight.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/vault/flight_recorder).

### 5.5 Master Whitelist Controller & Paper Watchlist (`whitelist_manager.py`)
- **Single Source of Truth:** Manages trading universe boundaries configured in [`config/master_trading_whitelist.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/master_trading_whitelist.json).
- **Hot-Reloading:** Watches the file modification timestamp (`os.path.getmtime`). When the whitelist configuration is updated on disk, it is reloaded into running bot memory without requiring process restarts.
- **Two-Tier Universe Partitioning:**
  1. `live_trading_whitelist`: Permitted to dispatch real orders to MT5.
  2. `paper_testing_watchlist`: Monitored exclusively by the Forward Signal Truth Tester to accumulate statistical confidence without risking capital.

### 5.6 Grand Confluence Ensemble Engine (`confluence_engine.py`)
- **Multi-Pillar Decision Model:** Blends four distinct analytical layers into a unified confidence score ($0.0 - 100.0$):
  1. *Kinetic Momentum & Mass:* Quantifies institutional volume commitment and velocity.
  2. *Trend Duration Lifecycle:* Evaluates trend maturity to avoid late-stage entries.
  3. *Liquidity Sweep Pro:* Identifies institutional stop-runs and liquidity grabs.
  4. *Equilibrium Reversion:* Measures statistical overextension from rolling equilibrium.

### 5.7 Dealer State Space & Microstructure Engine (`dealer_state_space.py`)
- **Microstructural Inspection:** Analyzes intra-bar dynamics, tick volume, and wick absorption ratios.
- **Three-Candle Confirmation:** Evaluates 3-bar sequences to confirm directional breakout commitment and detect dealer absorption traps before orders are committed.

### 5.8 Dynamic Regime Classifier (`sajim_regime_algos.py`)
- **Chameleon Market Classifier:** Evaluates real-time price distribution to categorize the market state:
  - `TRENDING_EXPANSION`: Favors trend continuation and trailing ratchets.
  - `MEAN_REVERTING_RANGE`: Favors boundary fading and rapid profit taking.
  - `COMPRESSED_CHOP`: Initiates execution blackout to preserve capital.

### 5.9 Expectancy Tracker & Mathematical Win-Rate Auditor (`expectancy_tracker.py`)
- **Realized Mathematical Expectancy:** Continuously tallies closed trades to calculate rolling win rates, payoff ratios ($R:R$), and statistical expected value ($EV$ per trade):
  $$EV = (P_{\text{win}} \times \text{Avg Win}) - (P_{\text{loss}} \times \text{Avg Loss})$$
- Logs performance metrics to disk to enable quantitative performance audits.

### 5.10 Signal Truth Tester & Forward Evaluation Engine (`signal_truth_tester.py`)
- **Forward Paper Auditor:** Evaluates signals emitted for paper-testing watchlist pairs.
- Tracks whether candidate setups achieve their projected take-profit targets before hitting stop-loss levels, recording forward outcomes into [`vault/signal_truth_scoreboard.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/vault/signal_truth_scoreboard.json).

### 5.11 Supabase Cloud Event Bus Bridge (`supabase_bridge.py`)
- **Server-Side REST Gateway:** Communicates with the cloud PostgreSQL instance using the `SUPABASE_SERVICE_ROLE_KEY`.
- Synchronizes client accounts, streams live signals, polls the `orders_queue` for 1-tap client orders, and uploads finalized trade history.

### 5.12 High-Speed Telegram Notification Bus (`telegram_broadcaster.py`)
- **Automated Channel Notifications:** Pushes structured Markdown alerts to private VIP channels and public communities when high-conviction opportunities are identified or major trade milestones are achieved.

### 5.13 24/7 Community Concierge AI & Conversion Bot (`sajim_community_concierge.py`)
- **Autonomous Community Manager:** Interfaces with the Telegram Bot API via non-blocking long-polling.
- Provides interactive commands (`/status`, `/strategy`, `/vip`) and onboarding support in English and Kenyan Sheng.
- Delivers tracked affiliate registration links to drive user conversions to partner brokers.

### 5.14 Daily Market & Pair Health Digest Generator (`market_digest_generator.py`)
- Computes daily volatility, spread ranges, and correlation shifts across major assets.
- Automatically compiles and broadcasts institutional market briefings to community members before major session opens.

### 5.15 Commercial API & Verification Gateway (`api.py`)
- Implements an asynchronous REST API providing authenticated third-party access to signal streams, mathematical verification proofs, and historical performance metrics.

### 5.16 Local Client Bridge & Sammy Compliance Auditor (`app.py`)
- Connects local clients to the quantitative engine, executing Sammy's 4-Check risk audits prior to trade confirmation.

### 5.17 Cryptographic Credential Vault (`credential_vault.py`)
- Uses AES/Fernet encryption to protect broker login credentials and account keys stored in configuration files or transmitted across local networks.

---

## 6. AUTONOMOUS BOT ENGINES (`bots/` & `v2/`)

### 6.1 Flagship Sajim V1 Bot: Multi-Pair Portfolio Engine (`bots/sajim_v1_bot.py`)
The V1 engine executes a 7-stage quantitative pipeline across a broad universe of assets:
$$\text{Data Ingestion} \to \text{Anomaly Evaluation} \to \text{Signal Extraction} \to \text{Portfolio Selection} \to \text{Order Entry} \to \text{Active Management} \to \text{PnL Accounting}$$

#### Core Operational Rules:
- **The Clean Plate Protocol:** Permanently blacklists toxic pairs with high spread-to-ATR friction (`XAUGBP`, `XAGUSD`, `CADCHF`, `AUDCHF`, `NZDCHF`, `AUDNZD`, `GBPCHF`).
- **Capital Milestone Standby Gate:** Benches high-notional assets (e.g., standard `XAUUSD`) on standby until account equity reaches a designated milestone ($\ge \$1,000$ USD or $\ge 100,000$ USC).
- **Macro Currency Cluster Caps:** Groups assets by underlying currency (`USD`, `EUR`, `GBP`, `JPY`, etc.) and enforces strict caps on simultaneous exposure to prevent correlated overextension.
- **Loss Recovery Cooldown:** Enforces a 20-minute trading blackout on any symbol following a loss, preventing revenge-trading during adverse regimes.

### 6.2 Flagship Sajim V2 Bot: Edge-Driven Asymmetric Engine (`bots/sajim_v2_bot.py`)
The V2 engine was designed to eliminate micro-milking bleed through data-driven edge whitelisting and asymmetric trade management.

#### Architectural Highlights:
- **Dynamic Edge Whitelisting:** Reads directly from [`docs/edge_matrix_results.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/docs/edge_matrix_results.json). Only instruments and timeframes with verified positive expectancy ($EV > 0$, Profit Factor $\ge 1.20$, Win Rate $\ge 60\%$) are permitted to submit orders.
- **Asymmetric Payoff Enforcement (Three Tranches):**
  - *Tranche 1 (+1.5R):* Advances Stop Loss to Break-Even $+0.15R$ (creating a risk-free position).
  - *Tranche 2 (+2.2R):* Locks in $+1.0R$ Net Profit into account equity.
  - *Tranche 3 (+3.0R to +3.5R):* Full institutional take-profit harvest.
- **Strict Spread Gate:** Dynamically queries current broker spreads and rejects any candidate setup where the spread consumes $> 12\%$ of the stop-loss distance.
- **Hard Daily Drawdown Circuit Breaker:** Ceases new trade entries if daily floating and closed losses exceed $5.0\%$.

### 6.3 24/7 Overnight Dedicated Quant Server Daemon (`bots/sajim_server_overnight.py`)
- Persistent server daemon designed to run 24/7 on dedicated Windows VPS instances (Hostinger).
- Operates a continuous scanning loop across global sessions (Asian, London, New York), managing position lifecycles, trailing ratchets, and telemetry emissions to [`overnight_status.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/overnight_status.json).

### 6.4 Prop Firm Challenge Qualification Suite (`bots/prop_firm/prop_firm_challenge_bot.py`)
Tailored for prop firm evaluation accounts ($50,000, $100,000, $200,000 tiers) with strict drawdown rules:
- **Internal Safety Margins:** Operates with an internal hard cap of **5.0% total drawdown** (prop firm rule: 8–10%) and an internal **3.5% daily drawdown** limit (prop firm rule: 5.0%).
- **Fixed Risk per Trade:** Hardcoded to **0.50% equity risk per trade**, sized dynamically via [`UniversalLotCalculator`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/lot_calculator.py).
- **Asymmetric Risk-to-Reward:** Enforces a minimum planned $R:R$ of **1:3.0**, guaranteeing positive mathematical expectancy even at modest win rates ($35\% - 45\%$).
- **Maximum Concurrent Exposure:** Limits open positions to a maximum of 2 concurrent trades across the entire portfolio.

### 6.5 Dynamic Compounding Cent Account Flipper (`bots/live_quant_cent_executor.py`)
- Validated in **Test 010**, this bot compounds micro accounts ($4.00 USD / 400 USC) into operational runway using dynamic position scaling in the tens ($0.10 \to 0.14 \to 0.19$ lot).
- Operates with strict survival buffering: the structural stop loss distance of 45 USC represents $11.25\%$ risk, providing an 8.8 consecutive-loss buffer on starter capital.

### 6.6 Reverse-FOMO Crowd Liquidity Milker (`bots/market_milker.py`)
- Capitalizes on retail crowd traps by identifying overextended momentum surges and fading exhaustion wicks at major liquidity boundaries.

---

## 7. THE V2 SUBSYSTEM: NEXT-GENERATION TRADING ARCHITECTURE (`v2/`)

The `v2/` directory houses modular, next-generation quantitative strategies, structural market engines, and coexistence coordination modules.

### 7.1 Dual Coexistence & Harmony Gatekeeper (`v2/coexistence.py`)
Enables Sajim V1 and Sajim V2 to trade simultaneously on the same MetaTrader 5 account without order collisions or conflict:

```
+-----------------------------------------------------------------------------+
|               COEXISTENCE GATEKEEPER (v2/coexistence.py)                    |
|                                                                             |
|  1. MAGIC NUMBER ISOLATION:                                                 |
|     - Sajim V1: 777999                                                      |
|     - Sajim V2: 888222                                                      |
|     (Neither bot ever modifies, trails, or closes tickets of the other)     |
|                                                                             |
|  2. DIRECTIONAL CONFLICT SHIELD:                                            |
|     - If V1 holds BUY EURUSD, V2 is BLOCKED from opening SELL EURUSD        |
|     - Prevents self-hedging broker spread cannibalization                   |
|                                                                             |
|  3. MACRO CURRENCY CLUSTER EXPOSURE CAP:                                    |
|     - Maximum 1-2 open positions per currency cluster across both bots      |
|                                                                             |
|  4. PORTFOLIO EXPOSURE & MARGIN FLOOR:                                      |
|     - Maximum combined open positions: 2 to 12                              |
|     - Minimum Margin Level required for new orders: >= 200% - 500%          |
|                                                                             |
|  5. UNIFIED DAILY DRAWDOWN CIRCUIT BREAKER:                                 |
|     - Halts new order submissions across both bots if combined daily        |
|       equity drawdown reaches 5.0%                                          |
+-----------------------------------------------------------------------------+
```

### 7.2 Master Dual Orchestrator (`v2/dual_orchestrator.py`)
- Coordinates the execution cycles of both V1 and V2 in a unified loop.
- Manages position lifecycles, queries the `CoexistenceGatekeeper` prior to submitting orders, and writes consolidated telemetry to [`v2/coexistence_status.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/coexistence_status.json) every 15 seconds.

### 7.3 Liquidity Sweep Pro Engine (`v2/engine/liquidity_sweep_engine.py`)
- **Smart Money Concepts (SMC) Implementation:** Algorithmic identification of Buy-Side Liquidity (BSL) and Sell-Side Liquidity (SSL) stop-runs.
- Evaluates multi-bar swing highs and lows, detects institutional wick rejections through liquidity pools, and confirms entries upon Change of Character (CHoCH) structural breaks.

### 7.4 Hummingbird Peak Momentum Harvester (`v2/risk/hummingbird.py`)
- **Intraday Peak Profit Extraction:** Monitors winning trades when floating profits reach between $+1.50R$ and $+2.85R$.
- Evaluates M1 bar velocity, wick-to-range ratios ($> 45\%$), and adverse candle closes.
- Automatically executes full or partial profit harvesting ($80\%$ volume cash-in with a risk-free runner) before price retraces to trailing stop levels.

### 7.5 Multi-Stage Trailing Ratchet & Capital Defense Shields (`v2/risk/ratchet.py`)
Manages the in-flight lifecycle of active positions:
- **Stage 0 Breakeven Shield (+0.35R):** Advances Stop Loss to Entry $+0.05R$, eliminating loss potential on the trade.
- **Stage 0B Adverse Euthanasia (-0.35R):** Closes trades early if immediate adverse microstructure emerges, taking a small $-0.35R$ loss rather than suffering a full $-1.0R$ stop hit.
- **Stage 1 Profit Lock (+1.50R):** Locks in $+0.30R$ profit.
- **Stage 2 Profit Lock (+2.20R):** Locks in $+1.00R$ profit.

### 7.6 Trend Duration Lifecycle Engine (`v2/trend_duration_engine.py`)
- Evaluates empirical trend duration distributions to forecast remaining directional runway.
- Categorizes setups into:
  - *Young Surge ($\le 0.60$ maturity):* Early-stage trend with high continuation probability.
  - *Mature Trend ($0.60 - 0.99$ maturity):* Reduced position sizing or tighter trailing stops.
  - *Terminal Exhaustion ($\ge 1.00$ maturity):* Entry prohibited; candidates evaluated for mean-reversion counter-trades.

### 7.7 Concrete Strategies (`v2/strategies/`)
- [`young_surge_continuation.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategies/young_surge_continuation.py): Trend-following model that enters early in high-velocity momentum surges.
- [`mirage_liquidity_sweep.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategies/mirage_liquidity_sweep.py): Institutional liquidity sweep reversal model capturing false breakouts.
- [`exhaustion_mean_reversion.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategies/exhaustion_mean_reversion.py): Mean-reversion model capturing overextended deviations from equilibrium.

### 7.8 Order Routing & Execution Dispatch (`v2/execution/order_router.py`)
- Thread-safe order router handling MT5 ticket dispatch, order modifications, and partial volume closures.

### 7.9 Telemetry Bridge (`v2/api/telemetry_bridge.py`)
- Exports real-time V2 bot state, open positions, and risk metrics for web application dashboards and external consumers.

---

## 8. RISK GOVERNANCE: SAMMY'S 4-CHECK GATEKEEPER

Every candidate trade must pass **Sammy's 4 Sequential Risk Checks** before an order is committed to the broker:

```
[Candidate Signal]
        |
        v
+-----------------------+
|  1. THE SPREAD GATE   | ----> REJECT if Spread > 12% - 15% of Stop Loss Distance
+-----------------------+
        | PASS
        v
+-----------------------+
| 2. MICROSTRUCTURE     | ----> REJECT if Opposing Wick > 40% or Volume Decelerating
+-----------------------+
        | PASS
        v
+-----------------------+
| 3. MULTI-SCALE        | ----> REJECT if Higher-Timeframe Market Structure Conflicts
+-----------------------+
        | PASS
        v
+-----------------------+
| 4. CAPITAL            | ----> REJECT if Daily Loss >= Circuit Breaker or Margin < Limit
+-----------------------+
        | PASS
        v
[Order Executed on MT5]
```

1. **Check 1: The Spread Gate**  
   Broker spread represents direct transaction friction. The system queries the real-time spread and verifies that it does not exceed $12\%$ to $15\%$ of the intended stop loss distance.
2. **Check 2: The Microstructure Gate**  
   The entry bar must confirm volume commitment and lack opposing absorption wicks ($< 40\%$ wick on the side of momentum).
3. **Check 3: The Multi-Scale Alignment Gate**  
   The higher-timeframe trend direction and structural floor must confirm the trade bias. Counter-trend setups against prevailing macro structures are vetoed.
4. **Check 4: The Capital Preservation Gate**  
   Verifies that account equity is above the daily drawdown threshold, margin level is above minimum requirements, and cluster exposure limits have not been reached.

---

## 9. CLOUD PERSISTENCE, DATABASE SCHEMA & SECURITY (`supabase/`)

The platform uses Supabase (PostgreSQL 15+) with Row-Level Security (RLS) as its central database. The complete schema is defined in [`supabase/schema.sql`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/supabase/schema.sql).

### 9.1 Relational Schema & Entity Roles

```
  +------------------+         +-----------------------+
  |  auth.users (ID) | <-----> |   public.profiles     |
  +------------------+         +-----------------------+
                                           |
                   +-----------------------+-----------------------+
                   | 1:N                                           | 1:N
                   v                                               v
        +----------------------+                       +----------------------+
        |   trading_accounts   |                       |     orders_queue     |
        +----------------------+                       +----------------------+
                   | 1:N                                           |
                   +-----------------------+-----------------------+
                                           | 1:N
                                           v
                               +----------------------+
                               |    trade_history     |
                               +----------------------+

                               +----------------------+
                               |       signals        | (Broadcast Feed)
                               +----------------------+
```

- **`public.profiles`:** Linked directly to Supabase Auth (`auth.users.id`). Stores user metadata, contact information, and role classifications (`trader`, `vip`, `admin`).
- **`public.trading_accounts`:** Stores linked MT5 broker accounts, server configurations, real-time financial telemetry (balance, equity, floating PnL, margin level), and Auto-Pilot toggles.
- **`public.signals`:** Stores active market opportunities broadcasted by scanning bots. Includes entry, stop loss, take profit, win probability estimates, and strategy tags.
- **`public.orders_queue`:** Asynchronous execution pipeline for 1-tap client orders and Auto-Pilot trade mirroring. Tracks order state (`PENDING`, `PROCESSING`, `FILLED`, `REJECTED`, `CLOSED`).
- **`public.trade_history`:** Historical record of all closed positions, net PnL, commissions, and swap fees.

### 9.2 Row-Level Security (RLS) & Multi-Tenant Scoping
Every table enforces PostgreSQL Row-Level Security:
- `profiles`: Users can only read and update their own profile (`auth.uid() = id`).
- `trading_accounts`: Users can only access their own linked broker accounts (`auth.uid() = user_id`).
- `orders_queue` & `trade_history`: Scoped strictly to the owning user (`auth.uid() = user_id`).
- `signals`: Public read access for active signals (`is_active = TRUE`), write-restricted to backend service roles.

### 9.3 Database Triggers & Automated User Provisioning
An automatic PostgreSQL trigger (`on_auth_user_created`) intercepts new user signups and generates a matching row in `public.profiles`:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger 
LANGUAGE plpgsql 
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        new.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$;
```

### 9.4 Supabase Realtime Replication Pipeline
Realtime publication is enabled on `signals`, `trading_accounts`, and `orders_queue`. Client web interfaces receive live database changes via WebSockets, eliminating the need for client-side polling.

---

## 10. WEB APPLICATION & CLIENT PORTAL INFRASTRUCTURE (`web/` & `frontend/`)

### 10.1 FastAPI Gateway & REST Architecture (`web/app.py`, `web/routes/`)
The web backend is an asynchronous FastAPI service run via Uvicorn:
- **JWT Authentication:** Validates Supabase bearer tokens via `/auth/v1/user`, scoping all operations to `auth.uid()`.
- **Modular Route Structure:**
  - [`web/routes/client.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/web/routes/client.py): Account telemetry, signal lists, 1-tap orders, and position closures.
  - [`web/routes/admin.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/web/routes/admin.py): Administrative controls, system metrics, and emergency liquidation overrides.

### 10.2 Next.js 14 Frontend Cockpit (`frontend/src/`)
Built with Next.js 14 (App Router), React, TypeScript, and Tailwind CSS:
- **Responsive HUD:** Dark-mode interface optimized for mobile and desktop trading.
- **Key Components:**
  - [`GateScreen.tsx`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/components/GateScreen.tsx): Onboarding screen with live platform stats and sandbox demo mode.
  - [`MetricHeroCard.tsx`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/components/MetricHeroCard.tsx): Displays equity, today's PnL, margin level, and broker connection status.
  - [`ActiveTradeCard.tsx`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/components/ActiveTradeCard.tsx): Real-time trade cards with live PnL, breakeven shield indicators, and 1-click close.
  - [`SignalsQuickGrid.tsx`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/components/SignalsQuickGrid.tsx): Visualizes active signals with risk/reward estimates and 1-tap execution buttons.
  - [`AccountConnectorModal.tsx`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/components/AccountConnectorModal.tsx): Modal for connecting external MT5 broker accounts.

### 10.3 1-Tap Execution Model & Auto-Pilot Trade Mirroring
- **1-Tap Execution:** Users can execute a broadcast signal with a single click. The frontend submits the order to `orders_queue`, which the backend picks up and dispatches to the client's MT5 terminal.
- **Auto-Pilot Trade Mirroring:** When enabled on an account, signals matching the user's risk profile are automatically mirrored to their MT5 account.

### 10.4 Freemium Onboarding & Broker Affiliate Conversion Funnel
- Users without an MT5 account can explore the platform using an interactive demo sandbox.
- Integrated affiliate banners route users to partner brokers (e.g., Headway) to register an account and unlock live execution.

---

## 11. DATA PIPELINES, DIAGNOSTICS & EMPIRICAL RESEARCH (`scripts/` & `docs/`)

### 11.1 Dukascopy High-Fidelity Historical Tick Pipeline (`scripts/download_dukascopy.py`)
- Directly downloads raw, volume-weighted tick data from Dukascopy Swiss servers in binary `.bi5` format.
- Decompresses and stitches multi-year historical feeds into clean OHLCV candle datasets for high-fidelity backtesting.

### 11.2 Multi-Asset Edge Matrix Backtesting Suite (`scripts/run_edge_matrix_backtest.py`)
- Exhaustively backtests candidate symbols across M5, M15, and H1 timeframes over 5-year historical spans.
- Automatically compiles [`docs/edge_matrix_results.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/docs/edge_matrix_results.json) and [`docs/EDGE_MATRIX_REPORT.md`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/docs/EDGE_MATRIX_REPORT.md), computing Profit Factors, Expected Value ($EV$), win rates, and drawdowns to establish the dynamic whitelist for Sajim V2.

### 11.3 Broker Spread & Friction Scanner (`scripts/scan_m1_broker_spreads.py`)
- Continuously polls live broker terminals to map intraday spread fluctuations across instruments, identifying optimal trading windows with minimal spread friction.

### 11.4 Post-Exit Ground-Truth Audit (`scripts/audit_flight_recorder.py`)
- Analyzes saved blackbox flight records to measure exit efficiency across closed positions, evaluating whether trailing stop rules leave excess profit on the table.

---

## 12. ITERATIVE VERIFICATION SUITES & BENCHMARKS (`tests/`)

The `tests/` directory maintains artifacts and logs across ten iterative testing phases, documented in [`tests/TEST_INDEX.md`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/tests/TEST_INDEX.md):

| Test Iteration | Focus & Objectives | Key Outcomes |
| :--- | :--- | :--- |
| **Test 001** | Baseline simulation on $400 USD Gold (`XAUUSD`). | Established initial risk benchmarks and baseline trade duration metrics. |
| **Test 002** | Intraday refined simulation on Gold M15. | Introduced loss cooldowns and trailing ratchet stages. |
| **Test 003** | Multi-pair portfolio simulation across 5 major pairs. | Formulated the macro currency cluster exposure rules. |
| **Test 004** | Market Milker account flip simulation. | Evaluated mean-reversion fades against momentum surges. |
| **Test 005** | Narrative asymmetric flip model. | Benchmarked multi-tranche take-profit structures. |
| **Test 006** | Real MT5 Cent Account compounding ($4.00 starter capital). | Verified dynamic lot compounding mechanics on live broker data. |
| **Test 007** | Tri-timeframe protected cent compounding model. | Enforced multi-timeframe structural alignment gates. |
| **Test 008** | Binary quant state inversion model. | Tested reverse-psychology execution filters during ranging regimes. |
| **Test 009** | Pure independent single-timeframe benchmarks (M5, M15, H1). | Evaluated standalone timeframe expectancies without multi-timeframe weighting. |
| **Test 010** | Layered Cent Flip on 1,000 live MT5 Gold candles. | Validated dynamic compounding across multiple signal layers with high win rates. |

### Automated Integration Tests
- [`tests/test_system.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/tests/test_system.py): End-to-end verification of the FastAPI gateway, Supabase connectivity, and MT5 bridge.
- [`tests/test_v1_v2_coexistence.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/tests/test_v1_v2_coexistence.py): Validates magic number isolation, directional conflict shields, and cluster exposure caps between V1 and V2.
- [`tests/test_v2_hummingbird_harvest.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/tests/test_v2_hummingbird_harvest.py): Unit tests for peak momentum exhaustion detection.
- [`tests/test_web_server.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/tests/test_web_server.py): Validates REST endpoints, authentication parsing, and order payload validation.

---

## 13. COMPLETE FILE-BY-FILE REPOSITORY REFERENCE INDEX

Below is the exhaustive file-by-file index of the Sajim Holdings repository:

### Root Directory
- [`run.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/run.py): Master CLI cockpit and bootstrap dispatcher.
- [`README.md`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/README.md): High-level repository architecture overview.
- [`requirements.txt`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/requirements.txt): Python package dependencies.
- [`requirements-windows.txt`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/requirements-windows.txt): Windows-specific Python package dependencies (including `MetaTrader5`).
- [`render.yaml`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/render.yaml): Render.com deployment configuration for web services.
- [`vercel.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/vercel.json): Vercel deployment configuration for Next.js frontend.
- [`.env.example`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/.env.example): Template for environment variables.
- [`broadcast_active.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/broadcast_active.json): Real-time snapshot of active market opportunities.
- [`broadcast_stream.jsonl`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/broadcast_stream.jsonl): Append-only log of historical signal emissions.
- [`overnight_status.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/overnight_status.json): Status output of the 24/7 overnight server daemon.
- [`edge_matrix_status.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/edge_matrix_status.json): Status tracker for edge matrix backtesting runs.

### `core/` — Foundational Engines
- [`core/__init__.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/__init__.py): Core package initialization and exports.
- [`core/mt5_bridge.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/mt5_bridge.py): Low-latency MetaTrader 5 C-API IPC terminal bridge.
- [`core/mt5_login.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/mt5_login.py): Terminal authentication and connection supervisor.
- [`core/multi_account_manager.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/multi_account_manager.py): Multi-tenant account routing and session manager.
- [`core/lot_calculator.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/lot_calculator.py): Scale-invariant universal position sizing engine.
- [`core/trade_flight_recorder.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/trade_flight_recorder.py): Sub-second trade blackbox flight recorder and post-exit auditor.
- [`core/whitelist_manager.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/whitelist_manager.py): Dynamic trading universe whitelist controller.
- [`core/confluence_engine.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/confluence_engine.py): Grand Confluence multi-pillar ensemble scoring engine.
- [`core/dealer_state_space.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/dealer_state_space.py): Dealer microstructure, tick volume, and absorption analyzer.
- [`core/sajim_regime_algos.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/sajim_regime_algos.py): Chameleon market regime classifier.
- [`core/expectancy_tracker.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/expectancy_tracker.py): Mathematical expectancy and win-rate auditor.
- [`core/signal_truth_tester.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/signal_truth_tester.py): Forward-testing verification engine for candidate signals.
- [`core/supabase_bridge.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/supabase_bridge.py): Cloud database REST client and execution queue synchronizer.
- [`core/telegram_broadcaster.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/telegram_broadcaster.py): High-speed Telegram push notification dispatcher.
- [`core/sajim_community_concierge.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/sajim_community_concierge.py): 24/7 automated Telegram community onboarding and conversion bot.
- [`core/market_digest_generator.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/market_digest_generator.py): Daily market volatility and asset health digest compiler.
- [`core/api.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/api.py): Commercial REST API gateway.
- [`core/app.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/app.py): Local client bridge and Sammy risk compliance auditor.
- [`core/backtester.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/backtester.py): Simulation harness for quantitative setups.
- [`core/credential_vault.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/core/credential_vault.py): Fernet-based cryptographic local credential vault.

### `bots/` — Automated Bot Engines
- [`bots/__init__.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/__init__.py): Bots package exports.
- [`bots/sajim_v1_bot.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/sajim_v1_bot.py): Multi-pair diversified production bot with loss cooldowns.
- [`bots/sajim_v2_bot.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/sajim_v2_bot.py): Edge-driven asymmetric production bot.
- [`bots/sajim_server_overnight.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/sajim_server_overnight.py): 24/7 dedicated overnight server daemon.
- [`bots/prop_firm/prop_firm_challenge_bot.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/prop_firm/prop_firm_challenge_bot.py): Drawdown-protected prop firm challenge bot.
- [`bots/live_quant_cent_executor.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/live_quant_cent_executor.py): Cent account dynamic compounding executor.
- [`bots/market_milker.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/market_milker.py): Reverse-FOMO crowd liquidity milker.
- [`bots/sajim_omniverse_bot.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/bots/sajim_omniverse_bot.py): Multi-asset, multi-timeframe live scanner.

### `v2/` — Next-Gen Asymmetric Subsystem
- [`v2/__init__.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/__init__.py): V2 package exports.
- [`v2/coexistence.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/coexistence.py): Multi-bot coexistence and harmony gatekeeper.
- [`v2/dual_orchestrator.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/dual_orchestrator.py): Master dual-bot concurrent execution orchestrator.
- [`v2/sajim_v2_dual_bot.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/sajim_v2_dual_bot.py): Coexistence-adapted V2 bot instance.
- [`v2/strategy_base.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategy_base.py): Abstract base class for quantitative strategies.
- [`v2/trend_duration_engine.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/trend_duration_engine.py): Statistical trend duration and runway forecaster.
- [`v2/engine/liquidity_sweep_engine.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/engine/liquidity_sweep_engine.py): SMC liquidity sweep and structural shift detector.
- [`v2/execution/order_router.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/execution/order_router.py): Thread-safe MT5 order dispatch router.
- [`v2/risk/hummingbird.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/risk/hummingbird.py): Microsecond peak momentum exhaustion harvester.
- [`v2/risk/ratchet.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/risk/ratchet.py): In-flight trailing ratchets and capital defense shields.
- [`v2/strategies/young_surge_continuation.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategies/young_surge_continuation.py): Early-stage momentum surge continuation model.
- [`v2/strategies/mirage_liquidity_sweep.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategies/mirage_liquidity_sweep.py): Liquidity grab reversal model.
- [`v2/strategies/exhaustion_mean_reversion.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/strategies/exhaustion_mean_reversion.py): Overextended equilibrium snapback model.
- [`v2/api/telemetry_bridge.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/v2/api/telemetry_bridge.py): V2 telemetry exporter for web consumers.

### `web/` & `frontend/` — Client & Web Layer
- [`web/app.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/web/app.py): FastAPI backend server with Supabase JWT authentication.
- [`web/server.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/web/server.py): Standalone fallback HTTP server.
- [`web/routes/client.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/web/routes/client.py): REST endpoints for client telemetry, signals, and orders.
- [`web/routes/admin.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/web/routes/admin.py): Administrative endpoints for diagnostics and overrides.
- [`frontend/src/app/page.tsx`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/app/page.tsx): Main dashboard view of the Next.js web application.
- [`frontend/src/hooks/useCockpit.ts`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/hooks/useCockpit.ts): React state hook coordinating data, sessions, and orders.
- [`frontend/src/components/`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/frontend/src/components): Complete library of trading HUD components.

### `config/` & `supabase/` — Configuration & Persistence
- [`config/master_trading_whitelist.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/master_trading_whitelist.json): Approved symbols for live trading and paper testing.
- [`config/broker_config.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/broker_config.json): Broker server names and parameters.
- [`config/client_accounts.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/client_accounts.json): Registry of linked client MT5 accounts.
- [`config/telegram_config.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/telegram_config.json): Telegram bot tokens and channel IDs.
- [`supabase/schema.sql`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/supabase/schema.sql): PostgreSQL database schema, RLS policies, indexing, and triggers.

---

## 14. DEPLOYMENT, ENVIRONMENT SETUP & OPERATIONAL RUNBOOK

### Step 1: Operating Environment Prerequisites
- **Operating System:** Windows 10/11 or Windows Server 2022 (Hostinger VPS).
- **Python Runtime:** Python 3.12+ (64-bit) installed and added to the system `PATH`.
- **MetaTrader 5 Client:** Desktop terminal installed and logged into a verified broker account (Headway, JustMarkets, Exness).
  - *Note:* In MT5, navigate to `Tools -> Options -> Expert Advisors` and ensure `Allow algorithmic trading` and `Allow DLL imports` are enabled.

### Step 2: Install Package Dependencies
From the repository root, install the required dependencies:
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Create a `.env` file in the root directory:
```ini
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...

# Admin & Security
ADMIN_KEY=your_secure_admin_api_key

# Telegram Notifications
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_VIP_CHANNEL_ID=-100123456789
```

### Step 4: Launching Production Services

1. **Launch the FastAPI Gateway & Client Web Terminal:**
   ```bash
   python run.py web --port 8080
   ```
2. **Execute the Dual Engine (V1 + V2 Coexistence in Live Mode):**
   ```bash
   python run.py dual --live --interval 15 --max-combined 6 --risk-v1 0.015 --risk-v2 0.015
   ```
3. **Execute Prop Firm Challenge Mode ($100,000 Account):**
   ```bash
   python run.py propfirm --size 100000 --live
   ```
4. **Execute Cent Account Compounding Ladder ($4.00 Starter):**
   ```bash
   python run.py cent --symbol XAUUSD --timeframe M15 --flips 3 --live
   ```
5. **Launch the 24/7 Community Telegram Concierge AI:**
   ```bash
   python run.py concierge
   ```
6. **Run the Full Integration Verification Suite:**
   ```bash
   python run.py test
   ```

---

*Report compiled and verified against production codebase artifacts. End of document.*
