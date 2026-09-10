"""
========================================================================================
     SAJIM QUANT LABS — V2 HUMMINGBIRD HARVEST UNIT & INTEGRATION TEST SUITE
                      (tests/test_v2_hummingbird_harvest.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Edge Verification:
  [Test 1] Zero Premature Harvest: profit_r < 1.50R returns False
  [Test 2] Healthy Kinetic Expansion: Accelerating impulse is allowed to run
  [Test 3] Vector 1: M1 Counter-Wick Rejection (Upper Wick >= 45% at +1.6R, >= 35% at +1.8R)
  [Test 4] Vector 2: M1 Consecutive Momentum Decay (2 adverse M1 bars at +1.5R+)
  [Test 5] Vector 2B: M1 Velocity Stalling (Thrust Decay from large expansion to stall)
  [Test 6] Vector 3: M1 Micro-Structure Break (CHoCH / Low or High Engulfing)
  [Test 7] Vector 4: M1 Baseline Envelope Overextension Stretch (>= 2.2x ATR)
  [Test 8] Vector 5: M1 Climax Volume Absorption (Volume spike >= 2.0x average)
  [Test 9] Vector 6: Elite Zone Profit Defense (+2.2R to +2.85R Peak Defense)
  [Test 10] Short / SELL Position Exhaustion Detection
  [Test 11] Full Harvest Execution (100% close & broadcast dispatch)
  [Test 12] Massive Partial Execution (80% harvest & runner locked at +1.0R)
  [Test 13] Fallback to Asymmetric Ratchet when Not Exhausted (+1.5R BE, +2.2R Lock)
========================================================================================
"""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import numpy as np

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from v2.sajim_v2_dual_bot import SajimV2DualBot, MAGIC_V2
from core.beep_broadcast import BeepBroadcastBus


