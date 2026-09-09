"""
tests/simulate_range_harvester_vs_trend.py
========================================================================================
SAJIM HOLDINGS — FORENSIC BENCHMARK: HUMMINGBIRD RANGE HARVESTER VS STATIC TREND BOT
========================================================================================
Compares performance on real historical MT5 bar data (500+ M15 bars):
  - Model A: Static Trend Bot (waits for +2.5R, chokes in negative drawdown)
  - Model B: Sajim Hummingbird (boundary ping-pong, 70% cash milk at +0.35R, BE ratchet)
========================================================================================
"""

import os
import sys
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from vault_original_beep.raw_beep_equations import OriginalRawBeep


def run_benchmark():
    if not mt5.initialize():
        print("[!] Failed to initialize MT5 terminal.")
        return

    raw_beep = OriginalRawBeep()
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    lookback_bars = 500

    print("================================================================================")
    print("      SAJIM HOLDINGS QUANT LABS — RANGE MICRO-HARVESTING BENCHMARK AUDIT        ")
    print("================================================================================")
    print(f"[*] Fetching {lookback_bars} real M15 bars across {symbols} from Headway live feed...")

    results = {}

    for sym in symbols:
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, lookback_bars)
        if rates is None or len(rates) < 200:
            print(f"[!] Warning: Insufficient rates for {sym}")
            continue

        sym_info = mt5.symbol_info(sym)
        point = sym_info.point or 0.00001
        spread_pts = sym_info.spread or 8
        spread_cost = spread_pts * point
        point_val = (sym_info.trade_tick_value / (sym_info.trade_tick_size or point)) if sym_info.trade_tick_value else 100000.0
        pip_val_005 = 0.05 * 10 * (1.0 if "JPY" not in sym else 0.65) # ~$0.50 per pip

        bars = []
        for r in rates:
            bars.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "tick_vol": float(r["tick_volume"]),
            })

        # Run Simulations
        res_trend = simulate_static_trend(bars, raw_beep, pip_val_005, spread_cost, point)
        res_hummingbird = simulate_hummingbird_range(bars, raw_beep, pip_val_005, spread_cost, point)

        results[sym] = {
            "static_trend": res_trend,
            "hummingbird_range": res_hummingbird,
        }

    mt5.shutdown()

    # Save results
    out_file = os.path.join(BASE_DIR, "range_benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print Summary Report
    print("\n================================================================================")
    print("                      FORENSIC SIMULATION COMPARISON RESULTS                    ")
    print("================================================================================")
    print(f"{'Metric':<25} | {'Model A (Static Trend)':<24} | {'Model B (Hummingbird)':<24}")
    print("-" * 80)

    total_trend_pnl = sum(r["static_trend"]["net_pnl"] for r in results.values())
    total_humming_pnl = sum(r["hummingbird_range"]["net_pnl"] for r in results.values())

    total_trend_trades = sum(r["static_trend"]["total_trades"] for r in results.values())
    total_humming_trades = sum(r["hummingbird_range"]["total_trades"] for r in results.values())

    total_trend_wins = sum(r["static_trend"]["wins"] for r in results.values())
    total_humming_wins = sum(r["hummingbird_range"]["wins"] for r in results.values())

    trend_wr = (total_trend_wins / max(1, total_trend_trades)) * 100.0
    humming_wr = (total_humming_wins / max(1, total_humming_trades)) * 100.0

    print(f"{'Starting Balance':<25} | {'$400.00 USD':<24} | {'$400.00 USD':<24}")
    print(f"{'Total Realized Trades':<25} | {total_trend_trades:<24} | {total_humming_trades:<24}")
    print(f"{'Winning Trades':<25} | {total_trend_wins:<24} | {total_humming_wins:<24}")
    print(f"{'Win Rate (%)':<25} | {trend_wr:<23.1f}% | {humming_wr:<23.1f}%")
    print(f"{'Net Realized PnL ($)':<25} | {total_trend_pnl:<+23.2f}$ | {total_humming_pnl:<+23.2f}$")
    print(f"{'Final Account Equity':<25} | {f'${400 + total_trend_pnl:.2f}':<24} | {f'${400 + total_humming_pnl:.2f}':<24}")
    print(f"{'Account Net Growth':<25} | {f'{(total_trend_pnl/400.0)*100:+.1f}%':<24} | {f'{(total_humming_pnl/400.0)*100:+.1f}%':<24}")

    for sym, d in results.items():
        print(f"\n--- {sym} Individual Performance ---")
        t_a = d["static_trend"]
        t_b = d["hummingbird_range"]
        print(f"  Model A (Trend)      : Trades={t_a['total_trades']}, WinRate={t_a['win_rate']}%, NetPnL=${t_a['net_pnl']:+.2f}, MaxDD={t_a['max_dd']:.2f}%")
        print(f"  Model B (Hummingbird): Trades={t_b['total_trades']}, WinRate={t_b['win_rate']}%, NetPnL=${t_b['net_pnl']:+.2f}, MaxDD={t_b['max_dd']:.2f}%")

    print("\n================================================================================")


def simulate_static_trend(bars: List[Dict[str, Any]], raw_beep: Any, pip_val: float, spread_cost: float, point: float) -> Dict[str, Any]:
    """Model A: Tries to hold for +2.5R, trails in negative (choking), trades blindly in ranges."""
    balance = 400.0
    equity = 400.0
    peak_equity = 400.0
    max_dd = 0.0
    trades = []
    wins = 0
    losses = 0

    in_trade = False
    entry_p = 0.0
    sl = 0.0
    tp = 0.0
    action = "BUY"
    risk_pips = 15.0

    for i in range(25, len(bars)):
        window_closes = [b["close"] for b in bars[i-20:i]]
        b_t = raw_beep.calculate_raw_baseline_B(window_closes)
        cur = bars[i]

        if not in_trade:
            # Simple momentum entry
            if cur["close"] > b_t and bars[i-1]["close"] <= b_t:
                in_trade = True
                action = "BUY"
                entry_p = cur["close"] + spread_cost
                sl = entry_p - (risk_pips * point * 10)
                tp = entry_p + (risk_pips * 2.5 * point * 10)
            elif cur["close"] < b_t and bars[i-1]["close"] >= b_t:
                in_trade = True
                action = "SELL"
                entry_p = cur["close"]
                sl = entry_p + (risk_pips * point * 10)
                tp = entry_p - (risk_pips * 2.5 * point * 10)
        else:
            # Trailing Choke in Drawdown flaw:
            # If price drops 5 pips against, amateur bot tightens stop to 7 pips
            pdist_pips = ((cur["close"] - entry_p) if action == "BUY" else (entry_p - cur["close"])) / (point * 10)

            # Choke check
            if pdist_pips < -4.0:
                # Tightened stop
                if action == "BUY":
                    sl = max(sl, entry_p - (6.0 * point * 10))
                else:
                    sl = min(sl, entry_p + (6.0 * point * 10))

            # Check hit
            if action == "BUY":
                if cur["low"] <= sl:
                    loss_pips = (entry_p - sl) / (point * 10)
                    pnl = -loss_pips * pip_val
                    balance += pnl
                    losses += 1
                    trades.append(pnl)
                    in_trade = False
                elif cur["high"] >= tp:
                    win_pips = (tp - entry_p) / (point * 10)
                    pnl = win_pips * pip_val
                    balance += pnl
                    wins += 1
                    trades.append(pnl)
                    in_trade = False
            else:
                if cur["high"] >= sl:
                    loss_pips = (sl - entry_p) / (point * 10)
                    pnl = -loss_pips * pip_val
                    balance += pnl
                    losses += 1
                    trades.append(pnl)
                    in_trade = False
                elif cur["low"] <= tp:
                    win_pips = (entry_p - tp) / (point * 10)
                    pnl = win_pips * pip_val
                    balance += pnl
                    wins += 1
                    trades.append(pnl)
                    in_trade = False

        equity = balance
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity * 100.0
        if dd > max_dd:
            max_dd = dd

    total_trades = wins + losses
    net_pnl = balance - 400.0
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round((wins / max(1, total_trades)) * 100.0, 1),
        "net_pnl": round(net_pnl, 2),
        "max_dd": round(max_dd, 2),
    }


