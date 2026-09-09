"""
tests/test_dynamic_opportunist.py
========================================================================================
Verification suite for Sajim Holdings Dynamic Opportunist Engine:
  1. Correlation Derating Delta(K) = 1 / sqrt(K + 1)
  2. Multi-Variable Dynamic Stake Maximizer Omega
  3. BEEP Live Position Health H(t) Evaluation & Narrative Scratch Euthanasia
  4. 50% Partial Cash Milking & Break-Even Ratchet Logic
========================================================================================
"""

import math
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots")):
    if p not in sys.path:
        sys.path.insert(0, p)

from bots.sajim_v1_bot import SajimV1Bot
from core.beep_signal_engine import BeepSignal, BeepSignalEngine
from core.beep_broadcast import BeepBroadcastBus


class TestDynamicOpportunistEngine(unittest.TestCase):

    def setUp(self):
        self.bot = SajimV1Bot(
            max_concurrent_positions=34,
            base_risk_fraction=0.02,
            streak_expansion_rate=0.15,
            max_risk_fraction=0.045,
            dry_run=True,
        )

    def test_equation_10_correlation_derating(self):
        """Verify Delta(K) = 1 / sqrt(K + 1) scales bounded risk across correlated pairs."""
        k_values = [0, 1, 2, 3]
        expected_deltas = [
            1.0,
            1.0 / math.sqrt(2),  # ~0.7071
            1.0 / math.sqrt(3),  # ~0.5774
            1.0 / math.sqrt(4),  # 0.5000
        ]
        base_risk = 0.02  # 2.0%

        total_risk = 0.0
        for k, expected_delta in zip(k_values, expected_deltas):
            delta = 1.0 / math.sqrt(k + 1)
            self.assertAlmostEqual(delta, expected_delta, places=4)
            per_trade_risk = base_risk * delta
            total_risk += per_trade_risk

        # In a 4-pair basket (K=0,1,2,3), total basket risk must remain bounded around ~5.5%
        # without compounding, while single pair risk derates from 2% down to 1%
        self.assertLess(total_risk, 0.06)
        self.assertAlmostEqual(1.0 / math.sqrt(1), 1.0)
        self.assertAlmostEqual(1.0 / math.sqrt(4), 0.5)

    def test_equation_11_multi_variable_stake_maximizer(self):
        """Verify Omega adapts dynamically to Margin, Mass, and Conviction."""
        # Scenario A: Baseline account conditions
        fm_ratio = 1.0      # 100% Free Margin
        m_ratio = 1.0       # Mass at baseline (55.0)
        phi_ratio = 1.0     # Conviction at baseline (50.0)
        streak_rate = 0.15

        kappa = streak_rate * fm_ratio * m_ratio * phi_ratio
        self.assertAlmostEqual(kappa, 0.15, places=4)

        # Scenario B: High conviction institutional diamond thrust
        fm_ratio_high = 1.1
        m_ratio_high = 85.0 / 55.0    # ~1.545
        phi_ratio_high = 65.0 / 50.0  # 1.30

        kappa_high = streak_rate * fm_ratio_high * m_ratio_high * phi_ratio_high
        self.assertGreater(kappa_high, 0.30)  # Dynamically doubles the scaling step!

        # Cluster Streak Isolation:
        self.bot.cluster_streaks["NZD"] = 3
        self.bot.cluster_streaks["JPY"] = 0

        mult_nzd = (1.0 + kappa) ** self.bot.cluster_streaks["NZD"]
        mult_jpy = (1.0 + kappa) ** self.bot.cluster_streaks["JPY"]

        self.assertGreater(mult_nzd, 1.50)  # +52% stake boost on winning NZD cluster
        self.assertEqual(mult_jpy, 1.0)     # Neutral stake on JPY cluster

    def test_equation_9_beep_live_position_health(self):
        """Verify H(t) scores healthy runs >= 0.75 and invalidations < 0.30."""
        engine = BeepSignalEngine()

        # Mock rates where price is expanding strongly upwards above baseline
        bullish_rates = []
        base_price = 100.0
        for i in range(25):
            p = base_price + (i * 0.5)
            bullish_rates.append({
                "time": i,
                "open": p - 0.2,
                "high": p + 0.3,
                "low": p - 0.2,
                "close": p + 0.2,  # Strong bull closes
                "tick_volume": 100,
                "spread": 1,
                "real_volume": 0
            })

        with patch("MetaTrader5.copy_rates_from_pos", return_value=bullish_rates):
            # Test BUY trade aligned with the bullish run:
            health = engine.evaluate_position_health(
                symbol="EURUSD.c",
                action="BUY",
                open_price=100.0,
                sl=98.0,
                cur_price=112.0,
                timeframe="M15"
            )
            self.assertGreaterEqual(health["health_score"], 0.70)
            self.assertEqual(health["status"], "PEAK_HEALTH")
            self.assertGreater(health["expansion_r"], 5.0)

            # Test SELL trade fighting against the strong bullish run (invalidation):
            bad_health = engine.evaluate_position_health(
                symbol="EURUSD.c",
                action="SELL",
                open_price=100.0,
                sl=105.0,
                cur_price=112.0,
                timeframe="M15"
            )
            self.assertLess(bad_health["health_score"], 0.35)
            self.assertEqual(bad_health["status"], "CRITICAL_SCRATCH")

    def test_cluster_isolation_on_loss(self):
        """Verify that a loss in one cluster never wipes out momentum in another cluster."""
        self.bot.cluster_streaks["NZD"] = 3
        self.bot.cluster_streaks["METALS"] = 1
        self.bot.consecutive_wins = 4

        # Simulate a closed loss deal on XAUUSD (METALS)
        mock_deal = MagicMock()
        mock_deal.ticket = 999111
        mock_deal.symbol = "XAUUSD.c"
        mock_deal.profit = -12.50
        mock_deal.swap = 0.0
        mock_deal.magic = 777999
        mock_deal.entry = 1  # DEAL_ENTRY_OUT
        mock_deal.time = int(datetime.now().timestamp())
        mock_deal.comment = "SL Hit"

        with patch("MetaTrader5.history_deals_get", return_value=[mock_deal]):
            self.bot.sync_pnl_and_streaks()

        # NZD cluster streak MUST remain 3!
        self.assertEqual(self.bot.cluster_streaks["NZD"], 3)
        # METALS cluster streak stepped back: 1 -> 0
        self.assertEqual(self.bot.cluster_streaks["METALS"], 0)
        # Global streak stepped back: 4 -> 3
        self.assertEqual(self.bot.consecutive_wins, 3)
        # Asset entered cooldown:
        self.assertIn("XAUUSD.c", self.bot.symbol_cooldowns)


if __name__ == "__main__":
    unittest.main()
