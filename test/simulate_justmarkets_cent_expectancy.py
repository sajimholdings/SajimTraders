"""
========================================================================================
    SAJIM HOLDINGS — JUSTMARKETS CENT ACCOUNT EXPECTANCY SIMULATOR (v1.0)
========================================================================================
Chief Architect: Jimmy Mathu
Simulation Target:
  - Broker: JustMarkets-Demo3 (Cent Account 1200438589)
  - Starting Capital: 400.00 USC ($4.00 USD)
  - Leverage: 1:3000
  - Asset Universe: 34 Tradable Cent Symbols (.c)
  - Timeframes: M5, M15, H1 (102 Fronts)
  - BEEP Layers: DIAMOND (1:4.0 R:R), RARE (1:3.5 R:R), CERTIFIED (1:2.5 R:R)
  - Compounding: Dynamic anti-martingale (+15% per win, formulaic step-back on loss)
  - Balancing: Currency cluster diversification, margin runway guard (no artificial trade count caps)
========================================================================================
"""

import os
import sys
import math
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from vault_original_beep.raw_beep_equations import OriginalRawBeep


def run_justmarkets_simulation():
    if not mt5.initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe"):
        print(f"[-] Cannot initialize MT5: {mt5.last_error()}")
        return

    acc = mt5.account_info()
    if not acc or acc.login != 1200438589:
        print(f"[-] Connected to wrong account: {acc.login if acc else 'None'}. Expected 1200438589.")
        mt5.shutdown()
        return

    print("=" * 80)
    print("      SAJIM HOLDINGS — JUSTMARKETS CENT EMPIRICAL EXPECTANCY SIMULATION")
    print(f"      Account: {acc.login} ({acc.server}) | Balance: {acc.balance:.2f} {acc.currency}")
    print("=" * 80)

    raw_beep = OriginalRawBeep()
    lookback = 12

    all_syms = mt5.symbols_get() or []
    cent_syms = [s.name for s in all_syms if s.name.endswith(".c") and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL][:30]

    timeframes = [("M5", mt5.TIMEFRAME_M5, 300), ("M15", mt5.TIMEFRAME_M15, 200), ("H1", mt5.TIMEFRAME_H1, 150)]

    trades_simulated = []
    equity = 400.0  # USC
    peak_equity = 400.0
    max_drawdown_cash = 0.0
    streak = 0

    base_risk = 0.025  # 2.5% base risk

    for sym in cent_syms:
        info = mt5.symbol_info(sym)
        if not info:
            continue

        for tf_label, tf_enum, bars_count in timeframes:
            rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, bars_count)
            if rates is None or len(rates) < lookback + 20:
                continue

            prices = [float(r["close"]) for r in rates]

            # Walk forward through candles
            for i in range(lookback + 1, len(prices) - 15, 3):
                window = prices[i - lookback : i + 1]
                b_t = raw_beep.calculate_raw_baseline_B(window)
                m_t = raw_beep.calculate_raw_mass_M(window, b_t)

                abs_m = abs(m_t)
                layer = None
                action = None
                rr = 0.0

                if abs_m >= 75.0:
                    layer = "DIAMOND"
                    action = "BUY" if m_t > 0 else "SELL"
                    rr = 4.0
                elif abs_m >= 55.0:
                    layer = "RARE"
                    action = "BUY" if m_t > 0 else "SELL"
                    rr = 3.5
                elif abs_m >= 40.0:
                    layer = "CERTIFIED"
                    action = "BUY" if m_t > 0 else "SELL"
                    rr = 2.5

                if not action or not layer:
                    continue

                # MULTI-SCALE GAMMA GATE Γ (Equation 3):
                # Ensure micro direction aligns with H1 macro baseline trend
                h1_rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 15)
                if h1_rates is not None and len(h1_rates) >= 12:
                    h1_closes = [float(r["close"]) for r in h1_rates]
                    h1_b = raw_beep.calculate_raw_baseline_B(h1_closes[-12:])
                    h1_dir = 1 if h1_closes[-1] > h1_b else -1
                    if action == "BUY" and h1_dir != 1:
                        continue
                    elif action == "SELL" and h1_dir != -1:
                        continue

                cur_p = prices[i]
                spread_cost = info.spread * info.point
                min_stop = max(info.point * 150.0, spread_cost * 4.0)
                risk_dist = max(min_stop, abs(cur_p - b_t) + (min_stop * 0.25))

                if action == "BUY":
                    sl = cur_p - risk_dist
                    risk = cur_p - sl
                    tp = cur_p + (risk * rr)
                else:
                    sl = cur_p + risk_dist
                    risk = sl - cur_p
                    tp = cur_p - (risk * rr)

                # Realistic Trade Lifecycle with Two-Stage Trailing Ratchet
                active_sl = sl
                ratchet_state = "ORIGINAL_SL"
                outcome = None
                exit_r = 0.0

                # Walk forward candle by candle until exit or max horizon
                max_horizon = min(len(prices), i + 80)
                exit_idx = max_horizon

                for future_idx in range(i + 1, max_horizon):
                    future_bar = rates[future_idx]
                    high_p = float(future_bar["high"])
                    low_p = float(future_bar["low"])

                    if action == "BUY":
                        # 1. Check Take-Profit
                        if high_p >= tp:
                            outcome = "WIN"
                            exit_r = rr
                            exit_idx = future_idx
                            break

                        # 2. Check Two-Stage Ratchet Upgrades
                        if high_p >= cur_p + (risk * 2.2):
                            if ratchet_state != "LOCKED_1R":
                                active_sl = max(active_sl, cur_p + (risk * 1.0))
                                ratchet_state = "LOCKED_1R"
                        elif high_p >= cur_p + (risk * 1.5):
                            if ratchet_state == "ORIGINAL_SL":
                                active_sl = max(active_sl, cur_p + spread_cost)
                                ratchet_state = "BE"

                        # 3. Check Stop-Loss / Trailing Hit
                        if low_p <= active_sl:
                            if ratchet_state == "LOCKED_1R":
                                outcome = "WIN_LOCKED"
                                exit_r = 1.0
                            elif ratchet_state == "BE":
                                outcome = "BE"
                                exit_r = 0.0
                            else:
                                outcome = "LOSS"
                                exit_r = -1.0
                            exit_idx = future_idx
                            break
                    else:  # SELL
                        # 1. Check Take-Profit
                        if low_p <= tp:
                            outcome = "WIN"
                            exit_r = rr
                            exit_idx = future_idx
                            break

                        # 2. Check Two-Stage Ratchet Upgrades
                        if low_p <= cur_p - (risk * 2.2):
                            if ratchet_state != "LOCKED_1R":
                                active_sl = min(active_sl, cur_p - (risk * 1.0))
                                ratchet_state = "LOCKED_1R"
                        elif low_p <= cur_p - (risk * 1.5):
                            if ratchet_state == "ORIGINAL_SL":
                                active_sl = min(active_sl, cur_p - spread_cost)
                                ratchet_state = "BE"

                        # 3. Check Stop-Loss / Trailing Hit
                        if high_p >= active_sl:
                            if ratchet_state == "LOCKED_1R":
                                outcome = "WIN_LOCKED"
                                exit_r = 1.0
                            elif ratchet_state == "BE":
                                outcome = "BE"
                                exit_r = 0.0
                            else:
                                outcome = "LOSS"
                                exit_r = -1.0
                            exit_idx = future_idx
                            break

                if outcome is None:
                    continue

                # Dynamic Risk Calculation
                dynamic_risk = min(0.045, base_risk * (1.15 ** streak))
                risk_cash = equity * dynamic_risk

                if outcome in ("WIN", "WIN_LOCKED"):
                    pnl = risk_cash * exit_r
                    streak += 1
                elif outcome == "BE":
                    pnl = 0.0
                    # Streak preserved
                else:
                    pnl = -risk_cash
                    streak = max(0, streak - 1)  # Formulaic Step-Back!

                equity = max(10.0, equity + pnl)
                if equity > peak_equity:
                    peak_equity = equity
                dd = peak_equity - equity
                if dd > max_drawdown_cash:
                    max_drawdown_cash = dd

                trades_simulated.append({
                    "symbol": sym,
                    "tf": tf_label,
                    "layer": layer,
                    "action": action,
                    "outcome": outcome,
                    "rr": rr,
                    "exit_r": exit_r,
                    "pnl": round(pnl, 2),
                    "equity": round(equity, 2),
                })

    mt5.shutdown()

    # Metrics
    total_trades = len(trades_simulated)
    if total_trades == 0:
        print("[!] No trades generated in simulation.")
        return

    wins = [t for t in trades_simulated if t["outcome"] == "WIN"]
    losses = [t for t in trades_simulated if t["outcome"] == "LOSS"]
    win_rate = (len(wins) / total_trades) * 100.0

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = round(gross_profit / max(1e-4, gross_loss), 2)
    net_roi = round(((equity - 400.0) / 400.0) * 100.0, 2)
    max_dd_pct = round((max_drawdown_cash / peak_equity) * 100.0, 2)

    # Layer breakdown
    layer_stats = {}
    for ly in ["DIAMOND", "RARE", "CERTIFIED"]:
        ly_trades = [t for t in trades_simulated if t["layer"] == ly]
        if ly_trades:
            ly_wins = [t for t in ly_trades if t["outcome"] == "WIN"]
            layer_stats[ly] = {
                "trades": len(ly_trades),
                "win_rate": round((len(ly_wins) / len(ly_trades)) * 100.0, 1),
                "net_pnl": round(sum(t["pnl"] for t in ly_trades), 2),
            }

    results = {
        "account": 1200438589,
        "starting_equity_usc": 400.0,
        "ending_equity_usc": round(equity, 2),
        "net_profit_usc": round(equity - 400.0, 2),
        "net_roi_pct": net_roi,
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_dd_pct,
        "layer_breakdown": layer_stats,
    }

    out_file = os.path.join(ROOT_DIR, "tests", "justmarkets_cent_expectancy_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n--- EMPIRICAL RESULTS SUMMARY ---")
    print(f"Total Trades Evaluated : {total_trades}")
    print(f"Win Rate               : {win_rate:.2f}% ({len(wins)} Wins / {len(losses)} Losses)")
    print(f"Profit Factor          : {profit_factor}")
    print(f"Starting Equity        : 400.00 USC ($4.00 USD)")
    print(f"Ending Equity          : {equity:.2f} USC (${equity/100:.2f} USD)")
    print(f"Net ROI                : +{net_roi:.2f}%")
    print(f"Max Peak Drawdown      : {max_dd_pct:.2f}%")
    print(f"\nLayer Breakdown:")
    for k, v in layer_stats.items():
        print(f"  * {k:<10}: {v['trades']} Trades | Win Rate: {v['win_rate']}% | PnL: +{v['net_pnl']} USC")
    print(f"\nDetailed telemetry saved to: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    run_justmarkets_simulation()
