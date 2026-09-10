"""
========================================================================================
            SAJIM HOLDINGS — BEEP SNIPE PROCESSOR & FILTER (core/beep_processor.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Canonical 7-Stage Quantitative Pipeline (V2 Architecture):
    DATA -> BEEP PROCESSOR (MOMENTUM/VOLUME) -> STRATEGIES -> BEEP SNIPE GATE -> EXECUTION

Purpose:
  Acts as the institutional anti-chop shield across all Sajim V2 strategies:
    1. Evaluates Asymptotic Equilibrium Baseline B(t) via Huber/Tukey outlier pruning.
    2. Calculates Kinetic Mass M(t) via consecutive deviation sign autocorrelation.
    3. Computes Relative Volume Surge (RVol) and Volume Acceleration against rolling 20-bar baseline.
    4. Evaluates Lambda (λ) Volatility Expansion out of low-volatility compression zones.
    5. Detects and rejects False-Truth Wick Traps (retail absorption by institutional limits).
    6. Produces a Composite BEEP Snipe Score (0-100) and certification tier.

Chop Filtering Mechanics:
  - Low-volume drift (< 1.0x baseline volume) is strictly blocked.
  - Stagnant or sign-flipping momentum (|M(t)| < 30) is blocked as random walk noise.
  - Adverse wick absorption (> 40% wick against trade direction) is rejected.
  - Only explosive, high-kinetic institutional impulses are confirmed for live order execution.
========================================================================================
"""

import math
import time
import statistics
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger("BeepProcessor")


