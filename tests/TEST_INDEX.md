# SAJIM HOLDINGS — BEEP BACKTEST ITERATION INDEX
This index catalogs all quantitative backtest iterations, parameters, and results starting from a **$400 USD** starter account.

---

## ITERATION SUMMARY TABLE

| Test ID | Style | Asset | Timeframe | Initial Bal | Final Bal | Net PnL | ROI % | Win Rate | Profit Factor | Max Drawdown | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **[TEST_001](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_001_baseline_400usd_xauusd/report.md)** | SWING | XAUUSD | H1 (1mo) | $400.00 | $483.82 | **+$83.82** | **+20.95%** | 57.53% | 1.09 | 43.00% ($176.53) | ✅ Baseline Established |
| **[TEST_002](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_002_intraday_refined_400usd_xauusd/report.md)** | INTRADAY | XAUUSD | H1 (1mo) | $400.00 | $562.44 | **+$162.44** | **+40.61%** | 50.00% | 1.19 | 37.86% ($163.35) | 🚀 Drawdown Reduced & Profit Doubled |
| **[TEST_003](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_003_collective_portfolio_5pairs/report.md)** | INTRADAY | 5-Pair Basket | H1 (1mo) | $400.00 | $456.48 | **+$56.48** | **+14.12%** | 43.38% | 1.05 | 53.25% ($225.60) | 🌐 Collective Portfolio (Gold carries) |
| **[TEST_004](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_004_market_milker_account_flip/report.md)** | MILKER | 4-Pair Basket | H1 (1mo) | $400.00 | $213.90 | **$-186.10** | **-46.52%** | 36.68% | 0.88 | 61.49% ($245.95) | ⚠️ Overtrading Stress-Test (Negative Expectancy) |
| **[TEST_005](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_005_narrative_asymmetric_flip/report.md)** | NARRATIVE | 4-Pair Basket | H1 (1mo) | $400.00 | $445.73 | **+$45.73** | **+11.43%** | 16.67% | 0.68 | 31.47% ($183.56) | 🎯 Asymmetric R:R Flip (Profitable despite 83% losses) |
| **[TEST_006](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_006_real_mt5_cent_flip_4usd/report.md)** | CENT_FLIP | XAUUSD (Gold) | M5 (Real MT5) | $4.00 (400¢) | $4.13 (413¢) | **+$0.13 (+13¢)** | **+3.23%** | 30.70% | 0.77 | 24.20% ($1.17) | ⚡ 100% Real MT5 Live Data: 19.3 min avg duration |
| **[TEST_007](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_007_tri_timeframe_protected_cent/report.md)** | TRI_GATE | XAUUSD (Gold) | H1+M15+M5 (Real) | $4.00 (400¢) | $5.20 (520¢) | **+$1.20 (+120¢)** | **+30.02%** | 35.71% | 1.08 | 14.53% ($0.80) | 🛡️ Tri-Timeframe Gamma Gate (H1+M15+M5): 90% WAIT |
| **[TEST_009_H1](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_009_pure_raw_independent_h1/report.md)** | RAW_SOVEREIGN | XAUUSD (Gold) | H1 (Real MT5) | $4.00 (400¢) | $7.29 (729¢) | **+$3.29 (+329¢)** | **+82.31%** | 38.89% | 1.24 | 41.38% ($1.83) | 🚀 Zero Weights / Pure BEEP: Nearly doubled account! |
| **[TEST_009_M15](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_009_pure_raw_independent_m15/report.md)** | RAW_SOVEREIGN | XAUUSD (Gold) | M15 (Real MT5) | $4.00 (400¢) | $4.63 (463¢) | **+$0.63 (+63¢)** | **+15.74%** | 36.73% | 1.07 | 29.33% ($1.90) | ⚡ Sovereign M15 execution with Reverse Psychology |
| **[TEST_010](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_010_layered_cent_flip_real_mt5/report.md)** | LAYERED_FLIP | XAUUSD (Gold) | M15 (Real MT5) | $4.00 (400¢) | $10.12 (1012¢) | **+$6.12 (+612¢)** | **+153.00%** | 71.43% | 2.14 | 34.20% ($1.75) | 🏆 All 4 BEEP Layers (Rare 92.6% WR): 38 Flips, 9.4h cycle |

---

## DETAILED TEST DIRECTORIES

### 1. [Test 001: Baseline $400 USD (Swing Mode)](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_001_baseline_400usd_xauusd/)
* **Objective:** Establish unoptimized baseline performance on Gold (XAUUSD) with strict 0.01 lot and Sammy's 4-Check.
* **Artifacts:**
  * [description.md](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_001_baseline_400usd_xauusd/description.md)
  * [report.md](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_001_baseline_400usd_xauusd/report.md)
  * [trades.csv](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_001_baseline_400usd_xauusd/trades.csv)
  * [metrics.json](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_001_baseline_400usd_xauusd/metrics.json)

### 2. [Test 002: Intraday Refined $400 USD](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_002_intraday_refined_400usd_xauusd/)
* **Objective:** Test tighter baseline support buffers ($1.618 \times \text{ATR}$) and faster dynamic Lambda decay ($\lambda = 0.03$).
* **Results:** Account grew from **$400.00 to $562.44 (+40.61%)**, with Profit Factor rising to **1.19** and Drawdown dropping to **37.86%**.
* **Artifacts:**
  * [description.md](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_002_intraday_refined_400usd_xauusd/description.md)
  * [report.md](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_002_intraday_refined_400usd_xauusd/report.md)
  * [trades.csv](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_002_intraday_refined_400usd_xauusd/trades.csv)
  * [metrics.json](file:///C:/Users/sajim/OneDrive/SAJIM%20HOLDINGS/test/test_002_intraday_refined_400usd_xauusd/metrics.json)
