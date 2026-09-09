"""
Sajim Holdings — $4 USD Cent Account (400 USC) Live Data Empirical Test (test_4usd_cent_flip.py)
Tests BEEP Institutional Narrative on 1,033 REAL LIVE 5-minute Gold (XAUUSD) candles.
Account: Headway Cent Seed = 400 Cents ($4.00 USD)
Lot Size: 0.01 Cent Lot (0.01 oz Gold, 1 cent per $1.00 move)
R:R: 1:3.5 Asymmetric Execution with Lambda Time Exit.
"""

import os
import sys
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault"), BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from beep_core import BeepCoreEngine
from beep_narrative import BeepNarrativeEngine
from backtester import BeepBacktester


def run_cent_flip_test():
    print("=" * 80)
    print("      BEEP $4.00 USD (400 CENTS) LIVE DATA EMPIRICAL TEST")
    print("      Asset: XAUUSD (Gold) | Timeframe: 5-Minute (M5) Live Market Candles")
    print("      Account: 400.0 USC ($4.00 USD) | Position: 0.01 Cent Lot")
    print("=" * 80)

    backtester = BeepBacktester()
    core = BeepCoreEngine()
    narrative_eng = BeepNarrativeEngine()

    # 1. Fetch REAL LIVE 5-Minute Gold Data
    print("[*] Ingesting real 5-minute Gold market candles from live feed...")
    bars = backtester.fetch_yahoo_historical(ticker="GC=F", interval="5m", range_period="5d")
    print(f"[+] Loaded {len(bars)} live 5-minute bars covering the last 5 trading days.")

    # 2. Cent Account Mechanics
    # Starting balance = 400 cents ($4.00 USD)
    balance = 400.0  # USC (cents)
    initial_balance = balance
    peak_balance = balance
    max_dd_cents = 0.0
    max_dd_pct = 0.0

    # 0.01 Cent Lot on Gold:
    # 1 Standard Lot = 100 oz. 1 Cent Lot = 1 oz. 0.01 Cent Lot = 0.01 oz.
    # $1.00 Gold price movement = $0.01 USD = 1.0 Cent (1 USC).
    cent_contract_mult = 1.0  # 1 price point = 1 cent PnL
    spread_cents = 0.35  # 35 cents per standard lot = 0.35 cents on 0.01 cent lot

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
        # A. MANAGE OPEN POSITION (FIGHT AGAINST TIME)
        # -------------------------------------------------------------
        if open_pos is not None:
            elapsed_bars = i - open_pos["entry_bar_idx"]
            elapsed_minutes = elapsed_bars * 5

            closed = False
            exit_price = 0.0
            exit_reason = ""

            # Check Stop Loss & Take Profits
            if open_pos["direction"] == "BUY":
                if cur_bar["low"] <= open_pos["sl"]:
                    closed = True
                    exit_price = open_pos["sl"]
                    exit_reason = "STOP_LOSS"
                elif cur_bar["high"] >= open_pos["tp2"]:
                    closed = True
                    exit_price = open_pos["tp2"]
                    exit_reason = "TP2_RUNNER_1:3.5"
                # TP1 Hit: Partial 50% harvest and move SL to Entry (Breakeven)
                elif cur_bar["high"] >= open_pos["tp1"] and not open_pos["tp1_hit"]:
                    open_pos["tp1_hit"] = True
                    open_pos["sl"] = open_pos["entry_price"]  # Breakeven lock
                    partial_pnl = (open_pos["tp1"] - open_pos["entry_price"]) * 0.5 * cent_contract_mult
                    balance += partial_pnl
                # TIME-FRICTION EXIT: Lambda decay half-life at 6-8 bars (30-40 mins)
                elif elapsed_bars >= 8:
                    closed = True
                    exit_price = cur_bar["close"]
                    exit_reason = f"TIME_EXPIRATION_{elapsed_minutes}MIN"

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
                    partial_pnl = (open_pos["entry_price"] - open_pos["tp1"]) * 0.5 * cent_contract_mult
                    balance += partial_pnl
                elif elapsed_bars >= 8:
                    closed = True
                    exit_price = cur_bar["close"]
                    exit_reason = f"TIME_EXPIRATION_{elapsed_minutes}MIN"

            if closed:
                mult = 1 if open_pos["direction"] == "BUY" else -1
                pnl_cents = (exit_price - open_pos["entry_price"]) * mult * cent_contract_mult - spread_cents
                balance += pnl_cents

                if pnl_cents <= 0:
                    consecutive_losses += 1
                    if consecutive_losses >= 3:
                        circuit_cooldown = 6  # Halt 30 minutes on chop
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
                    "direction": open_pos["direction"],
                    "entry_time": open_pos["entry_time"],
                    "exit_time": cur_bar["datetime"],
                    "duration_mins": elapsed_minutes,
                    "entry_price": open_pos["entry_price"],
                    "exit_price": round(exit_price, 2),
                    "sl": round(open_pos["initial_sl"], 2),
                    "tp2": round(open_pos["tp2"], 2),
                    "b_t": round(open_pos["b_t"], 2),
                    "m_t": round(open_pos["m_t"], 1),
                    "exit_reason": exit_reason,
                    "net_pnl_cents": round(pnl_cents, 2),
                    "net_pnl_usd": round(pnl_cents / 100.0, 4),
                    "running_balance_cents": round(balance, 2),
                    "running_balance_usd": round(balance / 100.0, 2),
                })
                open_pos = None

        # -------------------------------------------------------------
        # B. SCAN FOR DIAMOND/CERTIFIED NARRATIVE (FIGHT AGAINST TIME)
        # -------------------------------------------------------------
        if open_pos is None and circuit_cooldown == 0:
            history = [b["close"] for b in bars[i - lookback : i + 1]]

            # Run BEEP Institutional Narrative Engine
            narr = narrative_eng.generate_narrative(symbol="XAUUSD", prices=history, account_balance=400.0)

            # High-conviction filter: Diamond or Certified
            if narr["quality"] in ["DIAMOND", "CERTIFIED"] and narr["trade_action"] in ["BUY", "SELL"]:
                # Pre-execution check: False Truth (wick exhaustion trap)
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

                    # 1:3.5 Asymmetric Setup
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

    # 3. Calculate Results
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

    # Save to test catalog
    test_results = {
        "symbol": "XAUUSD_M5_LIVE",
        "style": "CENT_ACCOUNT_ASYMMETRIC_M5",
        "initial_balance_cents": initial_balance,
        "initial_balance_usd": initial_balance / 100.0,
        "final_balance_cents": round(balance, 2),
        "final_balance_usd": round(balance / 100.0, 2),
        "net_profit_cents": net_cents,
        "net_profit_usd": net_usd,
        "roi_pct": roi,
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": pf,
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_cents": round(max_dd_cents, 2),
        "avg_trade_duration_minutes": round(avg_duration, 1),
        "trades": trades,
    }

    test_desc = (
        "Empirical $4.00 USD (400 USC) Cent Account stress-test on 1,033 REAL LIVE 5-minute Gold candles. "
        "Enforces Jimmy Mathu's Lambda Time-Friction Exit (cutting dead trades within 40 minutes) "
        "and 1:3.5 Asymmetric R:R. Validates the exact survival and account flip mechanics on micro-cent seeds."
    )
    saved_dir = backtester.save_test_results("test_006_cent_4usd_live_m5_gold", test_desc, test_results)

    print("\n" + "=" * 80)
    print("                     TEST 006 LIVE CENT ACCOUNT REPORT")
    print("=" * 80)
    print(f"[*] Starting Balance        : 400.00 USC ($4.00 USD)")
    print(f"[*] Final Balance           : {balance:.2f} USC (${balance/100.0:.2f} USD)")
    print(f"[*] Net Profit              : {net_cents:+.2f} USC (${net_usd:+.2f} USD | {roi:+.2f}%)")
    print(f"[*] Total Trades Executed   : {total_trades} trades across 5 trading days")
    print(f"[*] Catches Per Day (Rate)  : {total_trades / 5.0:.1f} catches / day")
    print(f"[*] Win Rate                : {win_rate:.2f}%")
    print(f"[*] Profit Factor           : {pf}")
    print(f"[*] Max Drawdown            : {max_dd_pct:.2f}% ({max_dd_cents:.2f} USC)")
    print(f"[*] Avg Trade Duration      : {avg_duration:.1f} minutes (The Fight Against Time)")
    print("=" * 80)

    print("\nRecent 10 Executed Trades on Real Live Candles:")
    print("-" * 80)
    print(f"{'ID':<4} {'DIR':<5} {'ENTRY TIME':<17} {'DURATION':<10} {'ENTRY':<8} {'EXIT':<8} {'PnL (USC)':<10} {'EXIT REASON'}")
    print("-" * 80)
    for t in trades[-10:]:
        print(f"#{t['trade_id']:<3} {t['direction']:<5} {t['entry_time']:<17} {t['duration_mins']} mins   {t['entry_price']:<8.2f} {t['exit_price']:<8.2f} {t['net_pnl_cents']:>+8.2f}  {t['exit_reason']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_cent_flip_test()
