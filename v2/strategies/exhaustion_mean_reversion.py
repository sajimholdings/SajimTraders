"""
========================================================================================
 SAJIM HOLDINGS V2 — EXHAUSTION MEAN REVERSION CARTRIDGE (v2/strategies/exhaustion_mean_reversion.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Strategy Type: Trend Exhaustion & Baseline Mean Reversion
Edge Thesis:
  Identifies statistically dying trends where duration has exceeded historical life expectancy
  (maturity >= 1.00) and price has overextended away from the Hull Moving Average baseline
  (>= 1.2x ATR). Snipes the institutional equilibrium snapback toward the baseline with
  asymmetric 1:2.0R payoff.
========================================================================================
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from v2.strategy_base import BaseStrategyCartridge, StrategySignal
from v2.trend_duration_engine import TrendDurationEngine
from core.beep_processor import BeepSnipeFilter, BeepSnipeEvaluation


class ExhaustionMeanReversion(BaseStrategyCartridge):
    """
    Exhaustion Mean Reversion Cartridge.
    Fades terminal trend climaxes back toward equilibrium HMA-50.
    """

    # Proven positive-expectancy fronts for mean reversion from empirical audit
    REVERSION_UNIVERSE = {
        "EURUSD.c": ["M15", "H1"],
        "USDCAD.c": ["H1"],
        "XAUUSD.c": ["M15", "H1"],
        "GBPJPY.c": ["H1"],
        "USDJPY.c": ["H1"],
        "BTCUSD": ["H1"],
    }

    def __init__(
        self,
        name: str = "ExhaustionMeanReversion",
        enabled: bool = True,
        min_maturity_ratio: float = 1.00,
        min_stretch_atr_mult: float = 1.20,
        sl_atr_mult: float = 1.50,
        min_rr_ratio: float = 1.50,
        use_beep_filter: bool = False,
        min_beep_score: float = 50.0,
    ):
        super().__init__(name=name, enabled=enabled)
        self.engine = TrendDurationEngine(length=50, trend_length=3, max_samples=10)
        self.snipe_filter = BeepSnipeFilter(min_snipe_score=min_beep_score)
        self.parameters = {
            "min_maturity_ratio": min_maturity_ratio,
            "min_stretch_atr_mult": min_stretch_atr_mult,
            "sl_atr_mult": sl_atr_mult,
            "min_rr_ratio": min_rr_ratio,
            "atr_period": 14,
            "use_beep_filter": use_beep_filter,
            "min_beep_score": min_beep_score,
        }

    @staticmethod
    def calculate_atr(bars: List[Dict[str, Any]], period: int = 14) -> float:
        """Calculates Average True Range (ATR) over historical bars."""
        if len(bars) < period + 1:
            return 0.0010
        tr_list = []
        for i in range(1, len(bars)):
            h = bars[i]["high"]
            l = bars[i]["low"]
            prev_c = bars[i - 1]["close"]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)
        return float(np.mean(tr_list[-period:]))

    def evaluate(
        self,
        symbol: str,
        timeframe: str,
        bars: List[Dict[str, Any]],
        market_info: Dict[str, Any],
    ) -> Optional[StrategySignal]:
        if not self.enabled or len(bars) < 65:
            return None

        # Verify against master centralized whitelist
        try:
            from core.whitelist_manager import get_whitelist_manager
            if not get_whitelist_manager().is_pair_approved("ExhaustionMeanReversion", symbol, timeframe):
                return None
        except Exception:
            pass

        # 1. Evaluate Trend Maturity
        mat = self.engine.evaluate_maturity(symbol=symbol, timeframe=timeframe, bars=bars)
        trend = mat["trend"]
        maturity = mat["maturity_ratio"]
        hma_val = mat["hma_val"]

        # Only accept EXHAUSTED phase (maturity >= 1.00)
        if maturity < self.parameters["min_maturity_ratio"] or trend not in ("UP", "DOWN"):
            return None

        cur_bar = bars[-1]
        close_p = cur_bar["close"]
        point = market_info.get("point", 0.00001)

        atr = self.calculate_atr(bars, period=self.parameters["atr_period"])
        if atr <= 0:
            atr = point * 100.0

        dist_from_hma = abs(close_p - hma_val)
        min_stretch = self.parameters["min_stretch_atr_mult"] * atr

        # Ensure price is adequately stretched away from HMA baseline
        if dist_from_hma < min_stretch:
            return None

        # 2. Bullish Trend Exhaustion -> FADE SHORT (SELL Snapback to HMA)
        if trend == "UP" and close_p > hma_val:
            if self.parameters.get("use_beep_filter", False):
                eval_res = self.snipe_filter.evaluate(
                    symbol=symbol,
                    timeframe=timeframe,
                    action="SELL",
                    bars=bars,
                    strategy_name=self.name,
                    market_info=market_info,
                )
                if not eval_res.passed:
                    return None
                mat["beep_snipe"] = eval_res.to_dict()

            entry_p = close_p
            sl_p = entry_p + (self.parameters["sl_atr_mult"] * atr)
            tp_p = hma_val  # Target is snapback to baseline equilibrium

            risk_dist = abs(sl_p - entry_p)
            reward_dist = abs(entry_p - tp_p)
            rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

            if rr < self.parameters["min_rr_ratio"]:
                return None

            return StrategySignal(
                symbol=symbol,
                action="SELL",
                timeframe=timeframe,
                entry_price=round(entry_p, 5),
                stop_loss=round(sl_p, 5),
                take_profit=round(tp_p, 5),
                risk_reward=rr,
                confidence=round(min(1.0, (maturity / 1.50) * 0.9), 2),
                strategy_name=self.name,
                reason=(
                    f"Exhausted Bull Trend FADE: Maturity={maturity:.2f} >= 1.00 | "
                    f"Stretch={dist_from_hma/atr:.1f}x ATR | Snapback target: HMA-50 ({hma_val:.5f})"
                ),
                metadata=mat,
            )

        # 3. Bearish Trend Exhaustion -> FADE LONG (BUY Snapback to HMA)
        elif trend == "DOWN" and close_p < hma_val:
            if self.parameters.get("use_beep_filter", False):
                eval_res = self.snipe_filter.evaluate(
                    symbol=symbol,
                    timeframe=timeframe,
                    action="BUY",
                    bars=bars,
                    strategy_name=self.name,
                    market_info=market_info,
                )
                if not eval_res.passed:
                    return None
                mat["beep_snipe"] = eval_res.to_dict()

            entry_p = close_p
            sl_p = entry_p - (self.parameters["sl_atr_mult"] * atr)
            tp_p = hma_val  # Target is snapback to baseline equilibrium

            risk_dist = abs(entry_p - sl_p)
            reward_dist = abs(tp_p - entry_p)
            rr = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

            if rr < self.parameters["min_rr_ratio"]:
                return None

            return StrategySignal(
                symbol=symbol,
                action="BUY",
                timeframe=timeframe,
                entry_price=round(entry_p, 5),
                stop_loss=round(sl_p, 5),
                take_profit=round(tp_p, 5),
                risk_reward=rr,
                confidence=round(min(1.0, (maturity / 1.50) * 0.9), 2),
                strategy_name=self.name,
                reason=(
                    f"Exhausted Bear Trend FADE: Maturity={maturity:.2f} >= 1.00 | "
                    f"Stretch={dist_from_hma/atr:.1f}x ATR | Snapback target: HMA-50 ({hma_val:.5f})"
                ),
                metadata=mat,
            )

        return None
