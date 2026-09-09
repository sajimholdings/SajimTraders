"""
========================================================================================
            SAJIM HOLDINGS — V1 QUANTITATIVE EDGE FILTER (config/v1_edge_filter.py)
========================================================================================
Chief Architect: Jimmy Mathu
Purpose:
  - Plugs directly into Sajim V1 (`sajim_v1_bot.py` and `sajim_server_overnight.py`).
  - Restricts V1 execution strictly to the empirically verified positive-expectancy
    pairs and timeframes from the 204-front quantitative backtest.
  - Automatically filters out all 157 toxic bleeder setups without requiring code refactors.
========================================================================================
"""

import os
import json
from typing import Dict, List, Set, Optional

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(CONFIG_DIR, "v1_edge_filter.json")

# Fallback in-memory map if JSON is ever unreadable
DEFAULT_APPROVED_MAP: Dict[str, List[str]] = {
    # High-Velocity JPY Momentum Edges (PF 1.46 - 1.87)
    "EURJPY.c": ["M5"],
    "CADJPY.c": ["M5", "H1"],
    "AUDJPY.c": ["M5", "H4"],
    "CHFJPY.c": ["M5"],
    "GBPJPY.c": ["M5", "M30", "H1"],
    "NZDJPY.c": ["M30", "H1"],
    "USDJPY.c": ["M5", "M15"],

    # Institutional Trend Runners (PF 1.51 - 1.99)
    "USDCAD.c": ["M15", "M30", "H4"],
    "EURUSD.c": ["M30"],
    "NZDUSD.c": ["H4"],

    # Metals Macro Swings (PF 1.50 - 1.59)
    "XAUUSD.c": ["M30", "H4"],
    "XAUGBP.c": ["M1", "H4"],
    "XAUJPY.c": ["M1", "M30", "H4"],
    "XAGUSD.c": ["H4"],
    "XPDUSD.c": ["M30"],

    # Standard counterparts
    "EURJPY": ["M5"],
    "CADJPY": ["M5", "H1"],
    "AUDJPY": ["M5", "H4"],
    "CHFJPY": ["M5"],
    "GBPJPY": ["M5", "M30", "H1"],
    "NZDJPY": ["M30", "H1"],
    "USDJPY": ["M5", "M15"],
    "USDCAD": ["M15", "M30", "H4"],
    "EURUSD": ["M30"],
    "NZDUSD": ["H4"],
    "XAUUSD": ["M30", "H4"],
    "XAUGBP": ["M1", "H4"],
    "XAUJPY": ["M1", "M30", "H4"],
    "XAGUSD": ["H4"],
    "XPDUSD": ["M30"],
}


def load_approved_map() -> Dict[str, List[str]]:
    """Loads approved pairs and timeframes from JSON configuration."""
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                edges = data.get("approved_edges")
                if edges and isinstance(edges, dict):
                    return edges
        except Exception:
            pass
    return DEFAULT_APPROVED_MAP


V1_APPROVED_EDGE_MAP: Dict[str, List[str]] = load_approved_map()


def is_v1_approved(symbol: str, timeframe: str) -> bool:
    """
    Evaluates whether a symbol + timeframe combination is authorized for Sajim V1.
    Delegates to master centralized whitelist config/master_trading_whitelist.json.
    """
    try:
        from core.whitelist_manager import get_whitelist_manager
        return get_whitelist_manager().is_pair_approved("V1_BEEP", symbol, timeframe)
    except Exception:
        s = symbol.strip()
        tf = timeframe.strip().upper()
        allowed_tfs = DEFAULT_APPROVED_MAP.get(s) or DEFAULT_APPROVED_MAP.get(s.replace(".c", "")) or []
        return tf in allowed_tfs


def get_v1_approved_symbols() -> List[str]:
    """Returns the list of all symbols authorized for Sajim V1."""
    try:
        from core.whitelist_manager import get_whitelist_manager
        wl = get_whitelist_manager().get_strategy_whitelist("V1_BEEP")
        if wl:
            return sorted(list(wl.keys()))
    except Exception:
        pass
    return sorted(list(DEFAULT_APPROVED_MAP.keys()))
