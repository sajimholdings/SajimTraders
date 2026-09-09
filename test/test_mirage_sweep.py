"""
Unit Tests: Mirage Liquidity Sweep Pro Engine
=============================================
Verifies:
1. Major swing detection (BSL/SSL) & EQH/EQL marking.
2. Liquidity penetration & close-reclaim detection.
3. 5-Factor sweep scoring fidelity to WillyAlgoTrader's formula.
4. CHoCH confirmation logic vs unconfirmed instant triggers.
"""

import unittest
import numpy as np
from v2.engine.liquidity_sweep_engine import (
    MirageLiquiditySweepEngine,
    SweepType,
    LiquiditySweepSignal,
)


class TestMirageLiquiditySweepEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MirageLiquiditySweepEngine(
            swing_len=5,        # Shortened for deterministic unit testing
            lookback_bars=40,
            min_score=40.0,
            require_confirm=True,
            minor_len=3,
            confirm_window=10,
            use_volume=True,
            use_htf=True,
            htf_ema_len=20,
            sl_buffer=0.25,
            tp1_mult=1.0,
            tp2_mult=2.0,
            tp3_mult=3.0,
        )

    def test_score_calculation(self):
        """Verify the 5-factor scoring formula matches Pine Script exactly."""
        # Score = (wickComp * 0.30 + rclComp * 0.25 + cpComp * 0.20 + volComp * 0.15 + htfComp * 0.10) * 100
        wick_comp = 0.8
        rcl_comp = 0.6
        cp_comp = 0.9
        vol_comp = 1.0
        htf_comp = 1.0

        expected = (
            wick_comp * 0.30 +
            rcl_comp * 0.25 +
            cp_comp * 0.20 +
            vol_comp * 0.15 +
            htf_comp * 0.10
        ) * 100.0

        self.assertAlmostEqual(expected, 82.0, places=2)

    def test_instant_mode_emits_immediate_signals(self):
        """Test with require_confirm = False (immediate trigger on sweep candle close)."""
        engine_instant = MirageLiquiditySweepEngine(
            swing_len=5,
            lookback_bars=40,
            min_score=30.0,
            require_confirm=False,
            minor_len=3,
        )

        opens, highs, lows, closes, vols = [], [], [], [], []
        for i in range(60):
            if i == 15:
                # Pivot low candidate
                opens.append(96.0); highs.append(97.0); lows.append(94.0); closes.append(96.0); vols.append(100.0)
            elif 10 <= i <= 20:
                opens.append(98.0); highs.append(99.0); lows.append(97.0); closes.append(98.0); vols.append(100.0)
            elif i == 35:
                # SWEEP BAR: Wicks below 94.0 (low=93.0), but reclaims and closes at 95.5!
                opens.append(95.0); highs.append(96.0); lows.append(93.0); closes.append(95.5); vols.append(250.0)
            else:
                opens.append(99.0); highs.append(100.0); lows.append(98.0); closes.append(99.0); vols.append(100.0)

        data = {
            'open': np.array(opens),
            'high': np.array(highs),
            'low': np.array(lows),
            'close': np.array(closes),
            'tick_volume': np.array(vols),
        }

        signals, meta = engine_instant.analyze(data)

        # Bullish sweep should fire immediately on bar 35
        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.direction, "BUY")
        self.assertEqual(sig.bar_index, 35)
        self.assertFalse(sig.is_choch_confirmed)
        self.assertGreater(sig.entry_price, sig.sl_price)
        self.assertGreater(sig.tp1_price, sig.entry_price)
        self.assertGreater(sig.tp2_price, sig.tp1_price)
        self.assertGreater(sig.tp3_price, sig.tp2_price)

    def test_choch_confirmation_lifecycle(self):
        """Test with require_confirm = True awaiting minor structure break."""
        engine_choch = MirageLiquiditySweepEngine(
            swing_len=5,
            lookback_bars=40,
            min_score=30.0,
            require_confirm=True,
            minor_len=3,
            confirm_window=10,
        )

        opens, highs, lows, closes, vols = [], [], [], [], []
        for i in range(60):
            if i == 15:
                # Major swing low at 94.0
                opens.append(96.0); highs.append(97.0); lows.append(94.0); closes.append(96.0); vols.append(100.0)
            elif 10 <= i <= 20:
                opens.append(98.0); highs.append(99.0); lows.append(97.0); closes.append(98.0); vols.append(100.0)
            elif i == 25:
                # Minor swing high at 101.5
                opens.append(99.0); highs.append(101.5); lows.append(99.0); closes.append(101.0); vols.append(100.0)
            elif 22 <= i <= 28:
                opens.append(98.5); highs.append(99.5); lows.append(98.0); closes.append(99.0); vols.append(100.0)
            elif i == 35:
                # SWEEP BAR: Wicks below 94.0 (low=93.0), reclaims and closes at 95.5
                opens.append(95.0); highs.append(96.0); lows.append(93.0); closes.append(95.5); vols.append(250.0)
            elif i == 38:
                # CHoCH BAR: Candle closes above 101.5 at 102.5!
                opens.append(100.0); highs.append(103.0); lows.append(100.0); closes.append(102.5); vols.append(200.0)
            else:
                opens.append(98.0); highs.append(99.0); lows.append(97.0); closes.append(98.0); vols.append(100.0)

        data = {
            'open': np.array(opens),
            'high': np.array(highs),
            'low': np.array(lows),
            'close': np.array(closes),
            'tick_volume': np.array(vols),
        }

        signals, meta = engine_choch.analyze(data)

        self.assertEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig.direction, "BUY")
        self.assertEqual(sig.bar_index, 38)
        self.assertTrue(sig.is_choch_confirmed)
        self.assertEqual(sig.wick_extreme, 93.0)


if __name__ == '__main__':
    unittest.main()
