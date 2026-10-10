"""
========================================================================================
            SAJIM HOLDINGS — V1 EDGE FILTER SHIM (config/v1_edge_filter.py)
========================================================================================
DEPRECATED compatibility shim.

The single source of truth for every whitelist / blacklist is
`config/master_trading_whitelist.json`, read through `core/whitelist_manager.py`.
The former `config/v1_edge_filter.json` contradicted the master whitelist and was only
used as a silent fallback; it has been removed. This module now only delegates to the
whitelist manager and FAILS CLOSED (nothing approved) if the manager cannot be loaded.
========================================================================================
"""

import logging
from typing import List

logger = logging.getLogger("V1EdgeFilterShim")

V1_STRATEGY_KEY = "V1_BEEP"


def is_v1_approved(symbol: str, timeframe: str) -> bool:
    """True if symbol + timeframe is approved for Sajim V1 by the master whitelist."""
    try:
        from core.whitelist_manager import get_whitelist_manager
        return get_whitelist_manager().is_pair_approved(V1_STRATEGY_KEY, symbol, timeframe)
    except Exception as e:
        logger.error(f"Master whitelist unavailable ({e}); V1 entry on {symbol} {timeframe} denied.")
        return False


def get_v1_approved_symbols() -> List[str]:
    """Returns the symbols authorized for Sajim V1 by the master whitelist (empty on error)."""
    try:
        from core.whitelist_manager import get_whitelist_manager
        wl = get_whitelist_manager().get_strategy_whitelist(V1_STRATEGY_KEY)
        return sorted(list(wl.keys())) if wl else []
    except Exception as e:
        logger.error(f"Master whitelist unavailable ({e}); no V1 symbols approved.")
        return []
