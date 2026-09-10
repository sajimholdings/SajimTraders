"""
========================================================================================
       SAJIM QUANT LABS — HIGH-RESOLUTION TRADE FLIGHT RECORDER (BLACKBOX)
                           (core/trade_flight_recorder.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Concept:
  - Second-by-Second / Sub-Second Telemetry Flight Recorder for every live MT5 trade.
  - Captures microsecond state from open to close:
      * Elapsed seconds, Price, Floating PnL ($), Floating R
      * Maximum Favorable Excursion (MFE) & Maximum Adverse Excursion (MAE)
      * Kinetic Energy K(t), Rolling Baseline K_base(t), K_ratio
      * Real-time candle wicks and directional absorption
  - Post-Exit Telemetry (Ground-Truth Efficiency Audit):
      * Monitors the next 10 M1 bars after closure to verify whether price reversed
        (confirming an optimal peak exit) or continued surging (money left on the table).
  - Emits structured JSON blackbox files for every ticket into vault/flight_recorder/
========================================================================================
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import MetaTrader5 as mt5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
VAULT_DIR = os.path.join(ROOT_DIR, "vault", "flight_recorder")
os.makedirs(VAULT_DIR, exist_ok=True)

LEDGER_FILE = os.path.join(VAULT_DIR, "blackbox_ledger.json")

logger = logging.getLogger("TradeFlightRecorder")


class TradeFlightRecorder:
    """
    Sub-second Trade Flight Recorder & Post-Exit Ground-Truth Auditor.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.active_flights: Dict[int, Dict[str, Any]] = {}
        self.post_exit_queue: Dict[int, Dict[str, Any]] = {}
        self.load_pending_post_exits()

    def load_pending_post_exits(self) -> None:
        """Loads any trades waiting for post-exit 10-minute bar audits."""
        pending_file = os.path.join(VAULT_DIR, "pending_post_exits.json")
        if os.path.exists(pending_file):
            try:
                with open(pending_file, "r", encoding="utf-8") as f:
                    self.post_exit_queue = json.load(f)
            except Exception:
                self.post_exit_queue = {}

    def save_pending_post_exits(self) -> None:
        pending_file = os.path.join(VAULT_DIR, "pending_post_exits.json")
        try:
            with open(pending_file, "w", encoding="utf-8") as f:
                json.dump(self.post_exit_queue, f, indent=2)
        except Exception:
            pass

    def record_entry(
        self,
        ticket: int,
        symbol: str,
        action: str,
        volume: float,
        entry_price: float,
        sl: float,
        tp: float,
        strategy_name: str = "Unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initializes a new flight recorder log when an order fills."""
        init_risk = abs(entry_price - sl) if sl > 0 else 0.001
        now_ts = time.time()

        flight = {
            "ticket": ticket,
            "symbol": symbol,
            "action": action.upper(),
            "volume": volume,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "init_risk": init_risk,
            "strategy_name": strategy_name,
            "opened_at": datetime.now().isoformat(),
            "opened_timestamp": now_ts,
            "status": "ACTIVE",
            "entry_metadata": metadata or {},
            "mfe_r": 0.0,
            "mae_r": 0.0,
            "peak_profit_usd": 0.0,
            "samples_count": 0,
            "trajectory": [],  # Second-by-second micro-samples
        }
        self.active_flights[ticket] = flight
        logger.info(f"[🛰️ FLIGHT RECORDER] Initialized blackbox for #{ticket} {symbol} {action} @ {entry_price:.5f}")

    def record_tick(
        self,
        ticket: int,
        current_price: float,
        current_profit: float,
        k_field: Optional[Dict[str, Any]] = None,
        anatomy: Optional[Dict[str, Any]] = None,
        status_tag: str = "NORMAL",
    ) -> None:
        """Records a live sub-second or 1-second telemetry sample."""
        flight = self.active_flights.get(ticket)
        if not flight:
            return

        now_ts = time.time()
        elapsed_sec = round(now_ts - flight["opened_timestamp"], 1)

        is_buy = (flight["action"] == "BUY")
        open_price = flight["entry_price"]
        init_risk = max(1e-6, flight["init_risk"])

        raw_dist = (current_price - open_price) if is_buy else (open_price - current_price)
        floating_r = round(raw_dist / init_risk, 3)

        # Update MFE & MAE
        flight["mfe_r"] = max(flight["mfe_r"], floating_r)
        if floating_r < 0:
            flight["mae_r"] = max(flight["mae_r"], abs(floating_r))
        flight["peak_profit_usd"] = max(flight["peak_profit_usd"], current_profit)

        k_t = k_field.get("k_current", 0.0) if k_field else 0.0
        k_base = k_field.get("k_base", 0.0) if k_field else 0.0
        k_ratio = k_field.get("k_ratio", 1.0) if k_field else 1.0

        sample = {
            "sec": elapsed_sec,
            "price": round(current_price, 5),
            "profit": round(current_profit, 2),
            "r": floating_r,
            "k_t": k_t,
            "k_base": k_base,
            "k_ratio": k_ratio,
            "wick_opp": anatomy.get("upper_ratio" if is_buy else "lower_ratio", 0.0) if anatomy else 0.0,
            "tag": status_tag,
        }

        # Keep trajectory token-efficient (record every second, capped to last 600 samples = 10 mins)
        flight["trajectory"].append(sample)
        if len(flight["trajectory"]) > 600:
            flight["trajectory"].pop(0)

        flight["samples_count"] += 1

    def record_exit(
        self,
        ticket: int,
        exit_price: float,
        banked_profit: float,
        exit_reason: str,
    ) -> None:
        """Finalizes the trade flight log and schedules post-exit monitoring."""
        flight = self.active_flights.pop(ticket, None)
        if not flight:
            return

        now_ts = time.time()
        elapsed_sec = round(now_ts - flight["opened_timestamp"], 1)

        is_buy = (flight["action"] == "BUY")
        open_price = flight["entry_price"]
        init_risk = max(1e-6, flight["init_risk"])
        final_dist = (exit_price - open_price) if is_buy else (open_price - exit_price)
        final_r = round(final_dist / init_risk, 3)

        flight["status"] = "CLOSED"
        flight["closed_at"] = datetime.now().isoformat(),
        flight["closed_timestamp"] = now_ts
        flight["duration_seconds"] = elapsed_sec
        flight["exit_price"] = exit_price
        flight["banked_profit"] = banked_profit
        flight["final_r"] = final_r
        flight["exit_reason"] = exit_reason

        # Calculate Exit Efficiency (how close to peak MFE did we cash out?)
        peak_r = max(1e-4, flight["mfe_r"])
        efficiency = min(100.0, max(0.0, (final_r / peak_r) * 100.0)) if peak_r > 0 else 0.0
        flight["exit_efficiency_pct"] = round(efficiency, 1)

        # Save flight blackbox JSON
        ticket_file = os.path.join(VAULT_DIR, f"blackbox_{ticket}.json")
        try:
            with open(ticket_file, "w", encoding="utf-8") as f:
                json.dump(flight, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save blackbox file: {e}")

        # Append to Master Ledger
        self._append_to_ledger(flight)

        # Enqueue for Post-Exit Ground-Truth Monitoring (Next 10 M1 bars = 600 seconds)
        self.post_exit_queue[str(ticket)] = {
            "ticket": ticket,
            "symbol": flight["symbol"],
            "action": flight["action"],
            "exit_price": exit_price,
            "exit_r": final_r,
            "exit_time": now_ts,
            "init_risk": init_risk,
            "bars_inspected": 0,
        }
        self.save_pending_post_exits()

        logger.info(
            f"[🛰️ FLIGHT RECORDER CLOSED] #{ticket} {flight['symbol']} | "
            f"Result: {final_r:+.2f}R (${banked_profit:+.2f}) in {elapsed_sec:.0f}s | "
            f"MFE: +{flight['mfe_r']:.2f}R | Efficiency: {efficiency:.1f}% | Reason: {exit_reason}"
        )

    def audit_post_exits(self) -> None:
        """
        Monitors what happened in the market AFTER the trade was closed.
        Answers: Did price reverse immediately (proving our exit was genius)?
                 Or did price keep running (leaving money on the table)?
        """
        now_ts = time.time()
        to_delete = []

        for t_str, item in self.post_exit_queue.items():
            ticket = item["ticket"]
            symbol = item["symbol"]
            is_buy = (item["action"] == "BUY")
            exit_price = item["exit_price"]
            exit_r = item["exit_r"]
            init_risk = max(1e-6, item["init_risk"])

            age_sec = now_ts - item["exit_time"]
            if age_sec < 60:
                continue  # Wait for at least 1 closed M1 bar

            # Get M1 bars since exit
            bars_needed = min(15, max(3, int(age_sec / 60)))
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars_needed)
            if rates is None or len(rates) < 2:
                continue

            # Check price displacement post-exit
            post_high = max([float(r['high']) for r in rates])
            post_low = min([float(r['low']) for r in rates])

            if is_buy:
                post_run_r = (post_high - exit_price) / init_risk
                post_drop_r = (exit_price - post_low) / init_risk
            else:
                post_run_r = (exit_price - post_low) / init_risk
                post_drop_r = (post_high - exit_price) / init_risk

            # If 10 minutes elapsed, finalize post-exit truth audit
            if age_sec >= 600 or bars_needed >= 10:
                reversed_immediately = (post_drop_r > 0.30 and post_drop_r > post_run_r)
                ran_further = (post_run_r > 0.50)

                audit_result = {
                    "post_exit_duration_s": round(age_sec, 0),
                    "post_run_r": round(post_run_r, 2),
                    "post_reversal_drop_r": round(post_drop_r, 2),
                    "reversed_immediately": reversed_immediately,
                    "ran_further": ran_further,
                    "verdict": "OPTIMAL_PEAK_EXIT" if reversed_immediately else ("LEAVING_RUNNER_POTENTIAL" if ran_further else "BALANCED_EXIT")
                }

                # Update the ticket's blackbox JSON
                ticket_file = os.path.join(VAULT_DIR, f"blackbox_{ticket}.json")
                if os.path.exists(ticket_file):
                    try:
                        with open(ticket_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data["post_exit_audit"] = audit_result
                        with open(ticket_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                    except Exception:
                        pass

                logger.info(
                    f"[🔬 POST-EXIT AUDIT] #{ticket} {symbol} | Post Run: {post_run_r:+.2f}R | "
                    f"Post Drop: {post_drop_r:+.2f}R | Verdict: {audit_result['verdict']}"
                )
                to_delete.append(t_str)

        for k in to_delete:
            self.post_exit_queue.pop(k, None)
        if to_delete:
            self.save_pending_post_exits()

    def _append_to_ledger(self, flight: Dict[str, Any]) -> None:
        """Appends trade summary to the master flight recorder ledger."""
        ledger = []
        if os.path.exists(LEDGER_FILE):
            try:
                with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
            except Exception:
                ledger = []

        summary = {
            "ticket": flight["ticket"],
            "symbol": flight["symbol"],
            "action": flight["action"],
            "opened_at": flight["opened_at"],
            "closed_at": flight.get("closed_at"),
            "duration_s": flight.get("duration_seconds", 0),
            "final_r": flight.get("final_r", 0.0),
            "banked_profit": flight.get("banked_profit", 0.0),
            "mfe_r": flight.get("mfe_r", 0.0),
            "mae_r": flight.get("mae_r", 0.0),
            "efficiency_pct": flight.get("exit_efficiency_pct", 0.0),
            "exit_reason": flight.get("exit_reason", ""),
        }
        ledger.append(summary)
        try:
            with open(LEDGER_FILE, "w", encoding="utf-8") as f:
                json.dump(ledger[-200:], f, indent=2)  # Keep latest 200 flights
        except Exception:
            pass


def get_flight_recorder() -> TradeFlightRecorder:
    return TradeFlightRecorder.get_instance()
