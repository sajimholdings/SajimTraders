import MetaTrader5 as mt5
import numpy as np

if not mt5.initialize():
    print("MT5 Init Failed")
    exit(1)

candidates = [
    'XAUUSD', 'NASDAQ-100', 'DJ30', 'SP500', 'US500', 'US30', 'USTEC', 'NAS100', 
    'BTCUSD', 'ETHUSD', 'XAGUSD', 'GBPJPY', 'EURJPY', 'USDJPY', 'AUDJPY', 'CADJPY', 
    'CHFJPY', 'GBPUSD', 'EURUSD', 'EURAUD', 'GBPAUD', 'XAUAUD', 'USDCAD', 'USDCHF', 'NZDUSD'
]

results = []
for sym in candidates:
    info = mt5.symbol_info(sym)
    if not info:
        continue
    mt5.symbol_select(sym, True)
    rates_m1 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 100)
    rates_m5 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 100)
    spread_pts = info.spread
    point = info.point or 0.0001
    spread_price = spread_pts * point
    
    atr_m1 = np.mean([max(r['high']-r['low'], abs(r['high']-r['close'])) for r in rates_m1[-14:]]) if rates_m1 is not None and len(rates_m1)>=14 else 0
    atr_m5 = np.mean([max(r['high']-r['low'], abs(r['high']-r['close'])) for r in rates_m5[-14:]]) if rates_m5 is not None and len(rates_m5)>=14 else 0
    
    fric_m1 = (spread_price / atr_m1 * 100) if atr_m1 > 0 else 999
    fric_m5 = (spread_price / atr_m5 * 100) if atr_m5 > 0 else 999
    results.append({
        "symbol": sym,
        "spread_pts": spread_pts,
        "spread_price": spread_price,
        "atr_m1": atr_m1,
        "fric_m1": fric_m1,
        "atr_m5": atr_m5,
        "fric_m5": fric_m5,
        "digits": info.digits
    })

print(f"{'Symbol':<12} | {'Spread':<8} | {'M1 ATR':<10} | {'M1 Fric %':<10} | {'M5 ATR':<10} | {'M5 Fric %':<10}")
print("-" * 75)
for r in sorted(results, key=lambda x: x['fric_m5']):
    print(f"{r['symbol']:<12} | {r['spread_pts']:<8} | {r['atr_m1']:<10.4f} | {r['fric_m1']:<9.1f}% | {r['atr_m5']:<10.4f} | {r['fric_m5']:<9.1f}%")

mt5.shutdown()
