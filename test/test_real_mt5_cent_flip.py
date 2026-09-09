"""
Sajim Holdings — 100% REAL LIVE MT5 DATA EMPIRICAL CENT FLIP TEST (test_real_mt5_cent_flip.py)
Directly queries MetaTrader 5 Terminal for 1,000 REAL institutional 5-minute candles on Gold (XAUUSD).
Account: $4.00 USD (400 USC Cents)
Position Sizing: 0.01 Cent Lot
Enforces:
  1. 1:3.5 Asymmetric R:R with Invalidation Floor at B(t)
  2. Jimmy Mathu's Lambda Time-Friction Exit (The Fight Against Time)
  3. Pre-execution False Truth filter (Trapped Wick absorption)
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault"), BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from beep_core import BeepCoreEngine
from beep_narrative import BeepNarrativeEngine
from backtester import BeepBacktester


def run_real_mt5_test():
    print("=" * 85)
    print("      SAJIM HOLDINGS — 100% REAL LIVE METATRADER 5 DATA TEST")
    print("      Testing BEEP Narrative & Time-Friction Mechanics on a $4.00 USD (400 USC) Account")
    print("=" * 85)

    # 1. Initialize MT5 and Pull 100% Real Broker Candles
    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal_path):
        raise RuntimeError(f"Failed to connect to MT5 terminal at {terminal_path}")

    symbol = "XAUUSD"
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1000)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise RuntimeError("No rates received from MT5.")

    print(f"[+] Successfully extracted {len(rates)} REAL institutional M5 candles for {symbol} from MT5.")
    print(f"    Earliest Real Candle: {datetime.fromtimestamp(rates[0]['time']).strftime('%Y-%m-%d %H:%M')}")
    print(f"    Latest Real Candle  : {datetime.fromtimestamp(rates[-1]['time']).strftime('%Y-%m-%d %H:%M')}")

    # Format into standard bar dictionary
    bars = []
    for r in rates:
        bars.append({
            "timestamp": int(r["time"]),
            "datetime": datetime.fromtimestamp(r["time"]).strftime("%Y-%m-%d %H:%M"),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["tick_volume"]),
            "spread": float(r["spread"]) / 100.0,  # broker spread in dollars
        })

    # 2. Cent Account Mechanics:
    # Starting Capital: 400.0 Cents ($4.00 USD)
    # 0.01 Cent Lot on Gold:
    # 1 standard lot = 100 oz. 1 cent lot = 1 oz. 0.01 cent lot = 0.01 oz.
    # $1.00 move on Gold = 1.0 Cent PnL (1 USC).
    balance = 400.0  # Cents
    initial_balance = balance
    peak_balance = balance
    max_dd_cents = 0.0
    max_dd_pct = 0.0

    narrative_eng = BeepNarrativeEngine()
    backtester = BeepBacktester()

    trades = []
    open_pos = None
    lookback = 15

    consecutive_losses = 0
    circuit_cooldown = 0

    for i in range(lookback, len(bars)):
        cur_bar = bars[i]

        if circuit_cooldown > 0:
            circuit_cooldown -= 1

        # -------------------------------------------------------------
        # A. MANAGE ACTIVE POSITION — THE FIGHT AGAINST TIME
        # -------------------------------------------------------------
        if open_pos is not None:
            elapsed_bars = i - open_pos["entry_bar_idx"]
            elapsed_minutes = elapsed_bars * 5

            closed = False
            exit_price = 0.0
            exit_reason = ""

            if open_pos["direction"] == "BUY":
                if cur_bar["low"] <= open_pos["sl"]:
                    closed = True
                    exit_price = open_pos["sl"]
                    exit_reason = "STOP_LOSS"
                elif cur_bar["high"] >= open_pos["tp2"]:
                    closed = True
                    exit_price = open_pos["tp2"]
                    exit_reason = "TP2_RUNNER_1:3.5"
                # TP1 partial harvest at 1:2.0 and move SL to breakeven
                elif cur_bar["high"] >= open_pos["tp1"] and not open_pos["tp1_hit"]:
                    open_pos["tp1_hit"] = True
                    open_pos["sl"] = open_pos["entry_price"]
                    partial_pnl = (open_pos["tp1"] - open_pos["entry_price"]) * 0.5
                    balance += partial_pnl
                # TIME-DECAY EXIT: If position stalls for > 6 bars (30 mins), harvest/cut
                elif elapsed_bars >= 6:
                    closed = True
                    exit_price = cur_bar["close"]
                    exit_reason = f"TIME_FRICTION_{elapsed_minutes}M"

            elif open_pos["direction"] == "SELL":
                if cur_bar["high"] >= open_pos["sl"]:
                    closed = True
                    exit_price = open_pos["sl"]
                    exit_reason = "STOP_LOSS"
                elif cur_bar["low"] <= open_pos["tp2"]:
                    closed = True
                    exit_price = open_pos["tp2"]
                    exit_reason = "TP2_RUNNER_1:3.5"
                elif cur_bar["low"] <= open_pos["tp1"] and not open_pos["tp1_hit"]:
                    open_pos["tp1_hit"] = True
                    open_pos["sl"] = open_pos["entry_price"]
                    partial_pnl = (open_pos["entry_price"] - open_pos["tp1"]) * 0.5
                    balance += partial_pnl
                elif elapsed_bars >= 6:
                    closed = True
                    exit_price = cur_bar["close"]
                    exit_reason = f"TIME_FRICTION_{elapsed_minutes}M"

            if closed:
                mult = 1 if open_pos["direction"] == "BUY" else -1
                gross_pnl_cents = (exit_price - open_pos["entry_price"]) * mult
                spread_cents = cur_bar["spread"]
                net_pnl_cents = gross_pnl_cents - spread_cents
                balance += net_pnl_cents

                if net_pnl_cents <= 0:
                    consecutive_losses += 1
                    if consecutive_losses >= 3:
                        circuit_cooldown = 6  # 30-minute cooldown
                else:
                    consecutive_losses = 0

                peak_balance = max(peak_balance, balance)
                dd = peak_balance - balance
                dd_pct = (dd / peak_balance) * 100.0 if peak_balance > 0 else 0.0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd_cents = dd

                trades.append({
                    "trade_id": len(trades) + 1,
                    "symbol": "XAUUSD",
                    "direction": open_pos["direction"],
                    "entry_time": open_pos["entry_time"],
                    "exit_time": cur_bar["datetime"],
                    "duration_mins": elapsed_minutes,
                    "entry_price": round(open_pos["entry_price"], 2),
                    "exit_price": round(exit_price, 2),
                    "sl": round(open_pos["initial_sl"], 2),
                    "tp": round(open_pos["tp2"], 2),
                    "tp2": round(open_pos["tp2"], 2),
                    "lot_size": 0.01,
                    "b_t": round(open_pos["b_t"], 2),
                    "m_t": round(open_pos["m_t"], 1),
                    "exit_reason": exit_reason,
                    "net_pnl_cents": round(net_pnl_cents, 2),
                    "net_pnl_usd": round(net_pnl_cents / 100.0, 4),
                    "running_balance": round(balance / 100.0, 2),
                    "running_balance_cents": round(balance, 2),
                    "running_balance_usd": round(balance / 100.0, 2),
                })
                open_pos = None

        # -------------------------------------------------------------
        # B. SCAN FOR DIAMOND/CERTIFIED REAL NARRATIVE
        # -------------------------------------------------------------
        if open_pos is None and circuit_cooldown == 0:
            history = [b["close"] for b in bars[i - lookback : i + 1]]

            narr = narrative_eng.generate_narrative(symbol="XAUUSD", prices=history, account_balance=400.0)

            if narr["quality"] in ["DIAMOND", "CERTIFIED"] and narr["trade_action"] in ["BUY", "SELL"]:
                # False Truth Wick Filter (Avoid getting trapped by retail sweeps)
                high_p = cur_bar["high"]
                low_p = cur_bar["low"]
                open_p = cur_bar["open"]
                close_p = cur_bar["close"]
                tot_range = max(1e-4, high_p - low_p)

                is_trap = False
                if narr["trade_action"] == "BUY" and ((high_p - max(open_p, close_p)) / tot_range) > 0.45:
                    is_trap = True
                elif narr["trade_action"] == "SELL" and ((min(open_p, close_p) - low_p) / tot_range) > 0.45:
                    is_trap = True

                if not is_trap:
                    b_t = narr["b_t"]
                    risk_dist = max(2.5, abs(close_p - b_t))

                    if narr["trade_action"] == "BUY":
                        sl = close_p - risk_dist
                        tp1 = close_p + (risk_dist * 2.0)
                        tp2 = close_p + (risk_dist * 3.5)
                    else:
                        sl = close_p + risk_dist
                        tp1 = close_p - (risk_dist * 2.0)
                        tp2 = close_p - (risk_dist * 3.5)

                    open_pos = {
                        "direction": narr["trade_action"],
                        "entry_price": close_p,
                        "entry_time": cur_bar["datetime"],
                        "entry_bar_idx": i,
                        "sl": sl,
                        "initial_sl": sl,
                        "tp1": tp1,
                        "tp2": tp2,
                        "b_t": b_t,
                        "m_t": narr["m_t"],
                        "tp1_hit": False,
                    }

    # 3. Metrics Compilation
    total_trades = len(trades)
    wins = [t for t in trades if t["net_pnl_cents"] > 0]
    losses = [t for t in trades if t["net_pnl_cents"] <= 0]
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

    total_profit_cents = sum(t["net_pnl_cents"] for t in wins)
    total_loss_cents = abs(sum(t["net_pnl_cents"] for t in losses))
    pf = round(total_profit_cents / total_loss_cents, 2) if total_loss_cents > 0 else 99.0

    net_cents = round(balance - initial_balance, 2)
    net_usd = round(net_cents / 100.0, 2)
    roi = round((net_cents / initial_balance) * 100.0, 2)
    avg_duration = sum(t["duration_mins"] for t in trades) / total_trades if total_trades > 0 else 0.0

    # Number of days in sample: 1000 bars * 5 mins = 5,000 mins = 83.3 hours = 3.5 trading days
    sample_days = (bars[-1]["timestamp"] - bars[0]["timestamp"]) / 86400.0
    catches_per_day = total_trades / max(1.0, sample_days)

    test_results = {
        "symbol": "XAUUSD_M5_REAL_MT5",
        "style": "REAL_MT5_CENT_FLIP",
        "initial_balance": initial_balance / 100.0,
        "final_balance": round(balance / 100.0, 2),
        "net_profit_usd": net_usd,
        "roi_pct": roi,
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": pf,
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_usd": round(max_dd_cents / 100.0, 2),
        "initial_balance_cents": initial_balance,
        "final_balance_cents": round(balance, 2),
        "net_profit_cents": net_cents,
        "catches_per_day": round(catches_per_day, 1),
        "avg_trade_duration_mins": round(avg_duration, 1),
        "trades": trades,
    }

    test_desc = (
        "100% REAL LIVE METATRADER 5 DATA TEST. Evaluates 1,000 real broker M5 candles on Gold (XAUUSD) "
        "with real spreads. Demonstrates exact mechanics of a $4.00 USD (400 Cents) starter seed, "
        "1:3.5 Asymmetric R:R, and Jimmy Mathu's Lambda Time-Friction Exit."
    )
    saved_dir = backtester.save_test_results("test_006_real_mt5_cent_flip_4usd", test_desc, test_results)

    print("\n" + "=" * 85)
    print("               TEST 006: REAL METATRADER 5 DATA RESULTS")
    print("=" * 85)
    print(f"[*] Starting Balance        : {initial_balance:.2f} USC (${initial_balance/100.0:.2f} USD)")
    print(f"[*] Final Balance           : {balance:.2f} USC (${balance/100.0:.2f} USD)")
    print(f"[*] Net Profit              : {net_cents:+.2f} USC (${net_usd:+.2f} USD | {roi:+.2f}%)")
    print(f"[*] Total Trades Executed   : {total_trades} trades across {sample_days:.1f} days of real data")
    print(f"[*] Catches Per Day (Rate)  : {catches_per_day:.1f} high-conviction catches / day")
    print(f"[*] Win Rate                : {win_rate:.2f}%")
    print(f"[*] Profit Factor           : {pf}")
    print(f"[*] Max Drawdown            : {max_dd_pct:.2f}% ({max_dd_cents:.2f} USC)")
    print(f"[*] Avg Trade Duration      : {avg_duration:.1f} minutes (The Fight Against Time)")
    print("=" * 85)

    print("\nRecent 15 Executed Trades on 100% Real MT5 Broker Candles:")
    print("-" * 85)
    print(f"{'ID':<4} {'DIR':<5} {'ENTRY TIME':<17} {'DURATION':<10} {'ENTRY':<9} {'EXIT':<9} {'PnL (USC)':<10} {'EXIT REASON'}")
    print("-" * 85)
    for t in trades[-15:]:
        print(f"#{t['trade_id']:<3} {t['direction']:<5} {t['entry_time']:<17} {t['duration_mins']} mins   {t['entry_price']:<9.2f} {t['exit_price']:<9.2f} {t['net_pnl_cents']:>+8.2f}  {t['exit_reason']}")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_real_mt5_test()