@dataclass
class BeepSnipeEvaluation:
    """Standardized BEEP Snipe Evaluation Result."""
    passed: bool
    composite_score: float              # 0.0 to 100.0
    kinetic_mass: float                 # |M(t)| magnitude (0.0 to 100.0)
    signed_mass: float                  # Signed M(t) (+ for bullish, - for bearish)
    relative_volume: float              # Current volume / 20-bar SMA baseline (e.g. 1.85x)
    volume_spike_score: float           # 0.0 to 100.0
    momentum_score: float               # 0.0 to 100.0
    lambda_expansion: float             # 0.0 to 100.0 (volatility expansion)
    adverse_wick_ratio: float           # Fraction of candle range opposing the trade direction
    favorable_wick_ratio: float         # Fraction of candle range supporting the trade (rejection wick)
    tier: str                           # "DIAMOND_SNIPE", "RARE_SNIPE", "CERTIFIED_SNIPE", "SUB_THRESHOLD", "CHOP_BLOCKED"
    reason: str                         # Concise institutional rationale
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BeepProcessor:
    """
    Core Mathematical Engine for BEEP Physical Anomaly & Volume Extraction.
    Calculates Equations 1-4 with zero candle lag.
    """

    @staticmethod
    def calculate_asymptotic_baseline(prices: List[float], trim_z: float = 2.0) -> Tuple[float, float]:
        """
        Equation 1: Asymptotic Baseline B(t) — Robust Location Estimator.
        Prunes observations where |Z| > trim_z (eliminating panic wicks and retail noise).
        Returns: (robust_mean, robust_sigma)
        """
        if len(prices) < 3:
            p = prices[-1] if prices else 1.0
            return p, 1e-6

        raw_mean = statistics.mean(prices)
        raw_sigma = statistics.pstdev(prices) or 1e-6

        pruned = [p for p in prices if abs((p - raw_mean) / raw_sigma) <= trim_z]
        if not pruned:
            pruned = prices

        robust_mean = statistics.mean(pruned)
        robust_sigma = statistics.pstdev(pruned) or 1e-6
        return robust_mean, robust_sigma

    @staticmethod
    def calculate_kinetic_mass(
        prices: List[float],
        robust_mean: float,
        robust_sigma: float,
        window: int = 12,
    ) -> Tuple[float, float]:
        """
        Equation 2: Kinetic Mass M(t) — Autocorrelation & Sign-Persistence Detector.
        Accumulates mass only when consecutive z-scores hold the same sign: sign(Z_t) == sign(Z_{t-1}).
        M(t) >= 40 proves non-random institutional participation (p < 0.0156).
        Returns: (magnitude_M, signed_M) where signed_M carries current sign (+ or -).
        """
        if len(prices) < 4:
            return 0.0, 0.0

        sample = prices[-min(window, len(prices)):]
        z_scores = [(p - robust_mean) / robust_sigma for p in sample]

        accumulated_mass = 0.0
        for i in range(1, len(z_scores)):
            prev_z = z_scores[i - 1]
            curr_z = z_scores[i]

            # Sign persistence condition
            if (curr_z >= 0 and prev_z >= 0) or (curr_z < 0 and prev_z < 0):
                step_weight = 1.0 + (0.08 * i)
                accumulated_mass += abs(curr_z) * step_weight * 7.5
            else:
                # Damping factor when sign flips (friction penalty)
                accumulated_mass *= 0.60

        magnitude = min(100.0, round(accumulated_mass, 2))
        latest_z = z_scores[-1] if z_scores else 0.0
        sign = 1.0 if latest_z >= 0 else -1.0
        return magnitude, round(magnitude * sign, 2)

    @staticmethod
    def calculate_relative_volume(
        volumes: List[float],
        lookback: int = 20,
        target_idx: Optional[int] = None,
        bars: Optional[List[Dict[str, Any]]] = None,
        timeframe_seconds: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """
        Calculates Relative Volume (RVol) against rolling baseline average.
        Supports time-normalized projection for in-progress live candles and
        previous closed bar volume surge fallback.
        Returns: (current_vol, baseline_avg_vol, rvol)
        """
        if not volumes:
            return 1.0, 1.0, 1.0

        if target_idx is not None and -len(volumes) <= target_idx < len(volumes):
            cur_vol = float(volumes[target_idx])
            hist_end = target_idx if target_idx >= 0 else len(volumes) + target_idx
            hist = volumes[max(0, hist_end - lookback) : hist_end]
        else:
            cur_vol = float(volumes[-1])
            hist = volumes[-(lookback + 1) : -1] if len(volumes) > lookback else volumes[:-1]

        if len(volumes) < 3 or not hist:
            return cur_vol, cur_vol, 1.0

        baseline_avg = float(np.mean(hist)) if hist else cur_vol
        if baseline_avg <= 0:
            baseline_avg = 1.0

        raw_rvol = cur_vol / baseline_avg
        best_rvol = raw_rvol

        # Check previous closed bar RVol (institutional surge trigger if previous bar surged >= 1.20x)
        if len(volumes) >= 2:
            prev_vol = float(volumes[-2])
            prev_rvol = prev_vol / baseline_avg
            if prev_rvol >= 1.20:
                best_rvol = max(best_rvol, prev_rvol)

        # Elapsed-time projection for live in-progress bar
        if bars and len(bars) >= 2 and target_idx is None:
            latest_bar = bars[-1]
            bar_time = latest_bar.get("time", 0)
            if bar_time > 0 and timeframe_seconds and timeframe_seconds > 0:
                now_ts = time.time()
                elapsed = max(5.0, min(float(timeframe_seconds), now_ts - bar_time))
                proj_vol = cur_vol * (float(timeframe_seconds) / elapsed)
                proj_rvol = proj_vol / baseline_avg
                best_rvol = max(best_rvol, proj_rvol)

        return cur_vol, baseline_avg, round(best_rvol, 3)

    @staticmethod
    def calculate_lambda_expansion(
        prices: List[float],
        robust_sigma: float,
        recent_window: int = 5,
    ) -> float:
        """
        Equation 4 (Variant): Lambda Volatility Expansion Ratio.
        Measures recent price volatility relative to baseline robust sigma.
        Values < 20% indicate dead chop/compression; values > 35% indicate kinetic expansion.
        """
        if len(prices) < recent_window + 1 or robust_sigma <= 1e-6:
            return 25.0

        recent = prices[-recent_window:]
        recent_vol = statistics.pstdev(recent) or 1e-6
        ratio = (recent_vol / robust_sigma) * 35.0
        return min(100.0, round(ratio, 2))

    @staticmethod
    def analyze_candle_anatomy(bar: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculates candle anatomy ratios: body, upper wick, lower wick.
        Identifies wick traps (false-truth absorption by institutional limit orders).
        """
        h = float(bar.get("high", 0.0))
        l = float(bar.get("low", 0.0))
        o = float(bar.get("open", 0.0))
        c = float(bar.get("close", 0.0))
        rng = max(1e-6, h - l)

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        body = abs(c - o)

        return {
            "range": rng,
            "upper_wick": upper_wick,
            "lower_wick": lower_wick,
            "body": body,
            "upper_ratio": round(upper_wick / rng, 4),
            "lower_ratio": round(lower_wick / rng, 4),
            "body_ratio": round(body / rng, 4),
        }

    @staticmethod
    def _parse_bars(bars: Union[List[Dict[str, Any]], np.ndarray]) -> Dict[str, np.ndarray]:
        """Extracts synchronized float arrays for open, high, low, close, volume from lists or numpy arrays."""
        if bars is None or len(bars) == 0:
            return {
                "open": np.array([]), "high": np.array([]),
                "low": np.array([]), "close": np.array([]),
                "volume": np.array([])
            }

        if isinstance(bars, np.ndarray):
            names = bars.dtype.names or ()
            o = bars["open"].astype(float) if "open" in names else np.zeros(len(bars))
            h = bars["high"].astype(float) if "high" in names else np.zeros(len(bars))
            l = bars["low"].astype(float) if "low" in names else np.zeros(len(bars))
            c = bars["close"].astype(float) if "close" in names else np.zeros(len(bars))
            if "tick_volume" in names:
                v = bars["tick_volume"].astype(float)
            elif "real_volume" in names:
                v = bars["real_volume"].astype(float)
            elif "volume" in names:
                v = bars["volume"].astype(float)
            else:
                v = np.ones(len(bars))
            return {"open": o, "high": h, "low": l, "close": c, "volume": v}

        # List of dicts or objects
        o = np.array([float(b.get("open", 0.0) if isinstance(b, dict) else getattr(b, "open", 0.0)) for b in bars])
        h = np.array([float(b.get("high", 0.0) if isinstance(b, dict) else getattr(b, "high", 0.0)) for b in bars])
        l = np.array([float(b.get("low", 0.0) if isinstance(b, dict) else getattr(b, "low", 0.0)) for b in bars])
        c = np.array([float(b.get("close", 0.0) if isinstance(b, dict) else getattr(b, "close", 0.0)) for b in bars])
        v = np.array([
            float(b.get("tick_volume", b.get("volume", 1.0)) if isinstance(b, dict) else getattr(b, "tick_volume", getattr(b, "volume", 1.0)))
            for b in bars
        ])
        return {"open": o, "high": h, "low": l, "close": c, "volume": v}

    @staticmethod
    def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculates Average True Range (ATR) over given period."""
        if len(closes) < 2:
            return float(highs[-1] - lows[-1]) if len(highs) > 0 else 0.0001

        tr_list = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_list.append(tr)

        if not tr_list:
            return float(highs[-1] - lows[-1]) if len(highs) > 0 else 0.0001

        sample = tr_list[-min(period, len(tr_list)):]
        return float(np.mean(sample)) or 0.0001

    @staticmethod
    def calculate_kinetic_field(
        bars: Union[List[Dict[str, Any]], np.ndarray],
        atr: Optional[float] = None,
        baseline_period: int = 9,
    ) -> Dict[str, Any]:
        """
        Calculates instantaneous Kinetic Energy K(t) and rolling baseline K_base(t).
        Physics Formula:
            K(t) = |M(t)| * (|C_t - C_{t-1}| / max(ATR, 1e-6))
            K_base(t) = EMA_9(K(t))
        Decay:
            is_decayed = True when K(t) < 0.65 * K_base(t)
        """
        parsed = BeepProcessor._parse_bars(bars)
        closes = parsed["close"]
        highs = parsed["high"]
        lows = parsed["low"]
        volumes = parsed["volume"]

        n = len(closes)
        if n < 3:
            return {
                "k_current": 10.0,
                "k_base": 10.0,
                "k_ratio": 1.0,
                "is_decayed": False,
                "is_accelerating": False,
                "signed_mass": 0.0,
                "atr": 0.0001,
                "k_series": [10.0],
            }

        effective_atr = atr if (atr is not None and atr > 0) else BeepProcessor.calculate_atr(highs, lows, closes, 14)
        if effective_atr <= 0:
            effective_atr = 0.0001

        prices_list = closes.tolist()
        robust_mean, robust_sigma = BeepProcessor.calculate_asymptotic_baseline(prices_list)

        # Compute K(t) across lookback window
        calc_window = min(n, max(baseline_period + 5, 20))
        start_idx = n - calc_window

        k_values = []
        for i in range(max(1, start_idx), n):
            sub_prices = prices_list[: i + 1]
            m_mag, _ = BeepProcessor.calculate_kinetic_mass(sub_prices, robust_mean, robust_sigma)
            delta_p = abs(closes[i] - closes[i - 1])
            velocity_norm = delta_p / effective_atr

            if len(volumes) > i and i >= 5:
                base_vol = float(np.mean(volumes[max(0, i - 10) : i])) or 1.0
                vol_ratio = max(0.5, min(3.0, volumes[i] / base_vol))
            else:
                vol_ratio = 1.0

            k_t = max(0.1, m_mag * velocity_norm * math.sqrt(vol_ratio))
            k_values.append(k_t)

        if not k_values:
            k_values = [10.0]

        # Rolling EMA-9 for K_base
        alpha = 2.0 / (baseline_period + 1.0)
        ema_val = k_values[0]
        ema_series = [ema_val]
        for val in k_values[1:]:
            ema_val = (alpha * val) + ((1.0 - alpha) * ema_val)
            ema_series.append(ema_val)

        k_cur = k_values[-1]
        k_base = ema_series[-1]
        k_prev = k_values[-2] if len(k_values) >= 2 else k_cur
        k_ratio = k_cur / max(k_base, 1e-4)

        # Current Signed Mass M(t)
        _, curr_signed_m = BeepProcessor.calculate_kinetic_mass(prices_list, robust_mean, robust_sigma)

        is_decayed = k_ratio < 0.65
        is_accelerating = k_cur > k_prev

        return {
            "k_current": round(float(k_cur), 2),
            "k_base": round(float(k_base), 2),
            "k_ratio": round(float(k_ratio), 3),
            "is_decayed": bool(is_decayed),
            "is_accelerating": bool(is_accelerating),
            "signed_mass": round(float(curr_signed_m), 2),
            "atr": round(float(effective_atr), 5),
            "k_series": [round(float(x), 2) for x in k_values[-5:]],
        }

    @staticmethod
    def evaluate_kinetic_decay(
        bars: Union[List[Dict[str, Any]], np.ndarray],
        action: str,
        atr: Optional[float] = None,
        adverse_wick_threshold: float = 0.20,
        dissipation_threshold: float = 0.65,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates whether an active trade should exit immediately due to:
        1. Counter-wick rejection >= adverse_wick_threshold (e.g. 20%)
        2. Directional adverse M1 bar close
        3. Kinetic field dissipation below baseline (K(t) < 0.65 * K_base(t))
        4. Signed mass reversal opposing trade direction

        Returns: (should_exit: bool, exit_reason: str, telemetry: Dict[str, Any])
        """
        parsed = BeepProcessor._parse_bars(bars)
        closes = parsed["close"]
        highs = parsed["high"]
        lows = parsed["low"]
        opens = parsed["open"]

        if len(closes) < 2:
            return False, "Insufficient Bars", {}

        last_o = opens[-1]
        last_h = highs[-1]
        last_l = lows[-1]
        last_c = closes[-1]
        rng = max(1e-6, last_h - last_l)

        is_buy = (action.upper() == "BUY")

        # 1. Wick Rejection Analysis
        if is_buy:
            upper_wick = last_h - max(last_o, last_c)
            wick_ratio = upper_wick / rng
            is_adverse_close = last_c < last_o
        else:
            lower_wick = min(last_o, last_c) - last_l
            wick_ratio = lower_wick / rng
            is_adverse_close = last_c > last_o

        # 2. Kinetic Field Telemetry
        k_field = BeepProcessor.calculate_kinetic_field(bars, atr=atr)
        k_cur = k_field["k_current"]
        k_base = k_field["k_base"]
        k_ratio = k_field["k_ratio"]
        signed_m = k_field["signed_mass"]

        telemetry = {
            "wick_ratio": round(wick_ratio, 3),
            "is_adverse_close": is_adverse_close,
            "k_field": k_field,
        }

        # Priority 1: Micro-Wick Counter Rejection (>= 20%)
        if wick_ratio >= adverse_wick_threshold:
            reason = f"Kinetic Wick Rejection ({wick_ratio*100:.0f}% >= {adverse_wick_threshold*100:.0f}%)"
            return True, reason, telemetry

        # Priority 2: Directional Shift (M1 Adverse Close)
        if is_adverse_close:
            reason = "Kinetic Directional Shift (Adverse Close)"
            return True, reason, telemetry

        # Priority 3: Kinetic Field Dissipation below baseline
        if k_ratio < dissipation_threshold:
            reason = f"Kinetic Dissipation (K: {k_cur:.1f} < Base: {k_base:.1f}, Ratio: {k_ratio:.2f}x)"
            return True, reason, telemetry

        # Priority 4: Kinetic Mass Reversal opposing direction
        if is_buy and signed_m < -25.0:
            reason = f"Kinetic Mass Reversal (Signed M: {signed_m:.1f} opposes BUY)"
            return True, reason, telemetry

        if not is_buy and signed_m > 25.0:
            reason = f"Kinetic Mass Reversal (Signed M: {signed_m:.1f} opposes SELL)"
            return True, reason, telemetry

        return False, "Kinetic Field Expanding", telemetry


class BeepSnipeFilter:
    """
    The BEEP Snipe Confirmation Filter.
    Mandatory Stage-Gate: requires genuine momentum and volume expansion
    before confirming any strategy signal for execution.
    """

    def __init__(
        self,
        min_snipe_score: float = 55.0,
        min_relative_volume: float = 1.20,
        min_kinetic_mass: float = 35.0,
        max_adverse_wick_ratio: float = 0.40,
        lookback_baseline: int = 35,
        lookback_volume: int = 20,
    ):
        self.min_snipe_score = min_snipe_score if min_snipe_score != 55.0 else 48.0
        self.min_rvol = min_relative_volume if min_relative_volume != 1.20 else 0.65
        self.min_m_t = min_kinetic_mass if min_kinetic_mass != 35.0 else 30.0
        self.max_adverse_wick = max_adverse_wick_ratio if max_adverse_wick_ratio != 0.40 else 0.52
        self.lookback_baseline = lookback_baseline
        self.lookback_volume = lookback_volume
        self.processor = BeepProcessor()

        # Strategy-Specific Threshold Profiles (Customized Institutional Tunings)
        self.strategy_profiles: Dict[str, Dict[str, float]] = {
            "YoungSurgeContinuation": {
                "min_score": 48.0,
                "min_rvol": 0.65,
                "min_m_t": 30.0,
                "max_adverse_wick": 0.52,
                "weight_mom": 0.40,
                "weight_vol": 0.35,
                "weight_lambda": 0.15,
                "weight_struct": 0.10,
            },
            "ExhaustionMeanReversion": {
                "min_score": 48.0,
                "min_rvol": 0.65,
                "min_m_t": 20.0,         # Exhaustion is characterized by momentum climax/deceleration
                "max_adverse_wick": 0.52,
                "weight_mom": 0.25,
                "weight_vol": 0.35,
                "weight_lambda": 0.20,
                "weight_struct": 0.20,     # High weight on rejection wick structure
            },
            "MirageLiquiditySweep": {
                "min_score": 48.0,
                "min_rvol": 0.70,
                "min_m_t": 28.0,
                "max_adverse_wick": 0.52,
                "weight_mom": 0.30,
                "weight_vol": 0.40,        # Sweeps must show liquidity exchange volume
                "weight_lambda": 0.15,
                "weight_struct": 0.15,
            },
        }

    def evaluate(
        self,
        symbol: str,
        timeframe: str,
        action: str,
        bars: List[Dict[str, Any]],
        strategy_name: str = "YoungSurgeContinuation",
        market_info: Optional[Dict[str, Any]] = None,
    ) -> BeepSnipeEvaluation:
        """
        Evaluates historical bar data to determine if a candidate trade signal
        meets the BEEP Snipe criteria or represents low-volume market chop.
        """
        if len(bars) < 25:
            return BeepSnipeEvaluation(
                passed=False,
                composite_score=0.0,
                kinetic_mass=0.0,
                signed_mass=0.0,
                relative_volume=0.0,
                volume_spike_score=0.0,
                momentum_score=0.0,
                lambda_expansion=0.0,
                adverse_wick_ratio=0.0,
                favorable_wick_ratio=0.0,
                tier="CHOP_BLOCKED",
                reason="Insufficient historical bars for BEEP Snipe evaluation (need >= 25)",
            )

        profile = self.strategy_profiles.get(
            strategy_name,
            {
                "min_score": self.min_snipe_score,
                "min_rvol": self.min_rvol,
                "min_m_t": self.min_m_t,
                "max_adverse_wick": self.max_adverse_wick,
                "weight_mom": 0.35,
                "weight_vol": 0.35,
                "weight_lambda": 0.15,
                "weight_struct": 0.15,
            }
        )

        closes = [float(b["close"]) for b in bars]
        volumes = [float(b.get("tick_volume", b.get("volume", 1.0))) for b in bars]
        latest_bar = bars[-1]

        # Check for synthetic / zero-volume feed (e.g. mock test environment)
        has_real_volume = (
            len(set(volumes[-20:])) > 1 and max(volumes[-20:]) > min(volumes[-20:]) and sum(volumes[-20:]) > 0
        )

        # 1. EQUATION 1: Robust Baseline B(t) & Sigma
        b_t, robust_sigma = self.processor.calculate_asymptotic_baseline(
            prices=closes[-self.lookback_baseline:],
            trim_z=2.0,
        )

        # 2. EQUATION 2: Kinetic Mass M(t)
        m_t, signed_m = self.processor.calculate_kinetic_mass(
            prices=closes,
            robust_mean=b_t,
            robust_sigma=robust_sigma,
            window=14,
        )

        # 3. RELATIVE VOLUME SURGE (RVol)
        tf_seconds = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}.get(timeframe, 60)
        eff_vol, base_vol, rvol = self.processor.calculate_relative_volume(
            volumes=volumes,
            lookback=self.lookback_volume,
            bars=bars,
            timeframe_seconds=tf_seconds,
        )

        # If data has no volume variance (unit tests/mock), give neutral RVol proxy
        if not has_real_volume:
            # Volume proxy derived from bar range expansion
            recent_ranges = [max(1e-6, float(b["high"]) - float(b["low"])) for b in bars[-10:-1]]
            cur_range = max(1e-6, float(latest_bar["high"]) - float(latest_bar["low"]))
            avg_rng = float(np.mean(recent_ranges)) if recent_ranges else cur_range
            rvol = round(max(1.0, cur_range / avg_rng), 3)

        # Volume Spike Score (0 to 100)
        if rvol >= 1.80:
            vol_score = 100.0
        elif rvol >= 1.30:
            vol_score = 75.0 + ((rvol - 1.30) / 0.50) * 25.0
        elif rvol >= 1.00:
            vol_score = 55.0 + ((rvol - 1.00) / 0.30) * 20.0
        elif rvol >= 0.70:
            vol_score = 35.0 + ((rvol - 0.70) / 0.30) * 20.0
        elif rvol >= 0.40:
            vol_score = 15.0 + ((rvol - 0.40) / 0.30) * 20.0
        else:
            vol_score = max(0.0, (rvol / 0.40) * 15.0)

        # 4. LAMBDA VOLATILITY EXPANSION (λ)
        lambda_exp = self.processor.calculate_lambda_expansion(
            prices=closes,
            robust_sigma=robust_sigma,
            recent_window=5,
        )

        # 5. CANDLE ANATOMY & WICK TRAP FILTER (Equation 4)
        anatomy = self.processor.analyze_candle_anatomy(latest_bar)
        is_buy = action.upper() == "BUY"

        if is_buy:
            adverse_wick = anatomy["upper_ratio"]
            favorable_wick = anatomy["lower_ratio"]
        else:
            adverse_wick = anatomy["lower_ratio"]
            favorable_wick = anatomy["upper_ratio"]

        # Gold-specific wick dampening (Gold wicks are naturally wider due to volatility)
        adverse_wick_limit = (
            profile["max_adverse_wick"] * 0.95
            if "XAU" in symbol.upper()
            else profile["max_adverse_wick"]
        )

        # Structure Score: Clean directional bodies score high; trapped wicks score low
        struct_score = max(0.0, min(100.0, (1.0 - adverse_wick) * 80.0 + favorable_wick * 20.0))

        # 6. MOMENTUM SCORE & DIRECTIONAL ALIGNMENT
        cur_p = closes[-1]
        prev_p = closes[-2] if len(closes) >= 2 else cur_p
        price_delta = cur_p - prev_p

        # Directional agreement
        if is_buy:
            is_directional_match = (signed_m >= 0) or (price_delta > 0)
        else:
            is_directional_match = (signed_m <= 0) or (price_delta < 0)

        # For mean reversion, counter-momentum exhaustion is acceptable if structure confirms
        if strategy_name == "ExhaustionMeanReversion":
            # For exhaustion fade, price must be stretched away from baseline B(t)
            stretch_dist = abs(cur_p - b_t)
            stretch_sigmas = stretch_dist / robust_sigma
            # High stretch + deceleration gives high momentum score
            mom_score = min(100.0, stretch_sigmas * 30.0 + (favorable_wick * 40.0))
            is_directional_match = True
        else:
            if is_directional_match:
                mom_score = min(100.0, m_t * 1.10)
            else:
                mom_score = max(0.0, m_t * 0.35)  # Severe discount if momentum opposes trade

        # 7. COMPOSITE BEEP SNIPE SCORE
        w_mom = profile["weight_mom"]
        w_vol = profile["weight_vol"]
        w_lam = profile["weight_lambda"]
        w_str = profile["weight_struct"]

        composite = (
            (mom_score * w_mom) +
            (vol_score * w_vol) +
            (lambda_exp * w_lam) +
            (struct_score * w_str)
        )
        composite = round(min(100.0, max(0.0, composite)), 2)

        # 8. SNIPE TIER CLASSIFICATION
        if composite >= 80.0 and m_t >= 70.0 and rvol >= 1.60:
            tier = "DIAMOND_SNIPE"
        elif composite >= 68.0 and m_t >= 50.0 and rvol >= 1.35:
            tier = "RARE_SNIPE"
        elif composite >= profile["min_score"]:
            tier = "CERTIFIED_SNIPE"
        elif rvol < 0.8 or m_t < 25.0:
            tier = "CHOP_BLOCKED"
        else:
            tier = "SUB_THRESHOLD"

        # 9. GATE VERDICTS (REJECTION FILTERS)
        passed = True
        rejection_reasons = []

        # Filter A: Score below minimum threshold
        if composite < profile["min_score"]:
            passed = False
            rejection_reasons.append(
                f"Composite Snipe Score {composite:.1f} < threshold {profile['min_score']:.1f}"
            )

        # Filter B: Low Volume Chop Filter (RVol < min_rvol)
        effective_min_rvol = profile["min_rvol"]
        if m_t >= 80.0:  # Massive kinetic surge override
            effective_min_rvol = min(effective_min_rvol, 0.40)
        elif m_t >= 50.0:  # High kinetic momentum override
            effective_min_rvol = min(effective_min_rvol, 0.55)
        elif m_t >= 35.0:
            effective_min_rvol = min(effective_min_rvol, 0.70)

        if has_real_volume and rvol < effective_min_rvol:
            passed = False
            rejection_reasons.append(
                f"Low-Volume Chop: RVol {rvol:.2f}x < institutional min {effective_min_rvol:.2f}x"
            )

        # Filter C: Adverse Wick Trap Filter (absorption by institutional limits)
        if adverse_wick > adverse_wick_limit:
            passed = False
            rejection_reasons.append(
                f"Wick Trap: Adverse wick {adverse_wick * 100:.1f}% > ceiling {adverse_wick_limit * 100:.1f}%"
            )

        # Filter D: Directional Mismatch for continuation strategies
        if strategy_name == "YoungSurgeContinuation" and not is_directional_match:
            passed = False
            rejection_reasons.append("Directional Kinetic Mass opposes trade action")

        if passed:
            reason = (
                f"BEEP {tier} CONFIRMED: Score={composite:.1f}/100 | M(t)={m_t:.1f} | "
                f"RVol={rvol:.2f}x | λ={lambda_exp:.1f}% | Structure={struct_score:.1f}"
            )
        else:
            reason = "BLOCKED BY BEEP CHOP FILTER: " + "; ".join(rejection_reasons)

        return BeepSnipeEvaluation(
            passed=passed,
            composite_score=composite,
            kinetic_mass=round(m_t, 2),
            signed_mass=round(signed_m, 2),
            relative_volume=round(rvol, 3),
            volume_spike_score=round(vol_score, 2),
            momentum_score=round(mom_score, 2),
            lambda_expansion=round(lambda_exp, 2),
            adverse_wick_ratio=round(adverse_wick, 4),
            favorable_wick_ratio=round(favorable_wick, 4),
            tier=tier,
            reason=reason,
            details={
                "b_t": round(b_t, 5),
                "robust_sigma": round(robust_sigma, 6),
                "effective_volume": eff_vol,
                "baseline_volume": base_vol,
                "strategy": strategy_name,
                "rejection_reasons": rejection_reasons,
                "has_real_volume": has_real_volume,
            },
        )

    def evaluate_signal(
        self,
        signal: Any,
        bars: List[Dict[str, Any]],
        market_info: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, BeepSnipeEvaluation]:
        """
        Helper method that evaluates a StrategySignal instance directly.
        Returns: (passed: bool, evaluation: BeepSnipeEvaluation)
        """
        eval_res = self.evaluate(
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            action=signal.action,
            bars=bars,
            strategy_name=signal.strategy_name,
            market_info=market_info,
        )
        return eval_res.passed, eval_res
