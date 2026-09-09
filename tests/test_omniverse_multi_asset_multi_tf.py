"""
========================================================================================
     SAJIM HOLDINGS — COMPREHENSIVE MULTI-ASSET MULTI-TIMEFRAME QUANT BENCHMARK
                         (test_omniverse_multi_asset_multi_tf.py)
========================================================================================
Tests Jimmy Mathu's Universal Engine across MULTIPLE PAIRS & ALL AVAILABLE TIMEFRAMES:
  Pairs: XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, GBPJPY
  Timeframes: M1, M5, M15, M30, H1, H4
  Data: 100% Real Live Institutional Broker Candles
  Dynamic Scaling: Fixed-Fractional Risk & Scale-Invariant Compounding
========================================================================================
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault"), BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from vault_original_beep.raw_beep_equations import OriginalRawBeep


def run_comprehensive_benchmark():
    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal_path):
        raise RuntimeError(f"Cannot initialize MT5: {mt5.last_error()}")

    account = mt5.account_info()
    print("=" * 95)
    print(f"      SAJIM HOLDINGS — GLOBAL MULTI-ASSET & MULTI-TIMEFRAME QUANT BENCHMARK")
    print(f"      BROKER SERVER : {account.server} | ACCOUNT: {account.login} ({account.name})")
    print(f"      LIVE EQUITY   : {account.equity:.2f} {account.currency} (Balance: {account.balance:.2f})")
    print("=" * 95)

    test_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "GBPJPY"]
    tf_configs = [
        ("M1", mt5.TIMEFRAME_M1, 1),
        ("M5", mt5.TIMEFRAME_M5, 5),
        ("M15", mt5.TIMEFRAME_M15, 15),
        ("M30", mt5.TIMEFRAME_M30, 30),
        ("H1", mt5.TIMEFRAME_H1, 60),
        ("H4", mt5.TIMEFRAME_H4, 240),
    ]

    raw_beep = OriginalRawBeep()
    lookback = 12
    candles_per_test = 500  # 500 candles per front

    summary_results = []

    for sym in test_symbols:
        mt5.symbol_select(sym, True)
        sym_info = mt5.symbol_info(sym)
        if sym_info is None:
            continue

        point_val = (sym_info.trade_tick_value / sym_info.trade_tick_size) if sym_info.trade_tick_size > 0 else 1.0

        for tf_label, tf_enum, tf_mins in tf_configs:
            rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, candles_per_test)
            if rates is None or len(rates) < lookback + 20:
                continue

            prices = [float(r["close"]) for r in rates]
            highs = [float(r["high"]) for r in rates]
            lows = [float(r["low"]) for r in rates]

            # Dynamic balance simulation starting from $1,000 USD (or equivalent)
            balance = 1000.0
            peak_balance = balance
            max_dd_dollars = 0.0
            max_dd_pct = 0.0

            trades = []
            active_trade = None
            consecutive_wins = 0
            consecutive_losses = 0
            max_cons_losses = 0

            for i in range(lookback, len(prices)):
                cur_close = prices[i]
                cur_high = highs[i]
                cur_low = lows[i]

                # 1. Manage Active Trade
                if active_trade is not None:
                    pos = active_trade
                    closed = False
                    exit_price = cur_close
                    reason = ""

                    if pos["direction"] == "BUY":
                        if cur_high >= pos["tp"]:
                            closed = True
                            exit_price = pos["tp"]
                            reason = "TP"
                        elif cur_low <= pos["sl"]:
                            closed = True
                            exit_price = pos["sl"]
                            reason = "SL"
                    else:
                        if cur_low <= pos["tp"]:
                            closed = True
                            exit_price = pos["tp"]
                            reason = "TP"
                        elif cur_high >= pos["sl"]:
                            closed = True
                            exit_price = pos["sl"]
                            reason = "SL"

                    # Time decay exit (Lambda friction: 14 bars max holding)
                    if not closed and (i - pos["entry_idx"]) >= 14:
                        closed = True
                        exit_price = cur_close
                        reason = "TIME_DECAY"

                    if closed:
                        price_diff = (exit_price - pos["entry_price"]) if pos["direction"] == "BUY" else (pos["entry_price"] - exit_price)
                        pnl = price_diff * pos["lot"] * point_val
                        balance += pnl

                        if pnl > 0:
                            consecutive_wins += 1
                            consecutive_losses = 0
                        else:
                            consecutive_losses += 1
                            consecutive_wins = 0

                        max_cons_losses = max(max_cons_losses, consecutive_losses)
                        peak_balance = max(peak_balance, balance)
                        dd = peak_balance - balance
                        dd_p = (dd / peak_balance) * 100.0 if peak_balance > 0 else 0.0
                        max_dd_dollars = max(max_dd_dollars, dd)
                        max_dd_pct = max(max_dd_pct, dd_p)

                        trades.append({"pnl": pnl, "win": pnl > 0, "reason": reason})
                        active_trade = None

                # 2. Check for New Setup if Flat
                if active_trade is None:
                    window = prices[i - lookback : i + 1]
                    b_t = raw_beep.calculate_raw_baseline_B(window)
                    m_t = raw_beep.calculate_raw_mass_M(window, b_t)

                    abs_m = abs(m_t)
                    action = None
                    rr = 0.0

                    if abs_m >= 55.0:  # RARE LAYER
                        action = "BUY" if m_t > 0 else "SELL"
                        rr = 3.5
                    elif abs_m >= 35.0:  # CERTIFIED LAYER
                        action = "BUY" if m_t > 0 else "SELL"
                        rr = 2.5

                    if action is not None:
                        risk_dist = max(sym_info.point * 35.0, abs(cur_close - b_t))
                        if action == "BUY":
                            sl = cur_close - risk_dist
                            tp = cur_close + (risk_dist * rr)
                        else:
                            sl = cur_close + risk_dist
                            tp = cur_close - (risk_dist * rr)

                        # Dynamic Lot (5% risk scaled by streak)
                        risk_pct = min(0.12, 0.05 * (1.35 ** consecutive_wins))
                        risk_cash = balance * risk_pct
                        raw_lot = risk_cash / (risk_dist * point_val) if (risk_dist * point_val) > 0 else sym_info.volume_min
                        steps = round((raw_lot - sym_info.volume_min) / sym_info.volume_step)
                        lot = sym_info.volume_min + (steps * sym_info.volume_step)
                        lot = max(sym_info.volume_min, min(sym_info.volume_max, lot))
                        lot = round(lot, 2)

                        active_trade = {
                            "entry_idx": i,
                            "direction": action,
                            "entry_price": cur_close,
                            "sl": sl,
                            "tp": tp,
                            "lot": lot,
                        }

            tot_t = len(trades)
            wins = [t for t in trades if t["win"]]
            win_rate = (len(wins) / tot_t * 100.0) if tot_t > 0 else 0.0
            roi_pct = ((balance - 1000.0) / 1000.0) * 100.0

            summary_results.append({
                "symbol": sym,
                "tf": tf_label,
                "trades": tot_t,
                "wins": len(wins),
                "win_rate": round(win_rate, 1),
                "net_pnl": round(balance - 1000.0, 2),
                "roi_pct": round(roi_pct, 1),
                "max_dd_pct": round(max_dd_pct, 1),
                "max_cons_losses": max_cons_losses,
            })

    mt5.shutdown()

    # Sort results by Net ROI
    summary_results.sort(key=lambda x: x["roi_pct"], reverse=True)

    print("\n" + "=" * 95)
    print("          SAJIM HOLDINGS MULTI-ASSET MULTI-TIMEFRAME QUANT LEDGER")
    print("=" * 95)
    print(f"{'SYMBOL':<10} | {'TF':<5} | {'TRADES':<7} | {'WINS':<6} | {'WIN RATE':<9} | {'NET PNL ($)':<12} | {'ROI %':<8} | {'MAX DD %':<9} | {'MAX LOSS STREAK'}")
    print("-" * 95)

    for r in summary_results:
        print(f"{r['symbol']:<10} | {r['tf']:<5} | {r['trades']:<7} | {r['wins']:<6} | {r['win_rate']:>5.1f}%   | ${r['net_pnl']:>+10.2f} | {r['roi_pct']:>+6.1f}% | {r['max_dd_pct']:>6.1f}%  | {r['max_cons_losses']:<4}")

    print("=" * 95)

    # Save to JSON
    out_path = os.path.join(BASE_DIR, "multi_asset_multi_tf_benchmark.json")
    with open(out_path, "w") as f:
        json.dump(summary_results, f, indent=2)
    print(f"[+] Full benchmark ledger saved to {out_path}")


if __name__ == "__main__":
    run_comprehensive_benchmark()
