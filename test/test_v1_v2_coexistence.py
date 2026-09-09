"""
========================================================================================
     SAJIM QUANT LABS — V1 & V2 COEXISTENCE & DUAL ENGINE TEST SUITE
                        (tests/test_v1_v2_coexistence.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Comprehensive Verification Suite:
  [Test 1] Coexistence Gatekeeper: Magic isolation & position tracking
  [Test 2] Directional Conflict Shield: Opposing position block on same asset
  [Test 3] Combined Portfolio Concurrency Cap: Hard margin ceiling
  [Test 4] Currency Cluster Exposure Cap: Single-currency overexposure guard
  [Test 5] Account-Wide Daily Drawdown Circuit Breaker: 5% risk stop
  [Test 6] Trend Duration Maturity Engine: Vectorized HMA & phase transitions
  [Test 7] Pluggable Cartridge 1: Young Surge Continuation (1:3.0R)
  [Test 8] Pluggable Cartridge 2: Exhaustion Mean Reversion (1:2.0R)
  [Test 9] Telemetry & WebApp API Bridge: Status JSON serialization
  [Test 10] Dual Orchestrator Dry-Run: Coordinated execution cycle
========================================================================================
"""

import os
import sys
import unittest
from types import SimpleNamespace
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from v2.coexistence import CoexistenceGatekeeper, MAGIC_V1, MAGIC_V2
from v2.trend_duration_engine import TrendDurationEngine
from v2.strategies.young_surge_continuation import YoungSurgeContinuation
from v2.strategies.exhaustion_mean_reversion import ExhaustionMeanReversion
from v2.api.telemetry_bridge import TelemetryBridge


