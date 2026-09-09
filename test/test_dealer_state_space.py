"""
tests/test_dealer_state_space.py
========================================================================================
Unit tests for core/dealer_state_space.py
Verifies Particle Filter Dealer Inventory, Dynamic Elasticity, and Synthetic Gamma Tensors.
========================================================================================
"""

import unittest
import os
import sys
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.dealer_state_space import (
    ParticleFilterDealerEstimator,
    DynamicHedgeFlowElasticity,
    SyntheticGammaTensor,
    DealerMicrostructureEngine,
    ThreeCandleTickConfirmationEngine,
)


class TestDealerStateSpace(unittest.TestCase):

    def test_particle_filter_initialization(self):
        estimator = ParticleFilterDealerEstimator(num_particles=200)
        self.assertEqual(estimator.N, 200)
        self.assertEqual(len(estimator.particles), 200)
        self.assertAlmostEqual(float(np.sum(estimator.weights)), 1.0, places=5)

    def test_particle_filter_tick_updates(self):
        estimator = ParticleFilterDealerEstimator(num_particles=200)
        
        # Initial tick
        inv, elast, regime = estimator.update(bid=1.3500, ask=1.3502, volume=10.0, spread=0.0002)
        self.assertEqual(regime, "BALANCED")
        self.assertAlmostEqual(inv, 0.0, places=2)

        # Simulate heavy downward selling ticks (dealers absorb sellers -> dealer inventory rises)
        for i in range(15):
            p = 1.3500 - (i * 0.0005)
            inv, elast, regime = estimator.update(bid=p, ask=p + 0.0002, volume=20.0, spread=0.0002)

        self.assertTrue(-1.0 <= inv <= 1.0)
        self.assertTrue(elast > 0.0)

    def test_dynamic_elasticity(self):
        elast = DynamicHedgeFlowElasticity()
        
        # Prime baseline
        ratio, classification = elast.update(price_delta=0.0001, volume=5.0, spread=0.0002)
        self.assertTrue(classification in ["NORMAL_LIQUIDITY", "EXPLOSIVE_FLOW", "ABSORPTION_WALL"])

        # Thin book massive price jump (explosive flow)
        for _ in range(5):
            ratio, classification = elast.update(price_delta=0.0020, volume=1.0, spread=0.0002)
        self.assertTrue(ratio > 1.0)

    def test_synthetic_gamma_tensor(self):
        # Generate 15 simulated M5 bars accelerating upward away from baseline
        rates = []
        base_p = 1.3500
        for i in range(15):
            # Non-linear quadratic acceleration (Short Gamma signature)
            p = base_p + (i * 0.0005) + (i**2 * 0.0001)
            rates.append({
                "open": p - 0.0002,
                "high": p + 0.0005,
                "low": p - 0.0003,
                "close": p,
            })

        gamma_res = SyntheticGammaTensor.calculate_gamma_regime(
            rates=rates,
            spread=0.0002,
            point=0.0001,
        )
        self.assertIn(gamma_res["regime"], ["SHORT_GAMMA", "LONG_GAMMA", "TRANSITION"])
        self.assertTrue("gamma_value" in gamma_res)
        self.assertTrue("zero_gamma_level" in gamma_res)

    def test_dealer_microstructure_engine_approval(self):
        engine = DealerMicrostructureEngine()

        # Ingest a few ticks
        for i in range(5):
            engine.ingest_tick("GBPUSD", bid=1.3500 + i*0.0001, ask=1.3502 + i*0.0001, volume=10.0, spread=0.0002)

        rates = [
            {"open": 1.3500, "high": 1.3520, "low": 1.3490, "close": 1.3510 + (i*0.0005)}
            for i in range(12)
        ]

        approved, boost, regime, narrative = engine.evaluate_dealer_alignment(
            symbol="GBPUSD",
            action="BUY",
            cur_price=1.3560,
            rates_m5=rates,
            spread=0.0002,
            point=0.0001,
        )
        self.assertIsInstance(approved, bool)
        self.assertIsInstance(boost, float)
        self.assertIsInstance(regime, str)
        self.assertIsInstance(narrative, str)

    def test_three_candle_and_tick_confirmation_buy_approved(self):
        # C1: Hunt bar, C2: Absorption bar with 25% lower wick, C3: Bullish confirmation
        rates_m5 = [
            {"open": 4400.0, "high": 4405.0, "low": 4390.0, "close": 4392.0, "tick_volume": 100},
            {"open": 4392.0, "high": 4398.0, "low": 4385.0, "close": 4395.0, "tick_volume": 180},  # Low 4385, Open 4392 -> wick 7/13 = 53%
            {"open": 4395.0, "high": 4404.0, "low": 4394.0, "close": 4403.0, "tick_volume": 150},  # Strong close
        ]

        # Simulating aggressive buying ticks
        ticks = [
            {"bid": 4400.0 + i * 0.1, "ask": 4400.3 + i * 0.1, "volume": 5.0}
            for i in range(25)
        ]

        passed, boost, narrative, metrics = ThreeCandleTickConfirmationEngine.evaluate_three_candle_and_tick(
            symbol="XAUUSD",
            action="BUY",
            rates_m5=rates_m5,
            ticks=ticks,
        )
        self.assertTrue(passed)
        self.assertTrue(metrics["candle_confirmed"])
        self.assertTrue(metrics["tick_confirmed"])
        self.assertEqual(metrics["tape_bias"], "AGGRESSIVE_BUY")
        self.assertGreater(boost, 1.0)

    def test_three_candle_and_tick_confirmation_sell_veto(self):
        # Even if candle setup is fine, if ticks show aggressive buying against a SELL, it is vetoed
        rates_m5 = [
            {"open": 4400.0, "high": 4410.0, "low": 4398.0, "close": 4408.0, "tick_volume": 100},
            {"open": 4408.0, "high": 4415.0, "low": 4400.0, "close": 4402.0, "tick_volume": 180},
            {"open": 4402.0, "high": 4403.0, "low": 4390.0, "close": 4392.0, "tick_volume": 150},
        ]

        # Ticks are surging upward (aggressive buying lifting offers)
        ticks = [
            {"bid": 4400.0 + i * 0.2, "ask": 4400.3 + i * 0.2, "volume": 10.0}
            for i in range(25)
        ]

        passed, boost, narrative, metrics = ThreeCandleTickConfirmationEngine.evaluate_three_candle_and_tick(
            symbol="XAUUSD",
            action="SELL",
            rates_m5=rates_m5,
            ticks=ticks,
        )
        self.assertFalse(passed)  # Vetoed because tape is aggressively lifting against the sell
        self.assertIn("TICK OFI VETO", narrative)


if __name__ == "__main__":
    unittest.main()

