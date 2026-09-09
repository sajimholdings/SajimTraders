# SAJIM HOLDINGS — QUANTITATIVE LABS
### Scalable Institutional Trading Infrastructure & Autonomous Bot Engines
**Founder & Chief Quantitative Architect:** Jimmy Mathu  
**Core Mission:** Rapid capital accumulation and institutional prop firm qualification through mathematical anomaly extraction.

---

## 🏛️ REPOSITORY ARCHITECTURE

The Sajim Holdings workspace is organized into a modular, production-ready structure designed for clear separation of concerns, high-velocity cash generation, and rock-solid reliability:

```
SAJIM HOLDINGS/
├── bots/                          # Production Live Automated Trading Bots
│   ├── prop_firm/                 # Prop Firm Challenge Qualification Suite
│   │   ├── __init__.py
│   │   └── prop_firm_challenge_bot.py # 5% Total / 3.5% Daily Drawdown Protected Bot
│   ├── __init__.py
│   ├── sajim_omniverse_bot.py     # Universal Multi-Asset Multi-TF Live Engine
│   ├── live_quant_cent_executor.py# Dynamic Compounding Cent Account Flipper
│   ├── market_milker.py           # Reverse-FOMO Crowd Liquidity Milker
│   └── sajim_server_overnight.py  # 24/7 Dedicated Quant Server Daemon
│
├── core/                          # Foundational Quantitative Engines
│   ├── __init__.py                # Consolidated engine package exports
│   ├── beep_core.py               # 4 Universal BEEP Equations (B(t), M(t), Gamma, Lambda)
│   ├── beep_narrative.py          # Institutional Narrative & Asymmetry Generator
│   ├── sajim_regime_algos.py      # Regime Classifier & Risk Profiles
│   ├── beep_binary_quant_engine.py# Dynamic SAR & Parity Reversal Engine
│   ├── mt5_bridge.py              # Low-latency MetaTrader 5 Terminal IPC Bridge
│   ├── tick_beep_engine.py        # Microsecond Tick Transaction Engine
│   ├── backtester.py              # Quantitative Simulation & Test Runner
│   ├── beep_matrix_scanner.py     # 20+ Cross-Asset Institutional Matrix Scanner
│   ├── api.py                     # BEEP Commercial Gateway REST API
│   └── app.py                     # Client Bridge & Sammy Risk Auditor
│
├── vault/                         # Pure Research, Theory & Original BEEP Archive
│   ├── vault_original_beep/       # Unaltered baseline equations (raw_beep_equations.py)
│   ├── Meta AI/                   # Historical exploratory research & chat logs
│   ├── Meta AI.zip                # Research zip archive
│   ├── BEEP_MATHEMATICAL_FOUNDATION_AND_COLLECTIVE_THEORY.md
│   ├── BEEP_SCORING_SPECIFICATION.md
│   └── THE_MATH_OF_COLLAPSE_AND_THE_BEEP_NARRATIVE.md
│
├── tests/                         # Quantitative Backtests & Verification Suites
│   ├── TEST_INDEX.md              # Iteration log for Tests 001 through 010
│   ├── test_001_baseline_400usd_xauusd/
│   ├── ...                        # Backtest artifacts (trades.csv, metrics.json)
│   ├── test_010_layered_cent_flip_real_mt5/
│   ├── test_system.py             # End-to-End API & Gateway Verification
│   ├── run_test_005.py            # Narrative Asymmetry Flip Backtest
│   ├── run_test_010.py            # 4-Layer Real MT5 Cent Flip Backtest
│   └── test_*.py                  # Specialized stress tests
│
├── docs/                          # Governance, Legal Agreements & Risk Policies
│   ├── SAJIM_QUANT_TRADING_PLAYBOOK.md  # Official Quant Execution Playbook
│   ├── SAJIM_HOLDINGS_AGREEMENT.md      # Corporate Partnership Agreement
│   ├── SAMMYS_4_CHECK_RISK_POLICY.md    # Sammy's 4-Check Risk Gatekeeper Rulebook
│   ├── BEEP_IP_LICENSING_AGREEMENT.md   # Intellectual Property Licensing Terms
│   └── BEEP_API_INTEGRATION_GUIDE.md    # Commercial Gateway Documentation
│
├── run.py                         # Master Command-Line Operational Cockpit
└── .env.example                   # Environment configuration template
```

