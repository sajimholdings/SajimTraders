import os
import sys
import numpy as np
import MetaTrader5 as mt5

BASE_DIR = r"c:\Users\sajim\Documents\SAJIM HOLDINGS"
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "core"))

from core.confluence_engine import GrandConfluenceEngine
from scripts.audit_grand_confluence import simulate_confluence_trade, compute_metrics

def audit_indices():
    if not mt5.initialize():
        print("MT5 initialization failed")
        return

    engine = GrandConfluenceEngine()
    tf_list = [
        ("M1", mt5.TIMEFRAME_M1),
        ("M5", mt5.TIMEFRAME_M5),
        ("M15", mt5.TIMEFRAME_M15),
        ("H1", mt5.TIMEFRAME_H1)
    ]

    for sym in ["NASDAQ-100", "DJ30"]:
        mt5.symbol_select(sym, True)
        si = mt5.symbol_info(sym)
        for tf_name, tf in tf_list:
            rates = mt5.copy_rates_from_pos(sym, tf, 0, 3500)
            if rates is None or len(rates) < 300:
                continue
            n = len(rates)
            highs = rates["high"].astype(np.float64)
            lows = rates["low"].astype(np.float64)
            closes = rates["close"].astype(np.float64)
            tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, n)]
            atr = float(np.mean(tr[-100:]))
            spread_price = si.spread * si.point
            ratio = (spread_price / atr) * 100.0 if atr > 0 else 999.0

            signals, _ = engine.analyze(sym, tf_name, rates)
            trades = []
            for s in signals:
                if s.bar_index >= n - 15:
                    continue
                outcome, pnl_r, held = simulate_confluence_trade(
                    rates, s.bar_index, s.direction, s.entry_price, s.stop_loss,
                    s.take_profit_1, s.take_profit_2, s.take_profit_3, spread_price, max_bars=45
                )
                trades.append({"outcome": outcome, "pnl_r": pnl_r, "held": held})
            m = compute_metrics(trades)
            print(f"{sym:12s} {tf_name:4s} | Spread/ATR: {ratio:5.1f}% | Trades: {m['total_trades']:3d} | WR: {m['win_rate']:4.1f}% | PF: {m['profit_factor']:4.2f} | Net: {m['net_r']:+6.1f}R | Exp: {m['expectancy']:+5.3f}R")

    mt5.shutdown()

if __name__ == "__main__":
    audit_indices()
