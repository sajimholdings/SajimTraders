# Sajim Holdings V2 — Institutional Quant Framework & Pluggable Architecture

**Chief Quantitative Architect**: Jimmy Mathu  
**Organization**: Sajim Holdings Quant Labs  
**Target Environment**: MetaTrader 5 (`JustMarkets-Demo3` / Cent `.c` and Standard Accounts)

---

## 1. Executive Summary & Design Philosophy

Sajim V2 is an institutional-grade, plug-and-play quantitative trading ecosystem built to operate **concurrently and harmoniously alongside Sajim V1** on the same broker terminal. 

The architecture is strictly decoupled so that:
- **Core infrastructure remains constant**: Broker I/O, tick feeds, dynamic lot sizing, two-stage asymmetric ratchets, and telemetry broadcasting.
- **Strategy cartridges are dynamic**: Pluggable alpha models can be attached, detached, or tuned without touching the execution or broker layer.
- **Data exchange is WebApp-ready**: Real-time state is serialized to clean JSON schema (`v2/coexistence_status.json`), ready for REST endpoints, WebSockets, or frontend dashboards.

---

## 2. Directory Structure

Every module is explicitly named, purpose-bound, and neatly organized:

```
v2/
├── __init__.py                     # Package entrypoint exposing core classes
├── README.md                       # Comprehensive institutional documentation (this document)
├── coexistence_status.json         # Real-time multi-bot telemetry and state bridge
│
├── engine/                         # Mathematical & Quantitative Indicator Engines
│   ├── __init__.py
│   ├── trend_duration.py           # Vectorized HMA-50, slope analysis, rolling duration memory
│   └── trend_duration_engine.py    # Core statistical maturity calculation engine
│
├── core/                           # Abstract Contracts & Governance Protocols
│   ├── __init__.py
│   ├── strategy_base.py            # BaseStrategyCartridge ABC and StrategySignal dataclass
│   └── coexistence.py              # CoexistenceGatekeeper (multi-bot harmony & risk shield)
│
├── strategies/                     # Pluggable Strategy Cartridges
│   ├── __init__.py
│   ├── young_surge_continuation.py # Kinetic Trend Continuation (maturity <= 0.60, 1:3.0R target)
│   └── exhaustion_mean_reversion.py# Baseline Mean Reversion (maturity >= 1.00, 1:2.0R target)
│
├── execution/                      # Production Bot & Multi-Bot Orchestration
│   ├── __init__.py
│   ├── sajim_v2_dual_bot.py        # Independent V2 Bot Executor (Magic 888222)
│   └── dual_orchestrator.py        # Master Concurrent Runner for V1 & V2 side-by-side
│
└── api/                            # WebApp & Telemetry Interface
    ├── __init__.py
    └── telemetry_bridge.py         # Standardized reader/writer functions for external UI
```

---

## 3. Harmonic Coexistence with Sajim V1

To ensure V1 and V2 trade simultaneously without conflict ("ama si ati moja ikifanya ingine haiwezi"):

| Governance Pillar | Sajim V1 (`bots/sajim_v1_bot.py`) | Sajim V2 (`v2/execution/sajim_v2_dual_bot.py`) | Harmony Rule |
| :--- | :--- | :--- | :--- |
| **Magic Number** | `777999` | `888222` | Strict isolation; neither bot touches the other's orders |
| **Comments** | `Sajim_DIAMOND`, `Sajim_RARE`, `Sajim_Scratch` | `Sajim_V2_Continuation`, `Sajim_V2_Reversion` | Clear order attribution in broker records |
| **Max Concurrent Positions** | Up to 6 positions | Up to 6 positions | Aggregate portfolio ceiling capped at 12 combined positions |
| **Directional Conflicts** | BUY / SELL on whitelisted pairs | BUY / SELL on whitelisted pairs | **Opposing trades on the same pair are blocked** (prevents spread loss) |
| **Cluster Limits** | Max 2 positions per currency | Max 2 positions per currency | Combined portfolio cannot hold > 2 trades in the same currency |
| **Daily Drawdown** | Account 5% circuit breaker | Account 5% circuit breaker | Combined daily loss >= 5% halts new entries across both bots |

---

## 4. Pluggable Strategy Cartridges

### Cartridge 1: Young Surge Continuation (`v2/strategies/young_surge_continuation.py`)
- **Concept**: Rides fresh institutional breakouts during early trend lifecycles.
- **Statistical Gate**: Hull Moving Average (HMA-50) slope confirmed, maturity ratio $\le 0.60$ ($TrendCount \le 0.60 \times ProbableLength$).
- **Whitelisted Assets**: `EURJPY.c` (M5), `CADJPY.c` (M5), `NZDJPY.c` (H1), `USDCAD.c` (M15), `GBPJPY.c` (H1), `XAUUSD.c` (H4).
- **Target**: Asymmetric 1:3.0R with two-stage ratchet (+1.5R BE+0.15R, +2.2R Lock +1.0R).

### Cartridge 2: Exhaustion Mean Reversion (`v2/strategies/exhaustion_mean_reversion.py`)
- **Concept**: Fades terminal, overextended trends back toward the dynamic equilibrium baseline.
- **Statistical Gate**: Trend duration has exceeded rolling average (maturity ratio $\ge 1.00$) and price is stretched away from HMA-50 by $\ge 1.2 \times ATR$.
- **Universe**: Macro pairs on M15 & H1 (`EURUSD.c`, `USDCAD.c`, `XAUUSD.c`, `GBPJPY.c`, `USDJPY.c`).
- **Target**: Equilibrium snapback to HMA-50 baseline (1:2.0R payoff).

---

## 5. Operational Commands (`run.py`)

### Run V1 and V2 Concurrently (Recommended):
```powershell
# Continuous Live Multi-Bot Trading:
python run.py dual --live --interval 15 --max-combined 12 --max-v1 6 --max-v2 6

# Single Dual Verification Pass (Dry Run):
python run.py dual --once
```

### Run Bots Individually:
```powershell
# Run V1 Flagship Server Alone:
python run.py v1 --live --interval 30

# Run V2 Production Bot Alone:
python run.py v2 --live --interval 15
```

---

## 6. WebApp Integration Schema (`v2/api/telemetry_bridge.py`)

The WebApp reads `v2/coexistence_status.json` to render the dashboard:
```json
{
  "timestamp": "2026-09-09T09:30:00",
  "account": {
    "balance": 100.00,
    "equity": 98.50,
    "free_margin": 83.53,
    "margin_level_pct": 651.77,
    "currency": "USC"
  },
  "pnl": {
    "today_closed": 1.45,
    "today_floating": -2.43,
    "combined_daily_net": -0.98
  },
  "circuit_breaker": {
    "active": false,
    "reason": ""
  },
  "concurrency": {
    "total_open": 5,
    "max_combined": 12,
    "v1_count": 5,
    "v2_count": 0,
    "other_count": 0
  },
  "toggles": {
    "v1_enabled": true,
    "v2_enabled": true
  }
}
```
Use `TelemetryBridge.get_account_metrics()` or `TelemetryBridge.get_active_positions()` in FastAPI, Flask, or Streamlit routes for instant integration.
