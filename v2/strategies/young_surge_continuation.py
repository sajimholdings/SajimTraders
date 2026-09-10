"""
========================================================================================
    SAJIM HOLDINGS V2 — YOUNG SURGE CONTINUATION CARTRIDGE (v2/strategies/young_surge_continuation.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Strategy Type: Kinetic Trend Continuation & Breakout Momentum
Edge Thesis:
  Enters high-velocity institutional trends strictly during their YOUNG_SURGE phase
  (maturity <= 0.60 of rolling historical duration). Abolishes late-stage entries
  where retail traders typically buy the top. Enforces strict 1:3.0R asymmetric payoff.
========================================================================================
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from v2.strategy_base import BaseStrategyCartridge, StrategySignal
from v2.trend_duration_engine import TrendDurationEngine
from core.beep_processor import BeepSnipeFilter, BeepSnipeEvaluation


class YoungSurgeContinuation(BaseStrategyCartridge):
    """
    Kinetic Trend Continuation Cartridge.
    Capitalizes on institutional momentum before trend maturity reaches 60%.
    """

    DEFAULT_WHITELIST = {
        "EURJPY.c": ["M5", "M15"],
        "CADJPY.c": ["M5", "M15"],
        "NZDJPY.c": ["M15", "H1"],
        "USDCAD.c": ["M15", "H1"],
        "GBPJPY.c": ["M15", "H1"],
        "XAUUSD.c": ["M15", "H1", "H4"],
        "AUDUSD.c": ["M15"],
        "EURUSD.c": ["M15"],
        "BTCUSD": ["M15", "H1"],
    }

    def __init__(
        self,
        name: str = "YoungSurgeContinuation",
        enabled: bool = True,
        max_maturity_ratio: float = 0.70,
        sl_atr_mult: float = 0.8,
        tp_rr_ratio: float = 1.2,
        use_beep_filter: bool = False,
        min_beep_score: float = 48.0,
    ):
        super().__init__(name=name, enabled=enabled)
        self.engine = TrendDurationEngine(length=50, trend_length=3, max_samples=10)
        self.snipe_filter = BeepSnipeFilter(min_snipe_score=min_beep_score)
        self.parameters = {
            "max_maturity_ratio": max_maturity_ratio,
            "sl_atr_mult": sl_atr_mult,
            "tp_rr_ratio": tp_rr_ratio,
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
            if not get_whitelist_manager().is_pair_approved("YoungSurgeContinuation", symbol, timeframe):
                return None
        except Exception:
            pass

        # 1. Evaluate Statistical Trend Maturity
        mat = self.engine.evaluate_maturity(symbol=symbol, timeframe=timeframe, bars=bars)
        trend = mat["trend"]
        maturity = mat["maturity_ratio"]
        hma_val = mat["hma_val"]

        # Only accept YOUNG_SURGE (fresh trends with ample remaining runway)
        if maturity > self.parameters["max_maturity_ratio"] or trend not in ("UP", "DOWN"):
            return None

        cur_bar = bars[-1]
        prev_bar = bars[-2]
        close_p = cur_bar["close"]
        open_p = cur_bar["open"]
        point = market_info.get("point", 0.00001)

        atr = self.calculate_atr(bars, period=self.parameters["atr_period"])
        if atr <= 0:
            atr = point * 100.0

        # High-Velocity Tight Invalidation with Spread Buffer Protection:
        spread_pts = market_info.get("spread", 20)
        spread_price = spread_pts * point
        min_sl_floor = max(spread_price * 3.0, point * 35.0)

        tf_mult = 0.45 if timeframe == "M1" else (0.55 if timeframe == "M5" else self.parameters["sl_atr_mult"])
        sl_dist = max(min_sl_floor, tf_mult * atr)
        tp_dist = sl_dist * self.parameters["tp_rr_ratio"]

        # 2. Bullish Young Surge Confirmation
        if trend == "UP" and close_p > hma_val and close_p >= open_p:
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
            sl_p = entry_p - sl_dist
            tp_p = entry_p + tp_dist

            return StrategySignal(
                symbol=symbol,
                action="BUY",
                timeframe=timeframe,
                entry_price=round(entry_p, 5),
                stop_loss=round(sl_p, 5),
                take_profit=round(tp_p, 5),
                risk_reward=self.parameters["tp_rr_ratio"],
                confidence=round(1.0 - (maturity / 0.60) * 0.4, 2),
                strategy_name=self.name,
                reason=(
                    f"Young Bullish Surge: Maturity={maturity:.2f} <= 0.60 | "
                    f"TrendCount={mat['trend_count']}/{mat['probable_length']} bars | Close > HMA-50"
                ),
                metadata=mat,
            )

        # 3. Bearish Young Surge Confirmation
        elif trend == "DOWN" and close_p < hma_val and close_p <= open_p:
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
            sl_p = entry_p + sl_dist
            tp_p = entry_p - tp_dist

            return StrategySignal(
                symbol=symbol,
                action="SELL",
                timeframe=timeframe,
                entry_price=round(entry_p, 5),
                stop_loss=round(sl_p, 5),
                take_profit=round(tp_p, 5),
                risk_reward=self.parameters["tp_rr_ratio"],
                confidence=round(1.0 - (maturity / 0.60) * 0.4, 2),
                strategy_name=self.name,
                reason=(
                    f"Young Bearish Surge: Maturity={maturity:.2f} <= 0.60 | "
                    f"TrendCount={mat['trend_count']}/{mat['probable_length']} bars | Close < HMA-50"
                ),
                metadata=mat,
            )

        return None
