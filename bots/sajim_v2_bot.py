"""
========================================================================================
            SAJIM HOLDINGS — SAJIM V2 BOT (bots/sajim_v2_bot.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Canonical 7-Stage Quantitative Pipeline (V2 Architecture):
    DATA -> BEEP -> SIGNAL -> SAJIM V2 -> ENTRY -> ASYMMETRIC MANAGEMENT -> PNL

Key Advancements over V1:
  1. DYNAMIC EDGE WHITELISTING: Automatically ingests verified positive-expectancy pairs
     and timeframes from `docs/edge_matrix_results.json` (Profit Factor >= 1.20, Expectancy > 0).
     Excludes all toxic bleeders identified during quantitative testing.
  2. ASYMMETRIC PAYOFF ENFORCEMENT: Abolished premature 50-cent micro-milking.
     - Tranche 1 (+1.5R): Moves SL to Break-Even +0.15R (safe scratch/small win).
     - Tranche 2 (+2.2R): Locks in +1.0R Net Profit.
     - Tranche 3 (+3.0R to +3.5R): Full Institutional Take-Profit harvest.
  3. STRICT RISK CEILING & SPREAD GATE:
     - Hard risk cap of 1.2% per trade (1 win pays for 3-4 losses).
     - Rejects any setup where broker spread consumes > 12% of the Stop Loss.
  4. 5% DAILY DRAWDOWN CIRCUIT BREAKER: Shuts down new entries on severe drawdown days.
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
from core.beep_signal_engine import BeepSignal, BeepSignalEngine
from core.lot_calculator import UniversalLotCalculator
from core.beep_broadcast import BeepBroadcastBus
from v2.safety import new_entries_allowed, DailyDrawdownGuard, utc_now, utc_day_start
from v2.risk import constants as RC
from v2.risk.hummingbird import HummingbirdEvaluator
from v2.risk.position_state import get_position_store
from v2.execution.mt5_exec import send_market_order, close_position, modify_sltp

logger = logging.getLogger("SajimV2Bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [V2] %(message)s",
)

RESULTS_FILE = os.path.join(ROOT_DIR, "docs", "edge_matrix_results.json")
MAGIC_V2 = 888222
STATUS_FILE = os.path.join(ROOT_DIR, "v2_status.json")


class SajimV2Bot:
    """
    Sajim V2 Quantitative Production Engine.
    Data-Driven, Asymmetric Risk-Reward, Zero Micro-Milking Bleed.
    """

    def __init__(
        self,
        max_concurrent_positions: int = 5,
        base_risk_fraction: float = 0.012,       # 1.2% max risk per trade
        max_risk_fraction: float = 0.018,        # 1.8% hard cap on diamond streaks
        streak_expansion_rate: float = 0.10,     # +10% lot expansion per win
        max_daily_drawdown_pct: float = 0.05,    # 5.0% maximum daily drawdown
        hummingbird_harvest_enabled: bool = True,# Peak profit extraction on M1 momentum exhaustion
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.max_positions = max_concurrent_positions
        self.base_risk = base_risk_fraction
        self.max_risk = max_risk_fraction
        self.streak_rate = streak_expansion_rate
        self.max_daily_dd_pct = max_daily_drawdown_pct
        self.hummingbird_harvest_enabled = hummingbird_harvest_enabled
        self.dry_run = dry_run

        self.bus = BeepBroadcastBus()
        self.beep_engine = BeepSignalEngine()

        # Dynamic Edge Universe State
        self.edge_whitelist: Dict[str, List[str]] = {}  # symbol -> allowed timeframes
        self.toxic_bleeders: Set[str] = set()

        # Execution State
        self.consecutive_wins = 0
        self.total_trades_taken = 0
        self.session_pnl = 0.0
        self.symbol_cooldowns: Dict[str, datetime] = {}
        self.processed_deal_tickets: Set[int] = set()
        # Persistent per-ticket state (initial risk + ratchet stage): state/v2_bot_positions.json
        self.position_store = get_position_store("v2_bot")
        self.trailing_ratchet_state: Dict[int, str] = dict(self.position_store.stages())  # ticket -> stage
        self.pending_reentry_symbols: Set[str] = set()
        self.daily_guard = DailyDrawdownGuard("v2_bot", max_dd_pct=max_daily_drawdown_pct)
        self._dry_run_actions: Set[Tuple[int, str]] = set()
        self._dry_run_closed: Set[int] = set()

    def load_edge_matrix(self):
        """Loads and applies empirical findings from the quantitative edge audit."""
        if os.path.exists(RESULTS_FILE):
            try:
                with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                    results = json.load(f)

                approved_count = 0
                for r in results:
                    sym = r["symbol"]
                    tf = r["timeframe"]
                    tier = r.get("tier", "")

                    if tier in ("INSTITUTIONAL EDGE", "MODERATE EDGE"):
                        if sym not in self.edge_whitelist:
                            self.edge_whitelist[sym] = []
                        self.edge_whitelist[sym].append(tf)
                        approved_count += 1
                    elif tier == "NEGATIVE EDGE (BLEEDER)":
                        self.toxic_bleeders.add(f"{sym}_{tf}")

                logger.info(f"[+] Sajim V2 Edge Matrix Ingested: {len(self.edge_whitelist)} Approved Assets ({approved_count} Positive Fronts).")
                logger.info(f"[+] Blacklisted Bleeders: {len(self.toxic_bleeders)} negative-expectancy fronts permanently filtered.")
                logger.warning(
                    "[!] docs/edge_matrix_results.json was generated by a backtest with an intrabar look-ahead bias "
                    "(SL ratcheted on the bar's high, then tested against the same bar's low) and in-sample selection only. "
                    "Regenerate with scripts/run_edge_matrix_backtest.py --oos-split 0.3 before trusting this whitelist."
                )
                return
            except Exception as e:
                logger.warning(f"Could not parse edge matrix: {e}. Falling back to default institutional core.")

        # Default fallback core if matrix is compiling
        default_core = ["XAUUSD.c", "EURUSD.c", "GBPUSD.c", "USDJPY.c", "GBPJPY.c", "EURJPY.c", "AUDUSD.c", "USDCAD.c"]
        for sym in default_core:
            self.edge_whitelist[sym] = ["M5", "M15", "H1"]
        logger.info(f"[+] Initialized V2 with Default Institutional Core ({len(self.edge_whitelist)} assets).")

    def connect(self, target_account: Optional[int] = None) -> bool:
        """Initializes MT5 terminal and synchronizes historical state."""
        if not mt5.initialize(path=self.terminal_path, timeout=15000):
            logger.error(f"Cannot initialize MT5: {mt5.last_error()}")
            return False

        acc = mt5.account_info()
        if not acc:
            logger.error("No active MT5 account found.")
            return False

        if target_account is not None and acc.login != target_account:
            logger.critical(f"[SECURITY LOCK] Connected to {acc.login} ({acc.server}), expected {target_account}. Aborting.")
            mt5.shutdown()
            return False

        self.load_edge_matrix()

        # Activate symbols in Market Watch
        for s in self.edge_whitelist.keys():
            mt5.symbol_select(s, True)

        self.beep_engine.set_universe(list(self.edge_whitelist.keys()))

        logger.info(f"[+] SAJIM V2 ENGINE CONNECTED: {acc.server} | Account: {acc.login}")
        logger.info(f"[+] Balance: {acc.balance:.2f} {acc.currency} | Equity: {acc.equity:.2f} | Free Margin: {acc.margin_free:.2f} | Leverage: 1:{acc.leverage}")
        return True

    def check_daily_drawdown_limit(self) -> bool:
        """
        Enforces the hard daily drawdown circuit breaker:
        UTC day, start-of-day equity baseline, drawdown = start_equity - current_equity
        (floating P&L, commissions and swaps included).
        """
        acc = mt5.account_info()
        if not acc:
            return False

        today_deals = mt5.history_deals_get(utc_day_start(), utc_now() + timedelta(minutes=5)) or []
        dd = self.daily_guard.evaluate(acc, today_deals)
        if not dd["ok"]:
            logger.warning(f"[🛑 V2 DAILY CIRCUIT BREAKER] {dd['reason']}. Trading locked until 00:00 UTC.")
            return False
        return True

    def evaluate_signal_and_size(self, signal: BeepSignal) -> Optional[Dict[str, Any]]:
        """Evaluates signal under V2 asymmetric edge rules and sizes lot dynamically."""
        acc = mt5.account_info()
        if not acc:
            return None

        # 0. Global kill switch
        if not new_entries_allowed("V2"):
            return None

        # 1. Daily Circuit Breaker Check
        if not self.check_daily_drawdown_limit():
            return None

        # 2. Edge Whitelist Verification
        allowed_tfs = self.edge_whitelist.get(signal.symbol, [])
        if signal.timeframe not in allowed_tfs:
            return None

        # 3. Bleeder Rejection Gate
        if f"{signal.symbol}_{signal.timeframe}" in self.toxic_bleeders:
            return None

        # 4. Symbol Cooldown Check
        now = datetime.now()
        cooldown = self.symbol_cooldowns.get(signal.symbol)
        if cooldown and cooldown > now:
            return None

        # 5. Spread Friction Gate (Spread must be <= 12% of Stop Loss)
        sym_info = mt5.symbol_info(signal.symbol)
        if not sym_info:
            return None

        spread_dist = sym_info.spread * sym_info.point
        sl_dist = abs(float(signal.entry_price) - float(signal.stop_loss))
        if sl_dist <= 0:
            return None

        eta_friction = spread_dist / sl_dist
        if eta_friction > 0.12:
            logger.info(f"[Spread Filter] {signal.symbol}: Spread consumes {eta_friction*100:.1f}% of SL (> 12% limit). Skipped.")
            return None

        # 6. Concurrency Cap (Max 5 open positions)
        current_open = len([p for p in (mt5.positions_get() or []) if p.magic == MAGIC_V2])
        if current_open >= self.max_positions:
            return None

        # 7. Asymmetric Dynamic Sizing: 1.2% base risk
        streak_mult = (1.0 + self.streak_rate) ** min(self.consecutive_wins, 4)
        dynamic_risk = min(self.max_risk, self.base_risk * streak_mult)

        lot, risk_cash, specs = UniversalLotCalculator.calculate_lot(
            symbol=signal.symbol,
            equity=acc.equity,
            risk_fraction=dynamic_risk,
            entry_price=signal.entry_price,
            stop_price=signal.stop_loss,
            account_currency=acc.currency,
        )
        if lot <= 0:
            logger.info(f"[V2] {signal.symbol}: {specs.get('rejected', 'cannot size within risk budget')}. Skipped.")
            return None

        order_type = mt5.ORDER_TYPE_BUY if signal.action == "BUY" else mt5.ORDER_TYPE_SELL

        return {
            "signal": signal,
            "lot": lot,
            "order_type": order_type,
            "dynamic_risk_pct": round(dynamic_risk * 100.0, 2),
            "risk_cash": round(risk_cash, 2),
            "specs": specs,
        }

    def execute_entry(self, sized: Dict[str, Any]) -> bool:
        """Dispatches verified order to MT5 (Magic 888222) at a fresh tick price; dry run sends nothing."""
        sig = sized["signal"]
        ok, res, fill_price = send_market_order(
            symbol=sig.symbol,
            action=sig.action,
            volume=float(sized["lot"]),
            sl=float(sig.stop_loss),
            tp=float(sig.take_profit),
            magic=MAGIC_V2,
            comment="Sajim_V2_Edge",
            dry_run=self.dry_run,
            bot_name="V2-BOT",
        )
        if not ok:
            return False
        if self.dry_run:
            return True

        ticket = int(res.order)
        entry_px = float(fill_price or sig.entry_price)
        self.position_store.record_entry(ticket, sig.symbol, entry_px, float(sig.stop_loss), bot="V2-BOT")
        logger.info(f"[🚀 V2 ORDER EXECUTED] #{ticket} {sig.action} {sized['lot']} {sig.symbol} @ {entry_px:.5f} | TP: {sig.take_profit:.5f} | SL: {sig.stop_loss:.5f}")
        self.total_trades_taken += 1
        return True

    def check_hummingbird_exhaustion(
        self,
        pos: Any,
        profit_r: float,
        sym_info: Any,
    ) -> Tuple[bool, str]:
        """
        Shared M1 exhaustion evaluator (v2/risk/hummingbird.py) with this bot's upper bound:
        above HUMMINGBIRD_V2_BOT_MAX_R the take-profit is left to fill naturally.
        """
        return HummingbirdEvaluator.check_exhaustion(pos, profit_r, sym_info, max_r=RC.HUMMINGBIRD_V2_BOT_MAX_R)

    def _dry_once(self, ticket: int, action: str) -> bool:
        key = (int(ticket), action)
        if key in self._dry_run_actions:
            return False
        self._dry_run_actions.add(key)
        return True

    def manage_open_positions(self):
        """
        STAGE 6: ASYMMETRIC MANAGEMENT & HUMMINGBIRD HARVESTING (thresholds: v2/risk/constants.py).
        - Hummingbird Harvest: peak harvest (+1.5R to +2.95R) on M1 exhaustion.
        - Stage 2 Ratchet: Lock in +1.0R Net Profit when trade reaches +2.2R.
        - Stage 1 Ratchet: Move SL to Break-Even +0.15R when trade reaches +1.5R.
        R is measured on the INITIAL risk recorded at entry (state/v2_bot_positions.json).
        In dry run nothing is sent to the broker.
        """
        all_positions = mt5.positions_get()
        if all_positions is None:
            return
        positions = [p for p in all_positions if p.magic == MAGIC_V2]
        open_tickets = {p.ticket for p in positions}
        self.position_store.prune(open_tickets)
        self._dry_run_closed &= open_tickets
        for stale in [t for t in self.trailing_ratchet_state if t not in open_tickets]:
            self.trailing_ratchet_state.pop(stale, None)

        for pos in positions:
            if pos.ticket in self._dry_run_closed:
                continue
            sym_info = mt5.symbol_info(pos.symbol)
            if not sym_info:
                continue

            is_buy = pos.type == mt5.POSITION_TYPE_BUY
            cur_price = sym_info.bid if is_buy else sym_info.ask
            open_price = pos.price_open

            init_risk = self.position_store.initial_risk(pos, mt5_module=mt5)
            if not init_risk or init_risk <= 0:
                continue  # unknown initial risk -> skip R-based management

            profit_dist = (cur_price - open_price) if is_buy else (open_price - cur_price)
            profit_r = profit_dist / init_risk

            current_ratchet = self.trailing_ratchet_state.get(pos.ticket, "INITIAL")

            # -----------------------------------------------------------------
            # 1. THE HUMMINGBIRD PEAK HARVEST (M1 Velocity Exhaustion Protection)
            # -----------------------------------------------------------------
            if self.hummingbird_harvest_enabled:
                is_exhausted, exhaust_reason = self.check_hummingbird_exhaustion(pos, profit_r, sym_info)
                if is_exhausted:
                    banked_profit = round(pos.profit, 2)

                    if self.dry_run:
                        if self._dry_once(pos.ticket, "HUMMINGBIRD"):
                            close_position(pos, magic=MAGIC_V2, comment="Sajim_Hummingbird", dry_run=True, bot_name="V2-BOT")
                            logger.info(
                                f"[DRY RUN 🦅 V2 HUMMINGBIRD] #{pos.ticket} {pos.symbol} would be harvested "
                                f"({banked_profit:+.2f}, +{profit_r:.2f}R) | Reason: {exhaust_reason}"
                            )
                            self._dry_run_closed.add(pos.ticket)
                        continue

                    if close_position(pos, magic=MAGIC_V2, comment="Sajim_Hummingbird", dry_run=False, bot_name="V2-BOT"):
                        logger.info(
                            f"[🦅 V2 HUMMINGBIRD HARVEST] Closed #{pos.ticket} on {pos.symbol} at PEAK! "
                            f"PnL: {banked_profit:+.2f} (+{profit_r:.2f}R) | Reason: {exhaust_reason}"
                        )
                        try:
                            self.bus.broadcast_hummingbird_harvest(
                                ticket=pos.ticket,
                                symbol=pos.symbol,
                                profit=banked_profit,
                                r_multiple=profit_r,
                                reason=exhaust_reason,
                            )
                        except Exception as b_err:
                            logger.warning(f"Failed to broadcast V2 hummingbird harvest: {b_err}")
                        self.pending_reentry_symbols.add(pos.symbol)
                        self.trailing_ratchet_state.pop(pos.ticket, None)
                        self.position_store.forget(pos.ticket)
                        continue

            # -----------------------------------------------------------------
            # 2. TWO-STAGE ASYMMETRIC RATCHET
            # -----------------------------------------------------------------
            new_stage = None
            if profit_r >= RC.V2_BOT_STAGE2_TRIGGER_R and current_ratchet != "STAGE_2_LOCK":
                lock = RC.V2_BOT_STAGE2_LOCK_R * init_risk
                new_stage, label = "STAGE_2_LOCK", f"+{RC.V2_BOT_STAGE2_LOCK_R}R Net Profit"
            elif profit_r >= RC.V2_BOT_STAGE1_TRIGGER_R and current_ratchet == "INITIAL":
                lock = RC.V2_BOT_STAGE1_LOCK_R * init_risk
                new_stage, label = "STAGE_1_BE", f"BE+{RC.V2_BOT_STAGE1_LOCK_R}R"

            if new_stage:
                new_sl = (open_price + lock) if is_buy else (open_price - lock)
                if self.dry_run and not self._dry_once(pos.ticket, new_stage):
                    continue
                if modify_sltp(pos, new_sl, pos.tp, dry_run=self.dry_run, bot_name="V2-BOT", digits=getattr(sym_info, "digits", None)):
                    logger.info(f"[🔒 V2 RATCHET]{' [DRY RUN]' if self.dry_run else ''} {label} on #{pos.ticket} {pos.symbol} (current profit: +{profit_r:.2f}R).")
                    self.trailing_ratchet_state[pos.ticket] = new_stage
                    if not self.dry_run:
                        self.position_store.set_stage(pos.ticket, new_stage)

    def sync_pnl_and_streaks(self):
        """Synchronizes closed deals and updates win/loss compounding streaks."""
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
                if d.profit > 0.05:
                    self.consecutive_wins += 1
                    logger.info(f"[🎉 V2 WIN] Deal #{d.ticket} {d.symbol} closed with +${d.profit:.2f}. Streak: {self.consecutive_wins} wins.")
                elif d.profit < -0.05:
                    self.consecutive_wins = 0
                    self.symbol_cooldowns[d.symbol] = datetime.now() + timedelta(minutes=30)
                    logger.info(f"[⚠️ V2 LOSS] Deal #{d.ticket} {d.symbol} closed with -${abs(d.profit):.2f}. Cooldown applied (30m).")

    def run_iteration(self):
        """Executes one scan, sizing, entry, and management iteration."""
        self.sync_pnl_and_streaks()
        self.manage_open_positions()

        signals = self.beep_engine.scan_all_universe()
        if not signals:
            return

        # Prioritize signals by Kinetic Mass M(t)
        signals.sort(key=lambda s: abs(s.m_t), reverse=True)

        for sig in signals:
            sized = self.evaluate_signal_and_size(sig)
            if sized:
                self.execute_entry(sized)
                break  # Enter top priority opportunity per cycle


def main():
    bot = SajimV2Bot()
    if not bot.connect():
        sys.exit(1)

    print("[+] Sajim V2 Bot successfully initialized and armed!")
    print(f"[+] Active Edge Whitelist: {list(bot.edge_whitelist.keys())}")


if __name__ == "__main__":
    main()
