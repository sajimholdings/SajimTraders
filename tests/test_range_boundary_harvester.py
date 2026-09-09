"""
tests/test_range_boundary_harvester.py
Verification suite for the Decoupled Universal Boundary Absorption Architecture:
  1. Universal BEEP Anomaly Detection (Zero hardcoded pair whitelists!)
  2. The Extreme Boundary Rule (|p - B(t)| >= 1.2 * ATR)
  3. Wick Trap Absorption (>= 40% wick)
  4. Sajim V1 Dynamic Spread Gate (eta <= 0.15)
  5. Sajim V1 Dynamic Macro Trend Conflict Gate (Gamma Gate)
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

from core.beep_signal_engine import BeepSignalEngine, BeepSignal
from bots.sajim_v1_bot import SajimV1Bot


class TestUniversalBoundaryAbsorption(unittest.TestCase):

    def setUp(self):
        self.engine = BeepSignalEngine()
        self.bot = SajimV1Bot(dry_run=True)

    @patch("MetaTrader5.copy_rates_from_pos")
    @patch("MetaTrader5.symbol_info")
    def test_universal_detection_on_eurgbp(self, mock_sym, mock_rates):
        """BEEP universally detects boundary absorption on EURGBP without any whitelist!"""
        mock_sym_obj = MagicMock()
        mock_sym_obj.visible = True
        mock_sym_obj.trade_mode = 4  # SYMBOL_TRADE_MODE_FULL
        mock_sym_obj.point = 0.00001
        mock_sym_obj.spread = 8
        mock_sym_obj.digits = 5
        mock_sym.return_value = mock_sym_obj

        # Baseline = 0.8500. ATR = 8 pips. 1.2 * ATR = 9.6 pips.
        # Latest bar stretches 14 pips above baseline to 0.8514 with 75% upper rejection wick.
        bars = []
        for i in range(29):
            bars.append({
                "time": 1700000000 + (i * 900),
                "open": 0.8500,
                "high": 0.8504,
                "low": 0.8496,
                "close": 0.8500,
            })
        bars.append({
            "time": 1700000000 + (29 * 900),
            "open": 0.8514,
            "high": 0.8520,
            "low": 0.8512,
            "close": 0.8514,
        })
        mock_rates.return_value = bars

        sig = self.engine.scan_boundary_absorption_front("EURGBP", "M15")
        self.assertIsNotNone(sig)
        self.assertEqual(sig.symbol, "EURGBP")
        self.assertEqual(sig.action, "SELL")
        self.assertEqual(sig.layer, "BOUNDARY_ABSORPTION")
        self.assertEqual(sig.mode, "BOUNDARY_FADE")
        self.assertGreaterEqual(sig.risk_reward, 1.5)
        self.assertEqual(sig.take_profit, sig.b_t)

    @patch("MetaTrader5.copy_rates_from_pos")
    @patch("MetaTrader5.symbol_info")
    def test_middle_of_range_rejected(self, mock_sym, mock_rates):
        """Price inside the middle of the range (< 1.2 * ATR from Baseline) is REJECTED by BEEP."""
        mock_sym_obj = MagicMock()
        mock_sym_obj.visible = True
        mock_sym_obj.trade_mode = 4
        mock_sym_obj.point = 0.00001
        mock_sym_obj.spread = 8
        mock_sym_obj.digits = 5
        mock_sym.return_value = mock_sym_obj

        # Baseline = 1.1600. Current price = 1.1604 (only 4 pips away, ATR = 10 pips)
        bars = []
        for i in range(30):
            bars.append({
                "time": 1700000000 + (i * 900),
                "open": 1.1600,
                "high": 1.1610,
                "low": 1.1590,
                "close": 1.1600 if i < 29 else 1.1604,
            })
        mock_rates.return_value = bars

        sig = self.engine.scan_boundary_absorption_front("EURUSD", "M15")
        self.assertIsNone(sig)

    @patch("MetaTrader5.account_info")
    @patch("MetaTrader5.symbol_info")
    def test_sajim_dynamic_spread_gate_rejection(self, mock_sym, mock_acc):
        """Sajim V1 dynamically rejects an asset whose spread consumes > 15% of Stop Loss."""
        mock_acc_obj = MagicMock()
        mock_acc_obj.margin_free = 300.0
        mock_acc_obj.equity = 380.0
        mock_acc_obj.leverage = 2000
        mock_acc.return_value = mock_acc_obj

        # Wide spread pair: 35 points spread on 80 point SL (43.7% > 15%)
        mock_sym_obj = MagicMock()
        mock_sym_obj.spread = 35
        mock_sym_obj.point = 0.00001
        mock_sym.return_value = mock_sym_obj

        sig = BeepSignal(
            signal_id="BEEP_BOUNDARY_GBPNZD_M15_100",
            symbol="GBPNZD",
            timeframe="M15",
            bar_time=100,
            action="BUY",
            layer="BOUNDARY_ABSORPTION",
            m_t=-20.0,
            b_t=2.3100,
            entry_price=2.3050,
            stop_loss=2.3042,  # SL distance = 8 pips (80 pts)
            take_profit=2.3100,
            risk_reward=1.8,
            phi_energy=50.0,
            spread_points=35,
            created_at="2026-09-08 14:00:00",
        )

        prepared = self.bot.evaluate_signal_and_size(sig)
        self.assertIsNone(prepared, "Sajim V1 must dynamically reject wide spread (> 15% SL)!")

    @patch("core.beep_signal_engine.BeepSignalEngine.get_htf_trend")
    @patch("MetaTrader5.account_info")
    @patch("MetaTrader5.symbol_info")
    def test_sajim_dynamic_macro_conflict_rejection(self, mock_sym, mock_acc, mock_htf):
        """Sajim V1 dynamically rejects counter-trend boundary fade when H4 macro trend is surging."""
        mock_acc_obj = MagicMock()
        mock_acc_obj.margin_free = 300.0
        mock_acc_obj.equity = 380.0
        mock_acc_obj.leverage = 2000
        mock_acc.return_value = mock_acc_obj

        # Tight spread
        mock_sym_obj = MagicMock()
        mock_sym_obj.spread = 8
        mock_sym_obj.point = 0.00001
        mock_sym.return_value = mock_sym_obj

        # H4 Macro Trend is roaring Bullish (+1) -> e.g. USDJPY carry trade
        mock_htf.return_value = 1

        # An M15 ceiling fade signal (SELL)
        sig = BeepSignal(
            signal_id="BEEP_BOUNDARY_USDJPY_M15_100",
            symbol="USDJPY",
            timeframe="M15",
            bar_time=100,
            action="SELL",
            layer="BOUNDARY_ABSORPTION",
            m_t=25.0,
            b_t=150.00,
            entry_price=150.20,
            stop_loss=150.28,
            take_profit=150.00,
            risk_reward=2.5,
            phi_energy=50.0,
            spread_points=8,
            created_at="2026-09-08 14:00:00",
        )

        prepared = self.bot.evaluate_signal_and_size(sig)
        self.assertIsNone(prepared, "Sajim V1 must dynamically reject fading against Bullish H4 Macro Trend!")


if __name__ == "__main__":
    unittest.main()
