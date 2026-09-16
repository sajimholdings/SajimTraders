# 01 — System Overview

## Mission

Sajim Holdings Quant Labs ("SAJIM Lab") builds **scale-invariant algorithmic trading systems** to
extract "mathematical anomalies" from FX and commodities. Primary assets: `XAUUSD`, `EURJPY`,
`GBPJPY`, `USDCAD`, `BTCUSD`. The stated goals are, in order:

1. **Rapid capital accumulation** and **prop-firm qualification** (FTMO / FundedNext / Headway).
2. **Investor-grade reporting** — verifiable Mathematical Expectancy (E), Profit Factor (PF),
   Sharpe/Sortino, and drawdown metrics, as proof of edge for capital scaling.
3. **Institutional cloud execution** — headless, 24/5, freeing the operator's PC.

## The big architectural shift: MT5 → cTrader

- **Current/legacy path — MetaTrader 5 (MT5):** execution runs through the `MetaTrader5` Python
  package, which requires a **Windows desktop**, a running `terminal64.exe` GUI, and the operator's
  local machine bound to the broker. This is the working (or mostly-working) path today.
- **Target path — cTrader Open API:** pure Python over TLS/WebSockets + Protocol Buffers, running
  headless on **Linux / Render / Docker** with no GUI and no Windows VPS. cTrader's `label`/`comment`
  fields on every order let multiple bots trade one account with clean attribution.

> ⚠️ **Reality check:** the cTrader bridge (`core/ctrader_bridge.py`) is currently a **stub** — it
> authenticates by sleeping and returning `True`, and never transmits a real order. The migration is
> the *intent*, not yet a working system. See `04_audit_findings.md`.

## Repository / folder architecture

```
SAJIM HOLDINGS/
├── core/               # Foundational quant & execution engines (62 files)
│   ├── beep_core.py            # 4 BEEP equations (B, M, Gamma, Lambda)
│   ├── beep_signal_engine.py   # regime + signal generator
│   ├── beep_processor.py       # signal processor (ATR, thresholds)
│   ├── ctrader_bridge.py       # cTrader Open API bridge (STUB)
│   ├── mt5_bridge.py           # MT5 terminal IPC bridge
│   ├── quant_evaluator.py      # expectancy / Sharpe / Sortino / DD
│   ├── lot_calculator.py       # dynamic lot sizer
│   ├── investor_reporting.py   # investor audit deck
│   └── ... (bridges, scanners, managers)
├── v2/                 # Sajim V2 framework (40 files)
│   ├── coexistence.py          # multi-bot gatekeeper + risk shield
│   ├── dual_orchestrator.py    # co-runs V1 + V2
│   ├── strategies/             # surge / reversion / mirage sweep
│   ├── risk/                   # hummingbird harvest + ratchet
│   └── execution/order_router.py  # multi-broker dispatch
├── bots/               # production bots (15 files)
│   ├── sajim_v1_bot.py         # V1 flagship (magic 777999)
│   ├── sajim_v2_bot.py         # V2 asymmetric (magic 888222)
│   ├── sajim_server_overnight.py  # 24/7 daemon
│   └── prop_firm/prop_firm_challenge_bot.py
├── web/                # FastAPI gateway + routes + static export (49 files)
├── frontend/           # Next.js 14 "sajim-traders-portal" (396 MB incl. deps)
├── scripts/            # audits, backtests, downloads, ops (57 files)
├── tests/              # 10 backtest dirs + pytest suites (98 files)
├── config/             # credentials + trading whitelist (secrets — redacted)
├── data/dukascopy/     # 5y XAUUSD historical bid data (277 MB)
├── docs/               # reports, playbooks, legal, transcripts
├── vault/              # git-ignored: research, archived bots, investor reports
└── run.py              # master CLI cockpit
```

The complete disk map (sizes, counts, every directory) is in
`docs/FOLDER_INVENTORY_REPORT.md`.

## The two execution paths in practice

| | MT5 path | cTrader path |
|---|---|---|
| Entry point | `run.py dual` (default) / `run.py server` | `run.py dual --broker ctrader` |
| Bridge | `core/mt5_bridge.py` | `core/ctrader_bridge.py` |
| Requires | Windows + terminal GUI | Linux/Render, headless |
| Status | Works, but fabricated telemetry + Windows-bound | **Stub — not implemented** |
| Known blocker | unconditional `import MetaTrader5` crashes on Linux | silently degrades to sandbox and returns `True` |

## Current status at a glance

- The overnight daemon is in **`DRY_RUN`** mode (zeroed equity, no positions).
- `v2/coexistence_status.json` shows a default **$10,000 simulated** balance.
- The investor ledger (`vault/investor_reports/trade_ledger.csv`) holds **4 deals**.
- The telemetry stream (`broadcast_stream.jsonl`, 33 MB) contains signal and deal events with
  synthetic-looking ticket numbers.

> Bottom line: this is a **pre-production prototype** with a lot of moving parts, a serious,
> thoughtful *design*, and a gap between that design and what the code actually does.
