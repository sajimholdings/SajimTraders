"""
========================================================================================
           SAJIM HOLDINGS V2 — TELEMETRY & WEBAPP API BRIDGE (v2/api/telemetry_bridge.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  Provides standardized functions and data exchange interfaces for the upcoming
  Sajim Holdings WebApp and external monitoring dashboards.
  Reads live engine states, handles operational toggles, and exposes portfolio metrics.
========================================================================================
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("TelemetryBridge")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_FILE = os.path.join(BASE_DIR, "coexistence_status.json")


class TelemetryBridge:
    """
    Standardized Data Exchange & Management Bridge for Sajim V1 & V2.
    """

    @staticmethod
    def read_unified_status() -> Dict[str, Any]:
        """Reads real-time portfolio status emitted by the Dual Orchestrator."""
        if not os.path.exists(STATUS_FILE):
            return {
                "status": "OFFLINE",
                "message": "Dual Orchestrator has not yet generated status file.",
            }
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read coexistence status: {e}")
            return {"status": "ERROR", "error": str(e)}

    @staticmethod
    def get_active_positions(bot_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves active positions filtered by bot:
        - bot_filter="V1": only Magic 777999
        - bot_filter="V2": only Magic 888222
        - None: all active positions
        """
        data = TelemetryBridge.read_unified_status()
        positions_dict = data.get("positions", {})
        v1_pos = positions_dict.get("v1", [])
        v2_pos = positions_dict.get("v2", [])

        if bot_filter and bot_filter.upper() == "V1":
            return v1_pos
        elif bot_filter and bot_filter.upper() == "V2":
            return v2_pos
        return v1_pos + v2_pos

    @staticmethod
    def get_account_metrics() -> Dict[str, Any]:
        """Returns key financial health metrics for dashboard display."""
        data = TelemetryBridge.read_unified_status()
        acc = data.get("account", {})
        pnl = data.get("pnl", {})
        concurrency = data.get("concurrency", {})
        circuit = data.get("circuit_breaker", {})

        return {
            "balance": acc.get("balance", 0.0),
            "equity": acc.get("equity", 0.0),
            "free_margin": acc.get("free_margin", 0.0),
            "margin_level_pct": acc.get("margin_level_pct", 0.0),
            "currency": acc.get("currency", "USC"),
            "today_closed_pnl": pnl.get("today_closed", 0.0),
            "today_floating_pnl": pnl.get("today_floating", 0.0),
            "combined_daily_net": pnl.get("combined_daily_net", 0.0),
            "total_open_trades": concurrency.get("total_open", 0),
            "max_allowed_trades": concurrency.get("max_combined", 0),
            "circuit_breaker_active": circuit.get("active", False),
            "circuit_breaker_reason": circuit.get("reason", ""),
        }
