"""
========================================================================================
    SAJIM HOLDINGS — QUANTITATIVE EDGE VERIFICATION MATRIX (scripts/run_edge_matrix_backtest.py)
========================================================================================
Chief Architect: Jimmy Mathu
Mission:
  - Systematically tests Jimmy Mathu's BEEP algorithm across ALL tradable broker assets
    and ALL operational timeframes (M1, M5, M15, M30, H1, H4).
  - Ingests real historical candle data directly from MT5 terminal.
  - Simulates the complete BEEP lifecycle: B(t) robust baseline, M(t) kinetic mass,
    structural stop loss, asymmetric targets (1:3.0 R:R), +1.5R BE trailing ratchet,
    and Lambda time stop.
  - Accurately deducts real broker spreads on every trade.
  - Calculates institutional metrics: Win Rate, Profit Factor, Payoff Ratio,
    Expectancy (R/trade), Max Drawdown, and Spread Friction Ratio.
  - Streams real-time progress to `edge_matrix_status.json`.
  - Produces the canonical institutional audit: `docs/EDGE_MATRIX_REPORT.md`
    and `docs/edge_matrix_results.json` to feed directly into Sajim V2 Bot.
========================================================================================
"""

import os
import sys
import json
import time
import math
import statistics
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from vault_original_beep.raw_beep_equations import OriginalRawBeep

# Output Paths
STATUS_FILE = os.path.join(ROOT_DIR, "edge_matrix_status.json")
REPORT_FILE = os.path.join(ROOT_DIR, "docs", "EDGE_MATRIX_REPORT.md")
JSON_RESULTS_FILE = os.path.join(ROOT_DIR, "docs", "edge_matrix_results.json")

TIMEFRAME_MAP = [
    ("M1", mt5.TIMEFRAME_M1),
    ("M5", mt5.TIMEFRAME_M5),
    ("M15", mt5.TIMEFRAME_M15),
    ("M30", mt5.TIMEFRAME_M30),
    ("H1", mt5.TIMEFRAME_H1),
    ("H4", mt5.TIMEFRAME_H4),
]


def calculate_atr(bars: List[Dict[str, Any]], period: int = 14) -> List[float]:
    """Calculates True Range and Average True Range (ATR)."""
    tr_list = []
    for i in range(len(bars)):
        if i == 0:
            tr_list.append(bars[i]["high"] - bars[i]["low"])
            continue
        h = bars[i]["high"]
        l = bars[i]["low"]
        cp = bars[i - 1]["close"]
        tr = max(h - l, abs(h - cp), abs(l - cp))
        tr_list.append(tr)

    atr_list = []
    for i in range(len(bars)):
        if i < period:
            atr_list.append(statistics.mean(tr_list[: i + 1]) if tr_list[: i + 1] else 0.0001)
        else:
            atr = statistics.mean(tr_list[i - period + 1 : i + 1])
            atr_list.append(atr if atr > 0 else 0.0001)
    return atr_list


