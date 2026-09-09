# SAJIM HOLDINGS — V1 QUANTITATIVE EDGE FILTER MANUAL
### Integrating the 204-Front Empirical Edge Audit Exclusively into Sajim V1
**Chief Quantitative Architect:** Jimmy Mathu  
**Date:** 2026-09-09  

---

## 🏛️ Overview

To ensure **Sajim V1** operates strictly with mathematical edge and ceases leaking capital to low-timeframe noise or spread-heavy assets, the 204-front empirical audit results have been compiled and hard-wired into dedicated configuration files exclusively for V1.

---

## 📁 File Locations

| File | Purpose | Location |
| :--- | :--- | :--- |
| **Edge Whitelist JSON** | Editable JSON matrix containing all approved pairs & timeframes | [`config/v1_edge_filter.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/v1_edge_filter.json) |
| **V1 Filter Engine** | Python module enforcing the edge gatekeeper for V1 | [`config/v1_edge_filter.py`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/config/v1_edge_filter.py) |
| **Comprehensive Audit** | Full markdown report of all 204 fronts with Win Rates and PFs | [`docs/EDGE_MATRIX_REPORT.md`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/docs/EDGE_MATRIX_REPORT.md) |
| **Full Machine Results** | Raw JSON backtest data for all tested assets and timeframes | [`docs/edge_matrix_results.json`](file:///c:/Users/sajim/Documents/SAJIM%20HOLDINGS/docs/edge_matrix_results.json) |

---

## 🎯 Approved Edge Universe for Sajim V1

Sajim V1 is now restricted strictly to these **15 assets and their proven winning timeframes**:

```json
{
  "USDCAD.c": ["M15", "M30", "H4"],  // Top Trend Runner (PF: 1.99 | WR: 53.5% | E: +0.372R)
  "EURJPY.c": ["M5"],                 // Institutional Velocity (PF: 1.87 | WR: 56.2% | E: +0.334R)
  "NZDJPY.c": ["M30", "H1"],          // Trend Continuity (PF: 1.84 | WR: 54.9% | E: +0.284R)
  "CADJPY.c": ["M5", "H1"],           // Kinetic Momentum (PF: 1.70 | WR: 52.2% | E: +0.268R)
  "GBPJPY.c": ["M5", "M30", "H1"],    // Volatility Expansion (PF: 1.61 | WR: 63.2% | E: +0.200R)
  "XAUUSD.c": ["M30", "H4"],          // Gold Macro Swings (PF: 1.55 | WR: 51.4% | E: +0.240R)
  "XAUGBP.c": ["M1", "H4"],           // Gold Cross Divergence (PF: 1.59 | WR: 49.3%)
  "XAUJPY.c": ["M1", "M30", "H4"],    // Gold JPY Impulse (PF: 1.50 | WR: 52.7%)
  "AUDJPY.c": ["M5", "H4"],           // Commodity Currency Momentum (PF: 1.25)
  "CHFJPY.c": ["M5"],                 // Safe-Haven Flow (PF: 1.22)
  "USDJPY.c": ["M5", "M15"],          // Macro Trend Runner (PF: 1.48)
  "EURUSD.c": ["M30"],                // Liquid Mean Reversion (PF: 1.23)
  "NZDUSD.c": ["H4"],                 // Swing Follow-Through (PF: 1.51)
  "XAGUSD.c": ["H4"],                 // Silver Macro Swing (PF: 1.27)
  "XPDUSD.c": ["M30"]                 // Palladium Plume (PF: 1.30)
}
```

---

## 🛑 How V1 Protects Your Capital

Whenever Sajim V1 (`sajim_v1_bot.py` or `sajim_server_overnight.py`) scans the market:
1. **Universe Filtering:** Only the 15 approved assets are loaded into active scanning memory.
2. **Setup Invalidation:** If a signal arrives on an unapproved timeframe (e.g., `GBPUSD.c` on `M1` or `EURNZD.c`), the gatekeeper instantly discards it:
   ```text
   [🛡️ V1 EDGE FILTER] GBPUSD.c (M1) is not in verified edge whitelist (Bleeder/Marginal). Skipped.
   ```
3. **Friction Defense:** All 157 negative-expectancy setups identified in the audit are blocked before any trade execution can take place.

---

## ⚡ Running Sajim V1 Alone with the Edge Filter

You can run V1 immediately using the standard cockpit commands:

```powershell
# 1. Run Flagship Sajim V1 Engine (Live MT5 execution)
& "C:\Users\sajim\AppData\Local\Programs\Python\Python312\python.exe" run.py v1 --live --risk 0.015

# 2. Run Overnight Server Daemon (Armed with the Edge Filter)
& "C:\Users\sajim\AppData\Local\Programs\Python\Python312\python.exe" run.py server --live --interval 30
```
