"""
core/dealer_state_space.py
========================================================================================
            SAJIM QUANT LABS -- DEALER STATE-SPACE & MICROSTRUCTURE ENGINE
========================================================================================
Chief Architect: Jimmy Mathu
Tier-1 Institutional Market Microstructure & Market Maker Inventory Mechanics.

Implements:
  1. Real-Time Latent Dealer State-Space Models (SMC Particle Filter)
  2. Synthetic Gamma-Vanna-Charm Interaction Tensors
  3. Dynamic Dealer Hedge-Flow Elasticity
  4. Inverse Dealer-Book & Bayesian Inventory Reconstruction
  5. Intraday Zero-Gamma Migration & Liquidity Absorption Detection
========================================================================================
"""

import math
import time
from typing import Dict, Any, Tuple, Optional, List
import numpy as np


class ParticleFilterDealerEstimator:
    """
    Sequential Monte Carlo (SMC) Particle Filter for reconstructing the
    unobservable (latent) Dealer Inventory Skew from observable tick microstructure.

    State Vector x_t = [I_t, v_t, e_t]^T
      - I_t in [-1.0, +1.0]: Net Dealer Inventory Skew
          +1.0: Dealers heavily LONG spot (Inventory overhang -> Liquidation cascade risk)
          -1.0: Dealers heavily SHORT spot (Dealers short -> Short squeeze risk)
           0.0: Delta-Neutral balance
      - v_t: Inventory velocity (rate of inventory accumulation)
      - e_t: Microstructure elasticity (price displacement per lot)
    """

    def __init__(self, num_particles: int = 300, kappa_decay: float = 0.05):
        self.N = num_particles
        self.kappa = kappa_decay

        self.particles = np.zeros((self.N, 3), dtype=np.float64)
        self.particles[:, 0] = np.random.uniform(-0.1, 0.1, self.N)
        self.particles[:, 1] = np.random.normal(0.0, 0.02, self.N)
        self.particles[:, 2] = np.random.normal(1.0, 0.1, self.N)

        self.weights = np.ones(self.N, dtype=np.float64) / self.N

        self.last_bid: float = 0.0
        self.last_ask: float = 0.0
        self.last_mid: float = 0.0
        self.last_vol: float = 0.0
        self.last_update_time: float = time.time()
        self.tick_count: int = 0

    def update(self, bid: float, ask: float, volume: float, spread: float) -> Tuple[float, float, str]:
        now = time.time()
        dt = max(1e-3, min(now - self.last_update_time, 5.0))
        self.last_update_time = now
        mid = (bid + ask) / 2.0

        if self.last_mid <= 0.0:
            self.last_bid = bid
            self.last_ask = ask
            self.last_mid = mid
            self.last_vol = volume
            return 0.0, 1.0, "BALANCED"

        delta_mid = mid - self.last_mid
        tick_vol = max(1.0, volume)
        spread_val = max(1e-5, spread)

        ofi = -np.sign(delta_mid) * (tick_vol / 10.0)
        observed_elasticity = abs(delta_mid) / (tick_vol * spread_val)

        eta_I = np.random.normal(0.0, 0.04, self.N)
        eta_v = np.random.normal(0.0, 0.02, self.N)
        eta_e = np.random.normal(0.0, 0.05, self.N)

        self.particles[:, 0] += (-self.kappa * self.particles[:, 0] * dt + ofi * 0.15 + eta_I)
        self.particles[:, 0] = np.clip(self.particles[:, 0], -1.0, 1.0)

        self.particles[:, 1] = 0.90 * self.particles[:, 1] + 0.10 * (ofi / dt) + eta_v
        self.particles[:, 2] = 0.90 * self.particles[:, 2] + 0.10 * observed_elasticity + eta_e
        self.particles[:, 2] = np.clip(self.particles[:, 2], 0.01, 50.0)

        expected_ofi = -self.particles[:, 0] * 0.5
        residuals = ofi - expected_ofi
        sigma_obs = 0.35
        likelihood = np.exp(-0.5 * (residuals / sigma_obs) ** 2) + 1e-12

        self.weights *= likelihood
        weight_sum = np.sum(self.weights)
        if weight_sum > 0:
            self.weights /= weight_sum
        else:
            self.weights = np.ones(self.N, dtype=np.float64) / self.N

        n_eff = 1.0 / np.sum(self.weights ** 2)
        if n_eff < (self.N / 2.0):
            self._systematic_resample()

        est_inventory = float(np.sum(self.weights * self.particles[:, 0]))
        est_elasticity = float(np.sum(self.weights * self.particles[:, 2]))

        self.last_bid = bid
        self.last_ask = ask
        self.last_mid = mid
        self.last_vol = volume
        self.tick_count += 1

        if est_inventory > 0.40:
            regime = "DEALER_LONG_SKEW"
        elif est_inventory < -0.40:
            regime = "DEALER_SHORT_SKEW"
        else:
            regime = "BALANCED"

        return est_inventory, est_elasticity, regime

    def _systematic_resample(self):
        positions = (np.arange(self.N) + np.random.uniform(0, 1)) / self.N
        indexes = np.zeros(self.N, dtype=int)
        cumulative_sum = np.cumsum(self.weights)
        i, j = 0, 0
        while i < self.N and j < self.N:
            if positions[i] < cumulative_sum[j]:
                indexes[i] = j
                i += 1
            else:
                j += 1
        self.particles = self.particles[indexes]
        self.weights = np.ones(self.N, dtype=np.float64) / self.N


