"""
========================================================================================
        SAJIM HOLDINGS — MASTER DUAL ORCHESTRATOR (v2/dual_orchestrator.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  Simultaneously executes Sajim V1 and Sajim V2 side-by-side on the same MT5 terminal.
  Harmonizes risk, eliminates trade collisions, and publishes real-time unified telemetry.

Execution Logic:
  1. Refreshes CoexistenceGatekeeper with live MT5 account equity and active tickets.
  2. V1 manages its own positions (Magic 777999) via continuous narrative & stagnation euthanasia.
  3. V2 manages its own positions (Magic 888222) via two-stage asymmetric ratchets (+1.5R BE, +2.2R Lock).
  4. Both bots scan their respective universes, submitting orders only after passing Gatekeeper clearance.
  5. Emits v2/coexistence_status.json continuously for external WebApp integration.
========================================================================================
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots")):
    if p not in sys.path:
        sys.path.insert(0, p)

import MetaTrader5 as mt5
from v2.coexistence import CoexistenceGatekeeper, MAGIC_V1, MAGIC_V2
from bots.sajim_server_overnight import SajimOvernightServer
from v2.sajim_v2_dual_bot import SajimV2DualBot

logger = logging.getLogger("DualOrchestrator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DUAL] %(message)s",
)


class SajimDualOrchestrator:
    """
    Master Co-Execution Orchestrator for Sajim V1 and Sajim V2.
    """

    def __init__(
        self,
        scan_interval_seconds: int = 15,
        max_combined_positions: int = 12,
        max_v1_positions: int = 6,
        max_v2_positions: int = 6,
        base_risk_v1: float = 0.012,
        base_risk_v2: float = 0.012,
        dry_run: bool = False,
        target_account: Optional[int] = None,
    ):
        self.scan_interval = scan_interval_seconds
        self.max_combined = max_combined_positions
        self.max_v1_positions = max_v1_positions
        self.max_v2_positions = max_v2_positions
        self.dry_run = dry_run
        self.target_account = target_account

        # Shared Coexistence Gatekeeper
        self.gatekeeper = CoexistenceGatekeeper(
            max_combined_positions=max_combined_positions,
            status_file_path=os.path.join(BASE_DIR, "coexistence_status.json"),
        )
        if max_v1_positions <= 0:
            self.gatekeeper.v1_enabled = False

        # Sajim V1 Production Server Daemon
        self.v1_server = SajimOvernightServer(
            scan_interval_seconds=scan_interval_seconds,
            max_concurrent_positions=max_v1_positions,
            base_risk_fraction=base_risk_v1,
            dry_run=dry_run,
        )
        # Wire Gatekeeper clearance into V1 bot pre-entry check
        self.v1_server.bot.pre_entry_hook = self.gatekeeper.check_pre_entry_clearance

        # Sajim V2 Pluggable Dual Production Bot
        self.v2_bot = SajimV2DualBot(
            gatekeeper=self.gatekeeper,
            base_risk_fraction=base_risk_v2,
            dry_run=dry_run,
        )

        self.last_scan_time = 0.0
        self.cycle_count = 0

    def connect(self) -> bool:
        """Initializes MT5 terminal and binds both V1 and V2 engines."""
        # Connect to currently running MT5 terminal first; fallback to launch Headway if closed
        init_ok = mt5.initialize()
        if not init_ok:
            headway_path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
            if os.path.exists(headway_path):
                init_ok = mt5.initialize(path=headway_path, timeout=10000)
            else:
                terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
                init_ok = mt5.initialize(path=terminal_path, timeout=5000) if os.path.exists(terminal_path) else False

        if not init_ok:
            logger.critical(f"Failed to initialize MT5 terminal: {mt5.last_error()}")
            return False

        # Load broker configuration if available
        broker_cfg = {}
        cfg_path = os.path.join(ROOT_DIR, "config", "broker_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    broker_cfg = json.load(f)
            except Exception:
                pass

        target_acc = self.target_account or broker_cfg.get("active_account")
        pwd = broker_cfg.get("password")
        srv = broker_cfg.get("server")

        acc = mt5.account_info()
        if target_acc and (acc is None or acc.login != target_acc):
            logger.info(f"Switching active account to {target_acc} on server '{srv}'...")
            if pwd and srv:
                mt5.login(login=target_acc, password=pwd, server=srv)
            elif srv:
                mt5.login(login=target_acc, server=srv)
            else:
                mt5.login(login=target_acc)
            acc = mt5.account_info()

        if not acc:
            logger.critical("No active MT5 trading account found.")
            return False

        if target_acc is not None and acc.login != target_acc:
            logger.critical(f"[SECURITY LOCK] Connected to {acc.login}, expected {target_acc}. Aborting.")
            mt5.shutdown()
            return False

        # Initialize V1 Server (only if V1 is enabled)
        if self.max_v1_positions > 0 and self.gatekeeper.v1_enabled:
            if not self.v1_server.connect(target_account=target_acc):
                logger.critical("Failed to connect Sajim V1 Server.")
                return False
        else:
            logger.info("[🔇 V1 MUTED] Sajim V1 Server connection bypassed (V2 exclusive mode active).")

        # Initialize V2 Bot
        if not self.v2_bot.connect(target_account=target_acc):
            logger.critical("Failed to connect Sajim V2 Bot.")
            return False

        # Initial Gatekeeper Refresh
        self.sync_gatekeeper()

        logger.info("================================================================================")
        logger.info("              SAJIM QUANT LABS — DUAL COEXISTENCE RUNNER INITIALIZED           ")
        logger.info("================================================================================")
        logger.info(f"[+] Account: {acc.login} ({acc.server}) | Balance: {acc.balance:.2f} {acc.currency}")
        logger.info(f"[+] Equity: {acc.equity:.2f} | Free Margin: {acc.margin_free:.2f} | Leverage: 1:{acc.leverage}")
        logger.info(f"[+] V1 Engine: Magic {MAGIC_V1} | Max Positions: {self.v1_server.bot.max_positions}")
        logger.info(f"[+] V2 Engine: Magic {MAGIC_V2} | Max Positions: {self.v2_bot.gatekeeper.max_combined_positions}")
        logger.info(f"[+] Combined Margin Cap: Max {self.max_combined} Open Positions Portfolio-Wide")
        logger.info(f"[+] Execution Mode: {'SIMULATION / DRY RUN' if self.dry_run else 'LIVE BROKER EXECUTION'}")
        logger.info("================================================================================")
        return True

    def sync_gatekeeper(self) -> None:
        """Synchronizes MT5 live snapshot with the Coexistence Gatekeeper."""
        acc = mt5.account_info()
        positions = mt5.positions_get() or []
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(today_start, datetime.now() + timedelta(minutes=5)) or []
        self.gatekeeper.refresh(account_info=acc, all_positions=positions, today_deals=deals)

    def execute_dual_pass(self) -> None:
        """Executes a single coordinated pass for both V1 and V2."""
        self.cycle_count += 1
        self.sync_gatekeeper()

        # 1. Manage Active Positions independently by Magic Number
        # V1: Streaming tick euthanasia & trailing ratchets (only if active V1 trades exist)
        if len(self.gatekeeper.v1_positions) > 0:
            self.v1_server.manage_stream_tick()
        # V2: Two-stage asymmetric ratchets (+1.5R BE, +2.2R Lock)
        self.v2_bot.sync_pnl_and_streaks()
        self.v2_bot.manage_open_positions()

        # 2. Synchronize Gatekeeper after position modifications
        self.sync_gatekeeper()

        # 3. Scan & Entry for V1 (Bypassed if V1 is muted / max_v1 is 0)
        if self.gatekeeper.v1_enabled and self.max_v1_positions > 0 and not self.gatekeeper.circuit_breaker_active:
            try:
                self.v1_server.scan_and_entry_cycle()
            except Exception as e:
                logger.error(f"[V1 Scan Error]: {e}")

        # 4. Synchronize Gatekeeper after V1 potential entries
        self.sync_gatekeeper()

        # 5. Scan & Entry for V2
        if self.gatekeeper.v2_enabled and not self.gatekeeper.circuit_breaker_active:
            try:
                self.v2_bot.scan_and_evaluate()
            except Exception as e:
                logger.error(f"[V2 Scan Error]: {e}")

        # 6. Empirical Signal Truth Forward Audit (MFE, MAE, TP/SL Hit-Rate Tracking)
        try:
            from core.signal_truth_tester import get_signal_truth_tester
            audit_res = get_signal_truth_tester().audit_forward_signals()
            if audit_res.get("updated", 0) > 0:
                logger.info(f"[🔬 TRUTH AUDIT] Tracked {audit_res['updated']} signals forward | Active remaining: {audit_res['active_remaining']}")
        except Exception as t_err:
            logger.debug(f"Truth audit deferred: {t_err}")

        # 7. Final Sync & Status Persistence
        self.sync_gatekeeper()

        v1_cnt = len(self.gatekeeper.v1_positions)
        v2_cnt = len(self.gatekeeper.v2_positions)
        oth_cnt = len(self.gatekeeper.other_positions)
        tot_cnt = v1_cnt + v2_cnt + oth_cnt
        logger.info(
            f"[Cycle #{self.cycle_count}] Equity: {self.gatekeeper.account_equity:.2f} {self.gatekeeper.currency} | "
            f"Active Trades: {tot_cnt}/{self.max_combined} (V1: {v1_cnt} | V2: {v2_cnt} | Oth: {oth_cnt}) | "
            f"Daily PnL: {self.gatekeeper.today_closed_pnl:+.2f}"
        )

    def run_continuous(self) -> None:
        """Runs the continuous multi-bot execution loop."""
        logger.info(f"[+] Launching Dual Continuous Loop (Scan Interval: {self.scan_interval}s)...")
        try:
            while True:
                now = time.time()
                if now - self.last_scan_time >= self.scan_interval:
                    self.last_scan_time = now
                    self.execute_dual_pass()
                else:
                    # High-frequency sub-second management tick between scans
                    self.v1_server.manage_stream_tick()
                    self.v2_bot.manage_open_positions()
                    time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("\n[!] Dual Orchestrator paused by operator. Standing down.")
