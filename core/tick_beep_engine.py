"""
Sajim Holdings — Tick-Based BEEP Engine (tick_beep_engine.py)
Operates directly on atomic transaction ticks (Bid, Ask, Volumes, Milliseconds).
Zero candle lag — detects institutional kinetic momentum anomalies in real-time.
"""

import math
import statistics
from typing import List, Dict, Any, Tuple, Optional


class TickBeepEngine:
    """
    High-Frequency Tick-Level implementation of Jimmy Mathu's Contextual Deviation Protocol.
    Replaces arbitrary clock-time candles with transaction event windows (100 - 500 ticks).
    """

    def __init__(self, window_size: int = 150):
        self.window_size = window_size
        self.version = "1.0-TICK-PROD"

    def analyze_tick_window(self, ticks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes a rolling window of atomic market ticks.
        Each tick: {'time_ms', 'bid', 'ask', 'bid_vol', 'ask_vol'}
        """
        if len(ticks) < 30:
            return {"status": "INSUFFICIENT_TICKS", "direction": "HOLD"}

        # 1. Mid-Price Series (Eliminates bid-ask bounce noise)
        mid_prices = [(t["bid"] + t["ask"]) / 2.0 for t in ticks]
        spreads = [t["ask"] - t["bid"] for t in ticks]
        current_tick = ticks[-1]
        current_mid = mid_prices[-1]
        current_spread = spreads[-1]

        # 2. Equation 1: Asymptotic Baseline B(t) at Tick Scale
        raw_mean = statistics.mean(mid_prices)
        raw_sigma = statistics.pstdev(mid_prices) or 1e-6
        # Prune outlier micro-spikes (|Z| > 2.0)
        pruned = [p for p in mid_prices if abs((p - raw_mean) / raw_sigma) <= 2.0]
        b_t = statistics.mean(pruned) if pruned else raw_mean

        # 3. Equation 2: Kinetic Mass M(t) — Tick-to-Tick Autocorrelation
        # Measures consecutive directional persistence on ticks
        tick_deltas = [mid_prices[k] - mid_prices[k - 1] for k in range(1, len(mid_prices))]
        recent_deltas = tick_deltas[-25:]

        accumulated_mass = 0.0
        aligned_count = 0
        for k in range(1, len(recent_deltas)):
            prev_d = recent_deltas[k - 1]
            curr_d = recent_deltas[k]
            if (curr_d > 0 and prev_d > 0) or (curr_d < 0 and prev_d < 0):
                accumulated_mass += abs(curr_d / raw_sigma) * 12.0
                aligned_count += 1
            else:
                accumulated_mass *= 0.50  # Friction decay on direction flip

        m_t = min(100.0, round(accumulated_mass, 2))

        # 4. Order Flow Volume Delta (Institutional Footprint)
        recent_ticks = ticks[-25:]
        total_bid_vol = sum(t.get("bid_vol", 1.0) for t in recent_ticks)
        total_ask_vol = sum(t.get("ask_vol", 1.0) for t in recent_ticks)
        vol_delta = total_bid_vol - total_ask_vol
        vol_ratio = total_bid_vol / (total_ask_vol or 1e-4)

        # 5. Micro-Volatility & Lambda Friction Decay
        recent_tick_sigma = statistics.pstdev(mid_prices[-20:]) or 1e-6
        lambda_pct = min(100.0, round((recent_tick_sigma / raw_sigma) * 25.0, 2))

        # 6. Direction & Signal
        net_drift = current_mid - mid_prices[-25]
        if m_t >= 45.0 and lambda_pct > 10.0:
            if net_drift > 0 and (vol_delta >= 0 or vol_ratio > 0.8):
                direction = "BUY"
            elif net_drift < 0 and (vol_delta <= 0 or vol_ratio < 1.2):
                direction = "SELL"
            else:
                direction = "HOLD"
        else:
            direction = "HOLD"

        # 7. Dynamic Tick Stop Loss & Take Profit
        buffer = raw_sigma * 1.618
        if direction == "BUY":
            suggested_sl = round(b_t - (buffer * 0.5), 4)
            suggested_tp = round(current_tick["ask"] + (buffer * 2.0), 4)
        elif direction == "SELL":
            suggested_sl = round(b_t + (buffer * 0.5), 4)
            suggested_tp = round(current_tick["bid"] - (buffer * 2.0), 4)
        else:
            suggested_sl = round(current_mid - buffer, 4)
            suggested_tp = round(current_mid + buffer, 4)

        return {
            "time_ms": current_tick.get("time_ms", 0),
            "current_bid": current_tick["bid"],
            "current_ask": current_tick["ask"],
            "current_mid": round(current_mid, 4),
            "current_spread": round(current_spread, 4),
            "direction": direction,
            "M_t": m_t,
            "B_t": round(b_t, 4),
            "Lambda_pct": lambda_pct,
            "volume_delta": round(vol_delta, 2),
            "aligned_ticks": aligned_count,
            "suggested_sl": suggested_sl,
            "suggested_tp": suggested_tp,
        }