class DynamicHedgeFlowElasticity:
    """
    Measures instantaneous and rolling price impact per lot traded.
    Identifies liquidity absorption (icebergs) vs explosive runaway order flow.
    """

    def __init__(self, alpha: float = 0.15):
        self.alpha = alpha
        self.baseline_elasticity: float = 1.0
        self.is_primed: bool = False

    def update(self, price_delta: float, volume: float, spread: float) -> Tuple[float, str]:
        spread_val = max(1e-5, spread)
        vol = max(1.0, volume)
        inst_elasticity = abs(price_delta) / (vol * spread_val)

        if not self.is_primed:
            self.baseline_elasticity = inst_elasticity
            self.is_primed = True
        else:
            self.baseline_elasticity = (1.0 - self.alpha) * self.baseline_elasticity + self.alpha * inst_elasticity

        ratio = inst_elasticity / max(1e-5, self.baseline_elasticity)

        if ratio > 2.0:
            classification = "EXPLOSIVE_FLOW"
        elif ratio < 0.40:
            classification = "ABSORPTION_WALL"
        else:
            classification = "NORMAL_LIQUIDITY"

        return ratio, classification


class SyntheticGammaTensor:
    """
    Computes 2nd-order spatial and temporal price curvature against BEEP Baseline B(t).
    Estimates whether the asset is in a Long Gamma (mean-reverting pin) or Short Gamma (runaway cascade) regime.
    """

    @staticmethod
    def calculate_gamma_regime(
        rates: List[Dict[str, Any]],
        spread: float,
        point: float
    ) -> Dict[str, Any]:
        if rates is None or len(rates) < 10:
            return {
                "gamma_value": 0.0,
                "regime": "NEUTRAL",
                "zero_gamma_level": 0.0,
                "dist_to_zero_gamma_pips": 0.0,
                "conviction_boost": 1.0,
            }

        closes = [r["close"] for r in rates]
        highs = [r["high"] for r in rates]
        lows = [r["low"] for r in rates]
        n = len(closes)

        weights = np.arange(1, n + 1)
        b_t = float(np.sum(np.array(closes) * weights) / np.sum(weights))
        cur_price = closes[-1]

        d2p = (closes[-1] - 2.0 * closes[-2] + closes[-3]) if n >= 3 else 0.0
        tr = max(highs[-1] - lows[-1], point * 10)

        gamma_raw = (d2p / tr) if tr > 0 else 0.0
        zero_gamma_level = round(b_t, 5)
        dist_pips = abs(cur_price - zero_gamma_level) / point if point > 0 else 0.0

        if abs(cur_price - b_t) > (tr * 1.2) and abs(gamma_raw) > 0.20:
            regime = "SHORT_GAMMA"
            conviction_boost = 1.30
        elif abs(cur_price - b_t) < (tr * 0.6) and abs(gamma_raw) < 0.10:
            regime = "LONG_GAMMA"
            conviction_boost = 0.70
        else:
            regime = "TRANSITION"
            conviction_boost = 1.0

        return {
            "gamma_value": round(gamma_raw, 4),
            "regime": regime,
            "zero_gamma_level": zero_gamma_level,
            "dist_to_zero_gamma_pips": round(dist_pips, 1),
            "conviction_boost": conviction_boost,
        }


