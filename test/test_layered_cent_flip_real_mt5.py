"""
Sajim Holdings — Layered BEEP Dynamic Cent Flip Engine (test_layered_cent_flip_real_mt5.py)
Tests Jimmy Mathu's full architecture on 100% REAL LIVE MT5 Data:
  1. All 4 BEEP Layers Active:
     - Layer 1: Certified BEEP (Structured Trend, Dip to B(t))
     - Layer 2: Rare BEEP (Directional Momentum Plume)
     - Layer 3: Diamond BEEP (Institutional Thrust M >= 75)
     - Layer 4: Thief Fader (Retail Wick Trap Exhaustion)
  2. Dynamic Lot Scaling Ladder (Tens Progression):
     - Trade 1 (400 USC / $4 USD): 0.10 Cent Lot
     - Trade 2 (550 USC / $5.50 USD): 0.14 Cent Lot
     - Trade 3 (746 USC / $7.46 USD): 0.19 Cent Lot
     - Target: 1,000+ USC ($10+ USD) in 3 consecutive wins
  3. Time Expectancy Analysis:
     - Measures real elapsed time between setups and average duration to target.
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


def run_layered_test(symbol: str = "XAUUSD", timeframe_label: str = "M15", num_bars: int = 1000):
    print("=" * 90)
    print(f"      SAJIM HOLDINGS — ALL 4 BEEP LAYERS DYNAMIC CENT FLIP: {symbol} {timeframe_label}")
    print("      REAL LIVE BROKER CANDLES — ZERO SYNTHETIC DATA")
    print("      LAYERS: DIAMOND + RARE + CERTIFIED + THIEF WICK FADER")
    print("=" * 90)

    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal_path):
        raise RuntimeError(f"Cannot connect to MT5 at {terminal_path}")

    mt5.symbol_select(symbol, True)
    tf = mt5.TIMEFRAME_M5 if timeframe_label == "M5" else (mt5.TIMEFRAME_M15 if timeframe_label == "M15" else mt5.TIMEFRAME_H1)
    tf_minutes = 5 if timeframe_label == "M5" else (15 if timeframe_label == "M15" else 60)

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No rates for {symbol} on {timeframe_label}")

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
    lookback = 12

    # Cent Account State (400 USC = $4.00 USD)
    balance = 400.0
    initial_balance = balance
    peak_balance = balance
    max_dd_cents = 0.0
    max_dd_pct = 0.0

    # Dynamic Lot Ladder State
    consecutive_wins = 0
    consecutive_losses = 0
    max_consecutive_losses = 0

    # Tracking Layer Stats
    layer_counts = {
        "DIAMOND": {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0},
        "RARE": {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0},
        "CERTIFIED": {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0},
        "THIEF_FADER": {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0},
    }

    trades = []
    active_trade = None
    flips_achieved = 0  # Number of times 400 USC reached >= 1000 USC
    flip_durations = []  # Time taken in minutes for each flip cycle

    cycle_start_time = bars[lookback]["timestamp"]

    for i in range(lookback, len(bars)):
        cur_bar = bars[i]
        prices_window = [b["close"] for b in bars[i - lookback : i + 1]]

        b_t = raw_beep.calculate_raw_baseline_B(prices_window)
        m_t = raw_beep.calculate_raw_mass_M(prices_window, b_t)

        cur_p = cur_bar["close"]
        high_p = cur_bar["high"]
        low_p = cur_bar["low"]
        open_p = cur_bar["open"]
        tot_range = max(1e-4, high_p - low_p)

        # -----------------------------------------------------------------
        # 1. MANAGE ACTIVE TRADE
        # -----------------------------------------------------------------
        if active_trade is not None:
            pos = active_trade
            elapsed_bars = i - pos["entry_bar_idx"]
            elapsed_mins = elapsed_bars * tf_minutes

            closed = False
            exit_price = 0.0
            exit_reason = ""

            # Check BUY
            if pos["direction"] == "BUY":
                if high_p >= pos["tp"]:
                    closed = True
                    exit_price = pos["tp"]
                    exit_reason = "TP_HIT"
                elif low_p <= pos["sl"]:
                    closed = True
                    exit_price = pos["sl"]
                    exit_reason = "SL_HIT"
            # Check SELL
            elif pos["direction"] == "SELL":
                if low_p <= pos["tp"]:
                    closed = True
                    exit_price = pos["tp"]
                    exit_reason = "TP_HIT"
                elif high_p >= pos["sl"]:
                    closed = True
                    exit_price = pos["sl"]
                    exit_reason = "SL_HIT"

            # Check Lambda Friction Decay (Time exit if trade stalls > 16 bars)
            if not closed and elapsed_bars >= 16:
                closed = True
                exit_price = cur_p
                exit_reason = "LAMBDA_TIME_EXIT"

            if closed:
                lot = pos["lot"]
                layer = pos["layer"]
                if pos["direction"] == "BUY":
                    price_diff = exit_price - pos["entry_price"]
                else:
                    price_diff = pos["entry_price"] - exit_price

                # Cent account on Gold: 0.10 cent lot = 0.10 oz = $1 move is 10 USC
                # PnL (USC) = price_diff * lot * 100 (where 0.10 lot * 100 = 10 USC per $1)
                pnl_cents = price_diff * (lot * 100.0)
                balance += pnl_cents

                is_win = pnl_cents > 0
                if is_win:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    layer_counts[layer]["wins"] += 1
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    layer_counts[layer]["losses"] += 1

                layer_counts[layer]["trades"] += 1
                layer_counts[layer]["pnl"] += pnl_cents

                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

                peak_balance = max(peak_balance, balance)
                dd_c = peak_balance - balance
                dd_pct = (dd_c / peak_balance) * 100.0
                if dd_c > max_dd_cents:
                    max_dd_cents = dd_c
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

                trades.append({
                    "entry_time": pos["entry_time"],
                    "exit_time": cur_bar["datetime"],
                    "direction": pos["direction"],
                    "layer": layer,
                    "lot": lot,
                    "entry": pos["entry_price"],
                    "exit": exit_price,
                    "pnl_usc": round(pnl_cents, 2),
                    "balance": round(balance, 2),
                    "consecutive_wins": consecutive_wins,
                    "reason": exit_reason,
                    "duration_mins": elapsed_mins
                })

                # Check if 1,000 USC Target ($10 USD) Flip reached!
                if balance >= 1000.0:
                    flips_achieved += 1
                    cycle_duration = (cur_bar["timestamp"] - cycle_start_time) / 3600.0
                    flip_durations.append(cycle_duration)
                    # Reset to 400 for next flip cycle
                    balance = 400.0
                    consecutive_wins = 0
                    cycle_start_time = cur_bar["timestamp"]

                active_trade = None

        # -----------------------------------------------------------------
        # 2. SCAN FOR ALL 4 BEEP LAYERS IF NO ACTIVE TRADE
        # -----------------------------------------------------------------
        if active_trade is None:
            # Check Wick Sweep (Layer 4: Thief Fader)
            upper_wick = high_p - max(open_p, cur_p)
            lower_wick = min(open_p, cur_p) - low_p
            is_upper_sweep = (upper_wick / tot_range) > 0.45
            is_lower_sweep = (lower_wick / tot_range) > 0.45

            selected_layer = None
            action = None
            entry_p = cur_p
            sl = 0.0
            tp = 0.0

            # LAYER 4: THIEF FADER (Counter-trend trap)
            if is_upper_sweep and cur_p > b_t:
                selected_layer = "THIEF_FADER"
                action = "SELL"
                sl = high_p + 1.50
                risk = sl - cur_p
                tp = cur_p - (risk * 2.5)
            elif is_lower_sweep and cur_p < b_t:
                selected_layer = "THIEF_FADER"
                action = "BUY"
                sl = low_p - 1.50
                risk = cur_p - sl
                tp = cur_p + (risk * 2.5)

            # LAYER 3: DIAMOND BEEP (Extreme Institutional Thrust M >= 75)
            elif abs(m_t) >= 75.0:
                selected_layer = "DIAMOND"
                action = "BUY" if m_t > 0 else "SELL"
                risk_dist = max(3.50, abs(cur_p - b_t))
                if action == "BUY":
                    sl = b_t - 1.00
                    tp = cur_p + (risk_dist * 3.5)
                else:
                    sl = b_t + 1.00
                    tp = cur_p - (risk_dist * 3.5)

            # LAYER 2: RARE BEEP (Directional Plume M >= 55)
            elif abs(m_t) >= 55.0:
                selected_layer = "RARE"
                action = "BUY" if m_t > 0 else "SELL"
                risk_dist = max(3.00, abs(cur_p - b_t))
                if action == "BUY":
                    sl = b_t - 0.75
                    tp = cur_p + (risk_dist * 3.0)
                else:
                    sl = b_t + 0.75
                    tp = cur_p - (risk_dist * 3.0)

            # LAYER 1: CERTIFIED BEEP (Structured Trend Drift M >= 35)
            elif abs(m_t) >= 35.0:
                selected_layer = "CERTIFIED"
                action = "BUY" if m_t > 0 else "SELL"
                risk_dist = max(2.50, abs(cur_p - b_t))
                if action == "BUY":
                    sl = b_t - 0.50
                    tp = cur_p + (risk_dist * 2.5)
                else:
                    sl = b_t + 0.50
                    tp = cur_p - (risk_dist * 2.5)

            # -------------------------------------------------------------
            # DYNAMIC LOT SCALING IN THE TENS
            # Base lot at 400 USC: 0.10 Cent Lot
            # Scale proportionally: Lot = (Balance / 400.0) * 0.10
            # -------------------------------------------------------------
            if selected_layer is not None and action is not None:
                # Lot scaling ladder
                if consecutive_wins == 0:
                    lot_size = 0.10
                elif consecutive_wins == 1:
                    lot_size = 0.14
                elif consecutive_wins == 2:
                    lot_size = 0.19
                else:
                    lot_size = round((balance / 400.0) * 0.10, 2)
                    lot_size = min(0.30, max(0.10, lot_size))

                active_trade = {
                    "entry_bar_idx": i,
                    "entry_time": cur_bar["datetime"],
                    "direction": action,
                    "layer": selected_layer,
                    "lot": lot_size,
                    "entry_price": entry_p,
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                }

    # Output Comprehensive Quantitative Analysis
    total_trades = len(trades)
    wins = [t for t in trades if t["pnl_usc"] > 0]
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    net_pnl = balance - initial_balance if flips_achieved == 0 else (flips_achieved * 600.0 + (balance - 400.0))

    durations = [t["duration_mins"] for t in trades]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    print("\n" + "=" * 80)
    print("                    QUANTITATIVE EMPIRICAL RESULTS")
    print("=" * 80)
    print(f"Total REAL Candles Analyzed : {len(bars)} ({timeframe_label})")
    print(f"Total Completed Trades      : {total_trades}")
    print(f"Winning Trades              : {len(wins)} ({win_rate:.2f}%)")
    print(f"Final Balance               : {balance:.2f} USC (Peak Flips: {flips_achieved})")
    print(f"Total Flips ($4 -> $10 USD) : {flips_achieved} Complete Cycles")
    if flip_durations:
        print(f"Average Time per Flip Cycle : {sum(flip_durations)/len(flip_durations):.1f} hours")
    print(f"Max Drawdown                : {max_dd_pct:.2f}% ({max_dd_cents:.2f} USC)")
    print(f"Max Consecutive Losses      : {max_consecutive_losses} (Indestructible Buffer: >8.8)")
    print(f"Average Trade Duration      : {avg_duration:.1f} minutes ({avg_duration/60:.2f} hours)")

    print("\n--- PERFORMANCE BY BEEP LAYER ---")
    for lyr, data in layer_counts.items():
        tr = data["trades"]
        wn = data["wins"]
        wr = (wn / tr * 100.0) if tr > 0 else 0.0
        print(f"  {lyr:<14} | Trades: {tr:<3} | Wins: {wn:<3} ({wr:.1f}%) | Net PnL: {data['pnl']:>+8.2f} USC")

    print("\n--- SAMPLE CONSECUTIVE FLIP TRADES ---")
    for t in trades[-10:]:
        print(f"  [{t['entry_time']}] {t['layer']:<12} {t['direction']:<4} Lot:{t['lot']:.2f} -> PnL: {t['pnl_usc']:>+7.2f} USC | Bal: {t['balance']:.2f} USC | Wins in row: {t['consecutive_wins']}")

    print("=" * 80)


if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "M15"
    run_layered_test("XAUUSD", tf, 1000)
