"""
========================================================================================
           SAJIM V2 RISK — HUMMINGBIRD HARVEST EVALUATOR (v2/risk/hummingbird.py)
========================================================================================
Detects microsecond M1 momentum exhaustion, velocity stalling, and candle momentum
decay at the peak of a trade (+1.5R to +2.85R), banking profits before price retraces
to the trailing stop.
Modular Architecture: Strictly < 150 lines.
========================================================================================
"""

from typing import Any, Tuple
import MetaTrader5 as mt5


class HummingbirdEvaluator:
    """Evaluates whether an active winning trade has hit peak momentum exhaustion."""

    @staticmethod
    def check_exhaustion(pos: Any, profit_r: float, sym_info: Any) -> Tuple[bool, str]:
        """
        Evaluates active winning position (+1.50R <= profit_r <= +2.85R) for M1 momentum exhaustion.
        Returns: (should_harvest, reason)
        """
        if profit_r < 1.50:
            return False, ""

        rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M1, 0, 25)
        if rates is None or len(rates) < 10:
            return False, ""

        is_buy = (pos.type == mt5.POSITION_TYPE_BUY or pos.type == 0)
        cur_price = sym_info.bid if is_buy else sym_info.ask
        point = sym_info.point or 0.00001
        min_range = max(point * 5, 0.00002)

        bar_0 = rates[-1]
        bar_1 = rates[-2]
        bar_2 = rates[-3]

        rng_0 = max(min_range, float(bar_0['high'] - bar_0['low']))
        rng_1 = max(min_range, float(bar_1['high'] - bar_1['low']))

        if is_buy:
            wick_0 = float(bar_0['high'] - max(bar_0['open'], bar_0['close']))
            wick_ratio_0 = wick_0 / rng_0
            wick_1 = float(bar_1['high'] - max(bar_1['open'], bar_1['close']))
            wick_ratio_1 = wick_1 / rng_1

            body_0 = float(bar_0['close'] - bar_0['open'])
            body_1 = float(bar_1['close'] - bar_1['open'])
            body_2 = float(bar_2['close'] - bar_2['open'])

            adverse_close_0 = (body_0 < 0)
            adverse_close_1 = (body_1 < 0)
            micro_struct_break = (float(bar_0['close']) < float(bar_1['low']) and adverse_close_0)
        else:
            wick_0 = float(min(bar_0['open'], bar_0['close']) - bar_0['low'])
            wick_ratio_0 = wick_0 / rng_0
            wick_1 = float(min(bar_1['open'], bar_1['close']) - bar_1['low'])
            wick_ratio_1 = wick_1 / rng_1

            body_0 = float(bar_0['open'] - bar_0['close'])
            body_1 = float(bar_1['open'] - bar_1['close'])
            body_2 = float(bar_2['open'] - bar_2['close'])

            adverse_close_0 = (float(bar_0['close']) > float(bar_0['open']))
            adverse_close_1 = (float(bar_1['close']) > float(bar_1['open']))
            micro_struct_break = (float(bar_0['close']) > float(bar_1['high']) and adverse_close_0)

        # Baseline & ATR Computation (14-bar M1 Window)
        closes_14 = [float(r['close']) for r in rates[-14:]]
        m1_baseline = sum(closes_14) / len(closes_14)
        m1_tr = [
            max(
                float(rates[i]['high'] - rates[i]['low']),
                abs(float(rates[i]['high'] - rates[i-1]['close'])),
                abs(float(rates[i]['low'] - rates[i-1]['close']))
            )
            for i in range(-14, 0)
        ]
        m1_atr = max(sum(m1_tr) / len(m1_tr), point * 5)
        dist_atr = ((cur_price - m1_baseline) if is_buy else (m1_baseline - cur_price)) / m1_atr

        # Volume Profile Analysis
        vols = [float(r['tick_volume']) for r in rates[-10:]]
        avg_vol = sum(vols) / len(vols) if vols else 1.0
        vol_0 = float(bar_0['tick_volume'])
        vol_1 = float(bar_1['tick_volume'])

        # 1. Counter-Wick Supply/Demand Absorption
        if profit_r >= 1.80 and wick_ratio_0 >= 0.35:
            return True, f"M1 Counter-Wick Rejection ({wick_ratio_0*100:.1f}%) at +{profit_r:.2f}R"
        if profit_r >= 1.50 and wick_ratio_0 >= 0.45:
            return True, f"M1 Severe Rejection Wick ({wick_ratio_0*100:.1f}%) at +{profit_r:.2f}R"
        if profit_r >= 1.50 and wick_ratio_1 >= 0.40 and adverse_close_0:
            return True, f"M1 Peak Wick Invalidation ({wick_ratio_1*100:.1f}%) at +{profit_r:.2f}R"

        # 2. Candle Momentum Decay & Velocity Stalling
        if profit_r >= 1.50 and adverse_close_0 and adverse_close_1:
            return True, f"M1 Consecutive Momentum Decay (2 Adverse Bars) at +{profit_r:.2f}R"
        if profit_r >= 1.50 and body_2 > (m1_atr * 0.80) and body_1 < (body_2 * 0.30) and adverse_close_0:
            return True, f"M1 Velocity Stalling at +{profit_r:.2f}R"

        # 3. Micro-Structure Break
        if profit_r >= 1.50 and micro_struct_break:
            target_side = "Prev M1 Low" if is_buy else "Prev M1 High"
            return True, f"M1 Micro-Structure Break ({target_side}) at +{profit_r:.2f}R"

        # 4. Baseline Envelope Overextension Stretch
        if profit_r >= 1.70 and dist_atr >= 2.20 and (wick_ratio_0 >= 0.25 or adverse_close_0):
            return True, f"M1 Baseline Envelope Stretch ({dist_atr:.1f}x ATR) at +{profit_r:.2f}R"

        # 5. Climax Volume Absorption
        if profit_r >= 1.50 and (vol_0 >= 2.0 * avg_vol or vol_1 >= 2.0 * avg_vol):
            if wick_ratio_0 >= 0.30 or wick_ratio_1 >= 0.30 or adverse_close_0:
                peak_vol = max(vol_0, vol_1)
                return True, f"M1 Climax Volume Absorption ({peak_vol/avg_vol:.1f}x) at +{profit_r:.2f}R"

        # 6. Peak Defense Stall
        if profit_r >= 2.20 and (adverse_close_0 or wick_ratio_0 >= 0.25):
            return True, f"M1 Peak Profit Defense Stall at +{profit_r:.2f}R"

        return False, ""
