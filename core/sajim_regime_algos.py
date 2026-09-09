"""
Sajim Holdings — Specialized Regime Execution Algorithms (sajim_regime_algos.py)
Philosophy:
  BEEP does the Art (detects the market anomaly / "mahali wezi wako").
  Sajim Holdings provides the Execution Architecture: specialized algorithms tailored to
  distinct market regimes, speeds, and account types (Seed/Cent, Prop Firm, Institutional).
"""

import os
import sys
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class AccountProfile:
    """Configures risk parameters based on account tier and capital structure."""

    @staticmethod
    def get_profile(account_type: str = "CENT_SEED_400", balance: float = 400.0) -> Dict[str, Any]:
        account_type = account_type.upper()
        if account_type in ["CENT", "CENT_SEED_400"]:
            return {
                "name": "Headway Cent Seed ($400 = 40,000 USC)",
                "max_risk_usd": 6.0,  # Risks 6 cents per trade on 0.01 cent lot
                "max_consecutive_losses": 6,
                "circuit_breaker_hours": 4,
                "rr_target": 3.5,
                "lot_multiplier": 1.0,
                "indestructible_buffer": 6666,  # 6,666 losses to blow
            }
        elif account_type in ["PROP", "PROP_FIRM"]:
            return {
                "name": "Prop Firm Challenge ($50k - $200k)",
                "max_risk_usd": balance * 0.005,  # Strict 0.5% risk
                "max_consecutive_losses": 3,
                "circuit_breaker_hours": 12,
                "rr_target": 3.0,
                "lot_multiplier": 1.0,
                "indestructible_buffer": 200,
            }
        else:  # INSTITUTIONAL_SCALE
            return {
                "name": "Institutional High-Net-Worth ($10k+)",
                "max_risk_usd": balance * 0.015,  # 1.5% risk
                "max_consecutive_losses": 4,
                "circuit_breaker_hours": 6,
                "rr_target": 4.0,
                "lot_multiplier": 2.5,
                "indestructible_buffer": 66,
            }


