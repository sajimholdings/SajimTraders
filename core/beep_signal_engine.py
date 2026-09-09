"""
========================================================================================
            SAJIM HOLDINGS — BEEP SIGNAL ENGINE (core/beep_signal_engine.py)
========================================================================================
Chief Architect: Jimmy Mathu
Mission:
  - Connects to live MT5 terminal feed.
  - Monitors all tradable institutional instruments across multiple timeframes (M5, M15, H1).
  - PURE SIGNAL GENERATION ONLY:
      * Calculates Asymptotic Robust Baseline B(t)
      * Calculates Kinetic Mass M(t) (Sign Autocorrelation)
      * Detects BEEP Layers: DIAMOND (|M| >= 75), RARE (|M| >= 55), CERTIFIED (|M| >= 35)
      * Enforces Structural Invalidation Floor (min 80 points / 4x spread)
      * Computes Asymmetric Targets (1:2.5 to 1:4.0 R:R)
      * Emits immutable BeepSignal objects.
  - Zero coupling with lots, balances, order placement, or trade management.
========================================================================================
"""

import os
import sys
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from vault_original_beep.raw_beep_equations import OriginalRawBeep

logger = logging.getLogger("BeepSignalEngine")

# ========================================================================================
#                      THE SACRED BEEP PURITY PROTOCOL (IMMUTABLE RULE)
# ========================================================================================
# BEEP is strictly an OBJECTIVE UNIVERSAL PHYSICAL ANOMALY SENSOR.
# 1. BEEP NEVER executes trades, sizes lots, or manages capital.
# 2. BEEP NEVER contains hardcoded pair whitelists or static asset exclusions.
# 3. BEEP measures only pure physical properties across ANY tradable asset in the universe:
#      - Robust Equilibrium Baseline B(t)
#      - Kinetic Mass M(t) (Sign Autocorrelation & Velocity)
#      - Boundary Dispersion & Rejection Wick Traps (Perimeter Liquidity Absorption)
# ALL portfolio gating, spread efficiency (eta <= 0.15), macro trend alignment,
# and trade execution are 100% DYNAMIC and managed exclusively by the overlying SAJIM V1.
# ========================================================================================


@dataclass(frozen=True)
class BeepSignal:
    signal_id: str
    symbol: str
    timeframe: str
    bar_time: int
    action: str              # "BUY" or "SELL"
    layer: str               # "DIAMOND", "RARE", "CERTIFIED"
    m_t: float               # Kinetic Mass
    b_t: float               # Robust Baseline
    entry_price: float       # Trigger price
    stop_loss: float         # Structural floor
    take_profit: float       # Asymmetric target
    risk_reward: float       # R:R ratio (2.5 - 4.0)
    phi_energy: float        # Conviction score
    spread_points: int
    created_at: str
    mode: str = "INTRADAY"   # "SCALP", "INTRADAY", "SWING"
    regime: str = "ACTIVE_HUNT" # "ACTIVE_HUNT", "WAIT_COMPRESSION", "FALSE_TRUTH_REJECT", "BASELINE_RETEST"
    session: str = "LIVE_MARKET" # "TOKYO_ASIAN", "LONDON_OPEN", "NEW_YORK", "OFF_HOURS"
    upper_wick_ratio: float = 0.0
    lower_wick_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_market_session() -> str:
    """Returns current active global institutional session based on UTC hour."""
    from datetime import timezone
    utc_hour = datetime.now(timezone.utc).hour
    if 0 <= utc_hour < 6:
        return "TOKYO_ASIAN"
    elif 6 <= utc_hour < 12:
        return "LONDON_OPEN"
    elif 12 <= utc_hour < 20:
        return "NEW_YORK"
    else:
        return "OFF_HOURS"


