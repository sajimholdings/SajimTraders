"""
Sajim Holdings — BEEP Test 005: Institutional Narrative & Asymmetric Flip Backtest
Validates high-asymmetry (1:3.5 R:R), pre-execution regime filtering, and false-truth rejection
on a $400 USD starter account.
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


class NarrativeBacktestEngine:
    def __init__(self, initial_balance: float = 400.0, risk_per_trade_usd: float = 12.0):
        self.initial_balance = initial_balance
        self.risk_per_trade_usd = risk_per_trade_usd
        self.core = BeepCoreEngine()
        self.narrative = BeepNarrativeEngine()

    def detect_false_truth(self, current_bar: Dict[str, Any], previous_bars: List[Dict[str, Any]], direction: str) -> bool:
        if len(previous_bars) < 3:
            return False
        open_p = current_bar["open"]
        close_p = current_bar["close"]
        high_p = current_bar["high"]
        low_p = current_bar["low"]
        total_range = max(1e-4, high_p - low_p)

        if direction == "BUY":
            upper_wick = high_p - max(open_p, close_p)
            if (upper_wick / total_range) > 0.50:
                return True
        elif direction == "SELL":
            lower_wick = min(open_p, close_p) - low_p
            if (lower_wick / total_range) > 0.50:
                return True
        return False

    def run_narrative_test(self, asset_bars: Dict[str, List[Dict[str, Any]]], spreads: Dict[str, float], contracts: Dict[str, float]) -> Dict[str, Any]:
        balance = self.initial_balance
        peak_balance = balance
        max_dd_pct = 0.0
        max_dd_usd = 0.0

        all_trades: List[Dict[str, Any]] = []
        open_positions: Dict[str, Dict[str, Any]] = {}

        symbols = list(asset_bars.keys())
        min_bars = min(len(asset_bars[s]) for s in symbols)
        lookback = 15

        consecutive_losses = 0
        cooldown_remaining = 0

        for i in range(lookback, min_bars):
            if cooldown_remaining > 0:
                cooldown_remaining -= 1

            for sym in list(open_positions.keys()):
                pos = open_positions[sym]
                bar = asset_bars[sym][i]
                elapsed = i - pos["entry_bar_idx"]

                decay_lambda = self.core.calculate_lambda_decay(elapsed, style="INTRADAY")
                closed = False
                exit_price = 0.0
                exit_reason = ""

                contract = pos["contract_size"]
                lot = pos["lot_size"]
                spread = pos["spread"]
                mult = 1 if pos["direction"] == "BUY" else -1

                if pos["direction"] == "BUY":
                    if bar["low"] <= pos["sl"]:
                        closed = True
                        exit_price = pos["sl"]
                        exit_reason = "STOP_LOSS"
                    elif bar["high"] >= pos["tp2"]:
                        closed = True
                        exit_price = pos["tp2"]
                        exit_reason = "TAKE_PROFIT_RUNNER_1:3.5"
                    elif bar["high"] >= pos["tp1"] and not pos.get("tp1_hit", False):
                        pos["tp1_hit"] = True
                        pos["sl"] = pos["entry_price"]
                        partial_gain = (pos["tp1"] - pos["entry_price"]) * (lot * 0.5) * contract
                        balance += partial_gain
                        pos["lot_size"] = round(lot * 0.5, 2)
                    elif decay_lambda < 30.0:
                        closed = True
                        exit_price = bar["close"]
                        exit_reason = "LAMBDA_DECAY_HARVEST"

                elif pos["direction"] == "SELL":
                    if bar["high"] >= pos["sl"]:
                        closed = True
                        exit_price = pos["sl"]
                        exit_reason = "STOP_LOSS"
                    elif bar["low"] <= pos["tp2"]:
                        closed = True
                        exit_price = pos["tp2"]
                        exit_reason = "TAKE_PROFIT_RUNNER_1:3.5"
                    elif bar["low"] <= pos["tp1"] and not pos.get("tp1_hit", False):
                        pos["tp1_hit"] = True
                        pos["sl"] = pos["entry_price"]
                        partial_gain = (pos["entry_price"] - pos["tp1"]) * (lot * 0.5) * contract
                        balance += partial_gain
                        pos["lot_size"] = round(lot * 0.5, 2)
                    elif decay_lambda < 30.0:
                        closed = True
                        exit_price = bar["close"]
                        exit_reason = "LAMBDA_DECAY_HARVEST"

                if closed:
                    raw_gain = (exit_price - pos["entry_price"]) * mult * pos["lot_size"] * contract
                    spread_cost = spread * pos["lot_size"] * contract
                    net_pnl = raw_gain - spread_cost
                    balance += net_pnl

                    if net_pnl <= 0:
                        consecutive_losses += 1
                        if consecutive_losses >= 3:
                            cooldown_remaining = 6
                    else:
                        consecutive_losses = 0

                    peak_balance = max(peak_balance, balance)
                    dd_usd = peak_balance - balance
                    dd_pct = (dd_usd / peak_balance) * 100.0 if peak_balance > 0 else 0.0
                    if dd_pct > max_dd_pct:
                        max_dd_pct = dd_pct
                        max_dd_usd = dd_usd

                    all_trades.append({
                        "trade_id": len(all_trades) + 1,
                        "symbol": sym,
                        "direction": pos["direction"],
                        "entry_time": pos["entry_time"],
                        "exit_time": bar["datetime"],
                        "entry_price": pos["entry_price"],
                        "exit_price": exit_price,
                        "lot_size": pos["initial_lot"],
                        "sl": pos["initial_sl"],
                        "tp": pos["tp2"],
                        "b_t": pos["b_t"],
                        "m_t": pos["m_t"],
                        "exit_reason": exit_reason,
                        "net_pnl_usd": round(net_pnl, 2),
                        "running_balance": round(balance, 2),
                    })
                    del open_positions[sym]

            if cooldown_remaining > 0:
                continue

            for sym in symbols:
                if sym in open_positions:
                    continue
                if len(open_positions) >= 2:
                    break

                bars = asset_bars[sym]
                cur_bar = bars[i]
                history = [b["close"] for b in bars[i - lookback : i + 1]]

                narr = self.narrative.generate_narrative(
                    symbol=sym,
                    prices=history,
                    account_balance=balance,
                )

                if narr["trade_action"] in ["BUY", "SELL"] and narr["quality"] in ["DIAMOND", "CERTIFIED"]:
                    is_trap = self.detect_false_truth(cur_bar, bars[i - 3 : i], narr["trade_action"])
                    if is_trap:
                        continue

                    risk_dist = abs(cur_bar["close"] - narr["invalidation_sl"])
                    contract = contracts.get(sym, 100.0)
                    spread = spreads.get(sym, 0.35)

                    target_risk = min(15.0, balance * 0.035)
                    calc_lot = 0.01
                    lot_size = round(max(0.01, min(0.10, calc_lot)), 2)

                    open_positions[sym] = {
                        "direction": narr["trade_action"],
                        "entry_price": cur_bar["close"],
                        "entry_time": cur_bar["datetime"],
                        "entry_bar_idx": i,
                        "sl": narr["invalidation_sl"],
                        "initial_sl": narr["invalidation_sl"],
                        "tp1": narr["target_1"],
                        "tp2": narr["target_2"],
                        "b_t": narr["b_t"],
                        "m_t": narr["m_t"],
                        "lot_size": lot_size,
                        "initial_lot": lot_size,
                        "contract_size": contract,
                        "spread": spread,
                        "tp1_hit": False,
                    }

        total_trades = len(all_trades)
        wins = [t for t in all_trades if t["net_pnl_usd"] > 0]
        losses = [t for t in all_trades if t["net_pnl_usd"] <= 0]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

        tot_win = sum(t["net_pnl_usd"] for t in wins)
        tot_loss = abs(sum(t["net_pnl_usd"] for t in losses))
        pf = round(tot_win / tot_loss, 2) if tot_loss > 0 else 99.0
        net_profit = round(balance - self.initial_balance, 2)
        roi = round((net_profit / self.initial_balance) * 100.0, 2)

        return {
            "symbol": "MULTI_ASSET_NARRATIVE",
            "style": "NARRATIVE_ASYMMETRIC_FLIP",
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "net_profit_usd": net_profit,
            "roi_pct": roi,
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": pf,
            "max_drawdown_pct": round(max_dd_pct, 2),
            "max_drawdown_usd": round(max_dd_usd, 2),
            "trades": all_trades,
        }


def main():
    print("=" * 70)
    print("      BEEP TEST 005: NARRATIVE ASYMMETRIC FLIP & SURVIVAL TEST")
    print("      Target: Flip $400 USD using 1:3.5 Asymmetric R:R + Standby Filter")
    print("=" * 70)

    backtester = BeepBacktester()
    instruments = [
        ("XAUUSD", "GC=F", 0.35, 100.0),
        ("EURUSD", "EURUSD=X", 0.00015, 100000.0),
        ("GBPUSD", "GBPUSD=X", 0.00020, 100000.0),
        ("USDJPY", "USDJPY=X", 0.018, 1000.0),
    ]

    asset_data = {}
    spreads = {}
    contracts = {}

    for sym, ticker, spread, contract in instruments:
        print(f"[*] Ingesting market candles for {sym}...")
        bars = backtester.fetch_yahoo_historical(ticker=ticker, interval="1h", range_period="1mo")
        print(f"    [+] {len(bars)} bars loaded.")
        asset_data[sym] = bars
        spreads[sym] = spread
        contracts[sym] = contract

    engine = NarrativeBacktestEngine(initial_balance=400.0)
    print("\n[*] Running Narrative Asymmetric Flip Backtest...")
    results = engine.run_narrative_test(asset_data, spreads, contracts)

    test_name = "test_005_narrative_asymmetric_flip"
    test_desc = (
        "Empirical validation of Jimmy Mathu's Institutional Narrative Edge & Asymmetric Account Flip Theory. "
        "Transforms BEEP Universal Equations into high-asymmetry (1:3.5 R:R) setups with invalidation floors at B(t). "
        "Strictly filters out chop by enforcing STAND_BY on compression regimes (M < 45) and eliminates 'False Truth' "
        "retail traps before execution. Protects capital with a 3-loss session cooldown circuit breaker."
    )
    saved_dir = backtester.save_test_results(test_name=test_name, test_desc=test_desc, results=results)

    print("\n" + "=" * 70)
    print("                 TEST 005 PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"[*] Starting Balance   : ${results['initial_balance']:.2f}")
    print(f"[*] Final Balance      : ${results['final_balance']:.2f}")
    print(f"[*] Net Profit         : ${results['net_profit_usd']:+.2f} ({results['roi_pct']:+.2f}%)")
    print(f"[*] Total Trades       : {results['total_trades']}")
    print(f"[*] Win Rate           : {results['win_rate_pct']}%")
    print(f"[*] Profit Factor      : {results['profit_factor']}")
    print(f"[*] Max Drawdown       : {results['max_drawdown_pct']}% (${results['max_drawdown_usd']:.2f})")
    print("=" * 70)


if __name__ == "__main__":
    main()
