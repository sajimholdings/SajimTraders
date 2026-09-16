import os
import sys
import numpy as np
import MetaTrader5 as mt5

def scan_all_symbols():
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return

    symbols = mt5.symbols_get()
    results = []

    for s in symbols:
        # filter out local currencies, illiquid stock CFDs
        if s.trade_mode < 2 or 'LOCAL' in s.path.upper() or 'STOCKS\\IDX' in s.path.upper() or 'STOCKS\\BRL' in s.path.upper():
            continue
        
        mt5.symbol_select(s.name, True)
        si = mt5.symbol_info(s.name)
        if not si or si.point == 0:
            continue

        rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M1, 0, 300)
        if rates is None or len(rates) < 100:
            continue
            
        highs = rates['high'].astype(np.float64)
        lows = rates['low'].astype(np.float64)
        closes = rates['close'].astype(np.float64)
        
        tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(rates))]
        atr = float(np.mean(tr[-100:]))
        if atr <= 0:
            continue
            
        spread_pts = si.spread if si.spread > 0 else float(np.median(rates['spread'][-50:]))
        spread_price = spread_pts * si.point
        ratio = (spread_price / atr) * 100.0
        
        results.append({
            'symbol': s.name,
            'path': s.path,
            'spread_pts': spread_pts,
            'spread_price': spread_price,
            'atr': atr,
            'ratio': ratio,
            'price': closes[-1]
        })

    results.sort(key=lambda x: x['ratio'])
    print("Top 35 lowest Spread/ATR(14)% symbols on M1 across the entire broker:")
    print(f"{'Symbol':<12} | {'Ratio%':<8} | {'Spread':<10} | {'ATR(14)':<10} | {'Price':<10} | {'Path'}")
    print('-' * 95)
    for r in results[:35]:
        print(f"{r['symbol']:<12} | {r['ratio']:<7.1f}% | {r['spread_price']:<10.4f} | {r['atr']:<10.4f} | {r['price']:<10.2f} | {r['path']}")

    mt5.shutdown()

if __name__ == "__main__":
    scan_all_symbols()
