"""
========================================================================================
         SAJIM HOLDINGS — OVERNIGHT OMNIVERSE SERVER ENGINE (v2.0 CANONICAL)
                          (bots/sajim_server_overnight.py)
========================================================================================
Chief Architect: Jimmy Mathu
Canonical 7-Stage Quantitative Pipeline:
    DATA -> BEEP -> SIGNAL -> SAJIM -> ENTRY -> MANAGEMENT -> PNL

Decoupled Architecture:
  1. DATA        : Live MT5 multi-asset tick and bar ingestion
  2. BEEP        : Robust baseline B(t), Kinetic Mass M(t), Layer Classification
  3. SIGNAL      : Immutable BeepSignal generator with candle deduplication
  4. SAJIM       : Portfolio diversification, cooldowns, dynamic scale-invariant sizing
  5. ENTRY       : Margin-aware order dispatch with multi-filling mode fallback
  6. MANAGEMENT  : Two-stage trailing ratchet (+1.5R BE, +2.2R Lock +1.0R Net Profit)
  7. PNL         : Deal synchronizer, continuous dynamic compounding, formulaic step-back
========================================================================================
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from core.beep_signal_engine import BeepSignalEngine, BeepSignal
from bots.sajim_v1_bot import SajimV1Bot

# Configure Logging (Safe ASCII for Windows Console, UTF-8 for File)
log_file = os.path.join(ROOT_DIR, "overnight_execution.log")
status_file = os.path.join(ROOT_DIR, "overnight_status.json")

file_handler = logging.FileHandler(log_file, encoding="utf-8")
stream_handler = logging.StreamHandler(sys.stdout)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[file_handler, stream_handler],
)
logger = logging.getLogger("SajimServer")


# PILLAR 1: THE CLEAN PLATE PROTOCOL — TOXIC ASSET BLACKLIST
# Excludes assets with proven structural whipsaws, excessive spread-to-ATR friction, or contract mismatches
TOXIC_BLACKLIST = {
    "XAUGBP.c", "XAGUSD.c", "XAUGBP", "XAGUSD",
    "CADCHF", "CADCHF.c", "AUDCHF", "AUDCHF.c",
    "NZDCHF", "NZDCHF.c", "AUDNZD", "AUDNZD.c",
    "GBPCHF", "GBPCHF.c"
}


class SajimOvernightServer:
    """
    Dedicated 24/7 Quant Server Orchestrator.
    Executes the Canonical 7-Stage Pipeline continuously.
    """

    def __init__(
        self,
        scan_interval_seconds: int = 30,
        max_concurrent_positions: int = 8,
        base_risk_fraction: float = 0.02,
        dry_run: bool = False,
    ):
        self.terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self.scan_interval = scan_interval_seconds
        self.dry_run = dry_run

        # Dedicated Engine Instances
        self.beep_engine = BeepSignalEngine()
        self.bot = SajimV1Bot(
            max_concurrent_positions=max_concurrent_positions,
            base_risk_fraction=base_risk_fraction,
            dry_run=dry_run,
        )
        self.broadcasted_signal_ids = set()
        self.last_gift_day = None

        # ARMED: Autonomous 24/7 Community Concierge AI
        from core.sajim_community_concierge import get_concierge
        self.concierge = get_concierge()
        self.concierge.start()

    def connect(self, target_account: Optional[int] = None) -> bool:
        self.target_account = target_account
        if not self.bot.connect(target_account=target_account):
            return False

        # Gather strictly approved symbols from Master Whitelist JSON
        from core.whitelist_manager import get_whitelist_manager
        wl_mgr = get_whitelist_manager()
        live_targets = wl_mgr.get_live_trading_universe()
        toxic_bl = wl_mgr.get_toxic_blacklist()

        all_syms = mt5.symbols_get() or []
        cent_symbols = [
            s.name for s in all_syms
            if s.name.endswith('.c') and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL 
            and wl_mgr.is_live_trading_approved(s.name)
            and not wl_mgr.is_toxic(s.name)
        ]

        if cent_symbols:
            active_universe = []
            for s in cent_symbols:
                si = mt5.symbol_info(s)
                if si and not si.visible:
                    mt5.symbol_select(s, True)
                active_universe.append(s)
        else:
            active_universe = []
            for p in live_targets:
                if wl_mgr.is_toxic(p):
                    continue
                si = mt5.symbol_info(p)
                if si and si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    if not si.visible:
                        mt5.symbol_select(p, True)
                    active_universe.append(p)

        # Filter universe by empirical edge whitelist (Discarding 157 toxic bleeder setups)
        try:
            from config.v1_edge_filter import get_v1_approved_symbols
            approved_set = set(get_v1_approved_symbols())
            filtered_universe = [s for s in active_universe if s in approved_set]
            if filtered_universe:
                active_universe = filtered_universe
                logger.info(f"[🛡️ V1 EDGE INTEGRATION] Universe filtered to {len(active_universe)} positive-expectancy assets.")
        except Exception as e:
            logger.warning(f"Could not load v1_edge_filter: {e}")

        self.beep_engine.set_universe(active_universe)
        total_fronts = len(active_universe) * len(self.beep_engine.timeframes)
        logger.info(f"[+] Active Quant Universe: {len(active_universe)} Tradable Assets across {len(self.beep_engine.timeframes)} Timeframes ({total_fronts} Fronts) [Clean Plate & Edge Filters Active]")
        return True

    def write_status(self, active_signals: List[BeepSignal]):
        acc = mt5.account_info()
        active_trades = [p._asdict() for p in (mt5.positions_get() or []) if p.magic == 777999]
        status = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pipeline": "DATA -> BEEP -> SIGNAL -> SAJIM -> ENTRY -> MANAGEMENT -> PNL",
            "server": acc.server if acc else "Unknown",
            "account": acc.login if acc else 0,
            "equity": acc.equity if acc else 0.0,
            "balance": acc.balance if acc else 0.0,
            "free_margin": acc.margin_free if acc else 0.0,
            "active_bot_positions": len(active_trades),
            "consecutive_wins": self.bot.consecutive_wins,
            "cluster_streaks": self.bot.cluster_streaks,
            "total_trades": self.bot.total_trades_taken,
            "active_signals_count": len(active_signals),
            "top_signals": [s.to_dict() for s in active_signals[:5]],
            "open_positions": active_trades,
            "mode": "DRY_RUN" if self.dry_run else "LIVE_EXECUTION",
        }
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write status file: {e}")

    def manage_stream_tick(self):
        """Continuous sub-second streaming trade management & PnL sync."""
        self.bot.sync_pnl_and_streaks()
        self.bot.manage_open_positions()

    def scan_and_entry_cycle(self):
        """Periodic institutional universe scan and new entry dispatch."""
        signals = self.beep_engine.scan_all_universe()
        self.write_status(signals)

        if not signals:
            return

        # BROADCAST NERVE BUS & TRUTH VAULT LOGGING
        for sig in signals:
            # 0. Forward Truth Lab Logging (Empirical Catalogue Expansion)
            try:
                from core.signal_truth_tester import get_signal_truth_tester
                get_signal_truth_tester().register_signal(
                    strategy_name=f"BEEP_{sig.layer}",
                    symbol=sig.symbol,
                    timeframe=sig.timeframe,
                    action=sig.action,
                    entry_price=sig.entry_price,
                    stop_loss=sig.stop_loss,
                    take_profit=sig.take_profit,
                    risk_reward=sig.risk_reward,
                    confidence=sig.phi_energy,
                    metadata={"layer": sig.layer, "m_t": sig.m_t, "b_t": sig.b_t},
                )
            except Exception:
                pass

            if sig.layer in ("DIAMOND", "RARE") and sig.signal_id not in self.broadcasted_signal_ids:
                self.broadcasted_signal_ids.add(sig.signal_id)
                try:
                    narrative_why = f"Institutional thrust {sig.layer} {sig.action} in {sig.mode} mode."
                    self.bot.bus.broadcast_signal(
                        symbol=sig.symbol,
                        timeframe=sig.timeframe,
                        action=sig.action,
                        layer=sig.layer,
                        m_t=sig.m_t,
                        entry=sig.entry_price,
                        sl=sig.stop_loss,
                        tp=sig.take_profit,
                        rr=sig.risk_reward,
                        session=getattr(sig, "session", "LIVE_MARKET"),
                        why=narrative_why,
                    )
                except Exception as b_err:
                    logger.warning(f"Failed to broadcast signal {sig.signal_id}: {b_err}")

        # STAGES 4 & 5: SAJIM -> ENTRY
        entries_this_cycle = 0
        symbols_entered_this_cycle = set()
        # Sort candidate signals: High-Velocity Assets (XAUUSD, GBPUSD, EURUSD) get priority
        high_velocity_weights = {"XAUUSD": 10, "GBPUSD": 8, "EURUSD": 7, "USDCAD": 6, "GBPAUD": 5, "GBPCAD": 5}
        sorted_signals = sorted(
            signals,
            key=lambda s: (high_velocity_weights.get(s.symbol, 1), getattr(s, "phi_energy", 50.0)),
            reverse=True
        )
        for sig in sorted_signals:
            all_bot_pos = [p for p in (mt5.positions_get() or []) if p.magic == 777999]
            active_count = len(all_bot_pos)
            is_gold_or_vip = sig.symbol in ("XAUUSD", "GBPUSD")
            eff_max = max(10, self.bot.max_positions + 3) if is_gold_or_vip else self.bot.max_positions

            if active_count >= eff_max:
                break
            if entries_this_cycle >= 4:
                break
            if sig.symbol in symbols_entered_this_cycle:
                continue

            prepared = self.bot.evaluate_signal_and_size(sig)
            if prepared:
                executed = self.bot.execute_entry(prepared)
                if executed:
                    entries_this_cycle += 1
                    symbols_entered_this_cycle.add(sig.symbol)
                    logger.info(f"[🚀 PIPELINE COMPLETE] Trade activated on {sig.symbol} ({sig.layer} {sig.action})")

    def execute_cycle(self):
        """Executes one combined pass of streaming management and universe scan."""
        self.manage_stream_tick()
        self.scan_and_entry_cycle()

    def run_forever(self):
        logger.info(f"[+] ENGINE ARMED: Starting Sajim Canonical Quant Daemon (Scan Interval: {self.scan_interval}s, Streaming Health: 1s Tick, Max Concurrent: {self.bot.max_positions})")
        logger.info(f"[+] Pipeline: STREAMING TICK -> HEALTH H(t) -> SAJIM QUALITY GATE -> ENTRY -> PNL")
        logger.info(f"[+] Mode: {'SIMULATION / DRY RUN' if self.dry_run else 'LIVE BROKER EXECUTION'}")
        last_scan_time = 0.0
        try:
            while True:
                try:
                    # Verify MT5 connectivity
                    acc = mt5.account_info()
                    if not acc:
                        logger.warning("[!] MT5 account info is None (disconnected). Reconnecting to target account...")
                        self.connect(target_account=getattr(self, 'target_account', None))

                    # 1. Continuous Sub-Second Streaming Tick Management & PnL Sync
                    self.manage_stream_tick()

                    # 2. Periodic Universe Discovery & Entry Execution
                    now = time.time()
                    if now - last_scan_time >= self.scan_interval:
                        last_scan_time = now
                        self.scan_and_entry_cycle()
                except Exception as loop_err:
                    logger.error(f"[!] Server cycle anomaly (auto-recovering): {loop_err}", exc_info=True)
                    time.sleep(2.0)

                # 1-second heartbeat pause between streaming evaluations
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("[!] Daemon paused by operator. Standing down.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sajim Canonical Quant Server")
    parser.add_argument("--live", action="store_true", help="Execute real trades on MT5 server (default: Dry Run)")
    parser.add_argument("--interval", type=int, default=30, help="Scan interval in seconds (default: 30)")
    parser.add_argument("--risk", type=float, default=0.01, help="Base risk fraction per asset (default: 0.01 = 1.0%%)")
    parser.add_argument("--max-positions", type=int, default=6, help="Max concurrent open positions (default: 6)")
    args = parser.parse_args()

    server = SajimOvernightServer(
        scan_interval_seconds=args.interval,
        max_concurrent_positions=args.max_positions,
        base_risk_fraction=args.risk,
        dry_run=not args.live,
    )
    if server.connect():
        server.run_forever()
        mt5.shutdown()