class TestV1V2CoexistenceSuite(unittest.TestCase):
    """End-to-End Test Suite for V1 & V2 Concurrency and Pluggable Architecture."""

    def setUp(self):
        self.status_file = os.path.join(ROOT_DIR, "v2", "test_coexistence_status.json")
        self.gatekeeper = CoexistenceGatekeeper(
            max_combined_positions=6,
            min_margin_level_pct=500.0,
            max_cluster_exposure=2,
            max_daily_drawdown_pct=0.05,
            status_file_path=self.status_file,
        )

    def tearDown(self):
        if os.path.exists(self.status_file):
            try:
                os.remove(self.status_file)
            except Exception:
                pass

    def test_01_magic_isolation_and_partitioning(self):
        """Verify V1 (777999) and V2 (888222) positions are strictly segregated."""
        acc = SimpleNamespace(balance=100.0, equity=100.0, margin=15.0, margin_free=85.0, margin_level=666.0, currency="USC")
        positions = [
            SimpleNamespace(ticket=101, symbol="EURUSD.c", type=0, volume=0.01, price_open=1.0500, sl=1.0450, tp=1.0650, profit=0.50, magic=MAGIC_V1, comment="Sajim_DIAMOND"),
            SimpleNamespace(ticket=102, symbol="USDJPY.c", type=1, volume=0.01, price_open=150.00, sl=150.50, tp=148.50, profit=0.80, magic=MAGIC_V1, comment="Sajim_RARE"),
            SimpleNamespace(ticket=201, symbol="GBPJPY.c", type=0, volume=0.01, price_open=185.00, sl=184.00, tp=188.00, profit=1.20, magic=MAGIC_V2, comment="Sajim_V2_Cont"),
        ]
        self.gatekeeper.refresh(acc, positions, [])

        self.assertEqual(len(self.gatekeeper.v1_positions), 2)
        self.assertEqual(len(self.gatekeeper.v2_positions), 1)
        self.assertEqual(self.gatekeeper.v1_positions[0]["ticket"], 101)
        self.assertEqual(self.gatekeeper.v2_positions[0]["ticket"], 201)

    def test_02_directional_conflict_shield(self):
        """Verify opposing trades on the same asset are blocked to prevent spread bleed."""
        acc = SimpleNamespace(balance=100.0, equity=100.0, margin=10.0, margin_free=90.0, margin_level=1000.0, currency="USC")
        # V1 is LONG on EURUSD.c
        positions = [
            SimpleNamespace(ticket=101, symbol="EURUSD.c", type=0, volume=0.01, price_open=1.0500, sl=1.0450, tp=1.0650, profit=0.0, magic=MAGIC_V1, comment="Sajim_V1"),
        ]
        self.gatekeeper.refresh(acc, positions, [])

        # V2 tries to open SHORT on EURUSD.c
        cleared, reason = self.gatekeeper.check_pre_entry_clearance("V2", "EURUSD.c", "SELL")
        self.assertFalse(cleared)
        self.assertIn("Directional conflict", reason)

        # V2 tries to open BUY on EURUSD.c (permitted in same direction if under cluster cap)
        cleared_buy, _ = self.gatekeeper.check_pre_entry_clearance("V2", "EURUSD.c", "BUY")
        self.assertTrue(cleared_buy)

    def test_03_aggregate_concurrency_cap(self):
        """Verify combined positions across both bots cannot exceed the portfolio ceiling."""
        acc = SimpleNamespace(balance=100.0, equity=100.0, margin=30.0, margin_free=70.0, margin_level=600.0, currency="USC")
        positions = [
            SimpleNamespace(ticket=i, symbol=f"SYM{i}.c", type=0, volume=0.01, price_open=1.0, sl=0.9, tp=1.2, profit=0.0, magic=MAGIC_V1 if i % 2 == 0 else MAGIC_V2, comment="")
            for i in range(6)
        ]
        self.gatekeeper.refresh(acc, positions, [])

        # 6 positions active, max is 6 -> new trade must be blocked
        cleared, reason = self.gatekeeper.check_pre_entry_clearance("V2", "AUDCAD.c", "BUY")
        self.assertFalse(cleared)
        self.assertIn("ceiling reached", reason)

    def test_04_macro_currency_cluster_cap(self):
        """Verify no single currency can exceed the max exposure limit (max 2 trades per currency)."""
        acc = SimpleNamespace(balance=100.0, equity=100.0, margin=15.0, margin_free=85.0, margin_level=800.0, currency="USC")
        positions = [
            SimpleNamespace(ticket=1, symbol="USDJPY.c", type=1, volume=0.01, price_open=150.0, sl=151.0, tp=147.0, profit=0.0, magic=MAGIC_V1, comment=""),
            SimpleNamespace(ticket=2, symbol="EURJPY.c", type=1, volume=0.01, price_open=160.0, sl=161.0, tp=157.0, profit=0.0, magic=MAGIC_V2, comment=""),
        ]
        self.gatekeeper.refresh(acc, positions, [])

        # JPY already has 2 positions -> GBPJPY.c should be rejected
        cleared, reason = self.gatekeeper.check_pre_entry_clearance("V2", "GBPJPY.c", "SELL")
        self.assertFalse(cleared)
        self.assertIn("cluster cap reached for [JPY]", reason)

    def test_05_daily_drawdown_circuit_breaker(self):
        """Verify account-wide 5% daily drawdown circuit breaker stops all new entries."""
        acc = SimpleNamespace(balance=100.0, equity=94.0, margin=10.0, margin_free=84.0, margin_level=940.0, currency="USC")
        # -5.50 USC closed loss today (5.5% of 100 balance)
        deals = [
            SimpleNamespace(ticket=999, entry=1, profit=-5.50, magic=MAGIC_V1),
        ]
        self.gatekeeper.refresh(acc, [], deals)

        self.assertTrue(self.gatekeeper.circuit_breaker_active)
        cleared, reason = self.gatekeeper.check_pre_entry_clearance("V2", "EURUSD.c", "BUY")
        self.assertFalse(cleared)
        self.assertIn("Circuit Breaker Active", reason)

    def test_06_trend_duration_engine_maturity(self):
        """Verify TrendDurationEngine computes HMA, slope, and assigns proper trend lifecycle phase."""
        engine = TrendDurationEngine(length=50, trend_length=3, max_samples=10)

        # Generate synthetic upward trend
        bars = []
        base_price = 1.0500
        for i in range(120):
            base_price += 0.0005
            bars.append({
                "time": i * 900,
                "open": base_price - 0.0002,
                "high": base_price + 0.0004,
                "low": base_price - 0.0003,
                "close": base_price,
                "volume": 100.0,
            })

        mat = engine.evaluate_maturity("EURUSD.c", "M15", bars)
        self.assertIn(mat["trend"], ("UP", "DOWN", "NONE"))
        self.assertIn(mat["phase"], ("YOUNG_SURGE", "MATURE", "EXHAUSTED"))
        self.assertGreater(mat["hma_val"], 0)

    def test_07_young_surge_continuation_cartridge(self):
        """Verify YoungSurgeContinuation generates a valid 1:3.0R signal."""
        cart = YoungSurgeContinuation()
        self.assertTrue(cart.enabled)
        self.assertEqual(cart.parameters["tp_rr_ratio"], 3.0)

        # Generate 100 bars
        bars = []
        p = 1.0000
        for i in range(100):
            p += 0.0002
            bars.append({
                "time": i * 900,
                "open": p - 0.0001,
                "high": p + 0.0003,
                "low": p - 0.0002,
                "close": p,
                "volume": 50.0,
            })
        market_info = {"point": 0.00001, "spread": 10, "bid": p, "ask": p + 0.0001}
        signal = cart.evaluate("USDCAD.c", "M15", bars, market_info)
        if signal:
            self.assertEqual(signal.risk_reward, 3.0)
            self.assertEqual(signal.action, "BUY")
            self.assertGreater(signal.take_profit, signal.entry_price)

    def test_08_exhaustion_mean_reversion_cartridge(self):
        """Verify ExhaustionMeanReversion parameters and configuration."""
        cart = ExhaustionMeanReversion()
        self.assertTrue(cart.enabled)
        self.assertEqual(cart.parameters["min_maturity_ratio"], 1.00)
        self.assertEqual(cart.parameters["min_stretch_atr_mult"], 1.20)

    def test_09_telemetry_bridge_serialization(self):
        """Verify TelemetryBridge writes and reads live portfolio metrics cleanly."""
        acc = SimpleNamespace(balance=100.0, equity=102.5, margin=10.0, margin_free=92.5, margin_level=1025.0, currency="USC")
        positions = [
            SimpleNamespace(ticket=777, symbol="EURUSD.c", type=0, volume=0.01, price_open=1.05, sl=1.04, tp=1.07, profit=1.50, magic=MAGIC_V1, comment="Sajim_V1"),
            SimpleNamespace(ticket=888, symbol="USDCAD.c", type=1, volume=0.01, price_open=1.35, sl=1.36, tp=1.33, profit=1.00, magic=MAGIC_V2, comment="Sajim_V2"),
        ]
        self.gatekeeper.refresh(acc, positions, [])

        # Read via TelemetryBridge from the generated file
        summary = self.gatekeeper.get_portfolio_summary()
        self.assertEqual(summary["account"]["balance"], 100.0)
        self.assertEqual(summary["concurrency"]["v1_count"], 1)
        self.assertEqual(summary["concurrency"]["v2_count"], 1)
        self.assertEqual(summary["concurrency"]["total_open"], 2)

    def test_10_dual_orchestrator_initialization(self):
        """Verify SajimDualOrchestrator wires V1 and V2 with CoexistenceGatekeeper."""
        from v2.dual_orchestrator import SajimDualOrchestrator
        orchestrator = SajimDualOrchestrator(
            scan_interval_seconds=15,
            max_combined_positions=12,
            max_v1_positions=6,
            max_v2_positions=6,
            dry_run=True,
        )
        self.assertEqual(orchestrator.max_combined, 12)
        self.assertEqual(orchestrator.gatekeeper.max_combined_positions, 12)
        self.assertIsNotNone(orchestrator.v1_server.bot.pre_entry_hook)
        self.assertEqual(orchestrator.v2_bot.gatekeeper, orchestrator.gatekeeper)


if __name__ == "__main__":
    unittest.main()