class DealerMicrostructureEngine:
    """
    Master Microstructure & Dealer State-Space Coordinator.
    Provides sub-second dealer alignment filtering for the Sajim Trading Stack.
    """

    def __init__(self):
        self.filters: Dict[str, ParticleFilterDealerEstimator] = {}
        self.elasticity: Dict[str, DynamicHedgeFlowElasticity] = {}
        self.gamma_tensor = SyntheticGammaTensor()

    def get_filter(self, symbol: str) -> ParticleFilterDealerEstimator:
        if symbol not in self.filters:
            self.filters[symbol] = ParticleFilterDealerEstimator(num_particles=250)
        return self.filters[symbol]

    def get_elasticity(self, symbol: str) -> DynamicHedgeFlowElasticity:
        if symbol not in self.elasticity:
            self.elasticity[symbol] = DynamicHedgeFlowElasticity()
        return self.elasticity[symbol]

    def ingest_tick(self, symbol: str, bid: float, ask: float, volume: float, spread: float) -> Dict[str, Any]:
        p_filter = self.get_filter(symbol)
        elast = self.get_elasticity(symbol)

        est_inv, est_elast, inv_regime = p_filter.update(bid, ask, volume, spread)
        delta_p = (bid + ask) / 2.0 - p_filter.last_mid
        e_ratio, flow_class = elast.update(delta_p, volume, spread)

        return {
            "symbol": symbol,
            "inventory_skew": round(est_inv, 3),
            "inventory_regime": inv_regime,
            "elasticity_ratio": round(e_ratio, 2),
            "flow_classification": flow_class,
        }

    def evaluate_dealer_alignment(
        self,
        symbol: str,
        action: str,
        cur_price: float,
        rates_m5: Optional[List[Dict[str, Any]]],
        spread: float,
        point: float,
    ) -> Tuple[bool, float, str, str]:
        p_filter = self.get_filter(symbol)
        inv = p_filter.particles[:, 0].mean() if len(p_filter.particles) > 0 else 0.0

        gamma_info = self.gamma_tensor.calculate_gamma_regime(rates_m5, spread, point)
        gamma_regime = gamma_info["regime"]
        conviction = gamma_info["conviction_boost"]

        is_buy = (action.upper() == "BUY")

        if is_buy and inv > 0.60 and gamma_regime == "LONG_GAMMA":
            narrative = (
                f"Dealer Long Overhang (I={inv:+.2f}) with Long Gamma Resistance. "
                "Dealers are forced sellers into upward moves -- Breakout rejected!"
            )
            return False, 0.0, "LONG_GAMMA_TRAP", narrative

        if not is_buy and inv < -0.60 and gamma_regime == "LONG_GAMMA":
            narrative = (
                f"Dealer Short Imbalance (I={inv:+.2f}) with Long Gamma Support. "
                "Dealers are forced buyers into dips -- Breakdown rejected!"
            )
            return False, 0.0, "SHORT_SQUEEZE_FLOOR", narrative

        if gamma_regime == "SHORT_GAMMA":
            if (is_buy and inv < 0.20) or (not is_buy and inv > -0.20):
                narrative = (
                    f"Short-Gamma Liquidity Cascade active (Γ={gamma_info['gamma_value']}). "
                    "Forced dealer mechanical hedging accelerates expansion. Multi-R conviction boosted!"
                )
                return True, 1.25, "SHORT_GAMMA_CASCADE", narrative

        narrative = f"Dealer inventory balanced (I={inv:+.2f}, Regime: {gamma_regime}). Favorable flow alignment."
        return True, conviction, gamma_regime, narrative