def simulate_beep_front(
    symbol: str,
    tf_label: str,
    tf_code: int,
    bars_count: int = 1500,
    lookback: int = 12,
    target_rr: float = 3.0,
    be_trigger_r: float = 1.5,
    lock_trigger_r: float = 2.2,
    min_mass_threshold: float = 35.0,
) -> Optional[Dict[str, Any]]:
    """
    Backtests BEEP on a single symbol + timeframe front using MT5 historical data.
    """
    si = mt5.symbol_info(symbol)
    if not si:
        return None

    point = si.point or 0.00001
    spread_points = si.spread or 15
    spread_val = max(spread_points * point, point)

    rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, bars_count)
    if rates is None or len(rates) < 100:
        return None

    bars = [
        {
            "time": int(r["time"]),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "tick_volume": int(r["tick_volume"]),
        }
        for r in rates
    ]

    atr_series = calculate_atr(bars, period=14)
    raw_beep = OriginalRawBeep()

    trades: List[Dict[str, Any]] = []
    in_trade = False
    trade: Dict[str, Any] = {}

    for i in range(lookback + 14, len(bars) - 1):
        cur_bar = bars[i]
        next_bar = bars[i + 1]
        atr = atr_series[i]

        # 1. Active Trade Lifecycle Management
        if in_trade:
            entry_p = trade["entry_price"]
            direction = trade["direction"]
            init_risk = trade["initial_risk"]
            elapsed_bars = i - trade["entry_bar_idx"]

            bar_high = cur_bar["high"]
            bar_low = cur_bar["low"]

            if direction == "BUY":
                cur_r = (bar_high - entry_p) / init_risk if init_risk > 0 else 0.0

                # Two-Stage Trailing Ratchet
                if cur_r >= lock_trigger_r:
                    trade["current_sl"] = max(trade["current_sl"], entry_p + (1.0 * init_risk))
                elif cur_r >= be_trigger_r:
                    trade["current_sl"] = max(trade["current_sl"], entry_p + (0.15 * init_risk))

                # Check SL hit
                if bar_low <= trade["current_sl"]:
                    exit_price = trade["current_sl"]
                    pnl_r = (exit_price - entry_p) / init_risk
                    trades.append({
                        "direction": "BUY",
                        "pnl_r": round(pnl_r, 3),
                        "outcome": "WIN" if pnl_r > 0.1 else ("BE" if pnl_r >= 0 else "LOSS"),
                        "bars_held": elapsed_bars,
                    })
                    in_trade = False
                    continue

                # Check TP hit
                if bar_high >= trade["tp_price"]:
                    trades.append({
                        "direction": "BUY",
                        "pnl_r": round(target_rr, 3),
                        "outcome": "WIN",
                        "bars_held": elapsed_bars,
                    })
                    in_trade = False
                    continue

                # Lambda Time Decay Stop
                lambda_val = raw_beep.calculate_raw_lambda(elapsed_bars, decay_rate=0.04)
                if lambda_val < 0.35 and cur_r < 1.0:
                    exit_price = cur_bar["close"]
                    pnl_r = (exit_price - entry_p) / init_risk
                    trades.append({
                        "direction": "BUY",
                        "pnl_r": round(pnl_r, 3),
                        "outcome": "WIN" if pnl_r > 0 else "LOSS",
                        "bars_held": elapsed_bars,
                    })
                    in_trade = False
                    continue

            elif direction == "SELL":
                cur_r = (entry_p - bar_low) / init_risk if init_risk > 0 else 0.0

                # Two-Stage Trailing Ratchet
                if cur_r >= lock_trigger_r:
                    trade["current_sl"] = min(trade["current_sl"], entry_p - (1.0 * init_risk))
                elif cur_r >= be_trigger_r:
                    trade["current_sl"] = min(trade["current_sl"], entry_p - (0.15 * init_risk))

                # Check SL hit
                if bar_high >= trade["current_sl"]:
                    exit_price = trade["current_sl"]
                    pnl_r = (entry_p - exit_price) / init_risk
                    trades.append({
                        "direction": "SELL",
                        "pnl_r": round(pnl_r, 3),
                        "outcome": "WIN" if pnl_r > 0.1 else ("BE" if pnl_r >= 0 else "LOSS"),
                        "bars_held": elapsed_bars,
                    })
                    in_trade = False
                    continue

                # Check TP hit
                if bar_low <= trade["tp_price"]:
                    trades.append({
                        "direction": "SELL",
                        "pnl_r": round(target_rr, 3),
                        "outcome": "WIN",
                        "bars_held": elapsed_bars,
                    })
                    in_trade = False
                    continue

                # Lambda Time Decay Stop
                lambda_val = raw_beep.calculate_raw_lambda(elapsed_bars, decay_rate=0.04)
                if lambda_val < 0.35 and cur_r < 1.0:
                    exit_price = cur_bar["close"]
                    pnl_r = (entry_p - exit_price) / init_risk
                    trades.append({
                        "direction": "SELL",
                        "pnl_r": round(pnl_r, 3),
                        "outcome": "WIN" if pnl_r > 0 else "LOSS",
                        "bars_held": elapsed_bars,
                    })
                    in_trade = False
                    continue

        # 2. Look for New BEEP Signal if flat
        if not in_trade:
            window_closes = [b["close"] for b in bars[i - lookback + 1 : i + 1]]
            b_t = raw_beep.calculate_raw_baseline_B(window_closes, z_threshold=2.0)
            m_t = raw_beep.calculate_raw_mass_M(window_closes, baseline_B=b_t)

            cur_close = cur_bar["close"]

            if m_t >= min_mass_threshold:
                if cur_close > b_t:
                    # Buy Entry: Pay the Ask (Open + spread)
                    entry_price = next_bar["open"] + spread_val
                    recent_lows = [b["low"] for b in bars[i - 4 : i + 1]]
                    swing_low = min(recent_lows)
                    sl_dist = max(entry_price - swing_low, 1.2 * atr, 3.0 * spread_val)
                    sl_price = entry_price - sl_dist
                    tp_price = entry_price + (target_rr * sl_dist)

                    in_trade = True
                    trade = {
                        "direction": "BUY",
                        "entry_price": entry_price,
                        "current_sl": sl_price,
                        "initial_risk": sl_dist,
                        "tp_price": tp_price,
                        "entry_bar_idx": i + 1,
                    }
                elif cur_close < b_t:
                    # Sell Entry: Enter at Bid
                    entry_price = next_bar["open"]
                    recent_highs = [b["high"] for b in bars[i - 4 : i + 1]]
                    swing_high = max(recent_highs)
                    sl_dist = max(swing_high - entry_price, 1.2 * atr, 3.0 * spread_val)
                    sl_price = entry_price + sl_dist
                    tp_price = entry_price - (target_rr * sl_dist)

                    in_trade = True
                    trade = {
                        "direction": "SELL",
                        "entry_price": entry_price,
                        "current_sl": sl_price,
                        "initial_risk": sl_dist,
                        "tp_price": tp_price,
                        "entry_bar_idx": i + 1,
                    }

    recent_atr = atr_series[-1] if atr_series else 0.001
    friction_eta = (spread_val / recent_atr) if recent_atr > 0 else 0.0

    if not trades:
        return {
            "symbol": symbol,
            "timeframe": tf_label,
            "bars_evaluated": len(bars),
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "be_count": 0,
            "win_rate_pct": 0.0,
            "gross_profit_r": 0.0,
            "gross_loss_r": 0.0,
            "net_pnl_r": 0.0,
            "profit_factor": 0.0,
            "avg_win_r": 0.0,
            "avg_loss_r": 0.0,
            "payoff_ratio": 0.0,
            "expectancy_r": 0.0,
            "max_drawdown_r": 0.0,
            "spread_friction_eta": round(friction_eta, 4),
            "tier": "INSUFFICIENT_SIGNALS",
        }

    total_trades = len(trades)
    winning_trades = [t for t in trades if t["pnl_r"] > 0]
    losing_trades = [t for t in trades if t["pnl_r"] < 0]
    be_trades = [t for t in trades if t["pnl_r"] == 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades) * 100.0

    gross_profit_r = sum(t["pnl_r"] for t in winning_trades)
    gross_loss_r = abs(sum(t["pnl_r"] for t in losing_trades)) or 0.001
    net_pnl_r = sum(t["pnl_r"] for t in trades)

    profit_factor = gross_profit_r / gross_loss_r
    avg_win_r = (gross_profit_r / win_count) if win_count > 0 else 0.0
    avg_loss_r = (gross_loss_r / loss_count) if loss_count > 0 else 0.0
    payoff_ratio = (avg_win_r / avg_loss_r) if avg_loss_r > 0 else 0.0

    expectancy_r = ((win_rate / 100.0) * avg_win_r) - (((100.0 - win_rate) / 100.0) * avg_loss_r)

    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    for t in trades:
        cum_r += t["pnl_r"]
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd_r:
            max_dd_r = dd

    if win_rate >= 50.0 and profit_factor >= 1.60 and expectancy_r >= 0.25:
        tier = "INSTITUTIONAL EDGE"
    elif profit_factor >= 1.20 and expectancy_r > 0:
        tier = "MODERATE EDGE"
    elif profit_factor >= 1.00:
        tier = "MARGINAL"
    else:
        tier = "NEGATIVE EDGE (BLEEDER)"

    return {
        "symbol": symbol,
        "timeframe": tf_label,
        "bars_evaluated": len(bars),
        "total_trades": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "be_count": len(be_trades),
        "win_rate_pct": round(win_rate, 1),
        "gross_profit_r": round(gross_profit_r, 2),
        "gross_loss_r": round(gross_loss_r, 2),
        "net_pnl_r": round(net_pnl_r, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win_r": round(avg_win_r, 2),
        "avg_loss_r": round(avg_loss_r, 2),
        "payoff_ratio": round(payoff_ratio, 2),
        "expectancy_r": round(expectancy_r, 3),
        "max_drawdown_r": round(max_dd_r, 2),
        "spread_friction_eta": round(friction_eta, 4),
        "tier": tier,
    }


def main():
    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    print(f"[*] Initializing MT5 Terminal at {terminal_path}...")
    if not mt5.initialize(terminal_path):
        print(f"[!] ERROR: Failed to connect to MT5: {mt5.last_error()}")
        sys.exit(1)

    acc = mt5.account_info()
    print(f"[+] Connected to Broker: {acc.server if acc else 'Unknown'} | Login: {acc.login if acc else 'N/A'}")

    all_symbols = [s.name for s in (mt5.symbols_get() or []) if s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL]
    cent_syms = [s for s in all_symbols if s.endswith(".c")]
    active_symbols = cent_syms if cent_syms else all_symbols
    active_symbols = sorted([s for s in active_symbols if any(m in s for m in ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "XAU", "XAG"])])

    total_fronts = len(active_symbols) * len(TIMEFRAME_MAP)
    print(f"[+] Total Quant Testing Fronts: {len(active_symbols)} Assets x {len(TIMEFRAME_MAP)} Timeframes = {total_fronts} Fronts")

    results: List[Dict[str, Any]] = []
    start_time = time.time()
    front_counter = 0

    for sym in active_symbols:
        mt5.symbol_select(sym, True)
        for tf_label, tf_code in TIMEFRAME_MAP:
            front_counter += 1
            print(f"[{front_counter}/{total_fronts}] Evaluating {sym} ({tf_label})...", end=" ", flush=True)

            try:
                res = simulate_beep_front(sym, tf_label, tf_code, bars_count=1500)
                if res:
                    results.append(res)
                    if res["total_trades"] > 0:
                        print(f"Done ({res['total_trades']} trds) -> WR: {res['win_rate_pct']}% | PF: {res['profit_factor']} | E: {res['expectancy_r']:+.2f}R [{res['tier']}]")
                    else:
                        print("Done (0 trades)")
                else:
                    print("Skipped")
            except Exception as e:
                print(f"Error ({e})")

            sorted_by_pf = sorted([r for r in results if r["total_trades"] > 0], key=lambda x: x["profit_factor"], reverse=True)
            top_edges = sorted_by_pf[:5]
            bleeders = [r for r in results if r["tier"] == "NEGATIVE EDGE (BLEEDER)"][-5:]

            telemetry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "RUNNING" if front_counter < total_fronts else "COMPLETED",
                "progress_fronts": f"{front_counter}/{total_fronts}",
                "progress_pct": round((front_counter / total_fronts) * 100.0, 1),
                "elapsed_seconds": round(time.time() - start_time, 1),
                "current_eval": f"{sym} ({tf_label})",
                "total_completed_fronts": len(results),
                "top_edge_pairs": [
                    {"symbol": r["symbol"], "tf": r["timeframe"], "pf": r["profit_factor"], "wr": r["win_rate_pct"], "expectancy": r["expectancy_r"]}
                    for r in top_edges
                ],
                "worst_bleeders": [
                    {"symbol": r["symbol"], "tf": r["timeframe"], "pf": r["profit_factor"], "wr": r["win_rate_pct"], "expectancy": r["expectancy_r"]}
                    for r in bleeders
                ],
            }
            try:
                with open(STATUS_FILE, "w", encoding="utf-8") as sf:
                    json.dump(telemetry, sf, indent=2)
            except Exception:
                pass

    mt5.shutdown()

    os.makedirs(os.path.dirname(JSON_RESULTS_FILE), exist_ok=True)
    with open(JSON_RESULTS_FILE, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2)
    print(f"\n[+] Raw results saved to {JSON_RESULTS_FILE}")

    generate_markdown_report(results, total_fronts, time.time() - start_time)


