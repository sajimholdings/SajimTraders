"""
Analyze Session-by-Session M1 ATR and Spread Friction for Indices and Target Assets.
"""
import os
import sys
import numpy as np
from datetime import datetime, timezone
import MetaTrader5 as mt5

def analyze_sessions():
    if not mt5.initialize():
        print("MT5 Init failed")
        return

    targets = [
        ("NASDAQ-100", 4.10),
        ("DJ30", 6.00),
        ("XAUUSD", 0.36),
        ("XAGUSD", 0.04),
        ("BTCUSD", 60.00),
        ("ETHUSD", 4.70),
    ]

    print(f"{'Symbol':<12} | {'All-Hours ATR':<13} | {'All Sprd/ATR':<12} | {'NY (13:30-20 UTC) ATR':<21} | {'NY Sprd/ATR%':<12} | {'London (07-15 UTC) ATR':<22} | {'London Sprd/ATR%'}")
    print("-" * 125)

    for sym, sprd in targets:
        mt5.symbol_select(sym, True)
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 10000)
        if rates is None or len(rates) < 1000:
            print(f"[-] {sym} Insufficient bars")
            continue

        n = len(rates)
        highs = rates["high"].astype(np.float64)
        lows = rates["low"].astype(np.float64)
        closes = rates["close"].astype(np.float64)
        times = rates["time"]

        tr = np.zeros(n)
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))

        # Calculate by hour
        all_atr = float(np.mean(tr))
        all_ratio = (sprd / all_atr) * 100.0

        ny_trs = []
        lon_trs = []
        asia_trs = []

        for i in range(n):
            dt = datetime.fromtimestamp(times[i], tz=timezone.utc)
            # NY Cash Session: 13:30 - 20:00 UTC
            if (dt.hour == 13 and dt.minute >= 30) or (14 <= dt.hour < 20):
                ny_trs.append(tr[i])
            # London Session: 07:00 - 15:30 UTC
            if 7 <= dt.hour < 15:
                lon_trs.append(tr[i])
            # Asian Session: 00:00 - 07:00 UTC
            if 0 <= dt.hour < 7:
                asia_trs.append(tr[i])

        ny_atr = float(np.mean(ny_trs)) if ny_trs else 0.0
        ny_ratio = (sprd / ny_atr) * 100.0 if ny_atr > 0 else 999.0

        lon_atr = float(np.mean(lon_trs)) if lon_trs else 0.0
        lon_ratio = (sprd / lon_atr) * 100.0 if lon_atr > 0 else 999.0

        print(
            f"{sym:<12} | {all_atr:<13.4f} | {all_ratio:<11.1f}% | "
            f"{ny_atr:<21.4f} | {ny_ratio:<11.1f}% | "
            f"{lon_atr:<22.4f} | {lon_ratio:<11.1f}%"
        )

    mt5.shutdown()

if __name__ == "__main__":
    analyze_sessions()
