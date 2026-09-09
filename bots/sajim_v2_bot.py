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

logger = logging.getLogger("SajimV2Bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [V2] %(message)s",
)

RESULTS_FILE = os.path.join(ROOT_DIR, "docs", "edge_matrix_results.json")
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
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.max_positions = max_concurrent_positions
        self.base_risk = base_risk_fraction
        self.max_risk = max_risk_fraction
        self.streak_rate = streak_expansion_rate
        self.max_daily_dd_pct = max_daily_drawdown_pct
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
        self.trailing_ratchet_state: Dict[int, str] = {}  # ticket -> stage ('STAGE_1_BE', 'STAGE_2_LOCK')

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
        """Enforces hard 5% daily drawdown circuit breaker."""
        acc = mt5.account_info()
        if not acc:
            return False

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_deals = mt5.history_deals_get(today_start, datetime.now()) or []

        closed_losses = abs(sum(d.profit for d in today_deals if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT) and d.profit < 0))
        closed_wins = sum(d.profit for d in today_deals if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT) and d.profit > 0)
        net_daily_loss = closed_losses - closed_wins

        max_daily_loss = acc.balance * self.max_daily_dd_pct
        if net_daily_loss >= max_daily_loss:
            logger.warning(
                f"[🛑 V2 DAILY CIRCUIT BREAKER] Today's net loss is -{net_daily_loss:.2f} >= "
                f"limit of {max_daily_loss:.2f} (5% balance). Trading locked until 00:00 UTC."
            )
            return False
        return True

    def evaluate_signal_and_size(self, signal: BeepSignal) -> Optional[Dict[str, Any]]:
        """Evaluates signal under V2 asymmetric edge rules and sizes lot dynamically."""
        acc = mt5.account_info()
        if not acc:
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
        current_open = len([p for p in (mt5.positions_get() or []) if p.magic == 888222])
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
        )

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
        """Dispatches verified order to MT5 terminal with Magic Number 888222 (Sajim V2)."""
        if self.dry_run:
            logger.info(f"[DRY RUN V2 ENTRY] {sized['signal'].action} {sized['lot']} {sized['signal'].symbol} @ {sized['signal'].entry_price:.5f}")
            return True

        sig = sized["signal"]
        order_req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": sig.symbol,
            "volume": float(sized["lot"]),
            "type": sized["order_type"],
            "price": float(sig.entry_price),
            "sl": float(sig.stop_loss),
            "tp": float(sig.take_profit),
            "deviation": 20,
            "magic": 888222,
            "comment": "Sajim_V2_Edge",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        res = mt5.order_send(order_req)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"[🚀 V2 ORDER EXECUTED] #{res.order} {sig.action} {sized['lot']} {sig.symbol} @ {sig.entry_price:.5f} | TP: {sig.take_profit:.5f} | SL: {sig.stop_loss:.5f}")
            self.total_trades_taken += 1
            return True
        else:
            err = res.comment if res else mt5.last_error()
            logger.warning(f"[!] Order failed for {sig.symbol}: {err}")
            return False

    def manage_open_positions(self):
        """
        STAGE 6: ASYMMETRIC MANAGEMENT (Zero Premature Micro-Milking).
        - +1.5R: Move SL to Break-Even +0.15R (safe scratch/small win).
        - +2.2R: Trail SL to Lock in +1.0R Net Profit.
        - +3.0R to +3.5R: Take Profit hits naturally.
        """
        positions = [p for p in (mt5.positions_get() or []) if p.magic == 888222]
        for pos in positions:
            sym_info = mt5.symbol_info(pos.symbol)
            if not sym_info:
                continue

            is_buy = pos.type == mt5.POSITION_TYPE_BUY
            cur_price = sym_info.bid if is_buy else sym_info.ask
            open_price = pos.price_open
            sl_price = pos.sl

            # Calculate Initial Risk
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

    def sync_pnl_and_streaks(self):
        """Synchronizes closed deals and updates win/loss compounding streaks."""
        d_from = datetime.now() - timedelta(hours=6)
        d_to = datetime.now() + timedelta(minutes=5)
        deals = mt5.history_deals_get(d_from, d_to)
        if not deals:
            return

        for d in deals:
            if d.ticket in self.processed_deal_tickets or d.magic != 888222:
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
