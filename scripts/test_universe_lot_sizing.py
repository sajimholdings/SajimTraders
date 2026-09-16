import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import MetaTrader5 as mt5
from core.lot_calculator import UniversalLotCalculator

if not mt5.initialize():
    print("MT5 Init Failed")
    exit(1)

equity = 69.94
symbols = ['XAUUSD', 'NASDAQ-100', 'DJ30', 'USDJPY', 'EURJPY', 'GBPJPY', 'XAGUSD', 'BTCUSD']
print(f"{'Symbol':<12} | {'Bid':<10} | {'SL Dist':<10} | {'Lot Size':<10} | {'Risk USD':<10}")
print("-" * 60)
for sym in symbols:
    info = mt5.symbol_info(sym)
    if not info:
        continue
    mt5.symbol_select(sym, True)
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 20)
    atr = float(rates[-1]['high'] - rates[-1]['low']) if rates is not None and len(rates)>0 else info.point * 50
    sl_dist = atr * 1.5
    entry = info.bid
    sl = entry - sl_dist
    lot, risk_cash, specs = UniversalLotCalculator.calculate_lot(sym, equity, 0.05, entry, sl)
    print(f"{sym:<12} | {entry:<10.2f} | {sl_dist:<10.4f} | {lot:<10.2f} | {risk_cash:<10.2f}")

mt5.shutdown()
