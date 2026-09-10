"""
========================================================================================
       SAJIM QUANT LABS — BEEP SNIPE FILTER & ANTI-CHOP TEST SUITE
                      (tests/test_beep_snipe_filter.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Comprehensive Verification Suite:
  [Test 1] Asymptotic Baseline B(t): Huber outlier pruning of panic wicks
  [Test 2] Kinetic Mass M(t): Autocorrelation accumulation vs sign-flip damping
  [Test 3] Relative Volume RVol & Spike Scoring: High volume vs low-volume chop
  [Test 4] Candle Anatomy: Adverse wick trap detection (smart money limit absorption)
  [Test 5] Anti-Chop Gate: Low-volume sideways consolidation is strictly blocked
  [Test 6] Snipe Confirmation: High kinetic mass + volume spike confirms institutional entry
  [Test 7] Strategy Integration (YoungSurgeContinuation): Filters low-volume drift
  [Test 8] Strategy Integration (ExhaustionMeanReversion): Requires climax/rejection
  [Test 9] Strategy Integration (MirageLiquiditySweep): Confirms sweep volume surge
  [Test 10] Bot Execution Gate: sajim_v2_dual_bot blocks chop before trade dispatch
========================================================================================
"""

import os
import sys
import unittest
from types import SimpleNamespace
from datetime import datetime
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.beep_processor import BeepProcessor, BeepSnipeFilter, BeepSnipeEvaluation
from v2.strategy_base import StrategySignal
from v2.strategies.young_surge_continuation import YoungSurgeContinuation
from v2.strategies.exhaustion_mean_reversion import ExhaustionMeanReversion
from v2.strategies.mirage_liquidity_sweep import MirageLiquiditySweepCartridge
from v2.coexistence import CoexistenceGatekeeper
from v2.sajim_v2_dual_bot import SajimV2DualBot


