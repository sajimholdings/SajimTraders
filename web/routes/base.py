"""
========================================================================================
           SAJIM WEB GATEWAY — BASE ROUTE & UTILITY MODULE (web/routes/base.py)
========================================================================================
Modular Web Architecture: All modules < 250 lines.
"""

import os
import sys
import json
import logging
from datetime import datetime

logger = logging.getLogger("SajimWebBase")

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.abspath(os.path.join(WEB_DIR, ".."))
STATIC_DIR = os.path.join(WEB_DIR, "static")

# Shared state file paths
COEXISTENCE_STATUS_FILE = os.path.join(ROOT_DIR, "logs", "coexistence_status.json")
OVERNIGHT_STATUS_FILE = os.path.join(ROOT_DIR, "logs", "overnight_telemetry.json")
CIRCUIT_BREAKER_FILE = os.path.join(ROOT_DIR, "logs", "circuit_breaker_status.json")
SIGNALS_FILE = os.path.join(ROOT_DIR, "logs", "live_signals.json")
BROADCAST_ACTIVE_FILE = os.path.join(ROOT_DIR, "broadcast_active.json")
GRAND_CONFLUENCE_AUDIT = os.path.join(ROOT_DIR, "logs", "grand_confluence_audit.json")
COMMUNITY_STATE_FILE = os.path.join(ROOT_DIR, "logs", "community_concierge_state.json")
EXPECTANCY_EDGE_FILE = os.path.join(ROOT_DIR, "logs", "quant_expectancy_report.json")
FLIGHT_RECORDER_FILE = os.path.join(ROOT_DIR, "logs", "flight_recorder_manifest.json")


def load_json_safe(path: str, default: any = None) -> any:
    """Thread-safe and error-tolerant JSON loader."""
    if default is None:
        default = {}
    if not os.path.exists(path):
        alt_path = os.path.join(ROOT_DIR, os.path.basename(path))
        if os.path.exists(alt_path):
            path = alt_path
        else:
            return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def get_market_session() -> str:
    """Returns current active institutional market session."""
    hour = datetime.utcnow().hour
    if 0 <= hour < 7:
        return "Asian / Tokyo Session"
    elif 7 <= hour < 12:
        return "London Open / European Session"
    elif 12 <= hour < 17:
        return "London / New York Overlap (Prime High Velocity)"
    elif 17 <= hour < 21:
        return "New York Afternoon Session"
    else:
        return "Sydney / Asian Pre-Market"
