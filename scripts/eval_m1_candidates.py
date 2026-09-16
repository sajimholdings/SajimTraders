"""
========================================================================================
     SAJIM QUANT LABS — M1 HIGH-VOLATILITY CANDIDATE EVALUATION SUITE
========================================================================================
Purpose:
  - Connect to Headway Real MT5.
  - Calculate Spread vs ATR(14) on M1 for all high-volatility candidate assets.
  - Run full GrandConfluence forward trade simulation on M1 history.
  - Certify candidates meeting the strict <25% spread friction and statistical criteria.
========================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
import numpy as np
import MetaTrader5 as mt5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "v2")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.confluence_engine import GrandConfluenceEngine
from scripts.audit_grand_confluence import simulate_confluence_trade, compute_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("M1Evaluator")

# Candidates for M1 High-Frequency Scalping
CANDIDATES = [
    # US & Global Indices
    ("DJ30", "Index / US30"),
    ("NASDAQ-100", "Index / NAS100"),
    ("US500", "Index / S&P500"),
    ("DE30", "Index / DAX40"),
    # Crypto
    ("BTCUSD", "Crypto"),
    ("ETHUSD", "Crypto"),
    ("SOLUSD", "Crypto"),
    # Metals & Energies
    ("XAUUSD", "Metals / Gold (Benchmark)"),
    ("XAGUSD", "Metals / Silver"),
    ("XTIUSD", "Energies / Crude Oil"),
    # FX Crosses for reference
    ("EURJPY", "FX Cross (Benchmark)"),
    ("GBPJPY", "FX Cross"),
    ("EURUSD", "FX Major (Control)"),
]

BARS_COUNT = 5000  # ~3.5 days of M1 bars

def evaluate_m1_candidates():
    if not mt5.initialize():
        print(f"[!] MT5 Init failed: {mt5.last_error()}")
        return

    acc = mt5.account_info()
    print(f"Connected to MT5 Server: {acc.server} | Account: {acc.login}")
    print(f"Analyzing M1 Spread vs ATR(14) and Grand Confluence Scalping on {len(CANDIDATES)} candidates...\n")

    engine = GrandConfluenceEngine(
        swing_len=21,
        lookback_bars=80,
        mirage_min_score=45.0,
        trend_hma_len=50,
        trend_samples=10,
        beep_window=14,
    )

    results = []

    print(f"{'Symbol':<12} | {'Category':<24} | {'Price':<10} | {'Spread':<8} | {'ATR(14)':<10} | {'Sprd/ATR%':<10} | {'Pass <25%':<10} | {'Trades':<7} | {'WR%':<7} | {'PF':<6} | {'Net R':<8} | {'Tier'}")
    print("-" * 140)

    for sym, cat in CANDIDATES:
        mt5.symbol_select(sym, True)
        si = mt5.symbol_info(sym)
        if not si:
            print(f"[-] {sym:<10} Symbol not found")
            continue

        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, BARS_COUNT)
        if rates is None or len(rates) < 500:
            print(f"[-] {sym:<10} Insufficient M1 bars ({0 if rates is None else len(rates)})")
            continue

        n = len(rates)
        highs = rates["high"].astype(np.float64)
        lows = rates["low"].astype(np.float64)
        closes = rates["close"].astype(np.float64)
        bar_spreads = rates["spread"].astype(np.float64)

        # Calculate True Range
        tr = np.zeros(n, dtype=np.float64)
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

        # Simple 14-period and 500-period average ATR
        atr_14_recent = float(np.mean(tr[-14:]))
        atr_14_avg = float(np.mean(tr[-500:]))  # medium-term average M1 ATR

        # Live spread vs historical bar spread
        live_spread_pts = si.spread
        hist_median_spread_pts = float(np.median(bar_spreads[-500:]))
        
        # Effective spread price
        spread_price = float(live_spread_pts * si.point)
        if spread_price == 0:
            spread_price = float(hist_median_spread_pts * si.point)

        # Spread to ATR(14) ratio
        spread_to_atr_recent_pct = (spread_price / atr_14_recent * 100.0) if atr_14_recent > 0 else 999.0
        spread_to_atr_avg_pct = (spread_price / atr_14_avg * 100.0) if atr_14_avg > 0 else 999.0

        friction_pass = spread_to_atr_avg_pct < 25.0
        pass_str = "YES (PASS)" if friction_pass else "NO (HIGH)"

        # Run Grand Confluence M1 simulation
        confluence_signals, summary = engine.analyze(sym, "M1", rates)
        trades = []
        for sig in confluence_signals:
            idx = sig.bar_index
            if idx >= n - 15:
                continue

            outcome, pnl_r, held = simulate_confluence_trade(
                rates=rates,
                start_idx=idx,
                action=sig.direction,
                entry_price=sig.entry_price,
                stop_loss=sig.stop_loss,
                take_profit_1=sig.take_profit_1,
                take_profit_2=sig.take_profit_2,
                take_profit_3=sig.take_profit_3,
                spread_price=spread_price,
                max_bars=45,
            )
            trades.append({
                "outcome": outcome, "pnl_r": pnl_r, "held": held,
                "mode": sig.mode, "conf": sig.confidence_score
            })

        stats = compute_metrics(trades)

        # Determine Tier
        if friction_pass and (stats["profit_factor"] >= 1.30 or stats["win_rate"] >= 52.0) and stats["net_r"] > 0:
            tier = "TIER_1_PRIME"
        elif friction_pass and stats["profit_factor"] >= 1.05 and stats["net_r"] >= 0:
            tier = "TIER_2_VIABLE"
        elif not friction_pass:
            tier = "FRICTION_BLOCKED"
        else:
            tier = "LOW_EXPECTANCY"

        res = {
            "symbol": sym,
            "category": cat,
            "current_price": closes[-1],
            "live_spread_pts": live_spread_pts,
            "spread_price": spread_price,
            "atr_14_recent": atr_14_recent,
            "atr_14_avg": atr_14_avg,
            "spread_to_atr_recent_pct": round(spread_to_atr_recent_pct, 2),
            "spread_to_atr_avg_pct": round(spread_to_atr_avg_pct, 2),
            "friction_pass": friction_pass,
            "bars": n,
            "metrics": stats,
            "tier": tier,
        }
        results.append(res)

        print(
            f"{sym:<12} | {cat:<24} | {closes[-1]:<10.2f} | {spread_price:<8.4f} | {atr_14_avg:<10.4f} | "
            f"{spread_to_atr_avg_pct:<9.1f}% | {pass_str:<10} | {stats['total_trades']:<7} | "
            f"{stats['win_rate']:<6.1f}% | {stats['profit_factor']:<6.2f} | {stats['net_r']:<+8.1f} | {tier}"
        )

    mt5.shutdown()

    out_file = os.path.join(ROOT_DIR, "vault", "m1_candidate_evaluation_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Raw results saved to: {out_file}")
    return results

if __name__ == "__main__":
    evaluate_m1_candidates()
