"""
Mirage Liquidity Sweep Pro Engine (Microsecond Pure-NumPy Implementation)
========================================================================
Direct algorithmic translation of WillyAlgoTrader's "Mirage Liquidity Sweep Pro v1.3.1" (Pine Script v6).
Engineered for zero-overhead, ultra-low latency execution directly on MetaTrader 5 structured rates.

Core Capabilities:
1. Major Swing Detection (BSL & SSL) via pivot lookback (default: 21 bars).
2. Resting Liquidity Pool tracking with 80-bar age decay & EQH/EQL tolerance detection.
3. Liquidity Reclamation Validator (penetration wick + candle close reclaim).
4. 5-Factor Sweep Quality Scoring (0 - 100):
   - Wick Depth (30%)
   - Reclaim Distance (25%)
   - Close Position in Candle Range (20%)
   - Volume Spike vs 21-period SMA (15%)
   - Higher-Timeframe / Macro Trend Alignment (10%)
5. Change of Character (CHoCH) confirmation via minor structure (default: 8-bar pivot, 13-bar window).
6. Precise Risk Profiles (Balanced: 0.25 ATR stop buffer, TP1 @ 1R, TP2 @ 2R, TP3 @ 3R, Break-Even after TP1).
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
import numpy as np


class SweepType(Enum):
    BULLISH = 1   # SSL swept (swing low wicked & reclaimed) -> Long reversal setup
    BEARISH = -1  # BSL swept (swing high wicked & reclaimed) -> Short reversal setup


@dataclass
class SwingPoint:
    """Represents a major or minor structural swing."""
    bar_index: int
    price: float
    is_high: bool
    is_equal: bool = False
    is_swept: bool = False
    swept_at_bar: Optional[int] = None


@dataclass
class LiquiditySweepEvent:
    """Represents a validated sweep of resting liquidity."""
    bar_index: int
    timestamp: any
    sweep_type: SweepType
    swept_level: float
    wick_extreme: float
    score: float
    atr: float
    wick_comp: float
    reclaim_comp: float
    close_pos_comp: float
    vol_comp: float
    htf_comp: float
    is_equal_level: bool = False


@dataclass
class PendingChochSetup:
    """State machine tracking an unconfirmed sweep awaiting Change of Character (CHoCH)."""
    sweep_event: LiquiditySweepEvent
    setup_bar: int
    direction: int            # +1 for Bullish, -1 for Bearish
    target_minor_level: float # The minor pivot level that must be broken on candle close
    invalidation_level: float # The sweep wick extreme (if breached, setup is invalidated)
    expiry_bar: int           # Maximum bar index before expiration (setup_bar + confirm_window)


@dataclass
class LiquiditySweepSignal:
    """Institutional entry signal emitted by the Mirage engine."""
    bar_index: int
    timestamp: any
    direction: str            # "BUY" or "SELL"
    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    risk_r: float
    score: float
    swept_level: float
    wick_extreme: float
    is_choch_confirmed: bool
    confirmation_bar: int
    is_equal_sweep: bool


class MirageLiquiditySweepEngine:
    """
    High-performance engine for detecting, scoring, and confirming Liquidity Sweeps
    per WillyAlgoTrader's Mirage Liquidity Sweep Pro v1.3.1 specification.
    """

    def __init__(
        self,
        swing_len: int = 21,
        lookback_bars: int = 80,
        min_score: float = 50.0,
        require_confirm: bool = True,
        minor_len: int = 8,
        confirm_window: int = 13,
        use_volume: bool = True,
        vol_len: int = 21,
        vol_mult: float = 1.5,
        use_htf: bool = True,
        htf_ema_len: int = 50,
        atr_len: int = 14,
        sl_buffer: float = 0.25,
        tp1_mult: float = 1.0,
        tp2_mult: float = 2.0,
        tp3_mult: float = 3.0,
        eq_tol: float = 0.15,
        max_stored: int = 25,
    ):
        self.swing_len = swing_len
        self.lookback_bars = lookback_bars
        self.min_score = min_score
        self.require_confirm = require_confirm
        self.minor_len = minor_len
        self.confirm_window = confirm_window
        self.use_volume = use_volume
        self.vol_len = vol_len
        self.vol_mult = vol_mult
        self.use_htf = use_htf
        self.htf_ema_len = htf_ema_len
        self.atr_len = atr_len
        self.sl_buffer = sl_buffer
        self.tp1_mult = tp1_mult
        self.tp2_mult = tp2_mult
        self.tp3_mult = tp3_mult
        self.eq_tol = eq_tol
        self.max_stored = max_stored

    @staticmethod
    def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Wilder smoothed Average True Range (ATR) in pure NumPy."""
        n = len(highs)
        if n < 2:
            return np.zeros(n, dtype=np.float64)
        tr = np.empty(n, dtype=np.float64)
        tr[0] = highs[0] - lows[0]
        prev_close = closes[:-1]
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - prev_close)
        tr3 = np.abs(lows[1:] - prev_close)
        tr[1:] = np.maximum(tr1, np.maximum(tr2, tr3))

        atr = np.empty(n, dtype=np.float64)
        if n <= period:
            atr[:] = np.mean(tr)
            return atr

        atr[:period] = np.mean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        return atr

    @staticmethod
    def calculate_ema(values: np.ndarray, span: int = 50) -> np.ndarray:
        """Exponential Moving Average (EMA) in pure NumPy."""
        n = len(values)
        ema = np.empty(n, dtype=np.float64)
        if n == 0:
            return ema
        alpha = 2.0 / (span + 1.0)
        ema[0] = values[0]
        for i in range(1, n):
            ema[i] = alpha * values[i] + (1.0 - alpha) * ema[i - 1]
        return ema

    @staticmethod
    def calculate_sma(values: np.ndarray, length: int = 21) -> np.ndarray:
        """Simple Moving Average (SMA) in pure NumPy."""
        n = len(values)
        sma = np.empty(n, dtype=np.float64)
        if n == 0:
            return sma
        cumsum = np.cumsum(values, dtype=np.float64)
        for i in range(n):
            if i < length:
                sma[i] = cumsum[i] / (i + 1)
            else:
                sma[i] = (cumsum[i] - cumsum[i - length]) / length
        return sma

    def _extract_arrays(self, data: Any) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Converts MT5 rates, DataFrame, or dict into pure NumPy float arrays."""
        if hasattr(data, 'columns'):  # pandas DataFrame
            opens = data['open'].to_numpy(dtype=np.float64)
            highs = data['high'].to_numpy(dtype=np.float64)
            lows = data['low'].to_numpy(dtype=np.float64)
            closes = data['close'].to_numpy(dtype=np.float64)
            if 'tick_volume' in data.columns:
                vols = data['tick_volume'].to_numpy(dtype=np.float64)
            elif 'volume' in data.columns:
                vols = data['volume'].to_numpy(dtype=np.float64)
            else:
                vols = np.ones(len(closes), dtype=np.float64)
            times = data['time'].to_numpy() if 'time' in data.columns else np.arange(len(closes))
        elif isinstance(data, np.ndarray) and data.dtype.names:  # MT5 structured array
            opens = data['open'].astype(np.float64)
            highs = data['high'].astype(np.float64)
            lows = data['low'].astype(np.float64)
            closes = data['close'].astype(np.float64)
            vols = data['tick_volume'].astype(np.float64) if 'tick_volume' in data.dtype.names else np.ones(len(closes))
            times = data['time'] if 'time' in data.dtype.names else np.arange(len(closes))
        elif isinstance(data, dict):
            opens = np.asarray(data['open'], dtype=np.float64)
            highs = np.asarray(data['high'], dtype=np.float64)
            lows = np.asarray(data['low'], dtype=np.float64)
            closes = np.asarray(data['close'], dtype=np.float64)
            vols = np.asarray(data.get('tick_volume', data.get('volume', np.ones(len(closes)))), dtype=np.float64)
            times = np.asarray(data.get('time', np.arange(len(closes))))
        else:
            raise ValueError("Unsupported data type for Mirage engine. Provide MT5 rates, DataFrame, or dict.")

        return opens, highs, lows, closes, vols, times

    def analyze(self, data: Any) -> Tuple[List[LiquiditySweepSignal], Dict[str, Any]]:
        """
        Processes OHLCV data and returns all qualified Mirage signals
        along with resting liquidity pools and audit statistics.
        """
        opens, highs, lows, closes, vols, times = self._extract_arrays(data)
        n = len(closes)

        min_req_bars = max(self.swing_len * 2 + 1, self.htf_ema_len + 1, 50)
        if n < min_req_bars:
            return [], {"error": f"Insufficient bars ({n} < {min_req_bars})"}

        # Precompute indicators
        atrs = self.calculate_atr(highs, lows, closes, self.atr_len)
        vol_mas = self.calculate_sma(vols, self.vol_len) if self.use_volume else np.ones(n)
        htf_emas = self.calculate_ema(closes, self.htf_ema_len) if self.use_htf else closes

        # State tracking
        swing_highs: List[SwingPoint] = []
        swing_lows: List[SwingPoint] = []
        minor_highs: List[SwingPoint] = []
        minor_lows: List[SwingPoint] = []

        pending_setups: List[PendingChochSetup] = []
        emitted_signals: List[LiquiditySweepSignal] = []

        # Iterate bar-by-bar
        for i in range(self.swing_len * 2 + 1, n):
            # 1. Update Major Swings (Lookback confirmation on bar i - swing_len)
            pivot_idx = i - self.swing_len
            current_atr = atrs[i]

            # Check Major Pivot High
            is_pivot_h = True
            cand_h = highs[pivot_idx]
            for offset in range(1, self.swing_len + 1):
                if highs[pivot_idx - offset] >= cand_h or highs[pivot_idx + offset] > cand_h:
                    is_pivot_h = False
                    break
            if is_pivot_h:
                # Check for EQH (Equal Highs)
                is_eq = False
                for sp in swing_highs[-5:]:
                    if not sp.is_swept and abs(cand_h - sp.price) <= (self.eq_tol * current_atr):
                        is_eq = True
                        sp.is_equal = True
                        break
                swing_highs.append(SwingPoint(bar_index=pivot_idx, price=cand_h, is_high=True, is_equal=is_eq))
                if len(swing_highs) > self.max_stored:
                    swing_highs.pop(0)

            # Check Major Pivot Low
            is_pivot_l = True
            cand_l = lows[pivot_idx]
            for offset in range(1, self.swing_len + 1):
                if lows[pivot_idx - offset] <= cand_l or lows[pivot_idx + offset] < cand_l:
                    is_pivot_l = False
                    break
            if is_pivot_l:
                # Check for EQL (Equal Lows)
                is_eq = False
                for sp in swing_lows[-5:]:
                    if not sp.is_swept and abs(cand_l - sp.price) <= (self.eq_tol * current_atr):
                        is_eq = True
                        sp.is_equal = True
                        break
                swing_lows.append(SwingPoint(bar_index=pivot_idx, price=cand_l, is_high=False, is_equal=is_eq))
                if len(swing_lows) > self.max_stored:
                    swing_lows.pop(0)

            # 2. Update Minor Structure Swings (Pivot length = minor_len)
            if i >= self.minor_len * 2 + 1:
                m_idx = i - self.minor_len
                # Minor Pivot High
                m_is_h = True
                m_h = highs[m_idx]
                for offset in range(1, self.minor_len + 1):
                    if highs[m_idx - offset] >= m_h or highs[m_idx + offset] > m_h:
                        m_is_h = False
                        break
                if m_is_h:
                    minor_highs.append(SwingPoint(bar_index=m_idx, price=m_h, is_high=True))
                    if len(minor_highs) > self.max_stored:
                        minor_highs.pop(0)

                # Minor Pivot Low
                m_is_l = True
                m_l = lows[m_idx]
                for offset in range(1, self.minor_len + 1):
                    if lows[m_idx - offset] <= m_l or lows[m_idx + offset] < m_l:
                        m_is_l = False
                        break
                if m_is_l:
                    minor_lows.append(SwingPoint(bar_index=m_idx, price=m_l, is_high=False))
                    if len(minor_lows) > self.max_stored:
                        minor_lows.pop(0)

            # 3. Check for Sweep of Active Resting Liquidity on current bar i
            cur_o = opens[i]
            cur_h = highs[i]
            cur_l = lows[i]
            cur_c = closes[i]
            cur_rng = cur_h - cur_l
            cur_atr = atrs[i]

            # Volume component
            vol_comp = 0.5
            if self.use_volume and vol_mas[i] > 0:
                vol_comp = min(max(vols[i] / (vol_mas[i] * self.vol_mult), 0.0), 1.0)

            # HTF Bias
            htf_is_bull = cur_c >= htf_emas[i]

            # A. Bullish Sweep Check (Price wicks below active swing low, but closes above it)
            bullish_sweep_candidates: List[Tuple[SwingPoint, float]] = []
            for sp in swing_lows:
                if not sp.is_swept and (i - sp.bar_index) <= self.lookback_bars:
                    if cur_l < sp.price and cur_c > sp.price:
                        bullish_sweep_candidates.append((sp, sp.price))

            if bullish_sweep_candidates and cur_rng > 0 and cur_atr > 0:
                # Take the deepest sweep level
                target_sp, lvl = min(bullish_sweep_candidates, key=lambda x: x[1])
                target_sp.is_swept = True
                target_sp.swept_at_bar = i

                # Compute 5-factor quality score
                wick = min(cur_o, cur_c) - cur_l
                reclaim = cur_c - lvl
                close_pos = (cur_c - cur_l) / cur_rng

                wick_comp = min(max(wick, 0.0) / cur_atr, 1.0)
                rcl_comp = min(max(reclaim, 0.0) / cur_atr, 1.0)
                cp_comp = close_pos
                htf_comp = 1.0 if htf_is_bull else 0.0

                score = (
                    wick_comp * 0.30 +
                    rcl_comp * 0.25 +
                    cp_comp * 0.20 +
                    vol_comp * 0.15 +
                    htf_comp * 0.10
                ) * 100.0

                if score >= self.min_score:
                    ev = LiquiditySweepEvent(
                        bar_index=i,
                        timestamp=times[i],
                        sweep_type=SweepType.BULLISH,
                        swept_level=lvl,
                        wick_extreme=cur_l,
                        score=score,
                        atr=cur_atr,
                        wick_comp=wick_comp,
                        reclaim_comp=rcl_comp,
                        close_pos_comp=cp_comp,
                        vol_comp=vol_comp,
                        htf_comp=htf_comp,
                        is_equal_level=target_sp.is_equal,
                    )

                    if not self.require_confirm:
                        # Instant trigger on sweep bar close
                        sl = cur_l - (self.sl_buffer * cur_atr)
                        risk = cur_c - sl
                        if risk > 0:
                            emitted_signals.append(LiquiditySweepSignal(
                                bar_index=i,
                                timestamp=times[i],
                                direction="BUY",
                                entry_price=cur_c,
                                sl_price=sl,
                                tp1_price=cur_c + risk * self.tp1_mult,
                                tp2_price=cur_c + risk * self.tp2_mult,
                                tp3_price=cur_c + risk * self.tp3_mult,
                                risk_r=risk,
                                score=score,
                                swept_level=lvl,
                                wick_extreme=cur_l,
                                is_choch_confirmed=False,
                                confirmation_bar=i,
                                is_equal_sweep=target_sp.is_equal,
                            ))
                    else:
                        # Find most recent minor high for CHoCH
                        if minor_highs:
                            target_m_lvl = minor_highs[-1].price
                            pending_setups.append(PendingChochSetup(
                                sweep_event=ev,
                                setup_bar=i,
                                direction=+1,
                                target_minor_level=target_m_lvl,
                                invalidation_level=cur_l,
                                expiry_bar=i + self.confirm_window,
                            ))

            # B. Bearish Sweep Check (Price wicks above active swing high, but closes below it)
            bearish_sweep_candidates: List[Tuple[SwingPoint, float]] = []
            for sp in swing_highs:
                if not sp.is_swept and (i - sp.bar_index) <= self.lookback_bars:
                    if cur_h > sp.price and cur_c < sp.price:
                        bearish_sweep_candidates.append((sp, sp.price))

            if bearish_sweep_candidates and cur_rng > 0 and cur_atr > 0:
                # Take the highest sweep level
                target_sp, lvl = max(bearish_sweep_candidates, key=lambda x: x[1])
                target_sp.is_swept = True
                target_sp.swept_at_bar = i

                # Compute 5-factor quality score
                wick = cur_h - max(cur_o, cur_c)
                reclaim = lvl - cur_c
                close_pos = (cur_c - cur_l) / cur_rng

                wick_comp = min(max(wick, 0.0) / cur_atr, 1.0)
                rcl_comp = min(max(reclaim, 0.0) / cur_atr, 1.0)
                cp_comp = 1.0 - close_pos
                htf_comp = 1.0 if not htf_is_bull else 0.0

                score = (
                    wick_comp * 0.30 +
                    rcl_comp * 0.25 +
                    cp_comp * 0.20 +
                    vol_comp * 0.15 +
                    htf_comp * 0.10
                ) * 100.0

                if score >= self.min_score:
                    ev = LiquiditySweepEvent(
                        bar_index=i,
                        timestamp=times[i],
                        sweep_type=SweepType.BEARISH,
                        swept_level=lvl,
                        wick_extreme=cur_h,
                        score=score,
                        atr=cur_atr,
                        wick_comp=wick_comp,
                        reclaim_comp=rcl_comp,
                        close_pos_comp=cp_comp,
                        vol_comp=vol_comp,
                        htf_comp=htf_comp,
                        is_equal_level=target_sp.is_equal,
                    )

                    if not self.require_confirm:
                        # Instant trigger on sweep bar close
                        sl = cur_h + (self.sl_buffer * cur_atr)
                        risk = sl - cur_c
                        if risk > 0:
                            emitted_signals.append(LiquiditySweepSignal(
                                bar_index=i,
                                timestamp=times[i],
                                direction="SELL",
                                entry_price=cur_c,
                                sl_price=sl,
                                tp1_price=cur_c - risk * self.tp1_mult,
                                tp2_price=cur_c - risk * self.tp2_mult,
                                tp3_price=cur_c - risk * self.tp3_mult,
                                risk_r=risk,
                                score=score,
                                swept_level=lvl,
                                wick_extreme=cur_h,
                                is_choch_confirmed=False,
                                confirmation_bar=i,
                                is_equal_sweep=target_sp.is_equal,
                            ))
                    else:
                        # Find most recent minor low for CHoCH
                        if minor_lows:
                            target_m_lvl = minor_lows[-1].price
                            pending_setups.append(PendingChochSetup(
                                sweep_event=ev,
                                setup_bar=i,
                                direction=-1,
                                target_minor_level=target_m_lvl,
                                invalidation_level=cur_h,
                                expiry_bar=i + self.confirm_window,
                            ))

            # 4. Process Pending CHoCH Setups
            if self.require_confirm and pending_setups:
                remaining_setups: List[PendingChochSetup] = []
                for setup in pending_setups:
                    # Check invalidation (price breached sweep wick extreme)
                    if setup.direction == +1 and cur_l < setup.invalidation_level:
                        continue  # Invalidated
                    if setup.direction == -1 and cur_h > setup.invalidation_level:
                        continue  # Invalidated

                    # Check expiry
                    if i > setup.expiry_bar:
                        continue  # Expired without confirmation

                    # Check CHoCH confirmation on candle close
                    confirmed = False
                    if setup.direction == +1 and cur_c > setup.target_minor_level:
                        confirmed = True
                        sl = setup.invalidation_level - (self.sl_buffer * cur_atr)
                        risk = cur_c - sl
                        if risk > 0:
                            emitted_signals.append(LiquiditySweepSignal(
                                bar_index=i,
                                timestamp=times[i],
                                direction="BUY",
                                entry_price=cur_c,
                                sl_price=sl,
                                tp1_price=cur_c + risk * self.tp1_mult,
                                tp2_price=cur_c + risk * self.tp2_mult,
                                tp3_price=cur_c + risk * self.tp3_mult,
                                risk_r=risk,
                                score=setup.sweep_event.score,
                                swept_level=setup.sweep_event.swept_level,
                                wick_extreme=setup.sweep_event.wick_extreme,
                                is_choch_confirmed=True,
                                confirmation_bar=i,
                                is_equal_sweep=setup.sweep_event.is_equal_level,
                            ))
                    elif setup.direction == -1 and cur_c < setup.target_minor_level:
                        confirmed = True
                        sl = setup.invalidation_level + (self.sl_buffer * cur_atr)
                        risk = sl - cur_c
                        if risk > 0:
                            emitted_signals.append(LiquiditySweepSignal(
                                bar_index=i,
                                timestamp=times[i],
                                direction="SELL",
                                entry_price=cur_c,
                                sl_price=sl,
                                tp1_price=cur_c - risk * self.tp1_mult,
                                tp2_price=cur_c - risk * self.tp2_mult,
                                tp3_price=cur_c - risk * self.tp3_mult,
                                risk_r=risk,
                                score=setup.sweep_event.score,
                                swept_level=setup.sweep_event.swept_level,
                                wick_extreme=setup.sweep_event.wick_extreme,
                                is_choch_confirmed=True,
                                confirmation_bar=i,
                                is_equal_sweep=setup.sweep_event.is_equal_level,
                            ))

                    if not confirmed:
                        remaining_setups.append(setup)

                pending_setups = remaining_setups

        # Audit metadata
        meta = {
            "total_signals": len(emitted_signals),
            "resting_bsl_count": sum(1 for s in swing_highs if not s.is_swept),
            "resting_ssl_count": sum(1 for s in swing_lows if not s.is_swept),
            "active_pending_setups": len(pending_setups),
            "last_atr": float(atrs[-1]) if len(atrs) > 0 else 0.0,
        }

        return emitted_signals, meta