class SajimExecutionSuite:
    """
    Translates BEEP's physical narrative into specialized algorithmic tactics:
      1. DIAMOND_EXPANSION -> Momentum Jet Rider (1:4 R:R with trailing BE)
      2. CERTIFIED_TREND   -> Baseline Limit Harvester (Buy/Sell dips to B(t))
      3. LIQUIDITY_TRAP    -> Thief Fader (Exploits trapped retail wicks)
      4. COMPRESSION       -> Ammunition Lockout (0 trades, zero spread bleed)
    """

    def __init__(self, account_type: str = "CENT_SEED_400", initial_balance: float = 400.0):
        self.profile = AccountProfile.get_profile(account_type, initial_balance)

    def formulate_algo_order(
        self,
        symbol: str,
        narrative: Dict[str, Any],
        current_bar: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Receives BEEP's narrative and dispatches the specialized algo execution tactic.
        """
        regime = narrative.get("regime", "COMPRESSION_CONSOLIDATION")
        quality = narrative.get("quality", "STANDBY")
        direction = narrative.get("trade_action", "STAND_BY")
        b_t = narrative.get("b_t", current_bar["close"])
        m_t = narrative.get("m_t", 20.0)
        cur_price = current_bar["close"]
        high_p = current_bar["high"]
        low_p = current_bar["low"]
        open_p = current_bar["open"]
        tot_range = max(1e-4, high_p - low_p)

        # Check for Wick Sweep (The "Thief" / Liquidity Trap)
        upper_wick = high_p - max(open_p, cur_price)
        lower_wick = min(open_p, cur_price) - low_p
        is_upper_sweep = (upper_wick / tot_range) > 0.45
        is_lower_sweep = (lower_wick / tot_range) > 0.45

        # ---------------------------------------------------------------------
        # TACTIC 1: THE THIEF FADER (Counter-Trend Retail Trap Liquidity Exploit)
        # ---------------------------------------------------------------------
        # When retail got trapped buying the top wick, we trade WITH the smart money (SELL)!
        if is_upper_sweep and cur_price > b_t:
            invalidation = high_p + (tot_range * 0.20)
            target = b_t  # Target mean-reversion to baseline
            risk = invalidation - cur_price
            reward = cur_price - target
            rr = round(reward / max(1e-4, risk), 2)
            if rr >= 2.0:
                return {
                    "tactic": "THIEF_FADER_SHORT",
                    "tactic_desc": "Retail FOMO buyers trapped on upper wick. Fading the sweep back to Baseline B(t).",
                    "action": "SELL",
                    "entry_type": "MARKET",
                    "entry_price": cur_price,
                    "stop_loss": round(invalidation, 4),
                    "take_profit": round(target, 4),
                    "rr_ratio": f"1:{rr}",
                    "confidence": "HIGH_LIQUIDITY_CAPTURE",
                }

        # When retail got trapped panic-selling the bottom wick, we BUY!
        if is_lower_sweep and cur_price < b_t:
            invalidation = low_p - (tot_range * 0.20)
            target = b_t
            risk = cur_price - invalidation
            reward = target - cur_price
            rr = round(reward / max(1e-4, risk), 2)
            if rr >= 2.0:
                return {
                    "tactic": "THIEF_FADER_LONG",
                    "tactic_desc": "Retail panic dump absorbed by institutional buy limits. Fading sweep back to Baseline B(t).",
                    "action": "BUY",
                    "entry_type": "MARKET",
                    "entry_price": cur_price,
                    "stop_loss": round(invalidation, 4),
                    "take_profit": round(target, 4),
                    "rr_ratio": f"1:{rr}",
                    "confidence": "HIGH_LIQUIDITY_CAPTURE",
                }

        # ---------------------------------------------------------------------
        # TACTIC 2: MOMENTUM JET RIDER (Diamond Expansion M(t) >= 75)
        # ---------------------------------------------------------------------
        if quality == "DIAMOND" and direction in ["BUY", "SELL"]:
            risk_dist = abs(cur_price - b_t)
            if direction == "BUY":
                sl = round(b_t - (risk_dist * 0.20), 4)
                tp1 = round(cur_price + (risk_dist * 2.0), 4)
                tp2 = round(cur_price + (risk_dist * 4.0), 4)
            else:
                sl = round(b_t + (risk_dist * 0.20), 4)
                tp1 = round(cur_price - (risk_dist * 2.0), 4)
                tp2 = round(cur_price - (risk_dist * 4.0), 4)

            return {
                "tactic": "DIAMOND_JET_RIDER",
                "tactic_desc": "Full institutional volume expansion. Aggressive entry with 1:4 trailing runner.",
                "action": direction,
                "entry_type": "MARKET",
                "entry_price": cur_price,
                "stop_loss": sl,
                "take_profit_1": tp1,
                "take_profit_2": tp2,
                "rr_ratio": "1:4.0",
                "confidence": "LEGENDARY_INSTITUTIONAL_THRUST",
            }

        # ---------------------------------------------------------------------
        # TACTIC 3: BASELINE DIP HARVESTER (Certified Trend M(t) >= 45)
        # ---------------------------------------------------------------------
        if quality == "CERTIFIED" and direction in ["BUY", "SELL"]:
            # Place limit order on retest of B(t) instead of chasing market
            risk_dist = abs(cur_price - b_t)
            if direction == "BUY":
                limit_entry = round(b_t + (risk_dist * 0.20), 4)
                sl = round(b_t - (risk_dist * 0.30), 4)
                tp = round(cur_price + (risk_dist * 2.5), 4)
            else:
                limit_entry = round(b_t - (risk_dist * 0.20), 4)
                sl = round(b_t + (risk_dist * 0.30), 4)
                tp = round(cur_price - (risk_dist * 2.5), 4)

            return {
                "tactic": "BASELINE_DIP_HARVESTER",
                "tactic_desc": "Structured trend. Placing precision limit order near Baseline B(t) to maximize R:R.",
                "action": direction,
                "entry_type": "LIMIT",
                "entry_price": limit_entry,
                "stop_loss": sl,
                "take_profit": tp,
                "rr_ratio": "1:3.0",
                "confidence": "STRUCTURED_DISCIPLINED_ENTRY",
            }

        # ---------------------------------------------------------------------
        # TACTIC 4: AMMUNITION LOCKOUT (Compression / Standby)
        # ---------------------------------------------------------------------
        return {
            "tactic": "AMMUNITION_LOCKOUT",
            "tactic_desc": "Market is in dead compression (chop). No trade deployed. Ammunition preserved.",
            "action": "STAND_BY",
            "entry_type": "NONE",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "rr_ratio": "N/A",
            "confidence": "ZERO_CAPITAL_EXPOSURE",
        }


class SajimChameleonClassifier:
    """
    Dual-Regime Chameleon Engine:
    Distinguishes RANGE_COMPRESSION (The Hummingbird) vs TREND_EXPANSION (The Cheetah)
    using Equation 14: Dynamic Compression Ratio kappa_regime.
    """

    @staticmethod
    def calculate_compression_ratio(symbol: str, cur_price: float = 0.0, m_t: float = 0.0) -> Tuple[float, str]:
        """
        Computes the compression ratio kappa_regime for a given symbol.
        Returns (kappa_regime, regime_label) where regime_label is
        'RANGE_COMPRESSION' or 'TREND_EXPANSION'.
        """
        import MetaTrader5 as mt5
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 16)
        rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 16)

        if rates_m15 is None or len(rates_m15) < 14:
            # Fallback based purely on Kinetic Mass M(t)
            if abs(m_t) >= 70.0:
                return 1.0, "TREND_EXPANSION"
            return 0.50, "RANGE_COMPRESSION"

        # Calculate True Range for M15
        tr_m15 = [max(r["high"] - r["low"], abs(r["high"] - r["close"]), abs(r["low"] - r["close"])) for r in rates_m15[-14:]]
        atr_m15 = sum(tr_m15) / max(1, len(tr_m15))

        # Calculate True Range for H4
        if rates_h4 is not None and len(rates_h4) >= 14:
            tr_h4 = [max(r["high"] - r["low"], abs(r["high"] - r["close"]), abs(r["low"] - r["close"])) for r in rates_h4[-14:]]
            atr_h4 = sum(tr_h4) / max(1, len(tr_h4))
        else:
            atr_h4 = atr_m15 * 4.0

        # Baseline slope |dB/dt| approximation
        closes = [r["close"] for r in rates_m15]
        b_slope = abs(closes[-1] - closes[-7]) / max(1e-6, atr_m15)

        norm_h4_quarter = max(1e-6, atr_h4 / 4.0)
        kappa = (atr_m15 / norm_h4_quarter) * (1.0 + min(1.0, b_slope))

        # Decision threshold:
        if kappa < 0.75 and abs(m_t) < 65.0:
            return round(kappa, 3), "RANGE_COMPRESSION"
        return round(kappa, 3), "TREND_EXPANSION"

    @staticmethod
    def get_regime_params(regime: str) -> Dict[str, Any]:
        """Returns dynamic execution constraints based on active regime."""
        if regime == "RANGE_COMPRESSION":
            return {
                "name": "HUMMINGBIRD_RANGE_HARVESTER",
                "max_concurrent_positions": 4,
                "milk_trigger_r": 0.35,
                "milk_cash_usd": 1.50,
                "milk_fraction": 0.70,
                "trailing_be_buffer_points": 10,
                "stall_bar_limit": 4,
                "description": "Compression range active. Micro-harvesting 70% cash at +0.35R, exposure capped to 4.",
            }
        else:
            return {
                "name": "CHEETAH_TREND_EXPANSION",
                "max_concurrent_positions": 15,
                "milk_trigger_r": 1.50,
                "milk_cash_usd": 3.50,
                "milk_fraction": 0.50,
                "trailing_be_buffer_points": 20,
                "stall_bar_limit": 10,
                "description": "Institutional expansion active. 50% cash milk at +1.5R, trailing runner hunting +5.0R.",
            }

