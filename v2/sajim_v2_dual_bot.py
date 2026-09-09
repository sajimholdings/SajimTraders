"""
========================================================================================
           SAJIM HOLDINGS V2 — DUAL-ENGINE PRODUCTION BOT (v2/sajim_v2_dual_bot.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Canonical 7-Stage Quantitative Pipeline (V2 Architecture):
    DATA -> MATURITY ENGINE -> PLUGGABLE CARTRIDGES -> GATEKEEPER -> ENTRY -> ASYMMETRIC MANAGEMENT -> PNL

Integrated Strategies:
  1. YoungSurgeContinuation  : Rides institutional breakouts during early trend lifecycles (maturity <= 0.60).
  2. ExhaustionMeanReversion : Fades dying trends back to HMA-50 equilibrium (maturity >= 1.00).

Harmony Features:
  - Magic Number 888222 (isolated from V1's 777999).
  - Consults CoexistenceGatekeeper to eliminate trade collisions, margin exhaustion, and directional conflicts.
  - Asymmetric Two-Stage Ratchet (+1.5R BE+0.15R, +2.2R Lock +1.0R Net Profit).
========================================================================================
"""

import os
import sys
import time
import math
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
from core.lot_calculator import UniversalLotCalculator
from core.beep_broadcast import BeepBroadcastBus
from v2.strategy_base import BaseStrategyCartridge, StrategySignal
from v2.strategies.young_surge_continuation import YoungSurgeContinuation
from v2.strategies.exhaustion_mean_reversion import ExhaustionMeanReversion
from v2.strategies.mirage_liquidity_sweep import MirageLiquiditySweepCartridge
from v2.coexistence import CoexistenceGatekeeper, MAGIC_V2

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
        base_risk_fraction: float = 0.012,       # 1.2% base risk per trade
        max_risk_fraction: float = 0.018,        # 1.8% hard cap on win streaks
        streak_expansion_rate: float = 0.10,     # +10% lot expansion per win
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.base_risk = base_risk_fraction
        self.max_risk = max_risk_fraction
        self.streak_rate = streak_expansion_rate
        self.dry_run = dry_run

        self.gatekeeper = gatekeeper or CoexistenceGatekeeper()
        self.bus = BeepBroadcastBus()

        # Pluggable Strategy Cartridges Registry
        self.cartridges: List[BaseStrategyCartridge] = [
            YoungSurgeContinuation(enabled=True),
            ExhaustionMeanReversion(enabled=True),
            MirageLiquiditySweepCartridge(enabled=True),
        ]

        # Monitored Universe (Derived from Centralized Master Whitelist JSON)
        from core.whitelist_manager import get_whitelist_manager
        self.wl_mgr = get_whitelist_manager()
        self.target_symbols = self.wl_mgr.get_live_trading_universe()
        self.universe: List[str] = []

        # Execution & Ratchet State
        self.consecutive_wins = 0
        self.total_trades_taken = 0
        self.session_pnl = 0.0
        self.processed_deal_tickets: Set[int] = set()
        self.trailing_ratchet_state: Dict[int, str] = {}  # ticket -> stage ('STAGE_1_BE', 'STAGE_2_LOCK')
        self.symbol_cooldowns: Dict[str, datetime] = {}

    def register_cartridge(self, cartridge: BaseStrategyCartridge) -> None:
        """Plugs in a new strategy cartridge dynamically."""
        self.cartridges.append(cartridge)
        logger.info(f"[+] Plugged in Strategy Cartridge: {cartridge.name}")

    def connect(self, target_account: Optional[int] = None) -> bool:
        """Initializes MT5 terminal connection and enables universe symbols."""
        if not mt5.initialize(path=self.terminal_path, timeout=15000):
            logger.error(f"Cannot initialize MT5: {mt5.last_error()}")
            return False

        broker_cfg = {}
        cfg_path = os.path.join(ROOT_DIR, "config", "broker_config.json")
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

        # Auto-resolve broker symbol conventions (.c, standard, etc.)
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
        logger.info(
            f"[+] Balance: {acc.balance:.2f} {acc.currency} | Equity: {acc.equity:.2f} | "
            f"Free Margin: {acc.margin_free:.2f} | Leverage: 1:{acc.leverage}"
        )
        logger.info(f"[+] Active V2 Prime Universe ({len(self.universe)} Assets): {self.universe}")
        logger.info(f"[+] Loaded {len(self.cartridges)} Pluggable Strategies: {[c.name for c in self.cartridges]}")
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

                # Notify cartridges
                for cart in self.cartridges:
                    cart.on_trade_closed(d.position_id, d.profit)

                if d.profit > 0.05:
                    self.consecutive_wins += 1
                    logger.info(f"[🎉 V2 WIN] Deal #{d.ticket} {d.symbol} closed with +${d.profit:.2f}. Streak: {self.consecutive_wins} wins.")
                elif d.profit < -0.05:
                    self.consecutive_wins = 0
                    self.symbol_cooldowns[d.symbol] = datetime.now() + timedelta(minutes=30)
                    logger.info(f"[⚠️ V2 LOSS] Deal #{d.ticket} {d.symbol} closed with -${abs(d.profit):.2f}. Cooldown applied (30m).")

    def manage_open_positions(self) -> None:
        """
        STAGE 6: ASYMMETRIC MANAGEMENT (Zero Premature Micro-Milking).
        - +1.5R: Move SL to Break-Even +0.15R (safe scratch/small win).
        - +2.2R: Trail SL to Lock in +1.0R Net Profit.
        - +3.0R: Full Take Profit harvest.
        """
        positions = [p for p in (mt5.positions_get() or []) if p.magic == MAGIC_V2]
        for pos in positions:
            sym_info = mt5.symbol_info(pos.symbol)
            if not sym_info:
                continue

            is_buy = pos.type == mt5.POSITION_TYPE_BUY
            cur_price = sym_info.bid if is_buy else sym_info.ask
            open_price = pos.price_open
            sl_price = pos.sl

            init_risk = abs(open_price - sl_price) if sl_price > 0 else (sym_info.point * 150)
            if init_risk <= 0:
                continue

            profit_dist = (cur_price - open_price) if is_buy else (open_price - cur_price)
            profit_r = profit_dist / init_risk

            current_ratchet = self.trailing_ratchet_state.get(pos.ticket, "INITIAL")

            # Stage 2: Lock in +1.0R Net Profit when trade reaches +2.2R
            if profit_r >= 2.20 and current_ratchet != "STAGE_2_LOCK":
                new_sl = (open_price + (1.0 * init_risk)) if is_buy else (open_price - (1.0 * init_risk))
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🔒 V2 PROFIT LOCK] Locked +1.0R Net Profit on #{pos.ticket} {pos.symbol} (current profit: +{profit_r:.2f}R).")
                    self.trailing_ratchet_state[pos.ticket] = "STAGE_2_LOCK"

            # Stage 1: Move to Break-Even +0.15R when trade reaches +1.5R
            elif profit_r >= 1.50 and current_ratchet == "INITIAL":
                new_sl = (open_price + (0.15 * init_risk)) if is_buy else (open_price - (0.15 * init_risk))
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🛡️ V2 BREAK-EVEN RATCHET] Secured BE+0.15R on #{pos.ticket} {pos.symbol} (current profit: +{profit_r:.2f}R).")
                    self.trailing_ratchet_state[pos.ticket] = "STAGE_1_BE"

    def execute_signal(self, sig: StrategySignal) -> bool:
        """Sizes order and dispatches to MT5 trade server with Magic 888222."""
        acc = mt5.account_info()
        if not acc:
            return False

        # Dynamic Sizing based on winning streaks
        streak_mult = (1.0 + self.streak_rate) ** min(self.consecutive_wins, 4)
        dynamic_risk = min(self.max_risk, self.base_risk * streak_mult)

        lot, risk_cash, specs = UniversalLotCalculator.calculate_lot(
            symbol=sig.symbol,
            equity=acc.equity,
            risk_fraction=dynamic_risk,
            entry_price=sig.entry_price,
            stop_price=sig.stop_loss,
        )

        order_type = mt5.ORDER_TYPE_BUY if sig.action == "BUY" else mt5.ORDER_TYPE_SELL

        if self.dry_run:
            logger.info(
                f"[DRY RUN V2 ENTRY] {sig.strategy_name} | {sig.action} {lot} {sig.symbol} @ {sig.entry_price:.5f} | "
                f"SL: {sig.stop_loss:.5f} | TP: {sig.take_profit:.5f} (1:{sig.risk_reward}R) | Reason: {sig.reason}"
            )
            return True

        for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
            order_req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": sig.symbol,
                "volume": float(lot),
                "type": order_type,
                "price": float(sig.entry_price),
                "sl": float(sig.stop_loss),
                "tp": float(sig.take_profit),
                "deviation": 20,
                "magic": MAGIC_V2,
                "comment": f"Sajim_V2_{sig.strategy_name[:10]}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            res = mt5.order_send(order_req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(
                    f"[🚀 V2 ORDER EXECUTED] #{res.order} {sig.action} {lot} {sig.symbol} @ {sig.entry_price:.5f} | "
                    f"SL: {sig.stop_loss:.5f} | TP: {sig.take_profit:.5f} | Strategy: {sig.strategy_name}"
                )
                self.total_trades_taken += 1
                try:
                    self.bus.broadcast_v2_trade_executed(
                        ticket=res.order,
                        symbol=sig.symbol,
                        action=sig.action,
                        lot=lot,
                        entry=sig.entry_price,
                        sl=sig.stop_loss,
                        tp=sig.take_profit,
                        strategy_name=sig.strategy_name,
                        maturity_info=sig.metadata,
                    )
                except Exception as b_err:
                    logger.warning(f"Failed to broadcast V2 trade execution: {b_err}")
                for cart in self.cartridges:
                    if cart.name == sig.strategy_name:
                        cart.on_trade_opened(res.order, sig)
                return True
            elif res and "Unsupported filling mode" in (res.comment or ""):
                continue
            else:
                err = res.comment if res else mt5.last_error()
                logger.warning(f"[!] V2 Order failed on {sig.symbol}: {err}")
                return False

        return False

    def scan_and_evaluate(self) -> None:
        """Scans all registered symbols and timeframes against each strategy cartridge."""
        timeframes = ["M5", "M15", "H1"]
        for sym in self.universe:
            # Check symbol cooldown
            now = datetime.now()
            cooldown = self.symbol_cooldowns.get(sym)
            if cooldown and cooldown > now:
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

                # Run each pluggable strategy cartridge
                for cart in self.cartridges:
                    if not cart.enabled:
                        continue

                    signal = cart.evaluate(symbol=sym, timeframe=tf_label, bars=bars, market_info=market_info)
                    if signal:
                        # 0. Empirical Truth Vault Forward Tracking (Catalogue Expansion)
                        try:
                            from core.signal_truth_tester import get_signal_truth_tester
                            get_signal_truth_tester().register_signal(
                                strategy_name=signal.strategy_name,
                                symbol=signal.symbol,
                                timeframe=signal.timeframe,
                                action=signal.action,
                                entry_price=signal.entry_price,
                                stop_loss=signal.stop_loss,
                                take_profit=signal.take_profit,
                                risk_reward=signal.risk_reward,
                                confidence=signal.confidence,
                                metadata=signal.metadata,
                            )
                        except Exception as t_err:
                            logger.debug(f"Truth logging error: {t_err}")

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
                            )
                        except Exception as b_err:
                            logger.debug(f"V2 broadcast error: {b_err}")

                        # Request clearance from Coexistence Gatekeeper!
                        cleared, reason = self.gatekeeper.check_pre_entry_clearance(
                            bot_name="V2",
                            symbol=signal.symbol,
                            action=signal.action,
                        )
                        if cleared:
                            executed = self.execute_signal(signal)
                            if executed:
                                return  # Max 1 entry per scan cycle to prevent cluster floods
                        else:
                            logger.debug(f"[V2 Gatekeeper Block] {signal.symbol} {signal.action} rejected: {reason}")

    def run_iteration(self) -> None:
        """Single complete operational cycle."""
        self.sync_pnl_and_streaks()
        self.manage_open_positions()
        self.scan_and_evaluate()