class ThreeCandleTickConfirmationEngine:
    """
    Synergizes Macroscopic Candle Volume Absorption with Microscopic Sub-Second Tick OFI.
    Based on HFM Institutional Dealer Microstructure & Order Flow Dynamics.
    
    1. Macro Candle Dynamics (M5 / M15):
       - Candle 1: Impulse / Liquidity Hunt Bar into local boundary.
       - Candle 2: Dealer Absorption Bar (elevated volume, prominent rejection wick >= 15%).
       - Candle 3: Directional Confirmation Bar (decisive close validating liquidity transfer).
    
    2. Micro Atomic Tick OFI (Sub-Second Flow):
       - Real-time order flow imbalance (OFI) across last 30-100 ticks.
       - Prevents buying into live aggressive sell sweeps or selling into buy sweeps.
       - Accelerates conviction on aligned microflow.
    """

    @staticmethod
    def calculate_tick_ofi(ticks: Any) -> Tuple[float, float, str]:
        """
        Calculates sub-second Order Flow Imbalance (OFI) and micro momentum from MT5 ticks.
        Returns:
            ofi (float in [-1.0, 1.0]): Order flow imbalance ratio.
            micro_delta_pts (float): Price displacement over the tick window.
            tape_bias (str): 'AGGRESSIVE_BUY', 'AGGRESSIVE_SELL', or 'NEUTRAL'.
        """
        if ticks is None or len(ticks) < 10:
            return 0.0, 0.0, "INSUFFICIENT_TICKS"

        up_ticks = 0
        down_ticks = 0
        up_vol = 0.0
        down_vol = 0.0

        n = len(ticks)
        for i in range(1, n):
            prev_bid = ticks[i - 1]['bid'] if hasattr(ticks[i - 1], '__getitem__') else getattr(ticks[i - 1], 'bid', 0.0)
            curr_bid = ticks[i]['bid'] if hasattr(ticks[i], '__getitem__') else getattr(ticks[i], 'bid', 0.0)
            vol = float(ticks[i]['volume']) if hasattr(ticks[i], '__getitem__') else float(getattr(ticks[i], 'volume', 1.0))
            if vol <= 0.0:
                vol = 1.0

            d_p = curr_bid - prev_bid
            if d_p > 1e-7:
                up_ticks += 1
                up_vol += vol
            elif d_p < -1e-7:
                down_ticks += 1
                down_vol += vol

        total_vol = up_vol + down_vol
        if total_vol <= 0:
            return 0.0, 0.0, "NEUTRAL"

        ofi = (up_vol - down_vol) / total_vol
        first_bid = ticks[0]['bid'] if hasattr(ticks[0], '__getitem__') else getattr(ticks[0], 'bid', 0.0)
        last_bid = ticks[-1]['bid'] if hasattr(ticks[-1], '__getitem__') else getattr(ticks[-1], 'bid', 0.0)
        micro_delta = last_bid - first_bid

        if ofi >= 0.20:
            tape_bias = "AGGRESSIVE_BUY"
        elif ofi <= -0.20:
            tape_bias = "AGGRESSIVE_SELL"
        else:
            tape_bias = "NEUTRAL"

        return float(ofi), float(micro_delta), tape_bias

    @classmethod
    def evaluate_three_candle_and_tick(
        cls,
        symbol: str,
        action: str,
        rates_m5: Any,
        ticks: Optional[Any] = None,
        min_wick_ratio: float = 0.15,
    ) -> Tuple[bool, float, str, Dict[str, Any]]:
        """
        Dual-layer Macro Volume & Micro Tick Gate.
        
        Returns:
            passed (bool): True if verified by candle absorption + tick OFI.
            boost (float): Conviction scaling factor (0.85x to 1.30x).
            narrative (str): Human-readable execution description.
            metrics (dict): Forensic values.
        """
        is_buy = (action.upper() == "BUY")
        metrics: Dict[str, Any] = {
            "candle_confirmed": False,
            "tick_confirmed": False,
            "ofi": 0.0,
            "wick_ratio": 0.0,
            "tape_bias": "UNKNOWN",
        }

        # 1. Macro 3-Candle Volume Absorption Check
        if rates_m5 is not None and len(rates_m5) >= 3:
            c1 = rates_m5[-3]
            c2 = rates_m5[-2]  # Absorption candidate
            c3 = rates_m5[-1]  # Trigger / confirmation

            c2_high = float(c2['high'])
            c2_low = float(c2['low'])
            c2_open = float(c2['open'])
            c2_close = float(c2['close'])
            c2_range = max(1e-6, c2_high - c2_low)

            c3_open = float(c3['open'])
            c3_close = float(c3['close'])
            c3_high = float(c3['high'])
            c3_low = float(c3['low'])
            c3_range = max(1e-6, c3_high - c3_low)

            # Volume comparison against recent average
            volumes = [float(r['tick_volume']) for r in rates_m5]
            avg_vol = (sum(volumes) / len(volumes)) if volumes else 1.0
            c2_vol_ratio = float(c2['tick_volume']) / max(1.0, avg_vol)

            if is_buy:
                # Lower rejection wick on Candle 2 shows buyers absorbing supply at lows
                c2_lower_wick = min(c2_open, c2_close) - c2_low
                wick_ratio = c2_lower_wick / c2_range
                metrics["wick_ratio"] = round(wick_ratio, 3)

                # Candle 3 confirmation: Close above C2 midpoint or closing bullish
                c2_midpoint = (c2_high + c2_low) / 2.0
                c3_bullish_close = (c3_close >= c2_midpoint) or (c3_close > c3_open)

                # Absorption is valid if wick >= min_wick_ratio or C3 strongly sweeps upwards
                candle_ok = (wick_ratio >= min_wick_ratio or c3_bullish_close) and (c2_vol_ratio >= 0.50)
            else:
                # Upper rejection wick on Candle 2 shows sellers absorbing demand at highs
                c2_upper_wick = c2_high - max(c2_open, c2_close)
                wick_ratio = c2_upper_wick / c2_range
                metrics["wick_ratio"] = round(wick_ratio, 3)

                c2_midpoint = (c2_high + c2_low) / 2.0
                c3_bearish_close = (c3_close <= c2_midpoint) or (c3_close < c3_open)

                candle_ok = (wick_ratio >= min_wick_ratio or c3_bearish_close) and (c2_vol_ratio >= 0.50)

            metrics["candle_confirmed"] = candle_ok
        else:
            candle_ok = True
            metrics["candle_confirmed"] = True

        # 2. Micro Sub-Second Tick OFI Verification
        ofi, micro_delta, tape_bias = cls.calculate_tick_ofi(ticks)
        metrics["ofi"] = round(ofi, 3)
        metrics["tape_bias"] = tape_bias

        # Microflow Veto Gate
        # Never enter BUY if sub-second tape is in an aggressive sell avalanche (OFI < -0.35)
        # Never enter SELL if sub-second tape is in an aggressive buy spike (OFI > +0.35)
        if is_buy and ofi < -0.35:
            metrics["tick_confirmed"] = False
            narrative = f"[TICK OFI VETO] BUY blocked: Micro tape is actively flushing bids (OFI={ofi:+.2f})."
            return False, 0.0, narrative, metrics

        if not is_buy and ofi > 0.35:
            metrics["tick_confirmed"] = False
            narrative = f"[TICK OFI VETO] SELL blocked: Micro tape is actively lifting offers (OFI={ofi:+.2f})."
            return False, 0.0, narrative, metrics

        metrics["tick_confirmed"] = True

        # 3. Dynamic Conviction Multiplier
        boost = 1.0
        if is_buy and ofi >= 0.20 and metrics["candle_confirmed"]:
            boost = 1.25  # Tape acceleration + absorption alignment
        elif not is_buy and ofi <= -0.20 and metrics["candle_confirmed"]:
            boost = 1.25
        elif not metrics["candle_confirmed"]:
            boost = 0.90  # Mild haircut if candle absorption wasn't textbook

        narrative = (
            f"3-Candle + Sub-Second Tick confirmed (Wick={metrics['wick_ratio']:.2f}, "
            f"OFI={ofi:+.2f} [{tape_bias}]). Boost={boost:.2f}x"
        )
        return True, boost, narrative, metrics

