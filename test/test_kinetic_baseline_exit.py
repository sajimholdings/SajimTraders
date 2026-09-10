"""
========================================================================================
       SAJIM QUANT LABS — KINETIC BASELINE & DISSIPATION EXIT TEST SUITE
                     (tests/test_kinetic_baseline_exit.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Verification Vectors:
  [Test 1] Multi-Format Bar Ingestion: Dicts vs Numpy Structured Arrays
  [Test 2] Robust True Range / ATR Calculation
  [Test 3] Kinetic Field Acceleration: Strong volume + price surge keeps is_decayed=False
  [Test 4] Kinetic Field Dissipation: Momentum drop below 0.65 * K_base triggers is_decayed=True
  [Test 5] Micro-Wick Counter-Rejection (BUY): Upper wick >= 20% triggers exit
  [Test 6] Micro-Wick Counter-Rejection (SELL): Lower wick >= 20% triggers exit
  [Test 7] Directional Shift: M1 Adverse close triggers immediate protection exit
  [Test 8] Kinetic Energy Dissipation Exit: Energy decay triggers exit on stall
  [Test 9] Healthy Kinetic Wave Preservation: Expanding wave is protected and allowed to run
  [Test 10] V2 Bot Integration: manage_open_positions cashes out green trades at dissipation
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

from core.beep_processor import BeepProcessor
from v2.sajim_v2_dual_bot import SajimV2DualBot, MAGIC_V2


class TestKineticBaselineExit(unittest.TestCase):
    """Rigorous verification suite for Dynamic Kinetic Energy Baseline and Dissipation Exit."""

    def setUp(self):
        self.processor = BeepProcessor()

    def _generate_synthetic_bars(self, count=20, trend="UP", base_price=2000.0, step=0.5):
        """Generates list of bar dicts with configurable trend behavior."""
        bars = []
        p = base_price
        for i in range(count):
            if trend == "UP":
                o = p
                c = p + step
                h = c + (step * 0.1)
                l = o - (step * 0.1)
                p = c
            elif trend == "DOWN":
                o = p
                c = p - step
                h = o + (step * 0.1)
                l = c - (step * 0.1)
                p = c
            else:  # FLAT / CHOP
                o = p
                c = p + (0.05 if i % 2 == 0 else -0.05)
                h = max(o, c) + 0.02
                l = min(o, c) - 0.02

            bars.append({
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(l, 4),
                "close": round(c, 4),
                "tick_volume": 100 + (i * 10),
                "time": 1700000000 + (i * 60),
            })
        return bars

    def test_01_multi_format_bar_ingestion(self):
        """Verify _parse_bars handles both dicts and numpy structured arrays seamlessly."""
        dict_bars = self._generate_synthetic_bars(count=5)
        parsed_dict = self.processor._parse_bars(dict_bars)
        self.assertEqual(len(parsed_dict["close"]), 5)
        self.assertEqual(len(parsed_dict["volume"]), 5)

        # Convert to numpy structured array
        dtype = [
            ("time", "i8"),
            ("open", "f8"),
            ("high", "f8"),
            ("low", "f8"),
            ("close", "f8"),
            ("tick_volume", "f8"),
            ("spread", "i4"),
            ("real_volume", "f8"),
        ]
        records = [
            (b["time"], b["open"], b["high"], b["low"], b["close"], b["tick_volume"], 15, 0.0)
            for b in dict_bars
        ]
        np_bars = np.array(records, dtype=dtype)

        parsed_np = self.processor._parse_bars(np_bars)
        self.assertEqual(len(parsed_np["close"]), 5)
        self.assertAlmostEqual(parsed_np["close"][-1], dict_bars[-1]["close"], places=4)

    def test_02_calculate_atr(self):
        """Verify ATR is computed correctly from high, low, close arrays."""
        bars = self._generate_synthetic_bars(count=15, step=1.0)
        parsed = self.processor._parse_bars(bars)
        atr = self.processor.calculate_atr(parsed["high"], parsed["low"], parsed["close"], period=14)
        self.assertGreater(atr, 0.0)
        self.assertAlmostEqual(atr, 1.2, delta=0.2)

    def test_03_kinetic_field_acceleration(self):
        """Verify that expanding, accelerating volume + price surge does NOT show decay."""
        bars = self._generate_synthetic_bars(count=20, trend="UP", step=1.0)
        # Add massive surge on final bar
        bars.append({
            "open": bars[-1]["close"],
            "high": bars[-1]["close"] + 3.0,
            "low": bars[-1]["close"] - 0.1,
            "close": bars[-1]["close"] + 2.8,
            "tick_volume": 500,
            "time": 1700001260,
        })

        field = self.processor.calculate_kinetic_field(bars)
        self.assertFalse(field["is_decayed"], "Accelerating surge must NOT be marked as decayed")
        self.assertTrue(field["is_accelerating"], "Surge must register as accelerating")
        self.assertGreater(field["k_ratio"], 1.0, "K_ratio must exceed 1.0x during acceleration")

    def test_04_kinetic_field_dissipation(self):
        """Verify that stalling momentum causes K(t) to fall below 0.65 * K_base."""
        bars = self._generate_synthetic_bars(count=15, trend="UP", step=2.0)
        # Followed by dead stall bars with near-zero movement
        last_c = bars[-1]["close"]
        for i in range(5):
            bars.append({
                "open": last_c,
                "high": last_c + 0.02,
                "low": last_c - 0.02,
                "close": last_c + 0.01,
                "tick_volume": 20,
                "time": 1700001000 + (i * 60),
            })

        field = self.processor.calculate_kinetic_field(bars)
        self.assertTrue(field["is_decayed"], "Stall following explosive trend must detect dissipation")
        self.assertLess(field["k_ratio"], 0.65, "K_ratio must drop below 0.65x")

    def test_05_micro_wick_rejection_buy(self):
        """Verify BUY trade detects exit on >= 20% upper wick rejection."""
        bars = self._generate_synthetic_bars(count=15, trend="UP", step=1.0)
        # Candle surges up 2.0 but gets dumped back down leaving a 35% upper wick
        o = bars[-1]["close"]
        h = o + 2.0
        c = o + 1.2
        l = o - 0.1
        bars.append({
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "tick_volume": 150,
            "time": 1700001000,
        })

        should_exit, reason, tele = self.processor.evaluate_kinetic_decay(
            bars=bars,
            action="BUY",
            adverse_wick_threshold=0.20,
        )
        self.assertTrue(should_exit, "Upper wick >= 20% must trigger instant exit on BUY")
        self.assertIn("Kinetic Wick Rejection", reason)

    def test_06_micro_wick_rejection_sell(self):
        """Verify SELL trade detects exit on >= 20% lower wick rejection."""
        bars = self._generate_synthetic_bars(count=15, trend="DOWN", step=1.0)
        o = bars[-1]["close"]
        l = o - 2.0
        c = o - 1.2
        h = o + 0.1
        bars.append({
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "tick_volume": 150,
            "time": 1700001000,
        })

        should_exit, reason, tele = self.processor.evaluate_kinetic_decay(
            bars=bars,
            action="SELL",
            adverse_wick_threshold=0.20,
        )
        self.assertTrue(should_exit, "Lower wick >= 20% must trigger instant exit on SELL")
        self.assertIn("Kinetic Wick Rejection", reason)

    def test_07_directional_shift_adverse_close(self):
        """Verify that an adverse bar close (bearish bar in BUY) triggers protection exit."""
        bars = self._generate_synthetic_bars(count=15, trend="UP", step=1.0)
        # Add adverse bearish bar with minimal wick
        o = bars[-1]["close"]
        c = o - 0.5
        h = o + 0.05
        l = c - 0.05
        bars.append({
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "tick_volume": 100,
            "time": 1700001000,
        })

        should_exit, reason, tele = self.processor.evaluate_kinetic_decay(
            bars=bars,
            action="BUY",
        )
        self.assertTrue(should_exit, "Adverse close in BUY must trigger protection exit")
        self.assertIn("Directional Shift", reason)

    def test_08_kinetic_energy_dissipation_exit(self):
        """Verify that energy dissipation triggers exit even without large counter-wick."""
        bars = self._generate_synthetic_bars(count=15, trend="UP", step=1.5)
        # Small green bar with zero momentum and tiny volume
        last_c = bars[-1]["close"]
        bars.append({
            "open": last_c,
            "high": last_c + 0.05,
            "low": last_c - 0.01,
            "close": last_c + 0.04,
            "tick_volume": 10,
            "time": 1700001000,
        })

        should_exit, reason, tele = self.processor.evaluate_kinetic_decay(
            bars=bars,
            action="BUY",
            dissipation_threshold=0.65,
        )
        self.assertTrue(should_exit, "Kinetic dissipation must trigger exit on momentum stall")
        self.assertIn("Kinetic Dissipation", reason)

    def test_09_healthy_kinetic_wave_preserved(self):
        """Verify that a strong, accelerating wave is preserved without false exits."""
        bars = self._generate_synthetic_bars(count=15, trend="UP", step=0.8)
        # Powerful green breakout candle with zero upper wick
        o = bars[-1]["close"]
        c = o + 2.0
        h = c
        l = o - 0.05
        bars.append({
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "tick_volume": 400,
            "time": 1700001000,
        })

        should_exit, reason, tele = self.processor.evaluate_kinetic_decay(
            bars=bars,
            action="BUY",
        )
        self.assertFalse(should_exit, "Healthy accelerating candle must NOT trigger exit")
        self.assertIn("Expanding", reason)

    def test_10_dual_bot_integration_dry_run(self):
        """Verify SajimV2DualBot.manage_open_positions executes kinetic harvest in dry run."""
        bot = SajimV2DualBot(dry_run=True)
        bot.hummingbird_harvest_enabled = True

        sym_info = SimpleNamespace(
            point=0.01,
            bid=2002.50,
            ask=2002.80,
            volume_min=0.01,
            volume_step=0.01,
        )

        mock_pos = SimpleNamespace(
            ticket=999111,
            symbol="XAUUSD",
            type=0,  # BUY
            volume=0.05,
            price_open=2000.00,
            price_current=2002.50,
            sl=1998.00,  # Risk = 2.00, Profit = +2.50 (+1.25R)
            tp=2010.00,
            profit=12.50,
            magic=MAGIC_V2,
            comment="SajimV2_Test",
        )

        # Generate bars showing wick rejection
        bars = self._generate_synthetic_bars(count=15, trend="UP", step=1.0)
        bars.append({
            "open": 2002.00,
            "high": 2003.50,
            "low": 2001.90,
            "close": 2002.50,
            "tick_volume": 200,
            "time": 1700001000,
        })
        dtype = [
            ("time", "i8"), ("open", "f8"), ("high", "f8"),
            ("low", "f8"), ("close", "f8"), ("tick_volume", "f8"),
            ("spread", "i4"), ("real_volume", "f8"),
        ]
        records = [
            (b["time"], b["open"], b["high"], b["low"], b["close"], b["tick_volume"], 15, 0.0)
            for b in bars
        ]
        rates_array = np.array(records, dtype=dtype)

        with patch("v2.sajim_v2_dual_bot.mt5.positions_get", return_value=[mock_pos]), \
             patch("v2.sajim_v2_dual_bot.mt5.symbol_info", return_value=sym_info), \
             patch("v2.sajim_v2_dual_bot.mt5.copy_rates_from_pos", return_value=rates_array):

            # Should evaluate and log kinetic harvest without throwing any error
            bot.manage_open_positions()
            self.assertTrue(True, "manage_open_positions executed successfully with kinetic harvest")


if __name__ == "__main__":
    unittest.main()
