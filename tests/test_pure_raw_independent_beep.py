"""
Sajim Holdings — Pure Raw Independent BEEP Engine (test_pure_raw_independent_beep.py)
Implements Jimmy Mathu's true unaltered architecture:
  - ZERO artificial weights: Each timeframe is an INDEPENDENT trading sovereign.
  - Raw Universal Equations: B(t) robust median, M(t) sign accumulator, Lambda time exit.
  - Binary Reverse Psychology: If price fails at B(t), it immediately inverts into the opposite direction!
  - Tested on 100% REAL LIVE MT5 Gold candles.
"""

import os
import sys
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault"), BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from vault_original_beep.raw_beep_equations import OriginalRawBeep
from backtester import BeepBacktester


def run_pure_independent_test(timeframe_label: str = "M5"):
    print("=" * 85)
    print(f"      SAJIM HOLDINGS — PURE RAW INDEPENDENT BEEP: {timeframe_label} TIMEFRAME")
    print("      NO ARTIFICIAL WEIGHTS. PURE SOVEREIGN PHYSICAL EQUATIONS.")
    print("      'If not a BUY, then a SELL. Two Directions Only.'")
    print("=" * 85)

    # 1. Pull 1,000 REAL MT5 Candles
    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal_path):
        raise RuntimeError(f"Cannot connect to MT5 at {terminal_path}")

    symbol = "XAUUSD"
    mt5.symbol_select(symbol, True)
    tf = mt5.TIMEFRAME_M5 if timeframe_label == "M5" else (mt5.TIMEFRAME_M15 if timeframe_label == "M15" else mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 1000)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No rates for {symbol} on {timeframe_label}")

    print(f"[+] Loaded {len(rates)} REAL institutional candles for {symbol} on {timeframe_label}.")

    bars = [{
        "timestamp": int(r["time"]),
        "datetime": datetime.fromtimestamp(r["time"]).strftime("%Y-%m-%d %H:%M"),
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
        "spread": float(r["spread"]) / 100.0,
    } for r in rates]

    raw_beep = OriginalRawBeep()
    backtester = BeepBacktester()

    # 2. Account Mechanics: $4.00 USD Cent Account (400 Cents)
    balance = 400.0  # USC
    initial_balance = balance
    peak_balance = balance
    max_dd_cents = 0.0
    max_dd_pct = 0.0

    active_trade = None
    trades = []
    lookback = 12

    for i in range(lookback, len(bars)):
        cur_bar = bars[i]
        prices_window = [b["close"] for b in bars[i - lookback : i + 1]]

        # Raw Baseline B(t) & Kinetic Mass M(t) — Pure Jimmy Mathu Formulation
        b_t = raw_beep.calculate_raw_baseline_B(prices_window)
        m_t = raw_beep.calculate_raw_mass_M(prices_window, b_t)

        cur_p = cur_bar["close"]
        high_p = cur_bar["high"]
        low_p = cur_bar["low"]

        # -------------------------------------------------------------
        # 1. MANAGE ACTIVE TRADE & INSTANT STATE INVERSION
        # -------------------------------------------------------------
        if active_trade is not None:
            pos = active_trade
            elapsed_bars = i - pos["entry_bar_idx"]
            elapsed_mins = elapsed_bars * 5

            closed = False
            should_reverse = False
            reverse_dir = ""
            exit_price = 0.0
            exit_reason = ""

            # Check BUY position
            if pos["direction"] == "BUY":
                if high_p >= pos["tp"]:
                    closed = True
                    exit_price = pos["tp"]
                    exit_reason = "TAKE_PROFIT_1:3.5"
                # If Baseline breaks downward: Not a BUY -> Instant REVERSE to SELL!
                elif low_p <= pos["sl"]:
                    closed = True
                    exit_price = pos["sl"]
                    exit_reason = "SAR_REVERSE_TO_SELL"
                    should_reverse = True
                    reverse_dir = "SELL"
                elif elapsed_bars >= 6:  # Time-decay exit
                    closed = True
                    exit_price = cur_p
                    exit_reason = f"TIME_EXIT_{elapsed_mins}M"

            elif pos["direction"] == "SELL":
                if low_p <= pos["tp"]:
                    closed = True
                    exit_price = pos["tp"]
                    exit_reason = "TAKE_PROFIT_1:3.5"
                # If Baseline breaks upward: Not a SELL -> Instant REVERSE to BUY!
                elif high_p >= pos["sl"]:
                    closed = True
                    exit_price = pos["sl"]
                    exit_reason = "SAR_REVERSE_TO_BUY"
                    should_reverse = True
                    reverse_dir = "BUY"
                elif elapsed_bars >= 6:
                    closed = True
                    exit_price = cur_p
                    exit_reason = f"TIME_EXIT_{elapsed_mins}M"

            if closed:
                mult = 1 if pos["direction"] == "BUY" else -1
                gross_pnl = (exit_price - pos["entry_price"]) * mult
                spread = cur_bar["spread"]
                net_pnl = gross_pnl - spread
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
                active_trade = None

                # Execute Instant Reverse Trade
                if should_reverse:
                    risk_dist = max(3.0, abs(cur_p - b_t))
                    if reverse_dir == "BUY":
                        new_sl = cur_p - risk_dist
                        new_tp = cur_p + (risk_dist * 3.5)
                    else:
                        new_sl = cur_p + risk_dist
                        new_tp = cur_p - (risk_dist * 3.5)

                    active_trade = {
                        "direction": reverse_dir,
                        "entry_price": cur_p,
                        "entry_time": cur_bar["datetime"],
                        "entry_bar_idx": i,
                        "sl": new_sl,
                        "tp": new_tp,
                        "b_t": b_t,
                        "m_t": m_t,
                    }
                    continue

        # -------------------------------------------------------------
        # 2. INDEPENDENT BINARY TRIGGER (TWO DIRECTIONS ONLY)
        # -------------------------------------------------------------
        if active_trade is None:
            # If price is above B(t) with momentum mass -> BUY
            if cur_p > b_t and m_t >= 45.0:
                direction = "BUY"
            # If price is below B(t) with momentum mass -> SELL
            elif cur_p < b_t and m_t >= 45.0:
                direction = "SELL"
            else:
                direction = None

            if direction is not None:
                risk_dist = max(3.0, abs(cur_p - b_t))
                if direction == "BUY":
                    sl = cur_p - risk_dist
                    tp = cur_p + (risk_dist * 3.5)
                else:
                    sl = cur_p + risk_dist
                    tp = cur_p - (risk_dist * 3.5)

                active_trade = {
                    "direction": direction,
                    "entry_price": cur_p,
                    "entry_time": cur_bar["datetime"],
                    "entry_bar_idx": i,
                    "sl": sl,
                    "tp": tp,
                    "b_t": b_t,
                    "m_t": m_t,
                }

    # 3. Metrics Compilation
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

    sample_days = (bars[-1]["timestamp"] - bars[0]["timestamp"]) / 86400.0

    test_results = {
        "symbol": f"XAUUSD_{timeframe_label}_RAW_INDEPENDENT",
        "style": "PURE_RAW_BEEP_SOVEREIGN",
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
        "trades": trades,
    }

    test_name = f"test_009_pure_raw_independent_{timeframe_label.lower()}"
    test_desc = (
        f"Pure Raw Independent BEEP execution on {timeframe_label} timeframe using 100% REAL MT5 Gold candles. "
        "Operates with ZERO artificial weights. Uses pure B(t) robust location, M(t) sign persistence, "
        "and binary reverse psychology (instant Stop-and-Reverse when B(t) breaks)."
    )
    saved_dir = backtester.save_test_results(test_name, test_desc, test_results)

    print("\n" + "=" * 85)
    print(f"       REPORT: PURE RAW INDEPENDENT BEEP ON {timeframe_label} TIMEFRAME")
    print("=" * 85)
    print(f"[*] Starting Balance        : {initial_balance:.2f} USC (${initial_balance/100.0:.2f} USD)")
    print(f"[*] Final Balance           : {balance:.2f} USC (${balance/100.0:.2f} USD)")
    print(f"[*] Net Profit              : {net_cents:+.2f} USC (${net_usd:+.2f} USD | {roi:+.2f}%)")
    print(f"[*] Total Trades Executed   : {total_trades} trades across {sample_days:.1f} days")
    print(f"[*] Win Rate                : {win_rate:.2f}%")
    print(f"[*] Profit Factor           : {pf}")
    print(f"[*] Max Drawdown            : {max_dd_pct:.2f}% ({max_dd_cents:.2f} USC)")
    print("=" * 85)

    print("\nRecent 10 Executed Trades:")
    print("-" * 85)
    print(f"{'ID':<4} {'DIR':<5} {'ENTRY TIME':<17} {'DURATION':<10} {'ENTRY':<9} {'EXIT':<9} {'PnL (USC)':<10} {'EXIT REASON'}")
    print("-" * 85)
    for t in trades[-10:]:
        print(f"#{t['trade_id']:<3} {t['direction']:<5} {t['entry_time']:<17} {t['duration_mins']} mins   {t['entry_price']:<9.2f} {t['exit_price']:<9.2f} {t['net_pnl_cents']:>+8.2f}  {t['exit_reason']}")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_pure_independent_test("M5")
