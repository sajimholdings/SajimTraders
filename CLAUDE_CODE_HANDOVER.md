# SAJIM HOLDINGS QUANT LABS — SYSTEM HANDOVER & CLAUDE CODE AUDIT BRIEF

**Founder & Chief Quantitative Architect:** Jimmy Mathu  
**Target Environment:** Headless Cloud (Linux / Render) & cTrader Open API (Spotware)  
**Date:** September 16, 2026  
**Status:** Pre-cTrader Production Audit & Investor Readiness Phase  

---

## 🏛️ 1. MISSION & EXECUTIVE CONTEXT

### What We Are Building
Sajim Holdings Quant Labs develops scale-invariant, algorithmic trading systems designed to extract mathematical anomalies from foreign exchange and commodities (primary assets: `XAUUSD`, `EURJPY`, `GBPJPY`, `USDCAD`, `BTCUSD`). 

### Why We Are Transitioning to cTrader Open API
Historically, algorithmic execution ran through MetaTrader 5 (`MetaTrader5` Python package). MT5 imposes a strict **Windows desktop dependency** (requiring Windows OS, a running `terminal64.exe` GUI, and binding the operator's local machine). 

To scale institutional operations, we are migrating to **cTrader Open API**:
1. **Pure Python & Headless**: Communicates via TLS/WebSockets using Protocol Buffers. Operates 100% natively on **Linux / Render / Docker** with zero GUI, zero Wine, and zero Windows VPS dependencies.
2. **Local PC Freedom**: Execution runs 24/5 in the cloud, completely freeing the operator's PC for corporate legal structuring, licensing, compliance, and investor negotiations.
3. **Multi-Bot Attribution on a Single Account**: cTrader supports `label` and `comment` fields on every order. This allows multiple algorithms (Sajim V1, Sajim V2 Surge, Sajim V2 Reversion) to trade the exact same account with complete performance isolation.
4. **Investor-Grade Raw Math**: Automated real-time calculation of Mathematical Expectancy ($E$), Profit Factor ($PF$), Sharpe/Sortino ratios, and Drawdown to provide verifiable mathematical proof of edge for investors and capital scaling.

---

## 🧩 2. CODEBASE INVENTORY & REPOSITORY ARCHITECTURE

```
SAJIM HOLDINGS/
├── core/                              # Foundational Quantitative & Execution Engines
│   ├── ctrader_bridge.py             # Pure Python cTrader Open API 2.0 Bridge (TLS/WebSockets)
│   ├── quant_evaluator.py            # Mathematical Expectancy, Sharpe, PF, DD & Compounding Model
│   ├── investor_reporting.py         # Automated Audit Deck generator (JSON/CSV exports)
│   ├── beep_core.py                  # 4 Universal BEEP Equations (B(t), M(t), Gamma, Lambda)
│   ├── beep_signal_engine.py         # Institutional Regime & Signal Generator
│   ├── lot_calculator.py             # Universal Dynamic Lot Sizer with Micro-Lot bounds
│   ├── trade_flight_recorder.py      # Sub-second Blackbox & Post-Exit Telemetry
│   ├── mt5_bridge.py                 # Legacy MT5 Terminal IPC Bridge
│   └── supabase_bridge.py            # Cloud Database & Telemetry Sync
│
├── v2/                                # Sajim V2 Institutional Quant Framework
│   ├── coexistence.py                # CoexistenceGatekeeper (multi-bot harmony & risk shield)
│   ├── dual_orchestrator.py          # Master Co-Execution Runner (V1 + V2 side-by-side)
│   ├── execution/
│   │   └── order_router.py           # Multi-broker dispatch (MT5 & cTrader) with bot labels
│   ├── strategies/
│   │   ├── young_surge_continuation.py # Kinetic Trend Continuation (HMA-50, maturity <= 0.60)
│   │   └── exhaustion_mean_reversion.py# Baseline Mean Reversion (ATR stretch, maturity >= 1.00)
│   └── coexistence_status.json       # Real-time multi-bot telemetry and state bridge
│
├── bots/                              # Production Bot Implementations
│   ├── sajim_server_overnight.py     # Sajim V1 24/7 Overnight Dedicated Quant Daemon
│   ├── sajim_v1_bot.py               # Sajim V1 Flagship Execution Bot (Magic 777999)
│   └── sajim_v2_bot.py               # Sajim V2 Asymmetric Production Bot (Magic 888222)
│
├── web/                               # Cloud REST API & WebApp Gateway
│   └── app.py                        # FastAPI Gateway with Supabase Auth & Investor Endpoints
│
├── frontend/                          # Institutional Next.js 14 WebApp (Deployed on Vercel)
├── vault/investor_reports/            # Audited trade ledgers (CSV) and investor summaries (JSON)
├── run.py                             # Master CLI Operational Cockpit
├── render.yaml                        # Headless Render Cloud Configuration
└── requirements.txt                   # Linux/Render-safe Python Dependencies
```

---

## 📐 3. QUANTITATIVE MATH & ALGORITHMIC STRATEGIES

### A. The BEEP Anomaly Framework
- **$B(t)$ (Dynamic Equilibrium Baseline)**: Vectorized Hull Moving Average (HMA-50) representing fair value.
- **$M(t)$ (Institutional Momentum & Thrust)**: Kinetic energy acceleration relative to historical baseline.
- **$\Gamma$ (Volatility Compression/Expansion)**: Detects institutional liquidity sweeps and squeeze zones.
- **$\Lambda$ (Order Book & Tick Asymmetry)**: Quantifies directional absorption vs. retail noise.

### B. Sajim V2 Pluggable Cartridges
1. **Young Surge Continuation (`v2/strategies/young_surge_continuation.py`)**:
   - Enters early trend lifecycles when trend maturity ratio $\le 0.60$ ($TrendCount \le 0.60 \times ProbableLength$).
   - Targets asymmetric 1:3.0R payoff.
2. **Exhaustion Mean Reversion (`v2/strategies/exhaustion_mean_reversion.py`)**:
   - Fades terminal trends when trend duration is statistically overextended (maturity ratio $\ge 1.00$) and price stretches $\ge 1.2 \times ATR$ away from baseline.
   - Targets mean reversion to baseline (1:2.0R payoff).

### C. Asymmetric Management & Hummingbird Harvest
- **Stage 1 Ratchet (+1.5R)**: Move SL to Break-Even +0.15R (eliminates risk).
- **Stage 2 Ratchet (+2.2R)**: Lock in +1.0R Net Profit.
- **Hummingbird Peak Harvest**: Real-time M1 velocity decay and counter-wick detection that harvests peak profits (+1.5R to +2.5R+) before price retraces back to trailing stops.

### D. Multi-Bot Coexistence & Governance (`v2/coexistence.py`)
- **Isolation**: Sajim V1 (`label="SAJIM_V1"` / Magic `777999`), V2 Surge (`label="SAJIM_V2_SURGE"`), V2 Revert (`label="SAJIM_V2_REVERT"`).
- **Opposing Trade Shield**: Blocks opposing positions on the same pair (e.g. V1 BUY while V2 SELL) to avoid paying double spread.
- **Portfolio Caps**: Max 12 total concurrent positions, max 2 positions per currency cluster.
- **Circuit Breaker**: Halts all entries if daily loss exceeds 5.0% of balance.
- **Dynamic High-Watermark Floor**: Ratchets protected capital floor as account grows.

---

## 📊 4. INVESTOR REPORTING & RAW MATH ENGINE

Implemented in `core/quant_evaluator.py` and `core/investor_reporting.py`:
- **Mathematical Expectancy ($E$)**:
  $$E = (W \times \overline{\text{Win}}) - ((1 - W) \times \overline{\text{Loss}})$$
- **Profit Factor ($PF$)**:
  $$PF = \frac{\sum \text{Gross Wins}}{\sum \text{Gross Losses}} \quad (\text{Institutional Benchmark } \ge 1.40)$$
- **Sharpe & Sortino Ratios**: Quantifies risk-adjusted returns and penalizes downside volatility.
- **Payoff Asymmetry Ratio**: Average Win / Average Loss ratio ($\ge 2.0$).
- **Drawdown Metrics**: Maximum Adverse Excursion (MAE), Maximum Favorable Excursion (MFE), Max Drawdown (MDD %).
- **Compounded Capital Growth Model**: Projects 30d, 90d, 180d, and 365d equity scaling based on empirical EV.
- **Artifacts**:
  - `vault/investor_reports/investor_audit_summary.json`
  - `vault/investor_reports/trade_ledger.csv`

---

## 🚀 5. CURRENT OPERATIONAL COMMANDS (`run.py`)

```powershell
# 1. Generate & display the full Quantitative Investor Audit Deck
python run.py investor

# 2. Test cTrader Cloud Bridge multi-bot routing & Hummingbird harvest (Sandbox Mode)
python run.py ctrader --test

# 3. Run Sajim V1 and V2 Dual Coexistence on cTrader
python run.py dual --broker ctrader

# 4. Run single pass verification on cTrader
python run.py dual --broker ctrader --once

# 5. Launch FastAPI Gateway (Investor endpoints at /api/v2/investor/*)
python run.py web
```

---

## 🔍 6. CODE AUDIT INSTRUCTIONS FOR CLAUDE CODE

Claude Code, please perform an exhaustive, institutional code audit across the codebase before live capital is routed through cTrader:

### 1. cTrader Open API Robustness (`core/ctrader_bridge.py`)
- Audit TLS/WebSocket message encoding and decoding for Spotware Open API 2.0.
- Verify heartbeat (`ProtoHeartbeatEvent`), auto-reconnection on network disconnection, and thread safety of `_lock`.
- Inspect order filling modes, partial fills, slippage calculations, and symbol mapping (`DEFAULT_SYMBOL_MAP`).
- Verify behavior when API credentials are live in `.env` vs fallback in sandbox mode.

### 2. Multi-Bot Concurrency & Race Conditions (`v2/dual_orchestrator.py`, `v2/coexistence.py`, `v2/execution/order_router.py`)
- Audit order routing to ensure `label` and `comment` attribution is strictly preserved.
- Verify `CoexistenceGatekeeper` state locks during rapid concurrent signals from V1 and V2.
- Check the Opposing Trade Shield: ensure no scenario allows opposing trades on the same pair.
- Verify daily 5% circuit breaker calculations across both closed trades and floating drawdowns.

### 3. Mathematical Edge & Execution Integrity (`core/quant_evaluator.py`, `core/lot_calculator.py`)
- Audit the Mathematical Expectancy ($E$), Profit Factor, and Sharpe/Sortino formulas for statistical accuracy.
- Verify lot sizing logic: ensure micro-lot bounds ($0.01$) strictly protect accounts $<\$100$.
- Review Hummingbird Harvest logic in `bots/sajim_v2_bot.py`: verify that tick volume and wick rejection conditions cannot prematurely exit high-velocity runners.

### 4. Linux / Render Cloud Portability (`render.yaml`, `requirements.txt`, `web/app.py`)
- Confirm that zero Windows-only dependencies (`MetaTrader5` C-extensions) leak into cloud/cTrader execution paths.
- Audit FastAPI endpoints (`/api/v2/investor/*`, `/api/v2/ctrader/*`) for payload schema, latency, and error handling.
- Review `render.yaml` configuration for persistent background daemon operation.

---
*Ready for Claude Code review.*
