"""
Sajim Holdings — BEEP Institutional Narrative Engine (beep_narrative.py)
Transforms BEEP's Universal Equations into Actionable Market Narratives,
High-Asymmetry Risk:Reward Setups (1:3 to 1:5), and VIP Channel Broadcasts.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Tuple

# Add local path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from beep_core import BeepCoreEngine


class BeepNarrativeEngine:
    """
    Translates mathematical deviation states into institutional market narratives.
    Formulates high-asymmetry trading edges (1:3 to 1:5 R:R) for MT5 execution
    and VIP channel signal broadcasts.
    """

    def __init__(self):
        self.core = BeepCoreEngine()

    def generate_narrative(
        self,
        symbol: str,
        prices: List[float],
        current_spread: float = 0.0,
        account_balance: float = 400.0,
    ) -> Dict[str, Any]:
        """
        Generates the institutional market narrative for any pair.
        Normalizes pip-scale vs dollar-scale automatically.
        """
        if len(prices) < 10:
            return {
                "status": "INSUFFICIENT_DATA",
                "narrative_summary": "Awaiting market history (minimum 10 bars required)...",
                "broadcast_message": f"📊 *BEEP INTELLIGENCE: {symbol}*\nStatus: Collecting market ticks...",
            }

        # 1. Detect Asset Class & Point Scale
        is_fx = ("EUR" in symbol or "GBP" in symbol or "USD" in symbol) and ("XAU" not in symbol and "DJI" not in symbol and "US30" not in symbol)
        is_jpy = "JPY" in symbol
        pip_factor = 100.0 if is_jpy else (10000.0 if is_fx else 1.0)

        # 2. Run BEEP Multi-Style Analysis
        sig = self.core.analyze_market(prices, style="INTRADAY", symbol=symbol, account_balance=account_balance)

        m_t = sig["M_t"]
        b_t = sig["B_t"]
        lambda_pct = sig["Lambda_pct"]
        direction = sig["direction"]
        current_price = sig["current_price"]
        tier = sig["tier"]

        # 3. Formulate Institutional Market Regime
        if m_t >= 75.0 and lambda_pct >= 20.0:
            regime = "INSTITUTIONAL_EXPANSION"
            regime_desc = "Aggressive institutional order flow in control. High kinetic momentum."
            quality = "DIAMOND"
        elif m_t >= 45.0 and lambda_pct >= 12.0:
            regime = "STRUCTURED_TREND_FLOW"
            regime_desc = "Consistent directional drift with valid multi-timeframe backing."
            quality = "CERTIFIED"
        elif m_t < 25.0 and lambda_pct < 10.0:
            regime = "COMPRESSION_CONSOLIDATION"
            regime_desc = "Market is in dead equilibrium. Stand by — do not trade chop."
            quality = "STANDBY"
        else:
            regime = "POTENTIAL_LIQUIDITY_REVERSAL"
            regime_desc = "Price extended far from baseline with decaying energy. Mean-reversion risk."
            quality = "CAUTION"

        # 4. Formulate High-Asymmetry Execution Edge (1:3 to 1:4 R:R)
        # We use B(t) as the structural invalidation level (Hard Floor/Ceiling)
        risk_dist = abs(current_price - b_t)
        min_risk = (0.0015 if is_fx else (0.20 if is_jpy else 2.50))
        risk_dist = max(risk_dist, min_risk)

        if direction == "BUY" and quality in ["DIAMOND", "CERTIFIED"]:
            entry_price = current_price
            invalidation_sl = round(b_t - (risk_dist * 0.25), 4)
            target_1 = round(entry_price + (risk_dist * 2.0), 4)  # 1:2 R:R
            target_2 = round(entry_price + (risk_dist * 3.5), 4)  # 1:3.5 R:R
            rr_ratio = "1:3.5"
            trade_action = "BUY"
        elif direction == "SELL" and quality in ["DIAMOND", "CERTIFIED"]:
            entry_price = current_price
            invalidation_sl = round(b_t + (risk_dist * 0.25), 4)
            target_1 = round(entry_price - (risk_dist * 2.0), 4)
            target_2 = round(entry_price - (risk_dist * 3.5), 4)
            rr_ratio = "1:3.5"
            trade_action = "SELL"
        else:
            entry_price = current_price
            invalidation_sl = b_t
            target_1 = current_price
            target_2 = current_price
            rr_ratio = "N/A"
            trade_action = "STAND_BY"

        # 5. Position Sizing for Account Flipping (Controlled Aggression)
        # Risk exactly $15 on a $400 account (3.75%) targeting +$50 to +$60 per win
        target_risk_usd = 15.0
        contract = 100.0 if "XAU" in symbol else (100000.0 if is_fx else 1.0)
        lot_size = round(max(0.01, min(0.25, target_risk_usd / (risk_dist * contract))), 2)

        # 6. Formulate Broadcast Message for Tete's Channel / WhatsApp
        broadcast_text = (
            f"🏛️ *BEEP INSTITUTIONAL NARRATIVE: {symbol}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Regime:* {regime} ({quality})\n"
            f"📖 *Context:* {regime_desc}\n\n"
            f"🧭 *Action:* *{trade_action}*\n"
            f"📍 *Entry:* `{entry_price}`\n"
            f"🛑 *Invalidation (Floor):* `{invalidation_sl}`\n"
            f"🎯 *Target 1:* `{target_1}` (Take 50% profit)\n"
            f"🚀 *Target 2:* `{target_2}` (Runner)\n"
            f"⚖️ *Risk:Reward:* *{rr_ratio}* | Lot: `{lot_size}`\n\n"
            f"⚡ *Kinetic Mass M(t):* `{m_t}` | Energy: `{lambda_pct}%`\n"
            f"🔒 *BEEP Protocol — Sajim Holdings*"
        )

        return {
            "symbol": symbol,
            "regime": regime,
            "quality": quality,
            "trade_action": trade_action,
            "entry_price": entry_price,
            "invalidation_sl": invalidation_sl,
            "target_1": target_1,
            "target_2": target_2,
            "rr_ratio": rr_ratio,
            "lot_size": lot_size,
            "m_t": m_t,
            "b_t": b_t,
            "lambda_pct": lambda_pct,
            "narrative_summary": regime_desc,
            "broadcast_message": broadcast_text,
        }
