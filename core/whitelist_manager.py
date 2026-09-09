"""
========================================================================================
         SAJIM QUANT LABS — UNIFIED WHITELIST MANAGER (core/whitelist_manager.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  - Single Source of Truth for all trade whitelists across Sajim V1 and Sajim V2.
  - Hot-reloads `config/master_trading_whitelist.json` dynamically on any file modification.
  - Distinguishes:
      1. `live_trading_whitelist` : Strictly allowed to submit real money orders to MT5.
      2. `paper_testing_watchlist`: Monitored ONLY by the Forward Signal Truth Tester.
  - Automatically cleans broker symbol suffixes (.c, _c, c, standard).
========================================================================================
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
WHITELIST_JSON_PATH = os.path.join(ROOT_DIR, "config", "master_trading_whitelist.json")

logger = logging.getLogger("WhitelistManager")


class WhitelistManager:
    """
    Centralized controller for master trading whitelists and execution permissions.
    """

    def __init__(self, json_path: str = WHITELIST_JSON_PATH):
        self.json_path = json_path
        self.last_mtime: float = 0.0
        self.data: Dict[str, Any] = {}
        self._load()

    def _clean_symbol(self, symbol: str) -> str:
        """Strips broker suffixes (.c, _c, etc.) to get base canonical symbol."""
        s = symbol.upper().strip()
        for suffix in (".C", "_C", "C"):
            if s.endswith(suffix):
                candidate = s[:-len(suffix)]
                if len(candidate) >= 3 and not candidate.endswith("USD"):
                    s = candidate
                elif suffix in (".C", "_C"):
                    s = s[:-len(suffix)]
        return s

    def _load(self) -> None:
        """Reloads JSON from disk if file was updated."""
        if not os.path.exists(self.json_path):
            logger.warning(f"Whitelist JSON not found at {self.json_path}.")
            return

        try:
            mtime = os.path.getmtime(self.json_path)
            if mtime > self.last_mtime:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                self.last_mtime = mtime
                live_syms = self.data.get("live_trading_whitelist", [])
                logger.info(f"[+] Hot-Reloaded Master Whitelist: Live Universe = {live_syms}")
        except Exception as e:
            logger.error(f"Error reading master whitelist JSON: {e}")

    def get_live_trading_universe(self) -> List[str]:
        """Returns the strictly approved symbols allowed for LIVE trading."""
        self._load()
        return list(self.data.get("live_trading_whitelist", []))

    def get_paper_testing_watchlist(self) -> List[str]:
        """Returns the probation / research watchlist for forward testing only."""
        self._load()
        return list(self.data.get("paper_testing_watchlist", []))

    def get_all_scanned_universe(self) -> List[str]:
        """Returns union of live universe and paper testing symbols for truth monitoring."""
        self._load()
        live = self.get_live_trading_universe()
        paper = self.get_paper_testing_watchlist()
        # Deduplicate preserving order
        seen = set()
        combined = []
        for s in live + paper:
            if s not in seen:
                seen.add(s)
                combined.append(s)
        return combined

    def get_toxic_blacklist(self) -> Set[str]:
        """Returns blacklisted toxic assets."""
        self._load()
        bl = set()
        for s in self.data.get("toxic_blacklist", []):
            bl.add(s)
            bl.add(f"{s}.c")
            bl.add(f"{s}_c")
        return bl

    def is_toxic(self, symbol: str) -> bool:
        """Checks if symbol is toxic."""
        clean = self._clean_symbol(symbol)
        bl = self.get_toxic_blacklist()
        return clean in bl or symbol in bl

    def is_live_trading_approved(self, symbol: str) -> bool:
        """Checks if symbol is authorized for REAL MONEY execution."""
        clean = self._clean_symbol(symbol)
        live_syms = [self._clean_symbol(s) for s in self.get_live_trading_universe()]
        return clean in live_syms

    def get_strategy_whitelist(self, strategy_name: str) -> Dict[str, List[str]]:
        """Returns clean symbol -> timeframes mapping for strategy."""
        self._load()
        strategies = self.data.get("strategies", {})
        for key, wl in strategies.items():
            if key.lower() == strategy_name.lower() or key.lower() in strategy_name.lower():
                return wl
        return strategies.get(strategy_name, {})

    def is_pair_approved(self, strategy_name: str, symbol: str, timeframe: str) -> bool:
        """
        Full authorization check:
        1. Must NOT be toxic.
        2. Must be in live_trading_whitelist.
        3. Strategy must have an entry for this symbol & timeframe.
        """
        if self.is_toxic(symbol):
            return False

        if not self.is_live_trading_approved(symbol):
            return False

        wl = self.get_strategy_whitelist(strategy_name)
        if not wl:
            return False

        clean = self._clean_symbol(symbol)
        allowed_tfs = wl.get(clean) or wl.get(symbol) or wl.get(f"{clean}.c") or []
        return timeframe in allowed_tfs


# Global Singleton
_whitelist_manager: Optional[WhitelistManager] = None


def get_whitelist_manager() -> WhitelistManager:
    global _whitelist_manager
    if _whitelist_manager is None:
        _whitelist_manager = WhitelistManager()
    return _whitelist_manager
