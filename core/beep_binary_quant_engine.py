"""
Sajim Holdings — BEEP Binary Quant & State-Reversal Engine (beep_binary_quant_engine.py)
Philosophy:
  "If not a BUY, then a SELL. The market only has two directions."
  Exploits:
    1. Liquidity Vacuum Principle: The exact point where a BUY fails is the highest-expectancy SELL.
    2. Dynamic Baseline SAR (Stop-and-Reverse): Breaking B(t) is not just an exit—it flips the trade!
    3. Reverse Crowd Psychology: Fades retail breakout traps into explosive institutional cascades.
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import MetaTrader5 as mt5
from beep_core import BeepCoreEngine
from beep_narrative import BeepNarrativeEngine
from backtester import BeepBacktester


def run_binary_quant_simulation():
    print("=" * 85)
    print("      SAJIM HOLDINGS — BEEP BINARY QUANT & PARITY INVERSION ENGINE")
    print("      'If not a BUY, then a SELL. The Market Only Has Two Directions.'")
    print("=" * 85)

    # 1. Pull 1,000 REAL Live Candles from MetaTrader 5
    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal_path):
        raise RuntimeError(f"Failed to connect to MT5 terminal at {terminal_path}")

    symbol = "XAUUSD"
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1000)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise RuntimeError("No rates extracted from MT5.")

    print(f"[+] Loaded {len(rates)} REAL broker M5 candles for Gold ({symbol}) from MT5.")

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
            "spread": float(r["spread"]) / 100.0,
        })

    core = BeepCoreEngine()
    backtester = BeepBacktester()

    # 2. Cent Account State: $4.00 USD (400 USC Cents)
    balance = 400.0
    initial_balance = balance
    peak_balance = balance
    max_dd_cents = 0.0
    max_dd_pct = 0.0

    current_state = 0  # +1 = LONG, -1 = SHORT, 0 = NEUTRAL
    active_pos = None

    trades = []
    lookback = 15

    for i in range(lookback, len(bars)):
        cur_bar = bars[i]
        prev_bars = bars[i - lookback : i]
        closes = [b["close"] for b in bars[i - lookback : i + 1]]

        # Calculate BEEP Asymptotic Baseline B(t) & Kinetic Mass M(t)
        b_t, robust_sigma = core.calculate_asymptotic_baseline(closes)
        m_t = core.calculate_kinetic_mass(closes, b_t, robust_sigma)

        high_p = cur_bar["high"]
        low_p = cur_bar["low"]
        open_p = cur_bar["open"]
        close_p = cur_bar["close"]
        tot_range = max(1e-4, high_p - low_p)

        # -----------------------------------------------------------------
        # QUANT STEP 1: EVALUATE ACTIVE POSITION (STOP-AND-REVERSE PARITY)
        # -----------------------------------------------------------------
        if active_pos is not None:
            pos = active_pos
            elapsed_bars = i - pos["entry_bar_idx"]
            elapsed_mins = elapsed_bars * 5

            should_close = False
            should_reverse = False
            reverse_direction = ""
            exit_price = 0.0
            exit_reason = ""

            if pos["direction"] == "BUY":
                # Take Profit reached (1:3.5)
                if cur_bar["high"] >= pos["tp"]:
                    should_close = True
                    exit_price = pos["tp"]
                    exit_reason = "TAKE_PROFIT_1:3.5"
                # PARITY INVERSION AT B(t): If Baseline Floor Breaks -> STOP-AND-REVERSE TO SELL!
                elif cur_bar["low"] <= pos["sl"]:
                    should_close = True
                    exit_price = pos["sl"]
                    exit_reason = "BASELINE_BREAK_SAR_FLIP"
                    # THE QUANT FLIP: Price broke the floor, so it is now in a DOWNWARD CASCADE!
                    should_reverse = True
                    reverse_direction = "SELL"
                # TIME-FRICTION STALL: If stalled 6 bars (30 mins), reverse or harvest
                elif elapsed_bars >= 6:
                    should_close = True
                    exit_price = cur_bar["close"]
                    exit_reason = f"TIME_FRICTION_{elapsed_mins}M"

            elif pos["direction"] == "SELL":
                # Take Profit reached (1:3.5)
                if cur_bar["low"] <= pos["tp"]:
                    should_close = True
                    exit_price = pos["tp"]
                    exit_reason = "TAKE_PROFIT_1:3.5"
                # PARITY INVERSION AT B(t): If Baseline Ceiling Breaks -> STOP-AND-REVERSE TO BUY!
                elif cur_bar["high"] >= pos["sl"]:
                    should_close = True
                    exit_price = pos["sl"]
                    exit_reason = "BASELINE_BREAK_SAR_FLIP"
                    # THE QUANT FLIP: Price broke above the ceiling, so it is now an UPWARD JET!
                    should_reverse = True
                    reverse_direction = "BUY"
                elif elapsed_bars >= 6:
                    should_close = True
                    exit_price = cur_bar["close"]
                    exit_reason = f"TIME_FRICTION_{elapsed_mins}M"

            if should_close:
                mult = 1 if pos["direction"] == "BUY" else -1
                gross_pnl = (exit_price - pos["entry_price"]) * mult
                spread_cost = cur_bar["spread"]
                net_pnl = gross_pnl - spread_cost
                balance += net_pnl

                peak_balance = max(peak_balance, balance)
                dd = peak_balance - balance
                dd_pct = (dd / peak_balance) * 100.0 if peak_balance > 0 else 0.0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd_cents = dd

                trades.append({
                    "trade_id": len(trades) + 1,
                    "symbol": "XAUUSD",
                    "direction": pos["direction"],
                    "entry_time": pos["entry_time"],
                    "exit_time": cur_bar["datetime"],
                    "duration_mins": elapsed_mins,
                    "entry_price": round(pos["entry_price"], 2),
                    "exit_price": round(exit_price, 2),
                    "sl": round(pos["sl"], 2),
                    "tp": round(pos["tp"], 2),
                    "lot_size": 0.01,
                    "b_t": round(pos["b_t"], 2),
                    "m_t": round(pos["m_t"], 1),
                    "exit_reason": exit_reason,
                    "net_pnl_cents": round(net_pnl, 2),
                    "net_pnl_usd": round(net_pnl / 100.0, 4),
                    "running_balance": round(balance / 100.0, 2),
                    "running_balance_cents": round(balance, 2),
                    "running_balance_usd": round(balance / 100.0, 2),
                })
                active_pos = None

                # -------------------------------------------------------------
                # THE BINARY FLIP: INSTANT REVERSE EXECUTION
                # -------------------------------------------------------------
                if should_reverse:
                    risk_dist = max(3.0, abs(close_p - b_t))
                    if reverse_direction == "BUY":
                        new_sl = close_p - risk_dist
                        new_tp = close_p + (risk_dist * 3.5)
                    else:
                        new_sl = close_p + risk_dist
                        new_tp = close_p - (risk_dist * 3.5)

                    active_pos = {
                        "direction": reverse_direction,
                        "entry_price": close_p,
                        "entry_time": cur_bar["datetime"],
                        "entry_bar_idx": i,
                        "sl": new_sl,
                        "tp": new_tp,
                        "b_t": b_t,
                        "m_t": m_t,
                    }
                    continue

        # -----------------------------------------------------------------
        # QUANT STEP 2: BINARY STATE DETECTION ("If not BUY, then SELL")
        # -----------------------------------------------------------------
        if active_pos is None:
            # Check Wick Sweeps (The Liquidity Trap / Reverse Crowd Psychology)
            upper_wick = high_p - max(open_p, close_p)
            lower_wick = min(open_p, close_p) - low_p
            is_upper_sweep = (upper_wick / tot_range) > 0.45
            is_lower_sweep = (lower_wick / tot_range) > 0.45

            # Decision Logic:
            # Case A: Upper Wick Trap -> Retail bought high, got trapped. REVERSE IT -> ENTER SHORT!
            if is_upper_sweep and close_p > b_t:
                target_dir = "SELL"
                reason = "FADE_RETAIL_BUY_TRAP"
            # Case B: Lower Wick Trap -> Retail panic-sold low, got absorbed. REVERSE IT -> ENTER LONG!
            elif is_lower_sweep and close_p < b_t:
                target_dir = "BUY"
                reason = "FADE_RETAIL_SELL_TRAP"
            # Case C: Clear directional expansion away from B(t)
            elif close_p > b_t and m_t >= 45.0:
                target_dir = "BUY"
                reason = "EXPANSION_ABOVE_BASELINE"
            elif close_p < b_t and m_t >= 45.0:
                target_dir = "SELL"
                reason = "EXPANSION_BELOW_BASELINE"
            else:
                target_dir = None

            if target_dir in ["BUY", "SELL"]:
                risk_dist = max(3.0, abs(close_p - b_t))
                if target_dir == "BUY":
                    sl = close_p - risk_dist
                    tp = close_p + (risk_dist * 3.5)
                else:
                    sl = close_p + risk_dist
                    tp = close_p - (risk_dist * 3.5)

                active_pos = {
                    "direction": target_dir,
                    "entry_price": close_p,
                    "entry_time": cur_bar["datetime"],
                    "entry_bar_idx": i,
                    "sl": sl,
                    "tp": tp,
                    "b_t": b_t,
                    "m_t": m_t,
                }

    # 3. Compile Quant Metrics
    total_trades = len(trades)
    wins = [t for t in trades if t["net_pnl_cents"] > 0]
    losses = [t for t in trades if t["net_pnl_cents"] <= 0]
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

    tot_win = sum(t["net_pnl_cents"] for t in wins)
    tot_loss = abs(sum(t["net_pnl_cents"] for t in losses))
    pf = round(tot_win / tot_loss, 2) if tot_loss > 0 else 99.0

    net_cents = round(balance - initial_balance, 2)
    net_usd = round(net_cents / 100.0, 2)
    roi = round((net_cents / initial_balance) * 100.0, 2)

    sar_flips = [t for t in trades if "SAR_FLIP" in t["exit_reason"]]
    trap_fades = [t for t in trades if t["trade_id"] in [1, 2, 5, 8]]  # sample

    sample_days = (bars[-1]["timestamp"] - bars[0]["timestamp"]) / 86400.0

    test_results = {
        "symbol": "XAUUSD_M5_BINARY_QUANT",
        "style": "BINARY_STATE_INVERSION_SAR",
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
        "sar_flips_count": len(sar_flips),
        "trades": trades,
    }

    test_desc = (
        "BEEP Binary Quant & State-Reversal Engine ('If not a BUY, then a SELL'). "
        "Tested on 1,000 REAL LIVE MT5 Gold candles. Replaces passive waiting with Parity Inversion: "
        "Every failed BUY triggers an immediate SELL reversal, and every broken Baseline B(t) executes a Stop-and-Reverse."
    )
    saved_dir = backtester.save_test_results("test_008_binary_quant_state_inversion", test_desc, test_results)

    print("\n" + "=" * 85)
    print("         TEST 008: BEEP BINARY QUANT STATE-REVERSAL REPORT")
    print("=" * 85)
    print(f"[*] Starting Balance        : {initial_balance:.2f} USC (${initial_balance/100.0:.2f} USD)")
    print(f"[*] Final Balance           : {balance:.2f} USC (${balance/100.0:.2f} USD)")
    print(f"[*] Net Profit              : {net_cents:+.2f} USC (${net_usd:+.2f} USD | {roi:+.2f}%)")
    print(f"[*] Total Trades Executed   : {total_trades} trades across {sample_days:.1f} days")
    print(f"[*] Stop-and-Reverse Flips  : {len(sar_flips)} instant reversals executed at B(t)")
    print(f"[*] Win Rate                : {win_rate:.2f}%")
    print(f"[*] Profit Factor           : {pf}")
    print(f"[*] Max Drawdown            : {max_dd_pct:.2f}% ({max_dd_cents:.2f} USC = ${max_dd_cents/100.0:.2f} USD)")
    print("=" * 85)

    print("\nRecent 15 Executed Trades with Instant State Inversion:")
    print("-" * 85)
    print(f"{'ID':<4} {'DIR':<5} {'ENTRY TIME':<17} {'DURATION':<10} {'ENTRY':<9} {'EXIT':<9} {'PnL (USC)':<10} {'EXIT REASON'}")
    print("-" * 85)
    for t in trades[-15:]:
        print(f"#{t['trade_id']:<3} {t['direction']:<5} {t['entry_time']:<17} {t['duration_mins']} mins   {t['entry_price']:<9.2f} {t['exit_price']:<9.2f} {t['net_pnl_cents']:>+8.2f}  {t['exit_reason']}")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_binary_quant_simulation()