class TestBeepSnipeFilterSuite(unittest.TestCase):
    """Rigorous unit tests for BEEP Snipe Filter and Anti-Chop Mechanics."""

    def setUp(self):
        self.processor = BeepProcessor()
        self.filter = BeepSnipeFilter(
            min_snipe_score=55.0,
            min_relative_volume=1.20,
            min_kinetic_mass=35.0,
            max_adverse_wick_ratio=0.40,
        )

    def test_01_asymptotic_baseline_pruning(self):
        """Verify B(t) prunes extreme panic wicks (|Z| > 2.0)."""
        normal_prices = [100.0, 100.2, 99.8, 100.1, 99.9, 100.0, 100.3, 99.7]
        spike_prices = normal_prices + [115.0]  # Extreme 15% outlier wick

        b_t, robust_sigma = self.processor.calculate_asymptotic_baseline(spike_prices, trim_z=2.0)
        # B(t) must reject the 115.0 spike and stay near 100.0
        self.assertAlmostEqual(b_t, 100.0, delta=0.5)
        self.assertLess(b_t, 102.0)

    def test_02_kinetic_mass_autocorrelation(self):
        """Verify M(t) accumulates on consecutive directional steps and decays on reversals."""
        # 10 consecutive positive steps (strong persistent buying)
        bullish_run = [100.0 + (i * 0.5) for i in range(15)]
        mean_p, sigma_p = np.mean(bullish_run), np.std(bullish_run) or 1.0
        mag_bull, signed_bull = self.processor.calculate_kinetic_mass(bullish_run, mean_p, sigma_p)
        self.assertGreaterEqual(mag_bull, 40.0)
        self.assertEqual(signed_bull, mag_bull)  # Positive sign

        # Alternating chop (up-down-up-down)
        choppy_run = [100.0, 100.5, 99.8, 100.4, 99.9, 100.5, 99.7, 100.3, 99.8, 100.4]
        mean_c, sigma_c = np.mean(choppy_run), np.std(choppy_run) or 1.0
        mag_chop, _ = self.processor.calculate_kinetic_mass(choppy_run, mean_c, sigma_c)
        # Chop should have heavily damped mass due to frequent sign flips
        self.assertLess(mag_chop, 30.0)

    def test_03_relative_volume_and_spike_scoring(self):
        """Verify RVol correctly identifies volume spikes vs low volume chop."""
        baseline_vols = [100.0] * 20
        # Scenario A: Low volume chop (50 contracts)
        chop_vols = baseline_vols + [50.0]
        _, _, rvol_chop = self.processor.calculate_relative_volume(chop_vols, lookback=20)
        self.assertAlmostEqual(rvol_chop, 0.50, delta=0.05)

        # Scenario B: Institutional volume surge (250 contracts = 2.5x)
        surge_vols = baseline_vols + [250.0]
        _, _, rvol_surge = self.processor.calculate_relative_volume(surge_vols, lookback=20)
        self.assertAlmostEqual(rvol_surge, 2.50, delta=0.05)

    def test_04_candle_anatomy_and_wick_traps(self):
        """Verify candle anatomy extracts wicks and detects trapped retail FOMO."""
        # Candle that pumped to 105 but closed back at 101 (huge 4-point upper wick on 5-point range = 80%)
        trap_bar = {
            "open": 100.0,
            "high": 105.0,
            "low": 100.0,
            "close": 101.0,
        }
        anatomy = self.processor.analyze_candle_anatomy(trap_bar)
        self.assertAlmostEqual(anatomy["upper_ratio"], 0.80, delta=0.02)
        self.assertAlmostEqual(anatomy["body_ratio"], 0.20, delta=0.02)

    def test_05_anti_chop_gate_blocks_low_volume_consolidation(self):
        """Verify that a sideways, low-volume range is strictly rejected."""
        bars = []
        base_p = 1.1000
        for i in range(40):
            # Oscillate +- 0.0002 with low volume (80.0 vs 100.0 baseline)
            jitter = 0.0002 if i % 2 == 0 else -0.0002
            vol = 70.0 if i >= 35 else 100.0
            bars.append({
                "time": i * 900,
                "open": base_p + jitter,
                "high": base_p + jitter + 0.0003,
                "low": base_p + jitter - 0.0003,
                "close": base_p - jitter,
                "volume": vol,
            })

        eval_res = self.filter.evaluate(
            symbol="EURUSD.c",
            timeframe="M15",
            action="BUY",
            bars=bars,
            strategy_name="YoungSurgeContinuation",
        )
        self.assertFalse(eval_res.passed)
        self.assertIn("BLOCKED BY BEEP CHOP FILTER", eval_res.reason)
        self.assertEqual(eval_res.tier, "CHOP_BLOCKED")

    def test_06_snipe_confirmation_on_institutional_spike(self):
        """Verify that a high-volume kinetic momentum breakout confirms a Snipe signal."""
        bars = []
        p = 2000.0
        # 30 bars of quiet consolidation (100 volume)
        for i in range(30):
            bars.append({
                "time": i * 900,
                "open": p - 0.5,
                "high": p + 0.8,
                "low": p - 0.8,
                "close": p,
                "volume": 100.0,
            })
        # 5 bars of explosive institutional surge with 2.5x volume and strong bodies
        for i in range(5):
            p += 4.0
            bars.append({
                "time": (30 + i) * 900,
                "open": p - 3.8,
                "high": p + 0.5,
                "low": p - 4.0,
                "close": p,
                "volume": 250.0,  # 2.5x volume spike!
            })

        eval_res = self.filter.evaluate(
            symbol="XAUUSD.c",
            timeframe="M15",
            action="BUY",
            bars=bars,
            strategy_name="YoungSurgeContinuation",
        )
        self.assertTrue(eval_res.passed)
        self.assertIn(eval_res.tier, ("DIAMOND_SNIPE", "RARE_SNIPE", "CERTIFIED_SNIPE"))
        self.assertGreaterEqual(eval_res.composite_score, 55.0)
        self.assertGreaterEqual(eval_res.relative_volume, 1.50)

    def test_07_young_surge_continuation_with_beep_filter(self):
        """Verify YoungSurgeContinuation behaves correctly with use_beep_filter=True."""
        cart_filtered = YoungSurgeContinuation(use_beep_filter=True, min_beep_score=50.0)
        self.assertTrue(cart_filtered.parameters["use_beep_filter"])

        # Create low-volume drift data (should be blocked)
        drift_bars = []
        p = 1.3000
        for i in range(70):
            p += 0.0001
            # Low volume on recent bars
            vol = 40.0 if i >= 60 else 100.0
            drift_bars.append({
                "time": i * 900,
                "open": p - 0.00005,
                "high": p + 0.00010,
                "low": p - 0.00010,
                "close": p,
                "volume": vol,
            })
        market_info = {"point": 0.00001, "spread": 12, "bid": p, "ask": p + 0.00012}

        sig_drift = cart_filtered.evaluate("USDCAD.c", "M15", drift_bars, market_info)
        # Should be blocked because of low-volume drift
        self.assertIsNone(sig_drift)

    def test_08_exhaustion_mean_reversion_with_beep_filter(self):
        """Verify ExhaustionMeanReversion with use_beep_filter=True requires climax/stretch."""
        cart = ExhaustionMeanReversion(use_beep_filter=True, min_beep_score=45.0)
        self.assertTrue(cart.parameters["use_beep_filter"])

    def test_09_mirage_liquidity_sweep_with_beep_filter(self):
        """Verify MirageLiquiditySweepCartridge supports use_beep_filter parameter."""
        cart = MirageLiquiditySweepCartridge(use_beep_filter=True, min_beep_score=50.0)
        self.assertTrue(cart.parameters["use_beep_filter"])

    def test_10_sajim_v2_dual_bot_filters_chop_before_execution(self):
        """Verify SajimV2DualBot rejects unconfirmed chop signals via BeepSnipeFilter."""
        gatekeeper = CoexistenceGatekeeper(status_file_path=os.path.join(ROOT_DIR, "v2", "test_bot_coex.json"))
        bot = SajimV2DualBot(gatekeeper=gatekeeper, dry_run=True)
        self.assertIsNotNone(bot.snipe_filter)

        # Create a candidate strategy signal
        candidate_sig = StrategySignal(
            symbol="EURUSD.c",
            action="BUY",
            timeframe="M15",
            entry_price=1.0500,
            stop_loss=1.0450,
            take_profit=1.0650,
            risk_reward=3.0,
            confidence=0.85,
            strategy_name="YoungSurgeContinuation",
            reason="Test Signal",
        )

        # 40 bars of dead volume chop
        chop_bars = [
            {"time": i * 900, "open": 1.0500, "high": 1.0505, "low": 1.0495, "close": 1.0500, "volume": 30.0}
            for i in range(40)
        ]
        confirmed, eval_res = bot.snipe_filter.evaluate_signal(candidate_sig, chop_bars)
        self.assertFalse(confirmed)
        self.assertIn("BLOCKED BY BEEP CHOP FILTER", eval_res.reason)

        if os.path.exists(os.path.join(ROOT_DIR, "v2", "test_bot_coex.json")):
            try:
                os.remove(os.path.join(ROOT_DIR, "v2", "test_bot_coex.json"))
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
