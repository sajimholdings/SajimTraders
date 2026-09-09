"""
========================================================================================
           SAJIM HOLDINGS — COEXISTENCE & HARMONY GATEKEEPER (v2/coexistence.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Purpose:
  Enforces zero-conflict, scale-invariant co-execution of Sajim V1 and Sajim V2
  on the same MetaTrader 5 terminal account (JustMarkets-Demo3 / cent & standard).

Core Governance Pillars:
  1. MAGIC NUMBER ISOLATION:
     - Sajim V1: 777999 (comments: Sajim_DIAMOND, Sajim_RARE, Sajim_Scratch, etc.)
     - Sajim V2: 888222 (comments: Sajim_V2_Continuation, Sajim_V2_Reversion)
     Neither bot ever modifies, trails, or closes positions belonging to the other.
  2. AGGREGATE MARGIN & POSITION CAP:
     - Caps total open tickets across both bots (default: max 6 positions total).
     - Margin Level must stay >= 500% to permit new entries.
  3. DIRECTIONAL CONFLICT SHIELD:
     - Blocks opposing trades on the same currency pair (e.g. V1 BUY vs V2 SELL).
     - Eliminates self-hedging broker spread cannibalization.
  4. MACRO CURRENCY CLUSTER EXPOSURE CAP:
     - Max 2 positions per single currency (USD, EUR, GBP, JPY, CAD, AUD, NZD, CHF, XAU)
       across the entire portfolio combined.
  5. UNIFIED ACCOUNT 5% DAILY DRAWDOWN CIRCUIT BREAKER:
     - Sums closed and floating daily PnL across all tickets.
     - Halts new entries for both bots if account drops >= 5.0% on the day.
  6. REAL-TIME WEBAPP TELEMETRY:
     - Emits v2/coexistence_status.json continuously for external WebApp integration.
========================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger("CoexistenceGatekeeper")

MAGIC_V1 = 777999
MAGIC_V2 = 888222

MAX_COMBINED_POSITIONS = 6
MIN_MARGIN_LEVEL_PCT = 500.0
MAX_CLUSTER_EXPOSURE = 2
MAX_DAILY_DRAWDOWN_PCT = 0.05  # 5% max daily account risk


class CoexistenceGatekeeper:
    """
    Central Portfolio Guardian and Harmony Coordinator for Sajim V1 & V2.
    """

    def __init__(
        self,
        max_combined_positions: int = MAX_COMBINED_POSITIONS,
        min_margin_level_pct: float = MIN_MARGIN_LEVEL_PCT,
        max_cluster_exposure: int = MAX_CLUSTER_EXPOSURE,
        max_daily_drawdown_pct: float = MAX_DAILY_DRAWDOWN_PCT,
        status_file_path: Optional[str] = None,
    ):
        self.max_combined_positions = max_combined_positions
        self.min_margin_level = min_margin_level_pct
        self.max_cluster_exposure = max_cluster_exposure
        self.max_daily_dd_pct = max_daily_drawdown_pct

        if status_file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.status_file_path = os.path.join(base_dir, "coexistence_status.json")
        else:
            self.status_file_path = status_file_path

        # Dynamic State Tracking
        self.v1_positions: List[Dict[str, Any]] = []
        self.v2_positions: List[Dict[str, Any]] = []
        self.other_positions: List[Dict[str, Any]] = []

        self.account_balance: float = 0.0
        self.account_equity: float = 0.0
        self.account_margin: float = 0.0
        self.account_margin_free: float = 0.0
        self.account_margin_level: float = 9999.0
        self.currency: str = "USC"

        self.today_closed_pnl: float = 0.0
        self.today_floating_pnl: float = 0.0
        self.circuit_breaker_active: bool = False
        self.circuit_breaker_reason: str = ""

        # Bot active toggles (pluggable controls for WebApp)
        self.v1_enabled: bool = True
        self.v2_enabled: bool = True

    @staticmethod
    def get_currencies_for_symbol(symbol: str) -> List[str]:
        """Extracts underlying currency codes from symbol (e.g. 'EURUSD.c' -> ['EUR', 'USD'])."""
        clean = symbol.upper().replace(".C", "").replace("_C", "").replace(".M", "")
        currencies = []
        for curr in ("EUR", "USD", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF", "XAU", "XAG"):
            if curr in clean:
                currencies.append(curr)
        return currencies if currencies else ["OTHER"]

    def refresh(
        self,
        account_info: Any,
        all_positions: List[Any],
        today_deals: List[Any],
    ) -> None:
        """
        Refreshes live portfolio snapshot from MT5 objects.
        """
        if account_info:
            self.account_balance = float(account_info.balance)
            self.account_equity = float(account_info.equity)
            self.account_margin = float(account_info.margin)
            self.account_margin_free = float(account_info.margin_free)
            # When margin is 0, margin_level is infinite
            self.account_margin_level = (
                float(account_info.margin_level)
                if getattr(account_info, "margin_level", 0) > 0
                else 9999.0
            )
            self.currency = getattr(account_info, "currency", "USC")

        # Categorize positions by Magic Number
        self.v1_positions.clear()
        self.v2_positions.clear()
        self.other_positions.clear()
        total_float = 0.0

        for p in all_positions:
            total_float += float(p.profit)
            pos_dict = {
                "ticket": int(p.ticket),
                "symbol": str(p.symbol),
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": float(p.volume),
                "price_open": float(p.price_open),
                "sl": float(p.sl),
                "tp": float(p.tp),
                "profit": float(p.profit),
                "magic": int(p.magic),
                "comment": str(getattr(p, "comment", "")),
            }
            if p.magic == MAGIC_V1:
                self.v1_positions.append(pos_dict)
            elif p.magic == MAGIC_V2:
                self.v2_positions.append(pos_dict)
            else:
                self.other_positions.append(pos_dict)

        self.today_floating_pnl = round(total_float, 2)

        # Calculate today's closed deals PnL
        closed_pnl = 0.0
        for d in today_deals:
            # DEAL_ENTRY_OUT (1) or DEAL_ENTRY_INOUT (2) indicates a closed trade
            if getattr(d, "entry", 0) in (1, 2):
                closed_pnl += float(d.profit)

        self.today_closed_pnl = round(closed_pnl, 2)

        # Evaluate Daily Circuit Breaker
        net_daily_pnl = self.today_closed_pnl + min(0.0, self.today_floating_pnl)
        max_allowed_loss = self.account_balance * self.max_daily_dd_pct
        if net_daily_pnl < 0 and abs(net_daily_pnl) >= max_allowed_loss and self.account_balance > 0:
            self.circuit_breaker_active = True
            self.circuit_breaker_reason = (
                f"Combined daily net loss ({net_daily_pnl:.2f} {self.currency}) >= "
                f"5% limit ({max_allowed_loss:.2f} {self.currency})"
            )
        else:
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = ""

        # Emit updated JSON telemetry
        self.save_status()

    def check_pre_entry_clearance(
        self,
        bot_name: str,
        symbol: str,
        action: str,
    ) -> Tuple[bool, str]:
        """
        Universal Clearance Gate:
        Evaluates whether an order for `symbol` with `action` is permitted.
        Checks:
          1. Bot active toggle
          2. Daily circuit breaker
          3. Aggregate combined position ceiling
          4. Margin level health
          5. Directional conflict on the same asset
          6. Currency cluster exposure ceiling
        """
        # 1. Bot Active Toggle
        if bot_name.upper() == "V1" and not self.v1_enabled:
            return False, "Sajim V1 is currently toggled OFF in gatekeeper"
        if bot_name.upper() == "V2" and not self.v2_enabled:
            return False, "Sajim V2 is currently toggled OFF in gatekeeper"

        # 2. Daily Circuit Breaker
        if self.circuit_breaker_active:
            return False, f"🛑 Circuit Breaker Active: {self.circuit_breaker_reason}"

        # 3. Aggregate Combined Position Ceiling
        total_open = len(self.v1_positions) + len(self.v2_positions) + len(self.other_positions)
        if total_open >= self.max_combined_positions:
            return False, (
                f"Aggregate position ceiling reached ({total_open}/{self.max_combined_positions}). "
                f"V1: {len(self.v1_positions)} | V2: {len(self.v2_positions)} | Other: {len(self.other_positions)}"
            )

        # 4. Margin Level Health
        if self.account_margin > 0 and self.account_margin_level < self.min_margin_level:
            return False, (
                f"Margin level ({self.account_margin_level:.1f}%) < required {self.min_margin_level:.1f}%. "
                f"Capital preservation lock engaged."
            )

        # 5. Directional Conflict Blocker
        # Prohibit opening an opposite position on the exact same symbol
        all_active = self.v1_positions + self.v2_positions + self.other_positions
        for pos in all_active:
            if pos["symbol"] == symbol:
                existing_action = pos["type"]
                if existing_action != action:
                    return False, (
                        f"Directional conflict on {symbol}: Existing active {existing_action} (Ticket #{pos['ticket']} "
                        f"Magic: {pos['magic']}). Opposing {action} rejected to prevent spread cannibalization."
                    )

        # 6. Macro Currency Cluster Exposure Cap
        proposed_currencies = self.get_currencies_for_symbol(symbol)
        curr_counts: Dict[str, int] = {}
        for pos in all_active:
            pos_currs = self.get_currencies_for_symbol(pos["symbol"])
            for c in pos_currs:
                curr_counts[c] = curr_counts.get(c, 0) + 1

        for c in proposed_currencies:
            if c != "OTHER" and curr_counts.get(c, 0) >= self.max_cluster_exposure:
                return False, (
                    f"Currency cluster cap reached for [{c}]: Currently {curr_counts[c]} positions active "
                    f"(Max allowed: {self.max_cluster_exposure})."
                )

        return True, "CLEARANCE_GRANTED"

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Returns clean snapshot dictionary for logging and API telemetry."""
        return {
            "timestamp": datetime.now().isoformat(),
            "account": {
                "balance": self.account_balance,
                "equity": self.account_equity,
                "free_margin": self.account_margin_free,
                "margin_level_pct": round(self.account_margin_level, 2),
                "currency": self.currency,
            },
            "pnl": {
                "today_closed": self.today_closed_pnl,
                "today_floating": self.today_floating_pnl,
                "combined_daily_net": round(self.today_closed_pnl + self.today_floating_pnl, 2),
            },
            "circuit_breaker": {
                "active": self.circuit_breaker_active,
                "reason": self.circuit_breaker_reason,
            },
            "concurrency": {
                "total_open": len(self.v1_positions) + len(self.v2_positions) + len(self.other_positions),
                "max_combined": self.max_combined_positions,
                "v1_count": len(self.v1_positions),
                "v2_count": len(self.v2_positions),
                "other_count": len(self.other_positions),
            },
            "toggles": {
                "v1_enabled": self.v1_enabled,
                "v2_enabled": self.v2_enabled,
            },
            "positions": {
                "v1": self.v1_positions,
                "v2": self.v2_positions,
            },
        }

    def save_status(self) -> None:
        """Writes live status JSON to file."""
        try:
            summary = self.get_portfolio_summary()
            temp_path = self.status_file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            if os.path.exists(self.status_file_path):
                os.remove(self.status_file_path)
            os.rename(temp_path, self.status_file_path)
        except Exception as e:
            logger.debug(f"Failed to write coexistence status: {e}")