def simulate_hummingbird_range(bars: List[Dict[str, Any]], raw_beep: Any, pip_val: float, spread_cost: float, point: float) -> Dict[str, Any]:
    """Model B: Detects Range, Fades Rejection Wicks, Banks 70% cash at +0.35R, BE Ratchet, Exits at Baseline B(t)."""
    balance = 400.0
    equity = 400.0
    peak_equity = 400.0
    max_dd = 0.0
    trades = []
    wins = 0
    losses = 0

    in_trade = False
    entry_p = 0.0
    sl = 0.0
    tp_baseline = 0.0
    action = "BUY"
    milked = False
    initial_risk_pips = 6.0

    for i in range(25, len(bars)):
        window_closes = [b["close"] for b in bars[i-20:i]]
        b_t = raw_beep.calculate_raw_baseline_B(window_closes)
        m_mag = raw_beep.calculate_raw_mass_M(window_closes, b_t)
        cur = bars[i]

        # ATR 14 estimation
        trs = [max(bars[k]["high"] - bars[k]["low"], abs(bars[k]["high"] - bars[k]["close"]), abs(bars[k]["low"] - bars[k]["close"])) for k in range(i-14, i)]
        atr = sum(trs) / len(trs)

        rng = max(1e-6, cur["high"] - cur["low"])
        upper_wick = (cur["high"] - max(cur["open"], cur["close"])) / rng
        lower_wick = (min(cur["open"], cur["close"]) - cur["low"]) / rng

        # Range Condition: Kinetic mass < 60 and ATR is tight
        is_range = (m_mag < 60.0)

        if not in_trade and is_range:
            # Ceiling Rejection: Price above Baseline with Upper Wick > 40%
            if cur["close"] > b_t and upper_wick > 0.40:
                in_trade = True
                action = "SELL"
                entry_p = cur["close"]
                sl = cur["high"] + (2.0 * point * 10)  # Micro-stop: 2 pips above wick
                initial_risk_pips = max(4.0, (sl - entry_p) / (point * 10))
                tp_baseline = b_t  # Target is Baseline B(t)
                milked = False
            # Floor Rejection: Price below Baseline with Lower Wick > 40%
            elif cur["close"] < b_t and lower_wick > 0.40:
                in_trade = True
                action = "BUY"
                entry_p = cur["close"] + spread_cost
                sl = cur["low"] - (2.0 * point * 10)   # Micro-stop: 2 pips below wick
                initial_risk_pips = max(4.0, (entry_p - sl) / (point * 10))
                tp_baseline = b_t  # Target is Baseline B(t)
                milked = False
        elif in_trade:
            # In-trade execution
            pdist_pips = ((cur["close"] - entry_p) if action == "BUY" else (entry_p - cur["close"])) / (point * 10)
            profit_r = pdist_pips / initial_risk_pips

            # 1. Micro-Harvest at +0.35R (Bank 70% cash, Ratchet remainder to Break-Even)
            if profit_r >= 0.35 and not milked:
                milked = True
                banked_pips = pdist_pips
                # 70% volume cash banked
                pnl_70 = banked_pips * pip_val * 0.70
                balance += pnl_70
                # Ratchet SL to Break-Even + 1 pip
                if action == "BUY":
                    sl = entry_p + (1.0 * point * 10)
                else:
                    sl = entry_p - (1.0 * point * 10)

            # 2. Check Exits
            if action == "BUY":
                # Hit Baseline Target (full harvest of remaining 30%)
                if cur["high"] >= tp_baseline:
                    rem_pips = (tp_baseline - entry_p) / (point * 10)
                    rem_pnl = rem_pips * pip_val * (0.30 if milked else 1.0)
                    balance += rem_pnl
                    wins += 1
                    trades.append(rem_pnl)
                    in_trade = False
                elif cur["low"] <= sl:
                    if milked:
                        # Remainder exits at Break-Even (+1 pip)
                        rem_pnl = 1.0 * pip_val * 0.30
                        balance += rem_pnl
                        wins += 1
                        trades.append(rem_pnl)
                    else:
                        loss_pips = (entry_p - sl) / (point * 10)
                        pnl = -loss_pips * pip_val
                        balance += pnl
                        losses += 1
                        trades.append(pnl)
                    in_trade = False
            else:
                # SELL Hit Baseline Target
                if cur["low"] <= tp_baseline:
                    rem_pips = (entry_p - tp_baseline) / (point * 10)
                    rem_pnl = rem_pips * pip_val * (0.30 if milked else 1.0)
                    balance += rem_pnl
                    wins += 1
                    trades.append(rem_pnl)
                    in_trade = False
                elif cur["high"] >= sl:
                    if milked:
                        rem_pnl = 1.0 * pip_val * 0.30
                        balance += rem_pnl
                        wins += 1
                        trades.append(rem_pnl)
                    else:
                        loss_pips = (sl - entry_p) / (point * 10)
                        pnl = -loss_pips * pip_val
                        balance += pnl
                        losses += 1
                        trades.append(pnl)
                    in_trade = False

        equity = balance
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity * 100.0
        if dd > max_dd:
            max_dd = dd

    total_trades = wins + losses
    net_pnl = balance - 400.0
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round((wins / max(1, total_trades)) * 100.0, 1),
        "net_pnl": round(net_pnl, 2),
        "max_dd": round(max_dd, 2),
    }


if __name__ == "__main__":
    run_benchmark()
