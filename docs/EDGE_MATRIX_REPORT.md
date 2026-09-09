# SAJIM HOLDINGS — QUANTITATIVE EDGE VERIFICATION REPORT
### Empirical Mathematical Edge & Blacklist Audit across All Pairs and Timeframes
**Chief Quantitative Architect:** Jimmy Mathu  
**Audit Execution Time:** 2026-09-09 08:54:14  
**Total Fronts Evaluated:** 204 active of 204 | **Elapsed Time:** 162.2s

---

## 1. Executive Summary & Core Findings

- **Institutional Edges ($PF \ge 1.60, E \ge 0.25R$):** **4 setups (2.0%)**
- **Moderate Edges ($PF \ge 1.20, E > 0$):** **23 setups (11.3%)**
- **Marginal Setups ($1.00 \le PF < 1.20$):** **20 setups (9.8%)**
- **Bleeders / Negative Edge ($PF < 1.00$):** **157 setups (77.0%)** — *Mandatory Blacklist in Sajim V2*

---

## 2. Performance Breakdown by Timeframe

| Timeframe | Fronts | Total Trades | Win Rate | Gross Profit (R) | Gross Loss (R) | Profit Factor | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **M1** | 34 | 2009 | 37.1% | +577.6R | -909.8R | **0.63** | ❌ High Friction / Bleed |
| **M5** | 34 | 2212 | 41.8% | +917.5R | -1076.4R | **0.85** | ❌ High Friction / Bleed |
| **M15** | 34 | 2385 | 40.8% | +1013.6R | -1237.5R | **0.82** | ❌ High Friction / Bleed |
| **M30** | 34 | 2439 | 44.3% | +968.4R | -1193.4R | **0.81** | ❌ High Friction / Bleed |
| **H1** | 34 | 2348 | 43.2% | +915.2R | -1172.0R | **0.78** | ❌ High Friction / Bleed |
| **H4** | 34 | 2405 | 45.1% | +1041.1R | -1186.4R | **0.88** | ❌ High Friction / Bleed |

---

## 3. Top Institutional Edge Setups (Approved for Sajim V2 Engine)

| Asset | TF | Trades | Win Rate | Profit Factor | Payoff Ratio | Expectancy (R) | Max DD (R) | Spread Friction (η) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **USDCAD.c** | `M15` | 71 | **53.5%** | **1.99** | 1.68:1 | **+0.372R** | -6.8R | 0.6205 |
| **EURJPY.c** | `M5` | 73 | **56.2%** | **1.87** | 1.46:1 | **+0.334R** | -5.3R | 0.2609 |
| **NZDJPY.c** | `H1` | 51 | **54.9%** | **1.84** | 1.51:1 | **+0.284R** | -4.6R | 0.0899 |
| **CADJPY.c** | `M5` | 69 | **52.2%** | **1.70** | 1.56:1 | **+0.268R** | -5.4R | 0.3975 |

---

## 4. Toxic Bleeders (Mandatory Blacklist for Sajim V2)

| Asset | TF | Trades | Win Rate | Profit Factor | Payoff Ratio | Expectancy (R) | Net PnL (R) | Spread Friction (η) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EURNZD.c** | `M1` | 53 | 35.8% | **0.31** | 0.55:1 | **-0.348R** | -18.4R | 0.9655 |
| **XPTUSD.c** | `H1` | 76 | 31.6% | **0.33** | 0.71:1 | **-0.415R** | -31.6R | 0.0709 |
| **EURCHF.c** | `M5` | 59 | 35.6% | **0.34** | 0.62:1 | **-0.327R** | -19.3R | 1.5342 |
| **USDCHF.c** | `M5` | 67 | 28.4% | **0.34** | 0.85:1 | **-0.402R** | -26.9R | 0.7982 |
| **AUDUSD.c** | `M1` | 65 | 35.4% | **0.35** | 0.64:1 | **-0.376R** | -24.4R | 1.4483 |
| **EURCHF.c** | `M30` | 80 | 26.2% | **0.36** | 1.00:1 | **-0.420R** | -33.6R | 0.6222 |
| **XAGUSD.c** | `M1` | 48 | 29.2% | **0.37** | 0.87:1 | **-0.163R** | -7.5R | 2.6923 |
| **AUDNZD.c** | `M1` | 56 | 28.6% | **0.39** | 0.94:1 | **-0.284R** | -15.3R | 1.8941 |
| **EURGBP.c** | `M15` | 64 | 37.5% | **0.39** | 0.66:1 | **-0.328R** | -21.0R | 1.5077 |
| **EURGBP.c** | `M1` | 46 | 23.9% | **0.41** | 1.26:1 | **-0.192R** | -8.4R | 4.2609 |
| **GBPUSD.c** | `M1` | 70 | 31.4% | **0.41** | 0.88:1 | **-0.339R** | -23.7R | 1.1159 |
| **AUDCAD.c** | `M5` | 61 | 34.4% | **0.43** | 0.83:1 | **-0.304R** | -18.6R | 1.0000 |
| **GBPCHF.c** | `H1` | 75 | 34.7% | **0.43** | 0.82:1 | **-0.320R** | -24.0R | 0.2141 |
| **GBPAUD.c** | `M1` | 59 | 30.5% | **0.45** | 1.03:1 | **-0.284R** | -16.8R | 1.7889 |
| **CADCHF.c** | `M5` | 62 | 27.4% | **0.46** | 1.19:1 | **-0.327R** | -19.5R | 0.9106 |
| **CADJPY.c** | `M1` | 66 | 36.4% | **0.47** | 0.83:1 | **-0.287R** | -18.9R | 0.9882 |
| **NZDCAD.c** | `M1` | 53 | 41.5% | **0.47** | 0.66:1 | **-0.200R** | -10.6R | 2.0945 |
| **NZDCHF.c** | `H4` | 80 | 43.8% | **0.47** | 0.60:1 | **-0.278R** | -22.2R | 0.1551 |
| **AUDCAD.c** | `M1` | 53 | 39.6% | **0.48** | 0.74:1 | **-0.169R** | -8.9R | 2.8283 |
| **CADCHF.c** | `M15` | 71 | 32.4% | **0.48** | 1.00:1 | **-0.307R** | -21.8R | 0.6400 |
| **USDCHF.c** | `H1` | 73 | 38.4% | **0.48** | 0.77:1 | **-0.307R** | -22.4R | 0.2244 |
| **XPDUSD.c** | `H4` | 78 | 42.3% | **0.48** | 0.66:1 | **-0.283R** | -22.1R | 0.0401 |
| **CADCHF.c** | `M1` | 55 | 29.1% | **0.49** | 1.17:1 | **-0.215R** | -11.2R | 0.6400 |
| **NZDUSD.c** | `M1` | 58 | 34.5% | **0.49** | 0.93:1 | **-0.209R** | -12.1R | 1.7818 |
| **AUDNZD.c** | `M5` | 61 | 37.7% | **0.50** | 0.82:1 | **-0.274R** | -16.7R | 0.8214 |

---

## 5. Architectural Directives for Sajim V2 Bot

1. **Dynamic Whitelist Loading:** Sajim V2 automatically ingests only the Tier 1 & Tier 2 verified assets from this report.
2. **Timeframe Specialization:** Each asset trades strictly on its highest-expectancy timeframe.
3. **Asymmetric Payoff Ratchet:** Zero micro-milking before $+1.5R$. +2.2R locks +1.0R Net Profit. +3.0R TP target.
4. **Hard Risk Ceiling:** Sizing strictly capped at 1.2% per trade so 1 win pays for 3-4 losses.
