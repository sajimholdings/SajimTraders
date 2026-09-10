"""
========================================================================================
           SAJIM HOLDINGS V2 — DUAL-ENGINE PRODUCTION BOT (v2/sajim_v2_dual_bot.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Modular Canonical 7-Stage Quantitative Pipeline:
    DATA -> MATURITY ENGINE -> PLUGGABLE CARTRIDGES -> GATEKEEPER -> ENTRY -> ASYMMETRIC MANAGEMENT -> PNL

Decomposed Sub-Modules:
  - v2/risk/hummingbird.py     : M1 momentum exhaustion & peak extraction
  - v2/risk/ratchet.py         : Breakeven shield (+0.35R), early cuts, asymmetric ratchets
  - v2/execution/order_router.py: Dynamic sizing, micro-lot safeguarding, MT5 order dispatch
Modular Architecture: Master coordinator strictly < 280 lines.
========================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from core.beep_broadcast import BeepBroadcastBus
from core.expectancy_tracker import QuantExpectancyTracker
from core.beep_processor import BeepSnipeFilter
from core.trade_flight_recorder import get_flight_recorder
from core.whitelist_manager import get_whitelist_manager
from v2.strategy_base import BaseStrategyCartridge, StrategySignal
from v2.strategies.young_surge_continuation import YoungSurgeContinuation
from v2.strategies.exhaustion_mean_reversion import ExhaustionMeanReversion
from v2.strategies.mirage_liquidity_sweep import MirageLiquiditySweepCartridge
from v2.coexistence import CoexistenceGatekeeper, MAGIC_V2

# Sub-module imports
from v2.risk.hummingbird import HummingbirdEvaluator
from v2.risk.ratchet import V2PositionRiskManager
from v2.execution.order_router import V2OrderRouter

logger = logging.getLogger("SajimV2DualBot")


class SajimV2DualBot:
    """
    Modular, Cartridge-Driven V2 Production Bot.
    Runs harmoniously alongside Sajim V1 on the same terminal.
    """

    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    def __init__(
        self,
        gatekeeper: Optional[CoexistenceGatekeeper] = None,
        base_risk_fraction: float = 0.05,
        max_risk_fraction: float = 0.08,
        streak_expansion_rate: float = 0.25,
        hummingbird_harvest_enabled: bool = True,
        hummingbird_harvest_mode: str = "FULL",
        hummingbird_partial_ratio: float = 0.80,
        kinetic_exit_enabled: bool = True,
        snipe_filter: Optional[BeepSnipeFilter] = None,
        min_snipe_score: float = 55.0,
        min_snipe_rvol: float = 1.20,
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.base_risk = base_risk_fraction
        self.max_risk = max_risk_fraction
        self.streak_rate = streak_expansion_rate
        self.dry_run = dry_run

        self.gatekeeper = gatekeeper or CoexistenceGatekeeper()
        self.bus = BeepBroadcastBus()
        self.snipe_filter = snipe_filter or BeepSnipeFilter(
            min_snipe_score=min_snipe_score,
            min_relative_volume=min_snipe_rvol,
        )

        # Pluggable Strategy Cartridges Registry
        self.cartridges: List[BaseStrategyCartridge] = [
            YoungSurgeContinuation(enabled=True),
            ExhaustionMeanReversion(enabled=True),
            MirageLiquiditySweepCartridge(enabled=True),
        ]

        # Monitored Universe
        self.wl_mgr = get_whitelist_manager()
        self.target_symbols = self.wl_mgr.get_live_trading_universe()
        self.universe: List[str] = []

        # State tracking
        self.consecutive_wins = 0
        self.total_trades_taken = 0
        self.session_pnl = 0.0
        self.processed_deal_tickets: Set[int] = set()
        self.trailing_ratchet_state: Dict[int, str] = {}
        self.pending_reentry_symbols: Set[str] = set()
        self.harvested_tickets: Set[int] = set()
        self.symbol_cooldowns: Dict[str, datetime] = {}
        self.ev_trades_processed = 0

        # Sub-engine coordinators
        self.risk_manager = V2PositionRiskManager(
            bus=self.bus,
            trailing_ratchet_state=self.trailing_ratchet_state,
            harvested_tickets=self.harvested_tickets,
            pending_reentry_symbols=self.pending_reentry_symbols,
            hummingbird_harvest_enabled=hummingbird_harvest_enabled,
            hummingbird_harvest_mode=hummingbird_harvest_mode,
            hummingbird_partial_ratio=hummingbird_partial_ratio,
            kinetic_exit_enabled=kinetic_exit_enabled,
            dry_run=self.dry_run,
        )

        self.order_router = V2OrderRouter(
            bus=self.bus,
            base_risk=self.base_risk,
            max_risk=self.max_risk,
            streak_rate=self.streak_rate,
            dry_run=self.dry_run,
        )

    def register_cartridge(self, cartridge: BaseStrategyCartridge) -> None:
        """Plugs in a new strategy cartridge dynamically."""
        self.cartridges.append(cartridge)
        logger.info(f"[+] Plugged in Strategy Cartridge: {cartridge.name}")

    def connect(self, target_account: Optional[int] = None) -> bool:
        """Initializes MT5 connection and configures symbol universe."""
        if not mt5.initialize(path=self.terminal_path, timeout=5000):
            if not mt5.initialize():
                logger.error(f"Cannot initialize MT5: {mt5.last_error()}")
                return False

        cfg_path = os.path.join(ROOT_DIR, "config", "broker_config.json")
        broker_cfg = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    broker_cfg = json.load(f)
            except Exception:
                pass

        if target_account is None:
            target_account = broker_cfg.get("active_account")

        acc = mt5.account_info()
        if target_account is not None and (not acc or acc.login != target_account):
            pwd = broker_cfg.get("password") if target_account == broker_cfg.get("active_account") else None
            server_name = broker_cfg.get("server") if target_account == broker_cfg.get("active_account") else "Headway-Real"
            if pwd and server_name:
                mt5.login(login=target_account, password=pwd, server=server_name)
            acc = mt5.account_info()

        if not acc:
            logger.error("No active MT5 account found.")
            return False

        if target_account is not None and acc.login != target_account:
            logger.critical(f"[SECURITY LOCK] Connected to {acc.login} ({acc.server}), expected {target_account}. Aborting.")
            mt5.shutdown()
            return False

        self.universe = []
        for target in self.target_symbols:
            for candidate in (target, f"{target}.c", f"{target}_c", f"{target}c"):
                si = mt5.symbol_info(candidate)
                if si and si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    if not si.visible:
                        mt5.symbol_select(candidate, True)
                    self.universe.append(candidate)
                    break

        logger.info(f"[+] SAJIM V2 DUAL ENGINE CONNECTED: {acc.server} | Account: {acc.login}")
        logger.info(f"[+] Active V2 Prime Universe ({len(self.universe)} Assets): {self.universe}")
        return True

    def sync_pnl_and_streaks(self) -> None:
        """Synchronizes closed deals for Magic 888222 and updates streaks."""
        d_from = datetime.now() - timedelta(hours=6)
        d_to = datetime.now() + timedelta(minutes=5)
        deals = mt5.history_deals_get(d_from, d_to)
        if not deals:
            return

        for d in deals:
            if d.ticket in self.processed_deal_tickets or d.magic != MAGIC_V2:
                continue
            if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT):
                self.processed_deal_tickets.add(d.ticket)
                self.session_pnl += d.profit

                for cart in self.cartridges:
                    cart.on_trade_closed(d.position_id, d.profit)

                try:
                    get_flight_recorder().record_exit(
                        ticket=d.position_id,
                        exit_price=float(d.price),
                        banked_profit=float(d.profit),
                        exit_reason=str(d.comment or "DEAL_CLOSED"),
                    )
                except Exception:
                    pass

                if d.profit > 0.05:
                    self.consecutive_wins += 1
                    logger.info(f"[🎉 V2 WIN] #{d.ticket} {d.symbol} +${d.profit:.2f}. Streak: {self.consecutive_wins}")
                elif d.profit < -0.05:
                    self.consecutive_wins = 0
                    self.symbol_cooldowns[d.symbol] = datetime.now() + timedelta(minutes=3)
                    logger.info(f"[⚠️ V2 LOSS] #{d.ticket} {d.symbol} -${abs(d.profit):.2f}. Cooldown (3m).")

                if abs(d.profit) > 0.10:
                    self.ev_trades_processed += 1
                    if self.ev_trades_processed % 5 == 0:
                        stats = QuantExpectancyTracker().calculate_current_edge()
                        if "error" not in stats:
                            self.bus.broadcast_expectancy_report(stats)

    def check_hummingbird_exhaustion(self, pos: Any, profit_r: float, sym_info: Any) -> Tuple[bool, str]:
        """Backward-compatibility stub routing to HummingbirdEvaluator."""
        return HummingbirdEvaluator.check_exhaustion(pos, profit_r, sym_info)

    def manage_open_positions(self) -> None:
        """Delegates position management and ratchets to risk manager."""
        self.risk_manager.manage_positions()

    def execute_signal(self, sig: StrategySignal) -> bool:
        """Delegates signal execution to order router."""
        success = self.order_router.dispatch_signal(
            sig=sig,
            consecutive_wins=self.consecutive_wins,
            cartridges=self.cartridges,
        )
        if success:
            self.total_trades_taken += 1
        return success

    def scan_and_evaluate(self) -> None:
        """Scans all registered symbols and timeframes against each strategy cartridge."""
        current_targets = self.wl_mgr.get_live_trading_universe()
        if set(current_targets) != set(self.target_symbols) or not self.universe:
            self.target_symbols = current_targets
            self.universe = []
            for target in self.target_symbols:
                for candidate in (target, f"{target}.c", f"{target}_c", f"{target}c"):
                    si = mt5.symbol_info(candidate)
                    if si and si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                        if not si.visible:
                            mt5.symbol_select(candidate, True)
                        self.universe.append(candidate)
                        break

        timeframes = ["M1", "M5", "M15", "H1"]
        for sym in self.universe:
            now = datetime.now()
            if self.symbol_cooldowns.get(sym, now) > now:
                continue

            sym_info = mt5.symbol_info(sym)
            if not sym_info or not sym_info.visible:
                continue

            market_info = {
                "point": sym_info.point,
                "spread": sym_info.spread,
                "bid": sym_info.bid,
                "ask": sym_info.ask,
            }

            for tf_label in timeframes:
                tf_mt5 = self.TIMEFRAME_MAP.get(tf_label)
                if tf_mt5 is None:
                    continue

                rates = mt5.copy_rates_from_pos(sym, tf_mt5, 0, 150)
                if rates is None or len(rates) < 80:
                    continue

                bars = [
                    {
                        "time": int(r["time"]),
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "volume": float(r["tick_volume"]),
                    }
                    for r in rates
                ]

                for cart in self.cartridges:
                    if not cart.enabled:
                        continue

                    signal = cart.evaluate(symbol=sym, timeframe=tf_label, bars=bars, market_info=market_info)
                    if signal:
                        confirmed, eval_res = self.snipe_filter.evaluate_signal(
                            signal=signal,
                            bars=bars,
                            market_info=market_info,
                        )
                        if not confirmed:
                            continue

                        signal.metadata["beep_snipe"] = eval_res.to_dict()
                        signal.confidence = round(
                            min(1.0, (signal.confidence * 0.5) + (eval_res.composite_score / 200.0)), 2
                        )

                        # Broadcast V2 Trend Duration Signal
                        try:
                            mat = signal.metadata or {}
                            self.bus.broadcast_v2_signal(
                                symbol=signal.symbol,
                                timeframe=signal.timeframe,
                                action=signal.action,
                                strategy_name=signal.strategy_name,
                                entry=signal.entry_price,
                                sl=signal.stop_loss,
                                tp=signal.take_profit,
                                rr=signal.risk_reward,
                                trend_count=mat.get("trend_count", 0),
                                probable_length=mat.get("probable_length", 20.0),
                                maturity_ratio=mat.get("maturity_ratio", 0.0),
                                phase=mat.get("phase", "UNKNOWN"),
                                hma_val=mat.get("hma_val", signal.entry_price),
                                reason=signal.reason,
                                metadata=mat,
                            )
                        except Exception:
                            pass

                        cleared, reason = self.gatekeeper.check_pre_entry_clearance(
                            bot_name="V2",
                            symbol=signal.symbol,
                            action=signal.action,
                        )
                        if cleared:
                            executed = self.execute_signal(signal)
                            if executed:
                                return

    def run_iteration(self) -> None:
        """Single complete operational cycle."""
        self.sync_pnl_and_streaks()
        self.manage_open_positions()
        self.scan_and_evaluate()
        try:
            get_flight_recorder().audit_post_exits()
        except Exception:
            pass
