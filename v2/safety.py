"""
========================================================================================
           SAJIM HOLDINGS — SHARED TRADING SAFETY HELPERS (v2/safety.py)
========================================================================================
Small, dependency-free helpers shared by every bot (V1, V2, Dual, Prop Firm, 1-Tap):

  1. GLOBAL KILL SWITCH
     - Create a file named `KILL_SWITCH` in the repository root, or set the environment
       variable `SAJIM_KILL_SWITCH=1`, and every bot stops opening NEW trades.
     - Position management (stops, exits) keeps running so open risk is still managed.
     - Delete the file / unset the variable to resume.

  2. ACCOUNT CURRENCY NORMALISATION
     - Cent accounts are detected from `account_info().currency` (USC, EUC, ...), never
       from the broker server name or the symbol suffix.
     - `to_major_units()` converts cent balances to major units (USC -> USD) so that
       hard-coded dollar thresholds behave identically on cent and standard accounts.

  3. UTC DAILY DRAWDOWN GUARD
     - Day boundaries are UTC.
     - Baseline = start-of-day equity (persisted to state/daily_equity_baseline.json so a
       restart does not reset it), never lower than the start-of-day balance reconstructed
       from today's deals.
     - Drawdown = start_equity - current_equity, so floating P&L, commissions, swaps and
       fees are all included (they are already reflected in equity).
========================================================================================
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

logger = logging.getLogger("SajimSafety")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.environ.get("SAJIM_STATE_DIR", os.path.join(ROOT_DIR, "state"))

KILL_SWITCH_FILE = os.path.join(ROOT_DIR, "KILL_SWITCH")
KILL_SWITCH_ENV = "SAJIM_KILL_SWITCH"

# Account currencies that denote cent (1/100) accounts.
CENT_CURRENCIES = {"USC", "EUC", "GBC", "EUX", "GBX", "JPC", "AUC", "CAC", "CHC"}

# MT5 deal types that are external cash flows rather than trading results
# (DEAL_TYPE_BALANCE=2, DEAL_TYPE_CREDIT=3, DEAL_TYPE_BONUS=6).
_EXTERNAL_DEAL_TYPES = {2, 3, 6}


# ---------------------------------------------------------------------------
# 1. Kill switch
# ---------------------------------------------------------------------------
_last_kill_log = 0.0


def kill_switch_active() -> bool:
    """True if the global kill switch is engaged (file in repo root or env var)."""
    env = os.environ.get(KILL_SWITCH_ENV, "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    return os.path.exists(KILL_SWITCH_FILE)


def new_entries_allowed(bot_name: str = "BOT") -> bool:
    """Returns False (and logs, throttled) when the kill switch blocks new entries."""
    global _last_kill_log
    if not kill_switch_active():
        return True
    now = time.time()
    if now - _last_kill_log > 60.0:
        _last_kill_log = now
        logger.warning(
            f"[KILL SWITCH] {bot_name}: new entries blocked "
            f"(file {KILL_SWITCH_FILE} present or {KILL_SWITCH_ENV}=1). Open positions are still managed."
        )
    return False


# ---------------------------------------------------------------------------
# 2. Account currency normalisation
# ---------------------------------------------------------------------------
def is_cent_currency(currency: Optional[str]) -> bool:
    if not currency:
        return False
    cur = str(currency).strip()
    return cur.upper() in CENT_CURRENCIES or "cent" in cur.lower()


def is_cent_account(account_info: Any) -> bool:
    return is_cent_currency(getattr(account_info, "currency", None))


def cent_divisor(currency: Optional[str]) -> float:
    """100 for cent accounts (1 USD = 100 USC), otherwise 1."""
    return 100.0 if is_cent_currency(currency) else 1.0


def to_major_units(amount: float, currency: Optional[str]) -> float:
    """Converts an account-currency amount to major units (USC -> USD)."""
    return float(amount) / cent_divisor(currency)


def from_major_units(amount: float, currency: Optional[str]) -> float:
    """Converts a major-unit amount (USD) into account units (USD -> USC on cent accounts)."""
    return float(amount) * cent_divisor(currency)


def unit_label(currency: Optional[str]) -> str:
    return str(currency) if currency else "UNITS"


# ---------------------------------------------------------------------------
# 3. UTC day boundaries & daily drawdown
# ---------------------------------------------------------------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_day_start(now: Optional[datetime] = None) -> datetime:
    now = now or utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _deal_get(d: Any, key: str, default: float = 0.0) -> Any:
    if isinstance(d, dict):
        return d.get(key, default)
    return getattr(d, key, default)


def summarize_deals(deals: Optional[Iterable[Any]]) -> Tuple[float, float]:
    """
    Returns (trading_pnl, external_cash_flow) for a list of deals.
    trading_pnl includes profit + commission + swap + fee of every trading deal
    (entry AND exit deals, so entry commissions are counted).
    """
    trading = 0.0
    external = 0.0
    for d in deals or []:
        dtype = int(_deal_get(d, "type", 0) or 0)
        amount = (
            float(_deal_get(d, "profit", 0.0) or 0.0)
            + float(_deal_get(d, "commission", 0.0) or 0.0)
            + float(_deal_get(d, "swap", 0.0) or 0.0)
            + float(_deal_get(d, "fee", 0.0) or 0.0)
        )
        if dtype in _EXTERNAL_DEAL_TYPES:
            external += amount
        else:
            trading += amount
    return trading, external


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: str, data: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        logger.debug(f"Failed to persist {path}: {e}")


class DailyDrawdownGuard:
    """
    UTC-day drawdown guard measured on equity.
      drawdown = start_of_day_equity - current_equity
    Limit = min(max_dd_pct * start_equity, max_dd_amount) for whichever limits are set
    (max_dd_amount is in ACCOUNT currency units).
    """

    def __init__(
        self,
        name: str,
        max_dd_pct: Optional[float] = None,
        max_dd_amount: Optional[float] = None,
        state_file: Optional[str] = None,
        persist: bool = True,
    ):
        self.name = name
        self.max_dd_pct = max_dd_pct
        self.max_dd_amount = max_dd_amount
        self.persist = persist
        self.state_file = state_file or os.path.join(STATE_DIR, "daily_equity_baseline.json")
        self._memory: Dict[str, Any] = {}

    def _baseline(self, login: Any, day: str, equity: float, reconstructed: float, external: float) -> float:
        key = f"{self.name}:{login}"
        state = _load_json(self.state_file) if self.persist else self._memory
        entry = state.get(key)
        if not entry or entry.get("day") != day:
            entry = {"day": day, "equity": float(equity), "external_at_record": float(external)}
            state[key] = entry
            if self.persist:
                _save_json(self.state_file, state)
        # Adjust the recorded equity for deposits / withdrawals made after it was recorded.
        recorded = float(entry.get("equity", equity)) + (float(external) - float(entry.get("external_at_record", 0.0)))
        return max(recorded, reconstructed)

    def evaluate(self, account_info: Any, today_deals: Optional[Iterable[Any]]) -> Dict[str, Any]:
        """Returns a dict with ok / start_equity / equity / drawdown / limit / reason."""
        if account_info is None:
            return {"ok": False, "reason": "No account info available", "drawdown": 0.0, "limit": 0.0}

        balance = float(getattr(account_info, "balance", 0.0) or 0.0)
        equity = float(getattr(account_info, "equity", balance) or 0.0)
        currency = getattr(account_info, "currency", "")
        login = getattr(account_info, "login", "default")

        trading_pnl, external = summarize_deals(today_deals)
        reconstructed_start = balance - trading_pnl - external
        day = utc_day_start().strftime("%Y-%m-%d")
        start_equity = self._baseline(login, day, equity, reconstructed_start, external)

        drawdown = max(0.0, start_equity - equity)
        limits = []
        if self.max_dd_pct is not None and start_equity > 0:
            limits.append(start_equity * float(self.max_dd_pct))
        if self.max_dd_amount is not None:
            limits.append(float(self.max_dd_amount))
        limit = min(limits) if limits else float("inf")

        ok = drawdown < limit
        reason = "" if ok else (
            f"UTC daily drawdown {drawdown:.2f} {unit_label(currency)} >= limit {limit:.2f} "
            f"{unit_label(currency)} (start-of-day equity {start_equity:.2f}, equity {equity:.2f})"
        )
        return {
            "ok": ok,
            "start_equity": round(start_equity, 2),
            "equity": round(equity, 2),
            "drawdown": round(drawdown, 2),
            "limit": round(limit, 2) if limit != float("inf") else None,
            "today_trading_pnl": round(trading_pnl, 2),
            "currency": currency,
            "reason": reason,
        }
