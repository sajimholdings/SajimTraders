import os
import sys
import numpy as np
import MetaTrader5 as mt5

def check_additional():
    if not mt5.initialize():
        print("MT5 Init failed")
        return

    candidates = [
        'EURJPY', 'USDJPY', 'GBPJPY', 'CADJPY', 'AUDJPY', 
        'EURUSD', 'GBPUSD', 'USDCAD', 'USDCHF', 
        'DE30', 'US500', 'AUS200', 'UK100', 'XTIUSD', 'XBRUSD'
    ]
    
    print(f"{'Symbol':<10} | {'Spread':<10} | {'M1 ATR':<10} | {'Spread/ATR%':<12} | {'Pass <25%?'}")
    print('-' * 60)
    for sym in candidates:
        mt5.symbol_select(sym, True)
        si = mt5.symbol_info(sym)
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 1000)
        if si and rates is not None and len(rates) > 100:
            highs = rates['high'].astype(np.float64)
            lows = rates['low'].astype(np.float64)
            closes = rates['close'].astype(np.float64)
            tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(rates))]
            atr = float(np.mean(tr[-100:]))
            spread_price = si.spread * si.point
            ratio = (spread_price / atr) * 100.0 if atr > 0 else 999.0
            passed = 'YES (PASS)' if ratio < 25.0 else 'NO'
            print(f"{sym:<10} | {spread_price:<10.5f} | {atr:<10.5f} | {ratio:<11.1f}% | {passed}")
    mt5.shutdown()

if __name__ == "__main__":
    check_additional()
