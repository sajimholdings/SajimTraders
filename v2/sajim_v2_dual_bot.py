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
from core.expectancy_tracker import QuantExpectancyTracker
from core.beep_processor import BeepProcessor, BeepSnipeFilter, BeepSnipeEvaluation
from core.trade_flight_recorder import get_flight_recorder

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
        base_risk_fraction: float = 0.05,        # 5% base risk (~$3.70 per trade, survives 15 losses)
        max_risk_fraction: float = 0.08,         # 8% max cap on hot win streaks
        streak_expansion_rate: float = 0.25,     # +25% compounding per win
        hummingbird_harvest_enabled: bool = True, # Peak profit extraction on M1 momentum exhaustion
        hummingbird_harvest_mode: str = "FULL",  # "FULL" (100% close at peak) or "MASSIVE_PARTIAL" (80%) or "DYNAMIC"
        hummingbird_partial_ratio: float = 0.80, # Fraction to harvest if in MASSIVE_PARTIAL mode
        kinetic_exit_enabled: bool = True,       # Ultra-fast micro-scalp exit on kinetic energy baseline dissipation
        snipe_filter: Optional[BeepSnipeFilter] = None,
        min_snipe_score: float = 55.0,
        min_snipe_rvol: float = 1.20,
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.base_risk = base_risk_fraction
        self.max_risk = max_risk_fraction
        self.streak_rate = streak_expansion_rate
        self.hummingbird_harvest_enabled = hummingbird_harvest_enabled
        self.hummingbird_harvest_mode = hummingbird_harvest_mode.upper()
        self.hummingbird_partial_ratio = hummingbird_partial_ratio
        self.kinetic_exit_enabled = kinetic_exit_enabled
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

        # Monitored Universe (Derived from Centralized Master Whitelist JSON)
        from core.whitelist_manager import get_whitelist_manager
        self.wl_mgr = get_whitelist_manager()
        self.target_symbols = self.wl_mgr.get_live_trading_universe()
        self.universe: List[str] = []

        # Execution, Hummingbird & Ratchet State
        self.consecutive_wins = 0
        self.total_trades_taken = 0
        self.session_pnl = 0.0
        self.processed_deal_tickets: Set[int] = set()
        self.trailing_ratchet_state: Dict[int, str] = {}  # ticket -> stage ('STAGE_1_BE', 'STAGE_2_LOCK')
        self.pending_reentry_symbols: Set[str] = set()    # Assets standing by for discounted baseline re-entry
        self.harvested_tickets: Set[int] = set()          # Tickets that took partial harvest
        self.symbol_cooldowns: Dict[str, datetime] = {}
        self.ev_trades_processed = 0  # Counter to trigger EV reports

    def register_cartridge(self, cartridge: BaseStrategyCartridge) -> None:
        """Plugs in a new strategy cartridge dynamically."""
        self.cartridges.append(cartridge)
        logger.info(f"[+] Plugged in Strategy Cartridge: {cartridge.name}")

    def connect(self, target_account: Optional[int] = None) -> bool:
        """Initializes MT5 terminal connection and enables universe symbols."""
        if not mt5.initialize(path=self.terminal_path, timeout=5000):
            if not mt5.initialize():
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

                # Record flight blackbox exit and queue for post-exit tracking
                try:
                    get_flight_recorder().record_exit(
                        ticket=d.position_id,
                        exit_price=float(d.price),
                        banked_profit=float(d.profit),
                        exit_reason=str(d.comment or "DEAL_CLOSED"),
                    )
                except Exception as ex_err:
                    logger.warning(f"Failed to record flight exit: {ex_err}")

                if d.profit > 0.05:
                    self.consecutive_wins += 1
                    logger.info(f"[🎉 V2 WIN] Deal #{d.ticket} {d.symbol} closed with +${d.profit:.2f}. Streak: {self.consecutive_wins} wins.")
                elif d.profit < -0.05:
                    self.consecutive_wins = 0
                    self.symbol_cooldowns[d.symbol] = datetime.now() + timedelta(minutes=3)
                    logger.info(f"[⚠️ V2 LOSS] Deal #{d.ticket} {d.symbol} closed with -${abs(d.profit):.2f}. Scalp Cooldown applied (3m).")
                
                # Update EV Tracker every 5 closed trades
                if abs(d.profit) > 0.10:
                    self.ev_trades_processed += 1
                    if self.ev_trades_processed % 5 == 0:
                        tracker = QuantExpectancyTracker()
                        stats = tracker.calculate_current_edge()
                        if "error" not in stats:
                            self.bus.broadcast_expectancy_report(stats)

    def check_hummingbird_exhaustion(
        self,
        pos: Any,
        profit_r: float,
        sym_info: Any,
    ) -> Tuple[bool, str]:
        """
        Evaluates whether an active winning position (+1.50R <= profit_r <= +2.85R)
        has hit statistical M1 momentum exhaustion / velocity stalling / candle momentum decay,
        signaling an optimal Hummingbird Harvest at the peak before price retraces to the trailing stop.
        """
        # Hummingbird Peak Harvest activates strictly between +1.50R <= profit_r <= +2.85R
        if profit_r < 1.50:
            return False, ""

        # Query high-resolution M1 bars for microsecond momentum geometry
        rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M1, 0, 25)
        if rates is None or len(rates) < 10:
            return False, ""

        is_buy = (pos.type == mt5.POSITION_TYPE_BUY or pos.type == 0)
        cur_price = sym_info.bid if is_buy else sym_info.ask
        point = sym_info.point or 0.00001
        min_range = max(point * 5, 0.00002)

        bar_0 = rates[-1]  # In-progress / latest M1 bar
        bar_1 = rates[-2]  # Most recent closed M1 bar
        bar_2 = rates[-3]  # 2 bars ago

        rng_0 = max(min_range, float(bar_0['high'] - bar_0['low']))
        rng_1 = max(min_range, float(bar_1['high'] - bar_1['low']))

        # Compute Directional Wicks & Bodies
        if is_buy:
            wick_0 = float(bar_0['high'] - max(bar_0['open'], bar_0['close']))
            wick_ratio_0 = wick_0 / rng_0
            wick_1 = float(bar_1['high'] - max(bar_1['open'], bar_1['close']))
            wick_ratio_1 = wick_1 / rng_1

            body_0 = float(bar_0['close'] - bar_0['open'])  # Positive = Bullish
            body_1 = float(bar_1['close'] - bar_1['open'])
            body_2 = float(bar_2['close'] - bar_2['open'])

            adverse_close_0 = (body_0 < 0)
            adverse_close_1 = (body_1 < 0)
            micro_struct_break = (float(bar_0['close']) < float(bar_1['low']) and adverse_close_0)
        else:
            wick_0 = float(min(bar_0['open'], bar_0['close']) - bar_0['low'])
            wick_ratio_0 = wick_0 / rng_0
            wick_1 = float(min(bar_1['open'], bar_1['close']) - bar_1['low'])
            wick_ratio_1 = wick_1 / rng_1

            body_0 = float(bar_0['open'] - bar_0['close'])  # Positive = Bearish (Advancing in SELL)
            body_1 = float(bar_1['open'] - bar_1['close'])
            body_2 = float(bar_2['open'] - bar_2['close'])

            adverse_close_0 = (float(bar_0['close']) > float(bar_0['open']))
            adverse_close_1 = (float(bar_1['close']) > float(bar_1['open']))
            micro_struct_break = (float(bar_0['close']) > float(bar_1['high']) and adverse_close_0)

        # Baseline & ATR Computation (14-bar M1 Window)
        closes_14 = [float(r['close']) for r in rates[-14:]]
        m1_baseline = sum(closes_14) / len(closes_14)
        m1_tr = [
            max(
                float(rates[i]['high'] - rates[i]['low']),
                abs(float(rates[i]['high'] - rates[i-1]['close'])),
                abs(float(rates[i]['low'] - rates[i-1]['close']))
            )
            for i in range(-14, 0)
        ]
        m1_atr = max(sum(m1_tr) / len(m1_tr), point * 5)

        dist_atr = ((cur_price - m1_baseline) if is_buy else (m1_baseline - cur_price)) / m1_atr

        # Volume Profile Analysis (Climax Absorption)
        vols = [float(r['tick_volume']) for r in rates[-10:]]
        avg_vol = sum(vols) / len(vols) if vols else 1.0
        vol_0 = float(bar_0['tick_volume'])
        vol_1 = float(bar_1['tick_volume'])

        # ---------------------------------------------------------------------
        # VECTOR 1: M1 Counter-Wick Supply/Demand Absorption (Peak Rejection)
        # ---------------------------------------------------------------------
        if profit_r >= 1.80 and wick_ratio_0 >= 0.35:
            return True, f"M1 Counter-Wick Rejection ({wick_ratio_0*100:.1f}%) at +{profit_r:.2f}R"

        if profit_r >= 1.50 and wick_ratio_0 >= 0.45:
            return True, f"M1 Severe Rejection Wick ({wick_ratio_0*100:.1f}%) at +{profit_r:.2f}R"

        if profit_r >= 1.50 and wick_ratio_1 >= 0.40 and adverse_close_0:
            return True, f"M1 Peak Wick Invalidation ({wick_ratio_1*100:.1f}%) with Adverse Turn at +{profit_r:.2f}R"

        # ---------------------------------------------------------------------
        # VECTOR 2: M1 Candle Momentum Decay & Velocity Stalling
        # ---------------------------------------------------------------------
        # Scenario A: Two consecutive adverse M1 bars at peak
        if profit_r >= 1.50 and adverse_close_0 and adverse_close_1:
            return True, f"M1 Consecutive Momentum Decay (2 Adverse Bars) at +{profit_r:.2f}R"

        # Scenario B: Sudden thrust collapse (body shrunk by > 70% into negative close)
        if profit_r >= 1.50 and body_2 > (m1_atr * 0.80) and body_1 < (body_2 * 0.30) and adverse_close_0:
            return True, f"M1 Velocity Stalling (Thrust Decay {body_2/point:.0f}pts -> {body_0/point:.0f}pts) at +{profit_r:.2f}R"

        # ---------------------------------------------------------------------
        # VECTOR 3: M1 Micro-Structure Break (CHoCH / Low or High Engulfing)
        # ---------------------------------------------------------------------
        if profit_r >= 1.50 and micro_struct_break:
            target_side = "Prev M1 Low" if is_buy else "Prev M1 High"
            return True, f"M1 Micro-Structure Break (Closed Beyond {target_side}) at +{profit_r:.2f}R"

        # ---------------------------------------------------------------------
        # VECTOR 4: M1 Baseline Envelope Overextension Stretch (Mean Reversion Risk)
        # ---------------------------------------------------------------------
        if profit_r >= 1.70 and dist_atr >= 2.20 and (wick_ratio_0 >= 0.25 or adverse_close_0):
            return True, f"M1 Baseline Envelope Stretch ({dist_atr:.1f}x ATR) at +{profit_r:.2f}R"

        # ---------------------------------------------------------------------
        # VECTOR 5: M1 Climax Volume Absorption (Exhaustion Pin / Wall Hit)
        # ---------------------------------------------------------------------
        if profit_r >= 1.50 and (vol_0 >= 2.0 * avg_vol or vol_1 >= 2.0 * avg_vol):
            if wick_ratio_0 >= 0.30 or wick_ratio_1 >= 0.30 or adverse_close_0:
                peak_vol = max(vol_0, vol_1)
                return True, f"M1 Climax Volume Absorption ({peak_vol/avg_vol:.1f}x Vol) at +{profit_r:.2f}R"

        # ---------------------------------------------------------------------
        # VECTOR 6: Elite Zone Profit Defense (+2.20R to +2.85R Peak Defense)
        # ---------------------------------------------------------------------
        if profit_r >= 2.20 and (adverse_close_0 or wick_ratio_0 >= 0.25):
            return True, f"M1 Peak Profit Defense Stall at +{profit_r:.2f}R"

        return False, ""

    def manage_open_positions(self) -> None:
        """
        STAGE 6: ASYMMETRIC MANAGEMENT & HUMMINGBIRD HARVESTING.
        - Hummingbird Harvest: Quick peak harvest (+1.5R to +2.5R+) on M1 velocity stalling / exhaustion
          rather than waiting for price to retrace all the way to the trailing stop.
        - Stage 2 Ratchet: Lock in +1.0R Net Profit when trade reaches +2.2R.
        - Stage 1 Ratchet: Move SL to Break-Even +0.15R when trade reaches +1.5R.
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

            # Record high-resolution micro-telemetry sample in TradeFlightRecorder
            try:
                get_flight_recorder().record_tick(
                    ticket=pos.ticket,
                    current_price=float(cur_price),
                    current_profit=float(pos.profit),
                    status_tag=f"RATCHET_{current_ratchet}",
                )
            except Exception:
                pass

            # -----------------------------------------------------------------
            # 0. EARLY BREAKEVEN SHIELD (+0.35R) - CAPITAL PRESERVATION FIRST
            # -----------------------------------------------------------------
            # As soon as trade reaches +0.35R, move SL to Breakeven (+0.05R to cover costs).
            # Eliminates full -1.00R losses on trades that started moving in our favor.
            if profit_r >= 0.35 and current_ratchet == "INITIAL":
                be_offset = max(sym_info.point * 15, init_risk * 0.05)
                new_sl = (open_price + be_offset) if is_buy else (open_price - be_offset)
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🛡️ V2 BREAKEVEN SHIELD] Moved SL to Breakeven (+0.05R) on #{pos.ticket} {pos.symbol} (profit: +{profit_r:.2f}R). Downside risk eliminated!")
                    self.trailing_ratchet_state[pos.ticket] = "STAGE_0_BE"
                    current_ratchet = "STAGE_0_BE"
                    try:
                        self.bus.broadcast_ratchet_update(
                            ticket=pos.ticket,
                            symbol=pos.symbol,
                            stage="BREAK_EVEN",
                            new_sl=float(new_sl),
                            r_level=f"+{profit_r:.2f}R",
                        )
                    except Exception:
                        pass

            # -----------------------------------------------------------------
            # 0B. EARLY REVERSAL EUTHANASIA (-0.35R) - ACTIVE LOSS CUTTING
            # -----------------------------------------------------------------
            # If trade drops to -0.35R and momentum violently reverses against us,
            # cut early at -0.35R instead of absorbing a full -1.00R stop loss!
            if profit_r <= -0.35:
                rates_rev = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M1, 0, 5)
                if rates_rev is not None and len(rates_rev) >= 3:
                    bar_0 = rates_rev[-1]
                    bar_1 = rates_rev[-2]
                    is_adverse_turn = False
                    if is_buy:
                        body_0 = float(bar_0['open'] - bar_0['close'])
                        body_1 = float(bar_1['open'] - bar_1['close'])
                        if body_0 > 0 and body_1 > 0 and float(bar_0['close']) < float(bar_1['low']):
                            is_adverse_turn = True
                    else:
                        body_0 = float(bar_0['close'] - bar_0['open'])
                        body_1 = float(bar_1['close'] - bar_1['open'])
                        if body_0 > 0 and body_1 > 0 and float(bar_0['close']) > float(bar_1['high']):
                            is_adverse_turn = True

                    if is_adverse_turn:
                        order_type_close = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                        for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                            close_req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": pos.ticket,
                                "symbol": pos.symbol,
                                "volume": float(pos.volume),
                                "type": order_type_close,
                                "price": float(cur_price),
                                "deviation": 30,
                                "magic": MAGIC_V2,
                                "comment": "Adverse_Cut",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": filling,
                            }
                            res = mt5.order_send(close_req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                logger.info(f"[🚨 EARLY CUT] #{pos.ticket} {pos.symbol} cut at -{abs(profit_r):.2f}R on adverse momentum reversal (saved -{1.0 - abs(profit_r):.2f}R loss)!")
                                self.trailing_ratchet_state.pop(pos.ticket, None)
                                break
                        continue

            # -----------------------------------------------------------------
            # 0C. KINETIC MOMENTUM DECREMENT & EXHAUSTION EXIT (>= +0.65R)
            # -----------------------------------------------------------------
            # Let winners run! Only exit when trade is solidly profitable (>= +0.65R)
            # AND shows true structural momentum deceleration / adverse wick rejection (>= 40%).
            if self.kinetic_exit_enabled and profit_r >= 0.65 and (profit_r < 1.50 or not self.hummingbird_harvest_enabled):
                rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M1, 0, 15)
                should_fast_exit = False
                exit_reason = ""

                if rates is not None and len(rates) >= 2:
                    action_dir = "BUY" if is_buy else "SELL"
                    should_fast_exit, decay_reason, k_tele = BeepProcessor.evaluate_kinetic_decay(
                        bars=rates,
                        action=action_dir,
                        atr=None,
                        adverse_wick_threshold=0.40,
                        dissipation_threshold=0.70,
                    )
                    if should_fast_exit:
                        exit_reason = decay_reason

                if should_fast_exit:
                    if self.dry_run:
                        logger.info(f"[DRY RUN ⚡ KINETIC HARVEST] #{pos.ticket} {pos.symbol} cashed out (+{profit_r:.2f}R) | Reason: {exit_reason}")
                        continue
                    order_type_close = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                    for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                        close_req = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "position": pos.ticket,
                            "symbol": pos.symbol,
                            "volume": float(pos.volume),
                            "type": order_type_close,
                            "price": float(cur_price),
                            "deviation": 30,
                            "magic": MAGIC_V2,
                            "comment": f"Kinetic_{exit_reason[:15]}",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": filling,
                        }
                        res = mt5.order_send(close_req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"[⚡ KINETIC HARVEST] #{pos.ticket} {pos.symbol} cashed out (+{profit_r:.2f}R) | Reason: {exit_reason}")
                            try:
                                self.bus.broadcast_deal_closed(
                                    deal_ticket=res.order,
                                    symbol=pos.symbol,
                                    result="WIN",
                                    profit=pos.profit,
                                    streak=self.consecutive_wins,
                                    reason=f"Kinetic Momentum Decrement: {exit_reason} (+{profit_r:.2f}R)",
                                )
                            except Exception:
                                pass
                            self.trailing_ratchet_state.pop(pos.ticket, None)
                            break
                    continue

            # -----------------------------------------------------------------
            # 1. THE HUMMINGBIRD PEAK HARVEST (M1 Velocity Exhaustion Protection)
            # -----------------------------------------------------------------
            if self.hummingbird_harvest_enabled:
                already_partial = pos.ticket in self.harvested_tickets
                # If already partial harvested, only close remainder if in elite zone (>= +2.2R) and stalling
                should_check = (not already_partial) or (profit_r >= 2.20)

                if should_check:
                    is_exhausted, exhaust_reason = self.check_hummingbird_exhaustion(pos, profit_r, sym_info)
                    if is_exhausted:
                        min_v = sym_info.volume_min or 0.01
                        step_v = sym_info.volume_step or 0.01

                        if self.hummingbird_harvest_mode == "FULL" or already_partial or pos.volume <= min_v:
                            close_vol = float(pos.volume)
                            is_full = True
                        elif self.hummingbird_harvest_mode == "DYNAMIC":
                            if profit_r >= 2.20 or pos.volume < 0.04:
                                close_vol = float(pos.volume)
                                is_full = True
                            else:
                                raw_vol = pos.volume * self.hummingbird_partial_ratio
                                close_vol = max(min_v, math.floor(raw_vol / step_v) * step_v)
                                close_vol = round(close_vol, 2)
                                rem_vol = round(pos.volume - close_vol, 2)
                                is_full = (rem_vol < min_v or close_vol >= pos.volume)
                                if is_full:
                                    close_vol = float(pos.volume)
                        else:  # MASSIVE_PARTIAL
                            raw_vol = pos.volume * self.hummingbird_partial_ratio
                            close_vol = max(min_v, math.floor(raw_vol / step_v) * step_v)
                            close_vol = round(close_vol, 2)
                            rem_vol = round(pos.volume - close_vol, 2)
                            is_full = (rem_vol < min_v or close_vol >= pos.volume)
                            if is_full:
                                close_vol = float(pos.volume)

                        pct_closed = 100.0 if is_full else round(close_vol / pos.volume * 100.0, 1)
                        banked_profit = round(pos.profit if is_full else (pos.profit * (close_vol / pos.volume)), 2)
                        mode_label = "100% Closed" if is_full else f"Massive Partial ({pct_closed:.0f}%)"

                        if self.dry_run:
                            logger.info(
                                f"[DRY RUN 🦅 V2 HUMMINGBIRD] #{pos.ticket} {pos.symbol} harvested at PEAK! "
                                f"+${banked_profit:.2f} USD (+{profit_r:.2f}R) | Vol: {close_vol}/{pos.volume} ({mode_label}) | Reason: {exhaust_reason}"
                            )
                            try:
                                self.bus.broadcast_hummingbird_harvest(
                                    ticket=pos.ticket,
                                    symbol=pos.symbol,
                                    profit=banked_profit,
                                    r_multiple=profit_r,
                                    reason=f"[DRY RUN] {exhaust_reason}",
                                    pct_closed=pct_closed,
                                )
                            except Exception:
                                pass
                            continue

                        # Live Order Execution
                        close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                        close_price = sym_info.bid if is_buy else sym_info.ask
                        cmt = "Sajim_Hummingbird"
                        harvest_done = False

                        for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                            close_req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": pos.ticket,
                                "symbol": pos.symbol,
                                "volume": float(close_vol),
                                "type": close_type,
                                "price": float(close_price),
                                "deviation": 20,
                                "magic": MAGIC_V2,
                                "comment": cmt,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": filling,
                            }
                            res = mt5.order_send(close_req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                harvest_done = True
                                break
                            elif res and "Unsupported filling mode" in (res.comment or ""):
                                continue
                            else:
                                break

                        if not harvest_done:
                            close_req_simple = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": pos.ticket,
                                "symbol": pos.symbol,
                                "volume": float(close_vol),
                                "type": close_type,
                                "price": float(close_price),
                                "deviation": 20,
                                "magic": MAGIC_V2,
                                "comment": cmt,
                            }
                            res = mt5.order_send(close_req_simple)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                harvest_done = True

                        if harvest_done:
                            logger.info(
                                f"[🦅 V2 HUMMINGBIRD HARVEST] Closed #{pos.ticket} on {pos.symbol} at PEAK! "
                                f"PnL: +${banked_profit:.2f} USD (+{profit_r:.2f}R) | Vol: {close_vol}/{pos.volume} ({mode_label}) | Reason: {exhaust_reason}"
                            )
                            try:
                                self.bus.broadcast_hummingbird_harvest(
                                    ticket=pos.ticket,
                                    symbol=pos.symbol,
                                    profit=banked_profit,
                                    r_multiple=profit_r,
                                    reason=f"{exhaust_reason} ({mode_label})",
                                    pct_closed=pct_closed,
                                )
                            except Exception as b_err:
                                logger.warning(f"Failed to broadcast V2 hummingbird harvest: {b_err}")

                            self.pending_reentry_symbols.add(pos.symbol)

                            if is_full:
                                self.trailing_ratchet_state.pop(pos.ticket, None)
                                self.harvested_tickets.discard(pos.ticket)
                                continue
                            else:
                                # Protect remaining runner: lock in +1.0R Net Profit immediately
                                self.harvested_tickets.add(pos.ticket)
                                runner_sl = (open_price + (1.0 * init_risk)) if is_buy else (open_price - (1.0 * init_risk))
                                mod_req = {
                                    "action": mt5.TRADE_ACTION_SLTP,
                                    "position": pos.ticket,
                                    "sl": float(runner_sl),
                                    "tp": float(pos.tp),
                                }
                                mt5.order_send(mod_req)
                                self.trailing_ratchet_state[pos.ticket] = "STAGE_2_LOCK"
                                continue

            # -----------------------------------------------------------------
            # 2. TWO-STAGE ASYMMETRIC RATCHET (For Positions continuing to surge)
            # -----------------------------------------------------------------
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

            # Stage 1: Move to Profit Lock +0.30R when trade reaches +1.5R
            elif profit_r >= 1.50 and current_ratchet in ("INITIAL", "STAGE_0_BE"):
                new_sl = (open_price + (0.30 * init_risk)) if is_buy else (open_price - (0.30 * init_risk))
                mod_req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "sl": float(new_sl),
                    "tp": float(pos.tp),
                }
                res = mt5.order_send(mod_req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"[🛡️ V2 PROFIT SECURED] Secured +0.30R on #{pos.ticket} {pos.symbol} (current profit: +{profit_r:.2f}R).")
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

        cmt_text = "Scalping_Opp" if sig.timeframe == "M1" else f"Sajim_V2_{sig.strategy_name[:10]}"
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
                "comment": cmt_text,
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
                        timeframe=sig.timeframe,
                    )
                except Exception as b_err:
                    logger.warning(f"Failed to broadcast V2 trade execution: {b_err}")

                # Record flight blackbox entry
                try:
                    get_flight_recorder().record_entry(
                        ticket=res.order,
                        symbol=sig.symbol,
                        action=sig.action,
                        volume=float(lot),
                        entry_price=float(sig.entry_price),
                        sl=float(sig.stop_loss),
                        tp=float(sig.take_profit),
                        strategy_name=sig.strategy_name,
                        metadata=sig.metadata,
                    )
                except Exception as fr_err:
                    logger.warning(f"Failed to record flight entry: {fr_err}")

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
            logger.info(f"[+] Hot-Reloaded V2 Prime Universe ({len(self.universe)} Assets): {self.universe}")

        timeframes = ["M1", "M5", "M15", "H1"]
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
                        # 1. BEEP SNIPE CONFIRMATION FILTER (Anti-Chop Shield)
                        # Require a high momentum/volume score spike before any strategy signal is confirmed for execution
                        confirmed, eval_res = self.snipe_filter.evaluate_signal(
                            signal=signal,
                            bars=bars,
                            market_info=market_info,
                        )

                        if not confirmed:
                            logger.info(
                                f"[🛡️ BEEP CHOP FILTER] Blocked {signal.symbol} {signal.action} from {signal.strategy_name} ({signal.timeframe}): "
                                f"{eval_res.reason} (Score: {eval_res.composite_score:.1f}, M(t): {eval_res.kinetic_mass:.1f}, RVol: {eval_res.relative_volume:.2f}x)"
                            )
                            continue

                        # Signal confirmed! Enrich metadata with BEEP Snipe Telemetry
                        signal.metadata["beep_snipe"] = eval_res.to_dict()
                        signal.confidence = round(
                            min(1.0, (signal.confidence * 0.5) + (eval_res.composite_score / 200.0)), 2
                        )
                        logger.info(
                            f"[🎯 BEEP SNIPE CONFIRMED] {signal.symbol} {signal.action} from {signal.strategy_name} ({signal.timeframe}) | "
                            f"Tier: {eval_res.tier} | Score: {eval_res.composite_score:.1f} | M(t): {eval_res.kinetic_mass:.1f} | RVol: {eval_res.relative_volume:.2f}x"
                        )

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
                                metadata=mat,
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
        try:
            get_flight_recorder().audit_post_exits()
        except Exception:
            pass