---

## ⚡ MASTER COMMAND COCKPIT (`run.py`)

All systems can be operated directly from the root using `run.py`:

```bash
# 1. Run the Universal Omniverse Anomaly Scanner (Dry Run by default)
python run.py omniverse

# 2. Run Omniverse in Live Continuous Loop on MT5
python run.py omniverse --live --loop --interval 15 --risk 0.05

# 3. Run the Prop Firm Challenge Bot ($100,000 Challenge mode)
python run.py propfirm --size 100000

# 4. Run the Live Quant Cent Executor ($4 / Cent account compounding)
python run.py cent --symbol XAUUSD --timeframe M15 --flips 3

# 5. Run the 20+ Cross-Asset Institutional Matrix Scanner
python run.py scanner

# 6. Run the 24/7 Overnight Dedicated Quant Server
python run.py server

# 7. Run Quantitative Backtests (e.g. Test 001, 002, 003)
python run.py backtest --test_id 002

# 8. Run Full End-to-End System Verification Suite
python run.py test
```

---

## 🎯 CURRENT OPERATIONAL PHASES

### Phase 1: Immediate Cash Generation & Cent Compounding
* **Engine:** `bots/live_quant_cent_executor.py`
* **Target:** Compound small initial capital ($4 USD / 400 USC) into operational runway.
* **Strategy:** Trades strictly on high-edge **RARE (92.6% WR)** and **CERTIFIED (87.1% WR)** layers with dynamic lot compounding in the tens (0.10 -> 0.14 -> 0.19 lot).

### Phase 2: Institutional Prop Firm Challenges
* **Engine:** `bots/prop_firm/prop_firm_challenge_bot.py`
* **Account Tiers:** $50,000 | $100,000 | $200,000 (FTMO, FundedNext, Headway)
* **Risk Envelope:**
  * **Max Total Drawdown:** 5.0% internal hard circuit breaker (Prop rule: 8-10%)
  * **Max Daily Drawdown:** 3.5% internal circuit breaker (Prop rule: 5.0%)
  * **Risk per Trade:** 0.50% via `UniversalLotCalculator`
  * **Target R:R:** Minimum 1:3.0 (Positive expectancy even at 35% win rate)
  * **Correlated Exposure:** Max 2 open positions simultaneously

### Phase 3: Pure BEEP Theory Research & Exploration (Preserved in `vault/`)
* Pure research, mathematical derivations, collapse formulas, and historical prompt archives are safely cataloged in `vault/` for Jimmy Mathu's future deep R&D, keeping the production workspace clean, focused, and distraction-free.

---

## 🛡️ RISK GOVERNANCE: SAMMY'S 4-CHECK GATEKEEPER

Every trade executed by any Sajim bot must pass Sammy's 4 sequential audits:
1. **Spread Gate:** Broker spread must not exceed 15% of expected trade edge.
2. **Kinetic Mass Gate:** $M(t) \ge 35.0$ (Certified) or $M(t) \ge 55.0$ (Rare).
3. **Multi-Scale Alignment (Gamma Gate):** Higher timeframe structural floor must agree.
4. **Capital Preservation Gate:** Daily equity loss must not breach circuit breaker.

---

## 💻 ENVIRONMENT REQUIREMENTS
* Windows 10/11
* Python 3.12+ (installed at `C:\Users\sajim\AppData\Local\Programs\Python\Python312`)
* MetaTrader 5 Terminal (Desktop build) connected to Headway or chosen broker
* Installed packages: `metatrader5`, `numpy`, `requests`, `duka`
