"""
========================================================================================
       SAJIM HOLDINGS V2 — TREND DURATION MATURITY ENGINE (v2/trend_duration_engine.py)
========================================================================================
Chief Architect: Jimmy Mathu
Inspired by: Trend Duration Forecast v1.05 [Far_Q / ChartPrime]
Production Enhancements:
  - Microsecond vectorized Hull Moving Average (HMA) computation.
  - Multi-bar slope detection with rolling 10-trend memory.
  - Generates the 3 Institutional Trend Phases:
      1. YOUNG_SURGE   (maturity <= 0.60): Prime zone for BEEP Kinetic Trend Continuation.
      2. MATURE        (0.60 < maturity < 1.00): Transition zone; halts new breakouts.
      3. EXHAUSTED     (maturity >= 1.00): Prime zone for Sajim Mean Reversion Sniping.
========================================================================================
"""

import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np


class TrendDurationEngine:
    """
    Real-time Trend Duration & Statistical Maturity Forecaster.
    Categorizes any asset and timeframe into its precise lifecycle phase.
    """

    def __init__(self, length: int = 50, trend_length: int = 3, max_samples: int = 10):
        self.length = length
        self.trend_length = trend_length
        self.max_samples = max_samples

        # Memory store per (symbol, timeframe)
        # key: (symbol, timeframe) -> {'bullish': List[int], 'bearish': List[int], 'last_trend': int, 'count': int}
        self.memory: Dict[Tuple[str, str], Dict[str, Any]] = {}

    @staticmethod
    def calculate_wma(values: np.ndarray, length: int) -> np.ndarray:
        """Vectorized Weighted Moving Average (WMA)."""
        weights = np.arange(1, length + 1, dtype=np.float64)
        weight_sum = weights.sum()
        wma = np.full_like(values, fill_value=np.nan, dtype=np.float64)

        for i in range(length - 1, len(values)):
            wma[i] = np.dot(values[i - length + 1 : i + 1], weights) / weight_sum
        return wma

    @classmethod
    def calculate_hma(cls, values: np.ndarray, length: int = 50) -> np.ndarray:
        """Hull Moving Average (HMA)."""
        half_len = max(1, int(length / 2))
        sqrt_len = max(1, int(math.floor(math.sqrt(length))))

        wma_half = cls.calculate_wma(values, half_len)
        wma_full = cls.calculate_wma(values, length)

        diff = 2.0 * wma_half - wma_full
        return cls.calculate_wma(diff, sqrt_len)

    def evaluate_maturity(
        self,
        symbol: str,
        timeframe: str,
        bars: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates the current bar of the asset and returns its lifecycle phase.
        Returns:
          - trend: "UP", "DOWN", or "NONE"
          - trend_count: Number of bars current trend has been active
          - probable_length: Rolling average duration of past 10 trends
          - maturity_ratio: trend_count / probable_length
          - phase: "YOUNG_SURGE", "MATURE", "EXHAUSTED"
          - hma_val: Current HMA line value
        """
        if len(bars) < (self.length + self.trend_length + 15):
            return {
                "trend": "NONE",
                "trend_count": 0,
                "probable_length": 20.0,
                "maturity_ratio": 0.0,
                "phase": "YOUNG_SURGE",
                "hma_val": bars[-1]["close"] if bars else 0.0,
            }

        closes = np.array([b["close"] for b in bars], dtype=np.float64)
        hma = self.calculate_hma(closes, length=self.length)

        # Multi-bar slope detection over the entire historical window
        # to ensure historical trend memory is properly warmed up
        key = (symbol, timeframe)
        bullish_samples: List[int] = []
        bearish_samples: List[int] = []

        trend = 0  # 1=UP, -1=DOWN, 0=NONE
        trend_count = 0

        start_idx = self.length + self.trend_length
        for i in range(start_idx, len(bars)):
            # Check slope
            is_rising = True
            is_falling = True
            for k in range(self.trend_length):
                idx_curr = i - k
                idx_prev = i - k - 1
                if np.isnan(hma[idx_curr]) or np.isnan(hma[idx_prev]):
                    is_rising = False
                    is_falling = False
                    break
                if hma[idx_curr] <= hma[idx_prev]:
                    is_rising = False
                if hma[idx_curr] >= hma[idx_prev]:
                    is_falling = False

            prev_trend = trend
            if is_rising:
                trend = 1
            elif is_falling:
                trend = -1

            if trend != 0 and trend != prev_trend:
                # Trend flip event
                if prev_trend == 1 and trend_count > 0:
                    bullish_samples.append(trend_count)
                    if len(bullish_samples) > self.max_samples:
                        bullish_samples.pop(0)
                elif prev_trend == -1 and trend_count > 0:
                    bearish_samples.append(trend_count)
                    if len(bearish_samples) > self.max_samples:
                        bearish_samples.pop(0)
                trend_count = 1
            elif trend != 0:
                trend_count += 1

        # Current State Evaluation
        if trend == 1:
            trend_label = "UP"
            prob_len = float(np.mean(bullish_samples)) if bullish_samples else 22.0
        elif trend == -1:
            trend_label = "DOWN"
            prob_len = float(np.mean(bearish_samples)) if bearish_samples else 22.0
        else:
            trend_label = "NONE"
            prob_len = 22.0

        prob_len = max(5.0, prob_len)
        maturity_ratio = round(trend_count / prob_len, 2)

        # Determine Phase
        if maturity_ratio <= 0.60:
            phase = "YOUNG_SURGE"     # BEEP continuation zone
        elif maturity_ratio < 1.00:
            phase = "MATURE"          # Neutral transition / trailing zone
        else:
            phase = "EXHAUSTED"       # Mean reversion sniping zone

        cur_hma = float(hma[-1]) if not np.isnan(hma[-1]) else closes[-1]

        return {
            "trend": trend_label,
            "trend_count": trend_count,
            "probable_length": round(prob_len, 1),
            "maturity_ratio": maturity_ratio,
            "phase": phase,
            "hma_val": round(cur_hma, 5),
        }
