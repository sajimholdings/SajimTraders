"""
tests/test_chameleon_dual_regime.py
Automated verification of the Dual-Regime Chameleon Formula:
  1. Regime Parameter Verification (Hummingbird vs Cheetah)
  2. Range Exposure Gating (Cap at 4 positions to kill friction drain)
  3. Hummingbird Micro-Harvesting Trigger (+0.35R / $1.50 at 70% volume)
  4. Trend Expansion Uncapping (15 positions, +1.5R milk, 50% runner)
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.sajim_regime_algos import SajimChameleonClassifier
from bots.sajim_v1_bot import SajimV1Bot
from core.beep_signal_engine import BeepSignal


class TestChameleonDualRegime(unittest.TestCase):

    def test_regime_params_definition(self):
        p_range = SajimChameleonClassifier.get_regime_params("RANGE_COMPRESSION")
        self.assertEqual(p_range["max_concurrent_positions"], 4)
        self.assertEqual(p_range["milk_trigger_r"], 0.35)
        self.assertEqual(p_range["milk_fraction"], 0.70)
        self.assertEqual(p_range["name"], "HUMMINGBIRD_RANGE_HARVESTER")

        p_trend = SajimChameleonClassifier.get_regime_params("TREND_EXPANSION")
        self.assertEqual(p_trend["max_concurrent_positions"], 15)
        self.assertEqual(p_trend["milk_trigger_r"], 1.50)
        self.assertEqual(p_trend["milk_fraction"], 0.50)
        self.assertEqual(p_trend["name"], "CHEETAH_TREND_EXPANSION")

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_compression_ratio_calculation(self, mock_rates):
        mock_rates_m15 = [{"high": 1.1610, "low": 1.1605, "close": 1.1608} for _ in range(16)]
        mock_rates_h4 = [{"high": 1.1650, "low": 1.1600, "close": 1.1620} for _ in range(16)]

        def rates_side_effect(symbol, tf, start, count):
            if tf == 15:
                return mock_rates_m15
            return mock_rates_h4

        mock_rates.side_effect = rates_side_effect

        kappa, label = SajimChameleonClassifier.calculate_compression_ratio("EURUSD", 1.1608, m_t=30.0)
        self.assertEqual(label, "RANGE_COMPRESSION")
        self.assertLess(kappa, 0.75)

        kappa_exp, label_exp = SajimChameleonClassifier.calculate_compression_ratio("EURUSD", 1.1608, m_t=85.0)
        self.assertEqual(label_exp, "TREND_EXPANSION")

    @patch("core.sajim_regime_algos.SajimChameleonClassifier.calculate_compression_ratio")
    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.account_info")
    @patch("MetaTrader5.symbol_info")
    def test_range_concurrency_gate(self, mock_sym, mock_acc, mock_pos, mock_chameleon):
        mock_chameleon.return_value = (0.50, "RANGE_COMPRESSION")

        mock_acc_obj = MagicMock()
        mock_acc_obj.margin_free = 300.0
        mock_acc_obj.equity = 380.0
        mock_acc_obj.leverage = 2000
        mock_acc.return_value = mock_acc_obj

        mock_sym_obj = MagicMock()
        mock_sym_obj.spread = 8
        mock_sym_obj.point = 0.00001
        mock_sym_obj.trade_tick_value = 1.0
        mock_sym_obj.trade_tick_size = 0.00001
        mock_sym_obj.volume_min = 0.01
        mock_sym_obj.volume_step = 0.01
        mock_sym_obj.volume_max = 100.0
        mock_sym_obj.trade_contract_size = 100000.0
        mock_sym.return_value = mock_sym_obj

        bot = SajimV1Bot(max_concurrent_positions=15, dry_run=True)

        sig = BeepSignal(
            signal_id="BEEP_EURUSD_M15_1000000",
            symbol="EURUSD",
            timeframe="M15",
            bar_time=1000000,
            action="BUY",
            layer="CERTIFIED",
            m_t=45.0,
            b_t=1.1600,
            entry_price=1.1610,
            stop_loss=1.1590,
            take_profit=1.1650,
            risk_reward=2.5,
            phi_energy=50.0,
            spread_points=8,
            created_at="2026-09-08 13:00:00",
            mode="INTRADAY",
            regime="ACTIVE_HUNT",
            session="LONDON",
            upper_wick_ratio=0.1,
            lower_wick_ratio=0.1,
        )

        mock_pos.return_value = [MagicMock(magic=777999) for _ in range(3)]
        prepared = bot.evaluate_signal_and_size(sig)
        self.assertIsNotNone(prepared)

        mock_pos.return_value = [MagicMock(magic=777999) for _ in range(4)]
        blocked = bot.evaluate_signal_and_size(sig)
        self.assertIsNone(blocked)


if __name__ == "__main__":
    unittest.main()
