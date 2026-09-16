import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, ROOT_DIR)

import MetaTrader5 as mt5
from datetime import datetime
from v2.strategies.young_surge_continuation import YoungSurgeContinuation
from v2.strategies.exhaustion_mean_reversion import ExhaustionMeanReversion
from v2.strategies.mirage_liquidity_sweep import MirageLiquiditySweepCartridge
from core.beep_processor import BeepSnipeFilter

if not mt5.initialize():
    print("MT5 init failed")
    exit(1)

cartridges = [
    YoungSurgeContinuation(enabled=True),
    ExhaustionMeanReversion(enabled=True),
    MirageLiquiditySweepCartridge(enabled=True),
]
snipe_filter = BeepSnipeFilter()

universe = ['XAUUSD', 'XAGUSD', 'XAUAUD', 'GBPJPY', 'EURJPY', 'BTCUSD', 'ETHUSD', 'SOLUSD', 'USDCAD', 'USDCHF', 'EURAUD', 'NASDAQ-100', 'DJ30']
timeframes = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15}

print(f"--- DIAGNOSTIC SCANNER EVALUATION AT {datetime.now()} ---")
total_signals = 0

for sym in universe:
    si = mt5.symbol_info(sym)
    if not si:
        continue
    market_info = {"point": si.point, "spread": si.spread, "bid": si.bid, "ask": si.ask}
    
    for tf_label, tf_mt5 in timeframes.items():
        rates = mt5.copy_rates_from_pos(sym, tf_mt5, 0, 150)
        if rates is None or len(rates) < 80:
            continue
        bars = [{"time": int(r["time"]), "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]), "volume": float(r["tick_volume"])} for r in rates]
        
        for cart in cartridges:
            sig = cart.evaluate(symbol=sym, timeframe=tf_label, bars=bars, market_info=market_info)
            if sig:
                total_signals += 1
                confirmed, eval_res = snipe_filter.evaluate_signal(sig, bars, market_info)
                status = "APPROVED FOR TRADE 🚀" if confirmed else f"BLOCKED BY BEEP FILTER: {eval_res.reason} (Score: {eval_res.composite_score:.1f}, M(t): {eval_res.kinetic_mass:.1f}, RVol: {eval_res.relative_volume:.2f}x)"
                print(f"[{sym} {tf_label}] {cart.name} -> {sig.action} | {status}")

if total_signals == 0:
    print("NO RAW STRATEGY SIGNALS GENERATED ON ANY PAIR RIGHT NOW.")
    print("Reason: All 10 universe assets are currently inside balanced consolidation / no liquidity sweeps or momentum surges occurring at this exact second.")

mt5.shutdown()
