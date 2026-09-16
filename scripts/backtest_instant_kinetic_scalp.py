"""
scripts/backtest_instant_kinetic_scalp.py
========================================================================================
SAJIM QUANT LABS — INSTANT KINETIC SCALP & "TIME-TO-BLUE" EMPIRICAL BACKTEST
========================================================================================
Architect: Jimmy Mathu
Objective:
  Empirically prove and optimize the "Zero-Drawdown, Rapid-Turnover" scalping engine
  on M1 Gold (XAUUSD) and NASDAQ-100.
  
Key Metrics Evaluated:
  1. Time to Blue (Bars/Minutes to first reach positive edge)
  2. Average Trade Duration (Total minutes held before kinetic harvest)
  3. Win Rate % (W)
  4. Average Win (R) vs Average Loss (R)
  5. Net Mathematical Edge: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
  6. Trades Per Day & Compounding Rate/Sec
========================================================================================
"""

import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, ROOT_DIR)

import MetaTrader5 as mt5
import numpy as np
from datetime import datetime

from core.beep_processor import BeepProcessor


def run_kinetic_backtest(symbol: str, bars_count: int = 4000):
    print(f"\n{'='*70}")
    print(f"[*] RUNNING KINETIC SCALP BACKTEST: {symbol} (M1) — Last {bars_count} Bars")
    print(f"{'='*70}")

    if not mt5.initialize():
        print("[!] MT5 init failed")
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars_count)
    if rates is None or len(rates) < 500:
        print(f"[!] Insufficient M1 data for {symbol}")
        mt5.shutdown()
        return None

    sym_info = mt5.symbol_info(symbol)
    point = sym_info.point or 0.01
    spread_pts = sym_info.spread or 20
    spread_price = spread_pts * point

    processor = BeepProcessor()
    closes = [float(r["close"]) for r in rates]
    highs = [float(r["high"]) for r in rates]
    lows = [float(r["low"]) for r in rates]
    opens = [float(r["open"]) for r in rates]
    volumes = [float(r["tick_volume"]) for r in rates]
    times = [int(r["time"]) for r in rates]

    # Calculate rolling ATR(14) with native Python
    tr = []
    for i in range(1, len(rates)):
        h, l, pc = highs[i], lows[i], closes[i-1]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    tr = [tr[0]] + tr
    
    atr_series = []
    for i in range(len(tr)):
        if i < 14:
            atr_series.append(float(np.mean(tr[:i+1])))
        else:
            atr_series.append(float(np.mean(tr[i-13:i+1])))

    trades = []
    in_trade = False
    trade_info = {}

    lookback = 35

    for i in range(lookback + 20, len(rates) - 10):
        # If in a trade, manage it with the Pure Kinetic Exit
        if in_trade:
            bar_o = opens[i]
            bar_h = highs[i]
            bar_l = lows[i]
            bar_c = closes[i]
            rng = max(point * 5, bar_h - bar_l)
            bars_held = i - trade_info["entry_bar"]

            is_buy = trade_info["type"] == "BUY"
            cur_price = bar_c
            open_price = trade_info["open_price"]
            init_risk = trade_info["risk_dist"]

            # Calculate raw floating R
            raw_dist = (cur_price - open_price) if is_buy else (open_price - cur_price)
            # Subtract broker spread friction
            net_dist = raw_dist - spread_price
            net_r = net_dist / init_risk

            # Track Maximum Favorable Excursion & Maximum Adverse Excursion
            fav_dist = (bar_h - open_price) if is_buy else (open_price - bar_l)
            adv_dist = (open_price - bar_l) if is_buy else (bar_h - open_price)
            trade_info["mfe_r"] = max(trade_info["mfe_r"], (fav_dist - spread_price) / init_risk)
            trade_info["mae_r"] = max(trade_info["mae_r"], adv_dist / init_risk)

            if net_r > 0 and trade_info["bars_to_blue"] is None:
                trade_info["bars_to_blue"] = bars_held

            # 1. Stop Loss check
            sl_hit = (bar_l <= trade_info["sl_price"]) if is_buy else (bar_h >= trade_info["sl_price"])
            if sl_hit:
                pnl = 0.15 if trade_info["ratchet"] == "BE" else (-1.0)
                trades.append({
                    "symbol": symbol,
                    "type": trade_info["type"],
                    "result": "WIN" if pnl > 0 else "LOSS",
                    "pnl_r": pnl,
                    "bars_held": bars_held,
                    "bars_to_blue": trade_info["bars_to_blue"] or bars_held,
                    "mfe_r": trade_info["mfe_r"],
                    "mae_r": 1.0,
                    "exit_reason": "BE_STOP" if trade_info["ratchet"] == "BE" else "STOP_LOSS",
                })
                in_trade = False
                continue

            # 1B. Dynamic Kinetic Baseline Dissipation & Micro-Wick Exit
            if net_r >= 0.15:
                recent_rates = rates[max(0, i - 14) : i + 1]
                should_exit, decay_reason, _ = processor.evaluate_kinetic_decay(
                    bars=recent_rates,
                    action=trade_info["type"],
                    atr=cur_atr,
                    adverse_wick_threshold=0.20,
                    dissipation_threshold=0.65,
                )
                if should_exit:
                    trades.append({
                        "symbol": symbol,
                        "type": trade_info["type"],
                        "result": "WIN",
                        "pnl_r": round(net_r, 2),
                        "bars_held": bars_held,
                        "bars_to_blue": trade_info["bars_to_blue"] or bars_held,
                        "mfe_r": trade_info["mfe_r"],
                        "mae_r": trade_info["mae_r"],
                        "exit_reason": f"KINETIC_{decay_reason[:15]}",
                    })
                    in_trade = False
                    continue

            # 1C. Rapid Kinetic Loss Truncation (Cut Losers Fast When Momentum Reverses)
            if net_r <= -0.25:
                recent_rates = rates[max(0, i - 14) : i + 1]
                should_exit, decay_reason, _ = processor.evaluate_kinetic_decay(
                    bars=recent_rates,
                    action=trade_info["type"],
                    atr=cur_atr,
                    adverse_wick_threshold=0.30,
                    dissipation_threshold=0.70,
                )
                if should_exit:
                    trades.append({
                        "symbol": symbol,
                        "type": trade_info["type"],
                        "result": "LOSS",
                        "pnl_r": round(net_r, 2),
                        "bars_held": bars_held,
                        "bars_to_blue": trade_info["bars_to_blue"] or bars_held,
                        "mfe_r": trade_info["mfe_r"],
                        "mae_r": trade_info["mae_r"],
                        "exit_reason": f"KINETIC_CUT_{decay_reason[:15]}",
                    })
                    in_trade = False
                    continue

            # 2. Asymmetric Ratchet:
            # When trade reaches +1.5R, move SL to Break-Even (+0.15R)
            if net_r >= 1.50 and trade_info["ratchet"] == "INITIAL":
                trade_info["ratchet"] = "BE"
                trade_info["sl_price"] = open_price + (0.15 * init_risk) if is_buy else open_price - (0.15 * init_risk)

            # Full TP target at +2.8R
            if net_r >= 2.80:
                trades.append({
                    "symbol": symbol,
                    "type": trade_info["type"],
                    "result": "WIN",
                    "pnl_r": 2.80,
                    "bars_held": bars_held,
                    "bars_to_blue": trade_info["bars_to_blue"] or bars_held,
                    "mfe_r": trade_info["mfe_r"],
                    "mae_r": trade_info["mae_r"],
                    "exit_reason": "FULL_TP_2.8R",
                })
                in_trade = False
                continue

        # If flat, evaluate candidate BEEP Kinetic Surge entry
        else:
            cur_closes = closes[i-lookback:i+1]
            b_t, robust_sigma = processor.calculate_asymptotic_baseline(cur_closes, trim_z=2.0)
            m_t, signed_m = processor.calculate_kinetic_mass(cur_closes, robust_mean=b_t, robust_sigma=robust_sigma, window=14)
            eff_vol, base_vol, rvol = processor.calculate_relative_volume(volumes[i-25:i+1], lookback=20)
            anatomy = processor.analyze_candle_anatomy({
                "open": opens[i], "high": highs[i], "low": lows[i], "close": closes[i], "tick_volume": volumes[i]
            })

            cur_c = closes[i]
            cur_o = opens[i]
            cur_atr = atr_series[i]

            # Require explosive kinetic mass and clean volume surge
            is_kinetic_buy = (
                signed_m >= 45.0 and
                rvol >= 1.10 and
                anatomy["body_ratio"] >= 0.50 and
                anatomy["upper_ratio"] <= 0.25 and
                cur_c > cur_o
            )
            is_kinetic_sell = (
                signed_m <= -45.0 and
                rvol >= 1.10 and
                anatomy["body_ratio"] >= 0.50 and
                anatomy["lower_ratio"] <= 0.25 and
                cur_c < cur_o
            )

            if is_kinetic_buy:
                sl_dist = 0.85 * cur_atr
                trade_info = {
                    "type": "BUY",
                    "open_price": closes[i],
                    "sl_price": closes[i] - sl_dist,
                    "risk_dist": sl_dist,
                    "entry_bar": i,
                    "ratchet": "INITIAL",
                    "bars_to_blue": None,
                    "mfe_r": 0.0,
                    "mae_r": 0.0,
                }
                in_trade = True

            elif is_kinetic_sell:
                sl_dist = 0.85 * cur_atr
                trade_info = {
                    "type": "SELL",
                    "open_price": closes[i],
                    "sl_price": closes[i] + sl_dist,
                    "risk_dist": sl_dist,
                    "entry_bar": i,
                    "ratchet": "INITIAL",
                    "bars_to_blue": None,
                    "mfe_r": 0.0,
                    "mae_r": 0.0,
                }
                in_trade = True

    mt5.shutdown()

    if not trades:
        print("[!] Zero trades executed in test sample.")
        return None

    # Compute Quant Performance Metrics
    total_trades = len(trades)
    wins = [t for t in trades if t["pnl_r"] > 0]
    losses = [t for t in trades if t["pnl_r"] < 0]
    scratches = [t for t in trades if t["pnl_r"] == 0]

    win_rate = len(wins) / total_trades
    loss_rate = len(losses) / total_trades
    avg_win_r = float(np.mean([t["pnl_r"] for t in wins])) if wins else 0.0
    avg_loss_r = abs(float(np.mean([t["pnl_r"] for t in losses]))) if losses else 0.0

    # User's exact Expectancy Formula: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
    net_expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
    total_net_r = sum(t["pnl_r"] for t in trades)
    sum_wins = sum(t["pnl_r"] for t in wins)
    sum_losses = abs(sum(t["pnl_r"] for t in losses))
    profit_factor = (sum_wins / sum_losses) if sum_losses > 0 else 999.0

    avg_bars_held = float(np.mean([t["bars_held"] for t in trades]))
    blue_times = [t["bars_to_blue"] for t in trades if t["bars_to_blue"] is not None]
    avg_time_to_blue = float(np.mean(blue_times)) if blue_times else 1.0

    print(f"\n--- EMPIRICAL QUANT RESULTS FOR {symbol} (M1) ---")
    print(f"  Total Trades Fired:       {total_trades}")
    print(f"  Win Rate (W):             {win_rate*100:.1f}% ({len(wins)} Hits / {len(losses)} Misses)")
    print(f"  Average Win (R):          +{avg_win_r:.3f} R")
    print(f"  Average Loss (R):         -{avg_loss_r:.3f} R")
    print(f"  Net Mathematical Edge:    +{net_expectancy:.4f} R per trade")
    print(f"  Total Net Return:         +{total_net_r:.2f} R")
    print(f"  Profit Factor:            {profit_factor:.2f}")
    print(f"  Average Duration:         {avg_bars_held:.1f} M1 Bars ({avg_bars_held:.1f} Minutes!)")
    print(f"  Time-To-Blue (Speed):     {avg_time_to_blue:.1f} Bars (Goes green in {avg_time_to_blue*60:.0f} seconds!)")
    print(f"{'='*70}")

    return {
        "symbol": symbol,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win_r,
        "avg_loss": avg_loss_r,
        "expectancy": net_expectancy,
        "total_r": total_net_r,
        "profit_factor": profit_factor,
        "duration_min": avg_bars_held,
        "time_to_blue_min": avg_time_to_blue,
    }


if __name__ == "__main__":
    for sym in ["XAUUSD", "NASDAQ-100"]:
        run_kinetic_backtest(sym, bars_count=4500)
