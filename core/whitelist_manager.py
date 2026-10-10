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

TIMEFRAMES = {"M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H2", "H4", "H6", "H8", "H12", "D1", "W1", "MN1"}


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
        """
        Strips broker suffixes to get the base canonical symbol:
          'XAUUSD.c' / 'XAUUSD_c' -> 'XAUUSD', 'BTCUSDc' / 'EURUSDc' -> 'BTCUSD' / 'EURUSD',
          'GBPJPYC' -> 'GBPJPY' (upper-case 'C' only stripped when it cannot be part of 'USDC').
        """
        s = str(symbol).strip()
        lowered = s.lower()
        if lowered.endswith(".c") or lowered.endswith("_c"):
            return s[:-2].upper()
        # Lower-case 'c' cent suffix on an otherwise upper-case symbol (e.g. BTCUSDc)
        if len(s) >= 4 and s.endswith("c") and s[:-1].upper() == s[:-1]:
            return s[:-1].upper()
        s = s.upper()
        if s.endswith("C"):
            candidate = s[:-1]
            if len(candidate) >= 3 and not candidate.endswith("USD"):
                s = candidate
        return s

    @staticmethod
    def _split_symbol_tf(entry: str):
        """'GBPJPY_M15' -> ('GBPJPY', 'M15'); 'XAUGBP' -> ('XAUGBP', None)."""
        e = str(entry).strip()
        if "_" in e:
            base, tf = e.rsplit("_", 1)
            if tf.upper() in TIMEFRAMES:
                return base, tf.upper()
        return e, None

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
        """Returns symbol-level blacklisted toxic assets (with broker suffix variants)."""
        self._load()
        bl = set()
        for entry in self.data.get("toxic_blacklist", []):
            base, tf = self._split_symbol_tf(entry)
            if tf is not None:
                continue  # per-timeframe entries are handled by get_toxic_timeframes()
            clean = self._clean_symbol(base)
            for variant in (base, clean, f"{clean}.c", f"{clean}_c", f"{clean}c"):
                bl.add(variant)
        return bl

    def get_toxic_timeframes(self) -> Dict[str, Set[str]]:
        """Returns per-timeframe toxic fronts, e.g. {'GBPJPY': {'M15'}} from 'GBPJPY_M15'."""
        self._load()
        out: Dict[str, Set[str]] = {}
        for entry in self.data.get("toxic_blacklist", []):
            base, tf = self._split_symbol_tf(entry)
            if tf is None:
                continue
            out.setdefault(self._clean_symbol(base), set()).add(tf)
        return out

    def is_toxic(self, symbol: str, timeframe: Optional[str] = None) -> bool:
        """
        Checks if a symbol (or a symbol + timeframe front) is toxic.
        Symbol-level entries block every timeframe; 'SYMBOL_TF' entries block that front only.
        """
        clean = self._clean_symbol(symbol)
        bl = self.get_toxic_blacklist()
        if clean in bl or symbol in bl:
            return True
        if timeframe:
            return str(timeframe).strip().upper() in self.get_toxic_timeframes().get(clean, set())
        return False

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
        1. Must NOT be toxic (symbol-level or this symbol_TF front).
        2. Must be in live_trading_whitelist.
        3. Strategy must have an entry for this symbol & timeframe.
        """
        if self.is_toxic(symbol, timeframe):
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
