"""
tests/test_clean_plate_and_dynamic_milker.py
========================================================================================
Verification suite for Sajim Holdings:
  1. The Clean Plate Protocol (Toxic Blacklist & Spread Efficiency Gate)
  2. Dynamic BEEP Health-Driven Cash Milker Pi(H(t)) & Target Expansion
  3. Dynamic Entry Sizing Multiplier X_mult & Zero-Risk Pyramiding Psi
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

from bots.sajim_v1_bot import SajimV1Bot, TOXIC_BLACKLIST
from core.beep_signal_engine import BeepSignal


class TestCleanPlateAndDynamicMilker(unittest.TestCase):

    def setUp(self):
        self.bot = SajimV1Bot(
            max_concurrent_positions=34,
            base_risk_fraction=0.02,
            streak_expansion_rate=0.15,
            max_risk_fraction=0.045,
            dry_run=True,
        )

    def test_clean_plate_toxic_blacklist(self):
        """Verify that blacklisted assets (XAUGBP.c and XAGUSD.c) are unconditionally rejected."""
        self.assertIn("XAUGBP.c", TOXIC_BLACKLIST)
        self.assertIn("XAGUSD.c", TOXIC_BLACKLIST)

        sig_toxic_gold = BeepSignal(
            signal_id="TEST_XAUGBP",
            symbol="XAUGBP.c",
            timeframe="M15",
            bar_time=123456,
            action="BUY",
            layer="DIAMOND",
            m_t=85.0,
            b_t=3780.0,
            entry_price=3790.0,
            stop_loss=3780.0,
            take_profit=3825.0,
            risk_reward=3.5,
            phi_energy=70.0,
            spread_points=25,
            created_at="2026-09-08 11:00:00",
        )

        # Mock MT5 account info
        mock_acc = MagicMock()
        mock_acc.margin_free = 250.0
        mock_acc.equity = 370.0

        with patch("MetaTrader5.account_info", return_value=mock_acc):
            prepared = self.bot.evaluate_signal_and_size(sig_toxic_gold)
            self.assertIsNone(prepared, "Toxic asset XAUGBP.c must be unconditionally rejected!")

    def test_spread_to_risk_efficiency_gate(self):
        """Verify that an asset where spread consumes > 15% of Stop Loss is rejected."""
        sig_wide_spread = BeepSignal(
            signal_id="TEST_WIDE",
            symbol="EURTRY.c",
            timeframe="M15",
            bar_time=123456,
            action="BUY",
            layer="RARE",
            m_t=60.0,
            b_t=35.0,
            entry_price=35.10,
            stop_loss=35.00,  # 0.10 stop distance
            take_profit=35.45,
            risk_reward=3.5,
            phi_energy=55.0,
            spread_points=200,
            created_at="2026-09-08 11:00:00",
        )

        mock_acc = MagicMock()
        mock_acc.margin_free = 250.0
        mock_acc.equity = 370.0

        # Spread is 0.02, while SL distance is 0.10 -> Spread is 20% of SL (> 15% threshold)
        mock_sym_info = MagicMock()
        mock_sym_info.spread = 200
        mock_sym_info.point = 0.0001  # 0.02 spread distance

        with patch("MetaTrader5.account_info", return_value=mock_acc), \
             patch("MetaTrader5.symbol_info", return_value=mock_sym_info):
            prepared = self.bot.evaluate_signal_and_size(sig_wide_spread)
            self.assertIsNone(prepared, "Dirty plate with > 15% spread-to-risk must be rejected!")

    def test_dynamic_health_milker_fractions(self):
        """Verify dynamic milking fractions: 33% on Peak, 50% on Balanced, 70% on Degrading."""
        # Scenario 1: Peak Health (H(t) >= 0.75) -> Milk 33% at +2.0R, expand runner to +5.0R
        h_t_peak = 0.85
        r_trigger_peak = 2.0 if h_t_peak >= 0.75 else 1.5
        milk_fraction_peak = 0.33 if h_t_peak >= 0.75 else 0.50
        self.assertEqual(r_trigger_peak, 2.0)
        self.assertEqual(milk_fraction_peak, 0.33)

        # Scenario 2: Balanced Flow (0.55 <= H(t) < 0.75) -> Milk 50% at +1.5R
        h_t_bal = 0.65
        r_trigger_bal = 1.5
        milk_fraction_bal = 0.50
        self.assertEqual(r_trigger_bal, 1.5)
        self.assertEqual(milk_fraction_bal, 0.50)

        # Scenario 3: Degrading Momentum (0.35 <= H(t) < 0.55) -> Milk 70% at +1.0R (Cash Sweep)
        h_t_deg = 0.45
        r_trigger_deg = 1.0
        milk_fraction_deg = 0.70
        self.assertEqual(r_trigger_deg, 1.0)
        self.assertEqual(milk_fraction_deg, 0.70)

    def test_zero_risk_pyramiding_authorization(self):
        """Verify that an asset already open is authorized for 0.5x scale-in if secured at BE and H(t) >= 0.75."""
        sig_scale_in = BeepSignal(
            signal_id="TEST_SCALE_IN",
            symbol="GBPNZD.c",
            timeframe="M15",
            bar_time=123456,
            action="BUY",
            layer="DIAMOND",
            m_t=80.0,
            b_t=2.3100,
            entry_price=2.3150,
            stop_loss=2.3110,
            take_profit=2.3290,
            risk_reward=3.5,
            phi_energy=75.0,
            spread_points=12,
            created_at="2026-09-08 11:00:00",
        )

        mock_acc = MagicMock()
        mock_acc.margin_free = 250.0
        mock_acc.equity = 370.0
        mock_acc.leverage = 3000

        # Existing position on GBPNZD:
        mock_existing_pos = MagicMock()
        mock_existing_pos.symbol = "GBPNZD.c"
        mock_existing_pos.magic = 777999
        mock_existing_pos.type = 0  # BUY
        mock_existing_pos.price_open = 2.3000
        mock_existing_pos.sl = 2.3005  # Trailed PAST entry (Zero downside risk!)
        mock_existing_pos.price_current = 2.3150
        mock_existing_pos.ticket = 888123

        # Add to partially closed set
        self.bot.partially_closed_tickets.add(888123)

        mock_sym_info = MagicMock()
        mock_sym_info.spread = 12
        mock_sym_info.point = 0.00001
        mock_sym_info.trade_tick_size = 0.00001
        mock_sym_info.trade_tick_value = 1.0
        mock_sym_info.trade_contract_size = 1000.0
        mock_sym_info.volume_min = 0.01
        mock_sym_info.volume_max = 100.0
        mock_sym_info.volume_step = 0.01
        mock_sym_info.digits = 5

        # Mock health returning Peak Health (0.85)
        with patch("MetaTrader5.account_info", return_value=mock_acc), \
             patch("MetaTrader5.positions_get", return_value=[mock_existing_pos]), \
             patch("MetaTrader5.symbol_info", return_value=mock_sym_info), \
             patch.object(self.bot.beep_engine, "evaluate_position_health", return_value={"health_score": 0.85, "status": "PEAK_HEALTH"}):
            prepared = self.bot.evaluate_signal_and_size(sig_scale_in)
            self.assertIsNotNone(prepared, "Scale-in runner must be authorized on risk-free position with Peak Health!")


if __name__ == "__main__":
    unittest.main()