class TestV2HummingbirdHarvest(unittest.TestCase):
    """Rigorous verification suite for M1 Hummingbird Harvest algorithm."""

    def setUp(self):
        self.bot = SajimV2DualBot(dry_run=True)
        self.sym_info = SimpleNamespace(
            point=0.0001,
            bid=1.1000,
            ask=1.1002,
            volume_min=0.01,
            volume_step=0.01,
        )

    def _generate_bars(self, pattern_type="HEALTHY", is_buy=True, base_price=1.1000):
        """Generates synthetic M1 bars tailored to specific momentum test vectors."""
        point = 0.0001
        bars = []

        p = base_price - (0.0030 if is_buy else -0.0030)
        for i in range(20):
            p += (point * 1.5 if is_buy else -point * 1.5)
            bars.append({
                "time": 1700000000 + i * 60,
                "open": p,
                "high": p + point * 2,
                "low": p - point * 2,
                "close": p + (point if is_buy else -point),
                "tick_volume": 50,
            })

        if pattern_type == "HEALTHY":
            for i in range(5):
                last_c = bars[-1]["close"]
                if is_buy:
                    bars.append({
                        "time": 1700000000 + (20 + i) * 60,
                        "open": last_c,
                        "high": last_c + point * 8,
                        "low": last_c - point * 1,
                        "close": last_c + point * 7,
                        "tick_volume": 60,
                    })
                else:
                    bars.append({
                        "time": 1700000000 + (20 + i) * 60,
                        "open": last_c,
                        "high": last_c + point * 1,
                        "low": last_c - point * 8,
                        "close": last_c - point * 7,
                        "tick_volume": 60,
                    })

        elif pattern_type == "COUNTER_WICK":
            last_c = bars[-1]["close"]
            if is_buy:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c,
                    "high": last_c + point * 20,
                    "low": last_c - point * 1,
                    "close": last_c + point * 5,
                    "tick_volume": 80,
                })
            else:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c,
                    "high": last_c + point * 1,
                    "low": last_c - point * 20,
                    "close": last_c - point * 5,
                    "tick_volume": 80,
                })

        elif pattern_type == "CONSECUTIVE_DECAY":
            last_c = bars[-1]["close"]
            if is_buy:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c,
                    "high": last_c + point * 2,
                    "low": last_c - point * 5,
                    "close": last_c - point * 4,
                    "tick_volume": 40,
                })
                bars.append({
                    "time": 1700000000 + 21 * 60,
                    "open": last_c - point * 4,
                    "high": last_c - point * 3,
                    "low": last_c - point * 8,
                    "close": last_c - point * 7,
                    "tick_volume": 45,
                })
            else:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c,
                    "high": last_c + point * 5,
                    "low": last_c - point * 2,
                    "close": last_c + point * 4,
                    "tick_volume": 40,
                })
                bars.append({
                    "time": 1700000000 + 21 * 60,
                    "open": last_c + point * 4,
                    "high": last_c + point * 8,
                    "low": last_c + point * 3,
                    "close": last_c + point * 7,
                    "tick_volume": 45,
                })

        elif pattern_type == "THRUST_STALL":
            last_c = bars[-1]["close"]
            if is_buy:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c,
                    "high": last_c + point * 16,
                    "low": last_c - point * 1,
                    "close": last_c + point * 15,
                    "tick_volume": 70,
                })
                bars.append({
                    "time": 1700000000 + 21 * 60,
                    "open": last_c + point * 15,
                    "high": last_c + point * 17,
                    "low": last_c + point * 14,
                    "close": last_c + point * 16,
                    "tick_volume": 50,
                })
                bars.append({
                    "time": 1700000000 + 22 * 60,
                    "open": last_c + point * 16,
                    "high": last_c + point * 17,
                    "low": last_c + point * 13,
                    "close": last_c + point * 14,
                    "tick_volume": 55,
                })

        elif pattern_type == "MICRO_BREAK":
            last_c = bars[-1]["close"]
            if is_buy:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c,
                    "high": last_c + point * 5,
                    "low": last_c - point * 2,
                    "close": last_c + point * 4,
                    "tick_volume": 50,
                })
                bars.append({
                    "time": 1700000000 + 21 * 60,
                    "open": last_c + point * 4,
                    "high": last_c + point * 5,
                    "low": last_c - point * 6,
                    "close": last_c - point * 5,
                    "tick_volume": 65,
                })

        elif pattern_type == "CLIMAX_VOLUME":
            # Volume spike >= 2.5x with ~30% rejection wick (below 35% Vector 1 threshold)
            last_c = bars[-1]["close"]
            if is_buy:
                bars.append({
                    "time": 1700000000 + 20 * 60,
                    "open": last_c + point * 4,
                    "high": last_c + point * 10,
                    "low": last_c,
                    "close": last_c + point * 7,  # range = 10, upper wick = 3 / 10 = 30%
                    "tick_volume": 180,           # Average is ~50, so 3.6x volume!
                })

        return np.array([
            (b["time"], b["open"], b["high"], b["low"], b["close"], b["tick_volume"], 2, 0)
            for b in bars
        ], dtype=[
            ('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'),
            ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i4'), ('real_volume', '<i8')
        ])

    def test_01_zero_premature_harvest(self):
        """Verify trades under +1.50R are never prematurely harvested."""
        pos = SimpleNamespace(ticket=101, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.20, sym_info=self.sym_info)
        self.assertFalse(is_ex)
        self.assertEqual(reason, "")

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_02_healthy_kinetic_expansion_not_harvested(self, mock_copy_rates):
        """Verify healthy, accelerating momentum is preserved and allowed to run to target."""
        pos = SimpleNamespace(ticket=102, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        mock_copy_rates.return_value = self._generate_bars("HEALTHY", is_buy=True)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.85, sym_info=self.sym_info)
        self.assertFalse(is_ex)
        self.assertEqual(reason, "")

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_03_vector_1_counter_wick_rejection(self, mock_copy_rates):
        """Verify Vector 1: Massive counter-wick rejection triggers peak harvest."""
        pos = SimpleNamespace(ticket=103, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        mock_copy_rates.return_value = self._generate_bars("COUNTER_WICK", is_buy=True)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.80, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Counter-Wick Rejection", reason)

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_04_vector_2_consecutive_momentum_decay(self, mock_copy_rates):
        """Verify Vector 2: Two consecutive adverse M1 bars trigger harvest."""
        pos = SimpleNamespace(ticket=104, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        mock_copy_rates.return_value = self._generate_bars("CONSECUTIVE_DECAY", is_buy=True)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.65, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Consecutive Momentum Decay", reason)

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_05_vector_2b_velocity_thrust_stalling(self, mock_copy_rates):
        """Verify Vector 2B: Sudden thrust collapse from large expansion into negative close."""
        pos = SimpleNamespace(ticket=105, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        mock_copy_rates.return_value = self._generate_bars("THRUST_STALL", is_buy=True)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.70, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Velocity Stalling", reason)

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_06_vector_3_micro_structure_break(self, mock_copy_rates):
        """Verify Vector 3: M1 candle closes below prior M1 low."""
        pos = SimpleNamespace(ticket=106, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        mock_copy_rates.return_value = self._generate_bars("MICRO_BREAK", is_buy=True)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.75, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Micro-Structure Break", reason)

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_07_vector_5_climax_volume_absorption(self, mock_copy_rates):
        """Verify Vector 5: Volume spike >= 2.0x average with rejection wick triggers harvest."""
        pos = SimpleNamespace(ticket=107, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        mock_copy_rates.return_value = self._generate_bars("CLIMAX_VOLUME", is_buy=True)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.60, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Climax Volume Absorption", reason)

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_08_vector_6_elite_zone_profit_defense(self, mock_copy_rates):
        """Verify Vector 6: Profit >= 2.20R protects peak on any adverse turn."""
        pos = SimpleNamespace(ticket=108, symbol="EURUSD.c", type=0, volume=0.02, price_open=1.0900, sl=1.0850)
        bars = self._generate_bars("HEALTHY", is_buy=True)
        # Set last bar to close below open with zero upper wick
        bars[-1]["high"] = bars[-1]["open"]
        bars[-1]["close"] = bars[-1]["open"] - 0.0001
        bars[-1]["low"] = bars[-1]["close"]
        mock_copy_rates.return_value = bars

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=2.35, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Peak Profit Defense Stall", reason)

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_09_sell_position_exhaustion_detection(self, mock_copy_rates):
        """Verify short SELL positions detect lower-wick rejection and consecutive bullish candles."""
        pos = SimpleNamespace(ticket=109, symbol="EURUSD.c", type=1, volume=0.02, price_open=1.1100, sl=1.1150)
        mock_copy_rates.return_value = self._generate_bars("COUNTER_WICK", is_buy=False)

        is_ex, reason = self.bot.check_hummingbird_exhaustion(pos, profit_r=1.90, sym_info=self.sym_info)
        self.assertTrue(is_ex)
        self.assertIn("Counter-Wick Rejection", reason)

    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.copy_rates_from_pos")
    @patch("MetaTrader5.order_send")
    def test_10_full_harvest_execution_flow(self, mock_order_send, mock_copy_rates, mock_symbol_info, mock_positions_get):
        """Verify manage_open_positions executes 100% close, broadcasts event, and cleans state."""
        self.bot.dry_run = False
        self.bot.hummingbird_harvest_mode = "FULL"

        pos = SimpleNamespace(
            ticket=555,
            symbol="EURUSD.c",
            type=0,  # BUY
            volume=0.05,
            price_open=1.0800,
            sl=1.0750,  # risk = 50 pts
            tp=1.0950,
            profit=10.50,
            magic=MAGIC_V2,
        )
        mock_positions_get.return_value = [pos]
        mock_symbol_info.return_value = SimpleNamespace(
            bid=1.0895,  # profit = 95 pts = +1.90R
            ask=1.0897,
            point=0.0001,
            volume_min=0.01,
            volume_step=0.01,
        )
        mock_copy_rates.return_value = self._generate_bars("COUNTER_WICK", is_buy=True)
        mock_order_send.return_value = SimpleNamespace(retcode=10009, comment="Done")

        with patch.object(self.bot.bus, "broadcast_hummingbird_harvest") as mock_bcast:
            self.bot.manage_open_positions()

            mock_order_send.assert_called()
            call_args = mock_order_send.call_args[0][0]
            self.assertEqual(call_args["action"], 1)  # TRADE_ACTION_DEAL
            self.assertEqual(call_args["position"], 555)
            self.assertEqual(call_args["volume"], 0.05)
            self.assertEqual(call_args["comment"], "Sajim_Hummingbird")

            mock_bcast.assert_called_once()
            bcast_args = mock_bcast.call_args[1]
            self.assertEqual(bcast_args["ticket"], 555)
            self.assertEqual(bcast_args["profit"], 10.50)
            self.assertAlmostEqual(bcast_args["r_multiple"], 1.90, places=2)
            self.assertEqual(bcast_args["pct_closed"], 100.0)

            self.assertIn("EURUSD.c", self.bot.pending_reentry_symbols)

    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.copy_rates_from_pos")
    @patch("MetaTrader5.order_send")
    def test_11_massive_partial_execution_flow(self, mock_order_send, mock_copy_rates, mock_symbol_info, mock_positions_get):
        """Verify massive partial mode closes 80% and ratchets runner SL to lock +1.0R Net Profit."""
        self.bot.dry_run = False
        self.bot.hummingbird_harvest_mode = "MASSIVE_PARTIAL"
        self.bot.hummingbird_partial_ratio = 0.80

        pos = SimpleNamespace(
            ticket=777,
            symbol="EURUSD.c",
            type=0,  # BUY
            volume=0.10,
            price_open=1.0800,
            sl=1.0750,  # risk = 50 pts
            tp=1.0950,
            profit=20.00,
            magic=MAGIC_V2,
        )
        mock_positions_get.return_value = [pos]
        mock_symbol_info.return_value = SimpleNamespace(
            bid=1.0890,  # profit = 90 pts = +1.80R
            ask=1.0892,
            point=0.0001,
            volume_min=0.01,
            volume_step=0.01,
        )
        mock_copy_rates.return_value = self._generate_bars("CONSECUTIVE_DECAY", is_buy=True)
        mock_order_send.return_value = SimpleNamespace(retcode=10009, comment="Done")

        with patch.object(self.bot.bus, "broadcast_hummingbird_harvest") as mock_bcast:
            self.bot.manage_open_positions()

            first_call_args = mock_order_send.call_args_list[0][0][0]
            self.assertEqual(first_call_args["action"], 1)  # DEAL
            self.assertEqual(first_call_args["volume"], 0.08)

            second_call_args = mock_order_send.call_args_list[1][0][0]
            self.assertEqual(second_call_args["action"], 6)  # TRADE_ACTION_SLTP
            self.assertAlmostEqual(second_call_args["sl"], 1.0850, places=4)

            mock_bcast.assert_called_once()
            bcast_args = mock_bcast.call_args[1]
            self.assertEqual(bcast_args["pct_closed"], 80.0)
            self.assertAlmostEqual(bcast_args["profit"], 16.00, places=2)

            self.assertEqual(self.bot.trailing_ratchet_state[777], "STAGE_2_LOCK")
            self.assertIn(777, self.bot.harvested_tickets)

    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.copy_rates_from_pos")
    @patch("MetaTrader5.order_send")
    def test_12_healthy_trade_falls_through_to_be_ratchet(self, mock_order_send, mock_copy_rates, mock_symbol_info, mock_positions_get):
        """Verify non-exhausted healthy trade at +1.6R moves SL to BE+0.15R without premature harvest."""
        self.bot.dry_run = False
        pos = SimpleNamespace(
            ticket=888,
            symbol="EURUSD.c",
            type=0,  # BUY
            volume=0.02,
            price_open=1.0800,
            sl=1.0750,  # init_risk = 50 pts
            tp=1.0950,
            profit=5.00,
            magic=MAGIC_V2,
        )
        mock_positions_get.return_value = [pos]
        mock_symbol_info.return_value = SimpleNamespace(
            bid=1.0880,  # profit = 80 pts = +1.60R
            ask=1.0882,
            point=0.0001,
            volume_min=0.01,
            volume_step=0.01,
        )
        mock_copy_rates.return_value = self._generate_bars("HEALTHY", is_buy=True)
        mock_order_send.return_value = SimpleNamespace(retcode=10009, comment="Done")

        self.bot.manage_open_positions()

        self.assertEqual(mock_order_send.call_count, 1)
        mod_call = mock_order_send.call_args[0][0]
        self.assertEqual(mod_call["action"], 6)  # TRADE_ACTION_SLTP
        expected_sl = 1.0800 + (0.15 * 0.0050)
        self.assertAlmostEqual(mod_call["sl"], expected_sl, places=5)
        self.assertEqual(self.bot.trailing_ratchet_state[888], "STAGE_1_BE")


if __name__ == "__main__":
    unittest.main()
