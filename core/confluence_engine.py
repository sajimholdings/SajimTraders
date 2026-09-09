"""
========================================================================================
     SAJIM QUANT LABS — GRAND CONFLUENCE ENSEMBLE ENGINE (core/confluence_engine.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Edge Thesis:
  Unifies the 4 orthogonal pillars of Sajim Quantitative Systems into a single,
  high-conviction institutional execution framework:
    1. BEEP Kinetic Momentum & Mass M(t): Verifies institutional order velocity.
    2. Trend Duration Lifecycle: Confirms historical trend runway (Young Surge <= 0.60)
       or terminal exhaustion (Maturity >= 1.00).
    3. Mirage Liquidity Sweep Pro (SMC): Identifies BSL/SSL stop-runs with CHoCH.
    4. Baseline Equilibrium Reversion: Snipes overextended equilibrium snapbacks.
========================================================================================
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from v2.engine.liquidity_sweep_engine import MirageLiquiditySweepEngine, LiquiditySweepSignal
from v2.trend_duration_engine import TrendDurationEngine

logger = logging.getLogger("ConfluenceEngine")


@dataclass
class ConfluenceSignal:
    symbol: str
    timeframe: str
    direction: str                     # "BUY" or "SELL"
    mode: str                          # "KINETIC_SURGE", "INSTITUTIONAL_SWEEP_REVERSAL", "EXHAUSTION_SNAPBACK"
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward: float
    confidence_score: float            # 0.0 to 100.0
    pillars_aligned: List[str]         # e.g. ["BEEP_KINETIC", "TREND_YOUNG_SURGE", "MIRAGE_SWEEP"]
    metadata: Dict[str, Any] = field(default_factory=dict)
    bar_index: int = 0
    timestamp: Optional[int] = None


def compute_beep_kinetic_mass(closes: np.ndarray, window: int = 14) -> np.ndarray:
    """Vectorized calculation of BEEP Kinetic Mass M(t) via sign autocorrelation."""
    n = len(closes)
    m_t = np.zeros(n, dtype=np.float64)
    if n < window + 2:
        return m_t

    diffs = np.diff(closes)
    signs = np.sign(diffs)

    for i in range(window, len(signs)):
        sub = signs[i - window : i]
        net = np.sum(sub)
        m_t[i + 1] = (net / window) * 100.0

    return m_t


class GrandConfluenceEngine:
    """
    The Grand Confluence Ensemble.
    Combines BEEP Kinetic Momentum, Mirage Liquidity Sweeps, Trend Duration,
    and Baseline Equilibrium Reversion into high-conviction trades.
    """

    def __init__(
        self,
        swing_len: int = 21,
        lookback_bars: int = 80,
        mirage_min_score: float = 45.0,
        trend_hma_len: int = 50,
        trend_samples: int = 10,
        beep_window: int = 14,
    ):
        self.mirage_engine = MirageLiquiditySweepEngine(
            swing_len=swing_len,
            lookback_bars=lookback_bars,
            min_score=mirage_min_score,
            require_confirm=True,
            minor_len=8,
            confirm_window=13,
            sl_buffer=0.25,
            tp1_mult=1.0,
            tp2_mult=2.0,
            tp3_mult=3.0,
        )
        self.trend_engine = TrendDurationEngine(
            length=trend_hma_len,
            trend_length=3,
            max_samples=trend_samples
        )
        self.trend_hma_len = trend_hma_len
        self.beep_window = beep_window

    @staticmethod
    def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculates vectorized ATR over numpy arrays."""
        n = len(closes)
        atr = np.zeros(n, dtype=np.float64)
        if n < 2:
            return atr

        tr = np.zeros(n, dtype=np.float64)
        for i in range(1, n):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))

        # Initial SMA for TR
        if n > period:
            atr[period] = np.mean(tr[1 : period + 1])
            for i in range(period + 1, n):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        return atr

    def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: Any,
    ) -> Tuple[List[ConfluenceSignal], Dict[str, Any]]:
        """
        Executes full multi-pillar confluence analysis on historical bar data.
        data: Either a dict/recarray of numpy arrays ('open', 'high', 'low', 'close', 'tick_volume', 'time')
              or a list of bar dicts.
        """
        if isinstance(data, list):
            n = len(data)
            if n < self.trend_hma_len + 30:
                return [], {}
            closes = np.array([b["close"] for b in data], dtype=np.float64)
            opens = np.array([b["open"] for b in data], dtype=np.float64)
            highs = np.array([b["high"] for b in data], dtype=np.float64)
            lows = np.array([b["low"] for b in data], dtype=np.float64)
            times = [b.get("time", 0) for b in data]
            data_dict = {
                "open": opens, "high": highs, "low": lows, "close": closes,
                "time": times
            }
        elif isinstance(data, dict):
            closes = np.asarray(data["close"], dtype=np.float64)
            opens = np.asarray(data["open"], dtype=np.float64)
            highs = np.asarray(data["high"], dtype=np.float64)
            lows = np.asarray(data["low"], dtype=np.float64)
            times = data.get("time", [0] * len(closes))
            data_dict = data
            n = len(closes)
        else:
            # recarray from MT5 copy_rates_from_pos
            closes = data["close"].astype(np.float64)
            opens = data["open"].astype(np.float64)
            highs = data["high"].astype(np.float64)
            lows = data["low"].astype(np.float64)
            times = data["time"].tolist() if "time" in data.dtype.names else [0] * len(closes)
            data_dict = data
            n = len(closes)

        if n < self.trend_hma_len + 35:
            return [], {}

        # 1. PILLAR 1: BEEP Kinetic Mass Array M(t)
        m_t_arr = compute_beep_kinetic_mass(closes, window=self.beep_window)

        # 2. PILLAR 2: Trend Duration Lifecycle Arrays
        hma = self.trend_engine.calculate_hma(closes, length=self.trend_hma_len)
        atr_arr = self.calculate_atr(highs, lows, closes, period=14)

        trend_dirs = np.zeros(n, dtype=int)
        trend_counts = np.zeros(n, dtype=int)
        maturity_ratios = np.zeros(n, dtype=float)
        bull_mem: List[int] = []
        bear_mem: List[int] = []
        cur_t, cur_c = 0, 0

        start_eval = self.trend_hma_len + 5
        for i in range(start_eval, n):
            is_up = (hma[i] > hma[i - 1] > hma[i - 2] > hma[i - 3])
            is_down = (hma[i] < hma[i - 1] < hma[i - 2] < hma[i - 3])
            prev = cur_t
            if is_up:
                cur_t = 1
            elif is_down:
                cur_t = -1

            if cur_t != 0 and cur_t != prev:
                if prev == 1 and cur_c > 0:
                    bull_mem.append(cur_c)
                    if len(bull_mem) > 10:
                        bull_mem.pop(0)
                elif prev == -1 and cur_c > 0:
                    bear_mem.append(cur_c)
                    if len(bear_mem) > 10:
                        bear_mem.pop(0)
                cur_c = 1
            elif cur_t != 0:
                cur_c += 1

            trend_dirs[i] = cur_t
            trend_counts[i] = cur_c

            if cur_t == 1:
                exp_l = float(np.mean(bull_mem)) if bull_mem else 22.0
                maturity_ratios[i] = cur_c / max(5.0, exp_l)
            elif cur_t == -1:
                exp_l = float(np.mean(bear_mem)) if bear_mem else 22.0
                maturity_ratios[i] = cur_c / max(5.0, exp_l)

        # 3. PILLAR 3: Mirage Liquidity Sweep Pro Signals
        mirage_signals, _ = self.mirage_engine.analyze(data_dict)
        mirage_by_idx: Dict[int, LiquiditySweepSignal] = {s.bar_index: s for s in mirage_signals}

        # 4. CONFLUENCE DISCOVERY & SYNTHESIS
        confluence_signals: List[ConfluenceSignal] = []

        for i in range(start_eval + 10, n):
            cur_p = closes[i]
            cur_atr = max(atr_arr[i], cur_p * 0.0005)
            t_dir = trend_dirs[i]
            mat = maturity_ratios[i]
            m_t = m_t_arr[i]
            ts = times[i] if i < len(times) else 0

            # -------------------------------------------------------------
            # MODE A: INSTITUTIONAL LIQUIDITY SWEEP REVERSAL (Mirage + Confluence)
            # -------------------------------------------------------------
            if i in mirage_by_idx:
                sig = mirage_by_idx[i]
                is_buy = sig.direction == "BUY"
                is_sell = sig.direction == "SELL"

                is_with_trend = (is_buy and t_dir == 1) or (is_sell and t_dir == -1)
                is_counter_trend = (is_buy and t_dir == -1) or (is_sell and t_dir == 1)

                qualifies = False
                pillars = ["MIRAGE_SMC_SWEEP", "CHOCH_CONFIRMED"]

                if is_with_trend and mat <= 0.60:
                    qualifies = True
                    pillars.append("TREND_YOUNG_RUNWAY")
                    if (is_buy and m_t >= 0.0) or (is_sell and m_t <= 0.0):
                        pillars.append("BEEP_KINETIC_BOOST")
                elif is_counter_trend and mat >= 0.70:
                    qualifies = True
                    pillars.append("TREND_EXHAUSTION_FADE")
                    if (is_buy and m_t > -50.0) or (is_sell and m_t < 50.0):
                        pillars.append("BEEP_DECELERATION")

                if qualifies:
                    conf = min(98.0, 60.0 + sig.score * 0.25 + (len(pillars) * 5.0))
                    confluence_signals.append(
                        ConfluenceSignal(
                            symbol=symbol,
                            timeframe=timeframe,
                            direction=sig.direction,
                            mode="INSTITUTIONAL_SWEEP_REVERSAL",
                            entry_price=sig.entry_price,
                            stop_loss=sig.sl_price,
                            take_profit_1=sig.tp1_price,
                            take_profit_2=sig.tp2_price,
                            take_profit_3=sig.tp3_price,
                            risk_reward=3.0,
                            confidence_score=round(conf, 1),
                            pillars_aligned=pillars,
                            metadata={"mirage_score": sig.score, "maturity": round(mat, 2), "m_t": round(m_t, 1)},
                            bar_index=i,
                            timestamp=ts,
                        )
                    )
                    continue

            # -------------------------------------------------------------
            # MODE B: KINETIC TREND SURGE (BEEP + Trend Duration)
            # -------------------------------------------------------------
            if i % 4 == 0 and t_dir != 0:
                is_buy = t_dir == 1
                hma_diff = abs(cur_p - hma[i])

                if mat <= 0.55 and hma_diff <= (1.0 * cur_atr):
                    momentum_firing = (is_buy and m_t >= 25.0) or (not is_buy and m_t <= -25.0)
                    if momentum_firing:
                        action = "BUY" if is_buy else "SELL"
                        sl = (cur_p - 1.5 * cur_atr) if is_buy else (cur_p + 1.5 * cur_atr)
                        risk_d = abs(cur_p - sl)
                        tp1 = (cur_p + 1.0 * risk_d) if is_buy else (cur_p - 1.0 * risk_d)
                        tp2 = (cur_p + 2.0 * risk_d) if is_buy else (cur_p - 2.0 * risk_d)
                        tp3 = (cur_p + 3.0 * risk_d) if is_buy else (cur_p - 3.0 * risk_d)

                        pillars = ["TREND_YOUNG_SURGE", "BEEP_KINETIC_IMPULSE", "BASELINE_RETEST"]
                        conf = min(95.0, 70.0 + (0.55 - mat) * 35.0 + abs(m_t) * 0.15)

                        confluence_signals.append(
                            ConfluenceSignal(
                                symbol=symbol,
                                timeframe=timeframe,
                                direction=action,
                                mode="KINETIC_SURGE",
                                entry_price=cur_p,
                                stop_loss=sl,
                                take_profit_1=tp1,
                                take_profit_2=tp2,
                                take_profit_3=tp3,
                                risk_reward=3.0,
                                confidence_score=round(conf, 1),
                                pillars_aligned=pillars,
                                metadata={"maturity": round(mat, 2), "m_t": round(m_t, 1), "atr": round(cur_atr, 5)},
                                bar_index=i,
                                timestamp=ts,
                            )
                        )
                        continue

            # -------------------------------------------------------------
            # MODE C: EXHAUSTION MEAN REVERSION (Terminal Snapback)
            # -------------------------------------------------------------
            if i % 4 == 0 and t_dir != 0:
                is_bull_exhausted = (t_dir == 1 and cur_p > hma[i])
                is_bear_exhausted = (t_dir == -1 and cur_p < hma[i])
                stretch = abs(cur_p - hma[i]) / cur_atr if cur_atr > 0 else 0.0

                if mat >= 1.00 and stretch >= 1.25:
                    action = "SELL" if is_bull_exhausted else "BUY"
                    is_buy = action == "BUY"
                    sl = (cur_p - 1.5 * cur_atr) if is_buy else (cur_p + 1.5 * cur_atr)
                    risk_d = abs(cur_p - sl)
                    tp1 = (cur_p + 1.0 * risk_d) if is_buy else (cur_p - 1.0 * risk_d)
                    tp2 = float(hma[i])
                    tp3 = (cur_p + 2.5 * risk_d) if is_buy else (cur_p - 2.5 * risk_d)

                    pillars = ["TREND_EXHAUSTION_LIFECYCLE", "ATR_EQUILIBRIUM_STRETCH"]
                    conf = min(92.0, 68.0 + (mat - 1.00) * 20.0 + (stretch - 1.25) * 10.0)

                    confluence_signals.append(
                        ConfluenceSignal(
                            symbol=symbol,
                            timeframe=timeframe,
                            direction=action,
                            mode="EXHAUSTION_SNAPBACK",
                            entry_price=cur_p,
                            stop_loss=sl,
                            take_profit_1=tp1,
                            take_profit_2=tp2,
                            take_profit_3=tp3,
                            risk_reward=2.5,
                            confidence_score=round(conf, 1),
                            pillars_aligned=pillars,
                            metadata={"maturity": round(mat, 2), "stretch_atr": round(stretch, 2), "m_t": round(m_t, 1)},
                            bar_index=i,
                            timestamp=ts,
                        )
                    )

        summary = {
            "total_signals": len(confluence_signals),
            "modes": {
                "INSTITUTIONAL_SWEEP_REVERSAL": sum(1 for s in confluence_signals if s.mode == "INSTITUTIONAL_SWEEP_REVERSAL"),
                "KINETIC_SURGE": sum(1 for s in confluence_signals if s.mode == "KINETIC_SURGE"),
                "EXHAUSTION_SNAPBACK": sum(1 for s in confluence_signals if s.mode == "EXHAUSTION_SNAPBACK"),
            },
            "last_maturity": round(float(maturity_ratios[-1]), 2),
            "last_m_t": round(float(m_t_arr[-1]), 1),
            "last_trend": "UP" if trend_dirs[-1] == 1 else ("DOWN" if trend_dirs[-1] == -1 else "NONE"),
        }

        return confluence_signals, summary