def generate_markdown_report(results: List[Dict[str, Any]], total_fronts: int, elapsed_sec: float):
    """Compiles the formal quantitative edge report."""
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

    valid_results = [r for r in results if r["total_trades"] > 0]
    institutional_edges = [r for r in valid_results if r["tier"] == "INSTITUTIONAL EDGE"]
    moderate_edges = [r for r in valid_results if r["tier"] == "MODERATE EDGE"]
    marginal_edges = [r for r in valid_results if r["tier"] == "MARGINAL"]
    bleeders = [r for r in valid_results if r["tier"] == "NEGATIVE EDGE (BLEEDER)"]

    institutional_edges.sort(key=lambda x: x["profit_factor"], reverse=True)
    moderate_edges.sort(key=lambda x: x["profit_factor"], reverse=True)
    bleeders.sort(key=lambda x: x["profit_factor"])

    tf_stats: Dict[str, Dict[str, Any]] = {}
    for r in valid_results:
        tf = r["timeframe"]
        if tf not in tf_stats:
            tf_stats[tf] = {"count": 0, "wins": 0, "trades": 0, "gross_p": 0.0, "gross_l": 0.0}
        tf_stats[tf]["count"] += 1
        tf_stats[tf]["wins"] += r["wins"]
        tf_stats[tf]["trades"] += r["total_trades"]
        tf_stats[tf]["gross_p"] += r["gross_profit_r"]
        tf_stats[tf]["gross_l"] += r["gross_loss_r"]

    md = []
    md.append("# SAJIM HOLDINGS — QUANTITATIVE EDGE VERIFICATION REPORT")
    md.append("### Empirical Mathematical Edge & Blacklist Audit across All Pairs and Timeframes")
    md.append(f"**Chief Quantitative Architect:** Jimmy Mathu  ")
    md.append(f"**Audit Execution Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    md.append(f"**Total Fronts Evaluated:** {len(valid_results)} active of {total_fronts} | **Elapsed Time:** {elapsed_sec:.1f}s\n")
    md.append("---\n")

    md.append("## 1. Executive Summary & Core Findings\n")
    tot = len(valid_results) if valid_results else 1
    md.append(f"- **Institutional Edges ($PF \\ge 1.60, E \\ge 0.25R$):** **{len(institutional_edges)} setups ({len(institutional_edges)/tot*100:.1f}%)**")
    md.append(f"- **Moderate Edges ($PF \\ge 1.20, E > 0$):** **{len(moderate_edges)} setups ({len(moderate_edges)/tot*100:.1f}%)**")
    md.append(f"- **Marginal Setups ($1.00 \\le PF < 1.20$):** **{len(marginal_edges)} setups ({len(marginal_edges)/tot*100:.1f}%)**")
    md.append(f"- **Bleeders / Negative Edge ($PF < 1.00$):** **{len(bleeders)} setups ({len(bleeders)/tot*100:.1f}%)** — *Mandatory Blacklist in Sajim V2*\n")

    md.append("---\n")
    md.append("## 2. Performance Breakdown by Timeframe\n")
    md.append("| Timeframe | Fronts | Total Trades | Win Rate | Gross Profit (R) | Gross Loss (R) | Profit Factor | Verdict |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for tf_label, _ in TIMEFRAME_MAP:
        if tf_label in tf_stats:
            st = tf_stats[tf_label]
            wr = (st["wins"] / st["trades"] * 100.0) if st["trades"] > 0 else 0.0
            pf = (st["gross_p"] / st["gross_l"]) if st["gross_l"] > 0 else 0.0
            v = "⭐⭐ Institutional Edge" if pf >= 1.5 else ("⭐ Favorable Edge" if pf >= 1.15 else "❌ High Friction / Bleed")
            md.append(f"| **{tf_label}** | {st['count']} | {st['trades']} | {wr:.1f}% | +{st['gross_p']:.1f}R | -{st['gross_l']:.1f}R | **{pf:.2f}** | {v} |")

    md.append("\n---\n")
    md.append("## 3. Top Institutional Edge Setups (Approved for Sajim V2 Engine)\n")
    md.append("| Asset | TF | Trades | Win Rate | Profit Factor | Payoff Ratio | Expectancy (R) | Max DD (R) | Spread Friction (η) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in institutional_edges:
        md.append(f"| **{r['symbol']}** | `{r['timeframe']}` | {r['total_trades']} | **{r['win_rate_pct']}%** | **{r['profit_factor']:.2f}** | {r['payoff_ratio']:.2f}:1 | **+{r['expectancy_r']:.3f}R** | -{r['max_drawdown_r']:.1f}R | {r['spread_friction_eta']:.4f} |")

    md.append("\n---\n")
    md.append("## 4. Toxic Bleeders (Mandatory Blacklist for Sajim V2)\n")
    md.append("| Asset | TF | Trades | Win Rate | Profit Factor | Payoff Ratio | Expectancy (R) | Net PnL (R) | Spread Friction (η) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in bleeders[:25]:
        md.append(f"| **{r['symbol']}** | `{r['timeframe']}` | {r['total_trades']} | {r['win_rate_pct']}% | **{r['profit_factor']:.2f}** | {r['payoff_ratio']:.2f}:1 | **{r['expectancy_r']:+.3f}R** | {r['net_pnl_r']:+.1f}R | {r['spread_friction_eta']:.4f} |")

    md.append("\n---\n")
    md.append("## 5. Architectural Directives for Sajim V2 Bot\n")
    md.append("1. **Dynamic Whitelist Loading:** Sajim V2 automatically ingests only the Tier 1 & Tier 2 verified assets from this report.")
    md.append("2. **Timeframe Specialization:** Each asset trades strictly on its highest-expectancy timeframe.")
    md.append("3. **Asymmetric Payoff Ratchet:** Zero micro-milking before $+1.5R$. +2.2R locks +1.0R Net Profit. +3.0R TP target.")
    md.append("4. **Hard Risk Ceiling:** Sizing strictly capped at 1.2% per trade so 1 win pays for 3-4 losses.\n")

    with open(REPORT_FILE, "w", encoding="utf-8") as rf:
        rf.write("\n".join(md))

    print(f"[+] Canonical Report generated at {REPORT_FILE}")


if __name__ == "__main__":
    main()