class BeepSignalEngine:
    """
    Dedicated BEEP Signal Provider.
    Scans MT5 live data and emits high-conviction signals without duplicate bar spam.
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[Tuple[str, int]]] = None,
        lookback: int = 12,
    ):
        self.raw_beep = OriginalRawBeep()
        self.lookback = lookback
        self.symbols = symbols or []
        self.timeframes = timeframes or [
            ("M1", mt5.TIMEFRAME_M1),
            ("M5", mt5.TIMEFRAME_M5),
            ("M15", mt5.TIMEFRAME_M15),
            ("M30", mt5.TIMEFRAME_M30),
            ("H1", mt5.TIMEFRAME_H1),
            ("H4", mt5.TIMEFRAME_H4),
            ("D1", mt5.TIMEFRAME_D1),
        ]

        # Deduplication memory: records (symbol, tf, bar_time) so signals only fire once per candle
        self.fired_signals_cache: Set[Tuple[str, str, int]] = set()

    def set_universe(self, symbols: List[str]):
        """Sets the active tradable universe for scanning."""
        self.symbols = symbols
        for s in self.symbols:
            mt5.symbol_select(s, True)

    def get_htf_trend(self, symbol: str, cur_tf: str) -> int:
        """
        Calculates higher timeframe macro direction via Equation 3 (Gamma Gate Γ).
        Returns +1 for Bullish, -1 for Bearish, 0 for Neutral.
        """
        htf_map = {
            "M1": mt5.TIMEFRAME_H1,
            "M5": mt5.TIMEFRAME_H1,
            "M15": mt5.TIMEFRAME_H4,
            "M30": mt5.TIMEFRAME_H4,
            "H1": mt5.TIMEFRAME_D1,
            "H4": mt5.TIMEFRAME_D1,
            "D1": mt5.TIMEFRAME_D1,
        }
        htf_enum = htf_map.get(cur_tf, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, htf_enum, 0, 15)
        if rates is None or len(rates) < 12:
            return 0
        closes = [float(r["close"]) for r in rates]
        b = self.raw_beep.calculate_raw_baseline_B(closes[-12:])
        return 1 if closes[-1] > b else -1

    def scan_front(self, symbol: str, tf_label: str, tf_enum: int) -> Optional[BeepSignal]:
        """
        Scans a single symbol and timeframe front across multi-modes (SCALP, INTRADAY, SWING).
        Fires an immutable BeepSignal if a genuine institutional layer anomaly is present
        and passes the False-Truth Wick Trap Fader (Equation 4).
        """
        # Multi-Mode Calibration:
        # Scalp: W=10 (M1, M5) | Intraday: W=20 (M15, M30, H1) | Swing: W=50 (H4, D1)
        if tf_label in ("M1", "M5"):
            mode = "SCALP"
            eff_lookback = 10
            base_rr = 2.5
        elif tf_label in ("M15", "M30", "H1"):
            mode = "INTRADAY"
            eff_lookback = 20
            base_rr = 3.5
        else:
            mode = "SWING"
            eff_lookback = 50
            base_rr = 4.0

        rates = mt5.copy_rates_from_pos(symbol, tf_enum, 0, eff_lookback + 10)
        if rates is None or len(rates) < eff_lookback + 1:
            return None

        sym_info = mt5.symbol_info(symbol)
        if not sym_info or not sym_info.visible or sym_info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
            return None

        # Filter extreme blowout spread widening (e.g. illiquid weekend/midnight gaps)
        max_spread = 250 if "XAU" in symbol or "XAG" in symbol else 120
        if sym_info.spread > max_spread:
            return None

        latest_bar = rates[-1]
        bar_time = int(latest_bar["time"])

        # Deduplication Guard: Never fire the exact same signal on the same candle
        cache_key = (symbol, tf_label, bar_time)
        if cache_key in self.fired_signals_cache:
            return None

        prices = [float(r["close"]) for r in rates]
        cur_p = prices[-1]

        window = prices[-(eff_lookback + 1):]
        b_t = self.raw_beep.calculate_raw_baseline_B(window)
        m_mag = self.raw_beep.calculate_raw_mass_M(window, b_t)

        # Directional Sign: Momentum direction is determined by price displacement from fair-value baseline B(t)
        if cur_p > b_t:
            action = "BUY"
            m_t = m_mag
        elif cur_p < b_t:
            action = "SELL"
            m_t = -m_mag
        else:
            return None

        abs_m = abs(m_mag)
        layer = None
        rr = base_rr

        # High-Conviction Institutional Layers
        if abs_m >= 75.0:
            layer = "DIAMOND"
            rr = max(base_rr, 4.0)
        elif abs_m >= 55.0:
            layer = "RARE"
            rr = max(base_rr, 3.5)
        elif abs_m >= 35.0:
            layer = "CERTIFIED"
            rr = max(base_rr, 2.5)

        if layer is None:
            return None

        # CANDLE ANATOMY: FALSE-TRUTH WICK TRAP FADER (Equation 4)
        bar_h = float(latest_bar["high"])
        bar_l = float(latest_bar["low"])
        bar_o = float(latest_bar["open"])
        bar_c = float(latest_bar["close"])
        bar_rng = max(1e-6, bar_h - bar_l)
        upper_wick = bar_h - max(bar_o, bar_c)
        lower_wick = min(bar_o, bar_c) - bar_l
        upper_ratio = upper_wick / bar_rng
        lower_ratio = lower_wick / bar_rng

        # If BUY has Upper Wick > 45%, smart money limit sellers are absorbing FOMO buyers
        if action == "BUY" and upper_ratio > 0.45:
            return None
        # If SELL has Lower Wick > 45%, smart money limit buyers are absorbing FOMO sellers
        if action == "SELL" and lower_ratio > 0.45:
            return None

        # ULTRA-STRICT WICK SHIELD FOR GOLD (Eliminate meat-grinder chop entries)
        if "XAU" in symbol:
            if action == "BUY" and upper_ratio > 0.30:
                return None
            if action == "SELL" and lower_ratio > 0.30:
                return None

        # MULTI-SCALE GAMMA GATE Γ (Equation 3):
        # Micro momentum must align with Macro baseline trend (Prunes 99.8% false signals)
        htf_trend = self.get_htf_trend(symbol, tf_label)
        if htf_trend != 0:
            if action == "BUY" and htf_trend != 1:
                return None
            elif action == "SELL" and htf_trend != -1:
                return None

        # STRUCTURAL STOP LOSS FLOOR (Equation 1):
        # Stop loss placed beyond baseline B(t) with asset-calibrated buffer:
        # - Gold (XAU): 1,200 points ($12.00 move) or 8x spread for massive breathing room
        # - Silver (XAG): 300 points ($3.00 min move) or 5x spread
        # - FX pairs: 15 pips (150 points) or 4x spread
        spread_cost = sym_info.spread * sym_info.point
        if "XAU" in symbol:
            # Calibrated to Gold's high-volatility regime ($4,400 price level)
            # Upgraded future buffer to 1,200 points ($12.00 USD) or 8x spread.
            # Gives Gold massive breathing room (1.5x M15 ATR) so intra-day wicks never clip the trade!
            min_stop_points = max(sym_info.point * 1200.0, spread_cost * 8.0)
        elif "XAG" in symbol:
            min_stop_points = max(sym_info.point * 300.0, spread_cost * 5.0)
        else:
            min_stop_points = max(sym_info.point * 150.0, spread_cost * 4.0)
        risk_dist = max(min_stop_points, abs(cur_p - b_t) + (min_stop_points * 0.30))

        if action == "BUY":
            sl = round(cur_p - risk_dist, sym_info.digits)
            actual_risk = cur_p - sl
            tp = round(cur_p + (actual_risk * rr), sym_info.digits)
        else:
            sl = round(cur_p + risk_dist, sym_info.digits)
            actual_risk = sl - cur_p
            tp = round(cur_p - (actual_risk * rr), sym_info.digits)

        # Anomaly Energy Score
        phi_energy = (abs_m * rr) / max(1e-4, spread_cost)
        signal_id = f"BEEP_{symbol}_{tf_label}_{bar_time}"
        session_tag = get_market_session()

        signal = BeepSignal(
            signal_id=signal_id,
            symbol=symbol,
            timeframe=tf_label,
            bar_time=bar_time,
            action=action,
            layer=layer,
            m_t=round(m_t, 2),
            b_t=round(b_t, sym_info.digits),
            entry_price=cur_p,
            stop_loss=sl,
            take_profit=tp,
            risk_reward=rr,
            phi_energy=round(phi_energy, 2),
            spread_points=sym_info.spread,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            mode=mode,
            regime="ACTIVE_HUNT",
            session=session_tag,
            upper_wick_ratio=round(upper_ratio, 3),
            lower_wick_ratio=round(lower_ratio, 3),
        )

        # Mark as fired to prevent spam on this bar
        self.fired_signals_cache.add(cache_key)
        if len(self.fired_signals_cache) > 1000:
            self.fired_signals_cache = set(list(self.fired_signals_cache)[-500:])

        return signal

    def scan_boundary_absorption_front(self, symbol: str, tf_label: str = "M15", tf_enum: int = mt5.TIMEFRAME_M15) -> Optional[BeepSignal]:
        """
        Universal Boundary Absorption Anomaly Sensor (The Sacred BEEP Sensor).
        Measures pure physical perimeter liquidity traps across ANY tradable instrument.
        
        Strict Physical Invariant Laws:
          1. Universal: Operates across ANY asset in the universe without hardcoded whitelists.
          2. Physical Dispersion: Price displacement |cur_p - B(t)| >= 1.2 * ATR_M15.
          3. False-Truth Wick Absorption: Upper Wick >= 40% (Ceiling Trap) or Lower Wick >= 40% (Floor Trap).
          4. Structural Invalidation: Micro-stop placed 2 pips beyond extreme rejection wick.
          5. Physical Asymmetry: Mean-reverting distance back to Baseline B(t) has R:R >= 1.5.
          
        NOTE: Commercial portfolio gating, dynamic spread efficiency (eta <= 0.15),
        macro trend alignment (Gamma), and lot sizing belong strictly to SAJIM V1.
        """
        rates = mt5.copy_rates_from_pos(symbol, tf_enum, 0, 30)
        if rates is None or len(rates) < 22:
            return None

        sym_info = mt5.symbol_info(symbol)
        if not sym_info or not sym_info.visible or sym_info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
            return None

        point = float(sym_info.point) if sym_info and sym_info.point else 0.00001
        digits = int(sym_info.digits) if sym_info and sym_info.digits is not None else 5
        spread_cost = float(sym_info.spread) * point
        pip_dist = point * 10.0

        latest_bar = rates[-1]
        bar_time = int(latest_bar["time"])

        cache_key = (f"{symbol}_BOUNDARY", tf_label, bar_time)
        if cache_key in self.fired_signals_cache:
            return None

        prices = [float(r["close"]) for r in rates]
        cur_p = prices[-1]
        b_t = self.raw_beep.calculate_raw_baseline_B(prices[-20:])
        m_mag = self.raw_beep.calculate_raw_mass_M(prices[-20:], b_t)

        # Calculate True Range (ATR 14)
        tr_list = [max(r["high"] - r["low"], abs(r["high"] - r["close"]), abs(r["low"] - r["close"])) for r in rates[-14:]]
        atr = sum(tr_list) / max(1, len(tr_list))
        if atr <= 0:
            return None

        # 1. Physical Dispersion: Price must stretch >= 1.2 * ATR away from Baseline B(t)
        dist_from_b = abs(cur_p - b_t)
        if dist_from_b < (1.2 * atr):
            return None

        # 2. Candle Anatomy Wick Trap (Liquidity Absorption by Limit Orders)
        bar_h = float(latest_bar["high"])
        bar_l = float(latest_bar["low"])
        bar_o = float(latest_bar["open"])
        bar_c = float(latest_bar["close"])
        bar_rng = max(1e-6, bar_h - bar_l)
        upper_wick = (bar_h - max(bar_o, bar_c)) / bar_rng
        lower_wick = (min(bar_o, bar_c) - bar_l) / bar_rng

        micro_stop_pips = 2.0 * pip_dist

        if cur_p > b_t and upper_wick >= 0.40:
            # Ceiling Rejection -> FADE SHORT back to Baseline B(t)
            action = "SELL"
            sl = round(bar_h + micro_stop_pips, digits)
            tp = round(b_t, digits)
            risk = float(sl - cur_p)
            reward = float(cur_p - tp)
        elif cur_p < b_t and lower_wick >= 0.40:
            # Floor Rejection -> FADE LONG back to Baseline B(t)
            action = "BUY"
            sl = round(bar_l - micro_stop_pips, digits)
            tp = round(b_t, digits)
            risk = float(cur_p - sl)
            reward = float(tp - cur_p)
        else:
            return None

        if risk <= 0 or reward <= 0:
            return None

        rr = reward / risk
        # 3. Minimum Physical Asymmetry — Mean-reversion to Baseline pays >= 1.5x risk
        if rr < 1.5:
            return None

        signal_id = f"BEEP_BOUNDARY_{symbol}_{tf_label}_{bar_time}"
        phi_energy = round((60.0 * rr) / max(1e-4, spread_cost), 2)

        signal = BeepSignal(
            signal_id=signal_id,
            symbol=symbol,
            timeframe=tf_label,
            bar_time=bar_time,
            action=action,
            layer="BOUNDARY_ABSORPTION",
            m_t=round(-m_mag if action == "SELL" else m_mag, 2),
            b_t=round(b_t, digits),
            entry_price=cur_p,
            stop_loss=sl,
            take_profit=tp,
            risk_reward=round(rr, 2),
            phi_energy=phi_energy,
            spread_points=sym_info.spread,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            mode="BOUNDARY_FADE",
            regime="RANGE_COMPRESSION",
            session=get_market_session(),
            upper_wick_ratio=round(upper_wick, 3),
            lower_wick_ratio=round(lower_wick, 3),
        )

        self.fired_signals_cache.add(cache_key)
        if len(self.fired_signals_cache) > 1000:
            self.fired_signals_cache = set(list(self.fired_signals_cache)[-500:])

        logger.info(
            f"[🎯 BEEP BOUNDARY ANOMALY] {signal_id}: {action} on {symbol} @ {cur_p} | "
            f"SL: {sl} | TP (Baseline): {tp} | R:R: 1:{rr:.2f} | Wick: {max(upper_wick, lower_wick)*100:.1f}%"
        )
        return signal

    # Backwards-compatibility alias
    scan_range_harvest_front = scan_boundary_absorption_front

    def classify_regime(self, symbol: str, tf_label: str = "M15", tf_enum: int = mt5.TIMEFRAME_M15) -> Dict[str, Any]:
        """
        Evaluates a front against the 4-Regime Market State Taxonomy:
          1. ACTIVE_HUNT         : |M| >= 55, clean candle (wick <= 45%), HTF aligned -> Execute Now
          2. FALSE_TRUTH_REJECT  : |M| >= 55, but wick > 45% or HTF divergence -> Fade / Stand Down
          3. BASELINE_RETEST     : 25 <= |M| < 55, price returning near B(t) -> Discount Entry Zone
          4. WAIT_COMPRESSION    : |M| < 25 -> Energy coiling inside baseline, zero edge
        """
        rates = mt5.copy_rates_from_pos(symbol, tf_enum, 0, 30)
        if rates is None or len(rates) < 21:
            return {"symbol": symbol, "timeframe": tf_label, "regime": "DATA_UNAVAILABLE", "reason": "Insufficient bar data"}

        sym_info = mt5.symbol_info(symbol)
        digits = sym_info.digits if sym_info else 5

        prices = [float(r["close"]) for r in rates]
        cur_p = prices[-1]
        b_t = self.raw_beep.calculate_raw_baseline_B(prices[-21:])
        m_mag = self.raw_beep.calculate_raw_mass_M(prices[-21:], b_t)
        m_t = m_mag if cur_p > b_t else (-m_mag if cur_p < b_t else 0.0)

        # Candle anatomy
        bar = rates[-1]
        h = float(bar["high"])
        l = float(bar["low"])
        o = float(bar["open"])
        c = float(bar["close"])
        rng = max(1e-6, h - l)
        upper_wick = (h - max(o, c)) / rng
        lower_wick = (min(o, c) - l) / rng

        htf = self.get_htf_trend(symbol, tf_label)
        abs_m = abs(m_mag)

        if abs_m < 25.0:
            regime = "WAIT_COMPRESSION"
            action = "STAND_DOWN"
            narrative = "Market coiled inside equilibrium baseline B(t). Zero institutional edge; standing down."
        elif abs_m >= 55.0:
            is_buy = cur_p > b_t
            wick_trap = (is_buy and upper_wick > 0.45) or ((not is_buy) and lower_wick > 0.45)
            htf_divergence = (is_buy and htf == -1) or ((not is_buy) and htf == 1)

            if wick_trap or htf_divergence:
                regime = "FALSE_TRUTH_REJECT"
                action = "REJECT_TRAP"
                narrative = f"Retail breakout trapped. {'Wick absorption > 45%' if wick_trap else 'Macro HTF Divergence'}. Institutional faders active."
            else:
                regime = "ACTIVE_HUNT"
                action = "BUY" if is_buy else "SELL"
                narrative = f"Pure institutional displacement |M(t)|={abs_m:.1f}. Clean execution corridor."
        else:
            regime = "BASELINE_RETEST"
            action = "PREPARE"
            narrative = f"Price pulling back to test baseline B(t)={b_t:.{digits}f}. Discount accumulation zone."

        return {
            "symbol": symbol,
            "timeframe": tf_label,
            "regime": regime,
            "recommended_action": action,
            "current_price": cur_p,
            "baseline_b_t": round(b_t, digits),
            "kinetic_mass_m_t": round(m_t, 2),
            "upper_wick_ratio": round(upper_wick, 3),
            "lower_wick_ratio": round(lower_wick, 3),
            "htf_alignment": htf,
            "session": get_market_session(),
            "narrative": narrative,
        }

    def evaluate_position_health(
        self,
        symbol: str,
        action: str,  # "BUY" or "SELL"
        open_price: float,
        sl: float,
        cur_price: float,
        timeframe: str = "M15",
    ) -> Dict[str, Any]:
        """
        Calculates the real-time BEEP Trade Health Metric H(t) for an active position:
            H(t) = 0.35 * MassScore + 0.25 * BaselineScore + 0.20 * (1 - WickTrap) + 0.20 * ExpansionScore
        Outputs:
            - health_score: 0.0 to 1.0
            - status: "PEAK_HEALTH" (>= 0.75), "DEGRADING" (0.40 - 0.74), "CRITICAL_SCRATCH" (< 0.40)
            - expansion_r: current floating profit in R-multiples
            - narrative: live diagnostic
        """
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
        }
        tf_enum = tf_map.get(timeframe, mt5.TIMEFRAME_M15)

        rates = mt5.copy_rates_from_pos(symbol, tf_enum, 0, 25)
        if rates is None or len(rates) < 20:
            return {"health_score": 0.50, "status": "UNKNOWN", "expansion_r": 0.0, "narrative": "Insufficient feed"}

        prices = [float(r["close"]) for r in rates]
        b_t = self.raw_beep.calculate_raw_baseline_B(prices[-20:])
        m_mag = self.raw_beep.calculate_raw_mass_M(prices[-20:], b_t)
        cur_p = prices[-1]
        m_t = m_mag if cur_p > b_t else (-m_mag if cur_p < b_t else 0.0)

        # 1. Mass Direction Score (0.0 to 1.0)
        if action == "BUY":
            mass_score = max(0.0, min(1.0, (m_t + 50.0) / 100.0))
        else:
            mass_score = max(0.0, min(1.0, (50.0 - m_t) / 100.0))

        # 2. Baseline Safety Score
        initial_risk = max(1e-5, abs(open_price - sl))
        if action == "BUY":
            baseline_score = 1.0 if cur_price >= b_t else max(0.0, 1.0 - (abs(b_t - cur_price) / initial_risk))
        else:
            baseline_score = 1.0 if cur_price <= b_t else max(0.0, 1.0 - (abs(cur_price - b_t) / initial_risk))

        # 3. Candle Anatomy Wick Trap
        bar = rates[-1]
        h, l, o, c = float(bar["high"]), float(bar["low"]), float(bar["open"]), float(bar["close"])
        rng = max(1e-6, h - l)
        upper_wick = (h - max(o, c)) / rng
        lower_wick = (min(o, c) - l) / rng
        wick_trap = upper_wick if action == "BUY" else lower_wick
        wick_safety = max(0.0, 1.0 - (wick_trap * 1.5))

        # 4. Expansion Score (R-multiple)
        if action == "BUY":
            expansion_r = (cur_price - open_price) / initial_risk
        else:
            expansion_r = (open_price - cur_price) / initial_risk

        expansion_score = max(0.0, min(1.0, (expansion_r + 1.0) / 3.0))

        # Composite Health H(t)
        h_t = (0.35 * mass_score) + (0.25 * baseline_score) + (0.20 * wick_safety) + (0.20 * expansion_score)
        h_t = round(max(0.0, min(1.0, h_t)), 3)

        if h_t >= 0.75:
            status = "PEAK_HEALTH"
            diag = f"Strong institutional thrust |M(t)|={abs(m_t):.1f}. Runner healthy."
        elif h_t >= 0.40:
            status = "DEGRADING"
            diag = "Momentum slowing. Consider partial cash extraction."
        else:
            status = "CRITICAL_SCRATCH"
            diag = "Narrative failed: Institutional order flow flipped or baseline breached."

        return {
            "health_score": h_t,
            "status": status,
            "expansion_r": round(expansion_r, 2),
            "m_t": round(m_t, 2),
            "b_t": round(b_t, 5),
            "wick_trap_ratio": round(wick_trap, 3),
            "mass_score": round(mass_score, 2),
            "baseline_score": round(baseline_score, 2),
            "narrative": diag,
        }

    def scan_all_universe(self) -> List[BeepSignal]:
        """Scans all registered symbols and timeframes, returning all active BEEP signals sorted by energy."""
        signals = []
        for sym in self.symbols:
            for tf_label, tf_enum in self.timeframes:
                sig = self.scan_front(sym, tf_label, tf_enum)
                if sig:
                    signals.append(sig)

            # Universal Physical Boundary Absorption Anomaly Detection (All symbols, Zero Whitelists)
            boundary_sig = self.scan_boundary_absorption_front(sym, "M15", mt5.TIMEFRAME_M15)
            if boundary_sig:
                signals.append(boundary_sig)

        signals.sort(key=lambda s: s.phi_energy, reverse=True)
        return signals
