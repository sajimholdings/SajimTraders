"""
========================================================================================
        SAJIM RISK — PERSISTENT PER-TICKET POSITION STATE (v2/risk/position_state.py)
========================================================================================
Stores, per position ticket:
  - initial_risk : |entry - initial SL| recorded at entry. ALL R-multiples are computed
                   against this value, never against the current (trailed) stop loss.
  - stage        : ratchet stage ("INITIAL", "STAGE_0_BE", "STAGE_1_BE", "STAGE_2_LOCK")
  - harvested    : True once a partial harvest was banked (prevents a second 50% close
                   after a restart).
State is persisted to state/<name>_positions.json so a restart keeps it.

Initial-risk resolution order for a ticket with no stored record:
  1. the opening order's SL from MT5 order history (history_orders_get(position=...))
  2. |TP - entry| / default_rr when the caller supplies the strategy's R:R
  3. None -> callers must SKIP R-based management for that ticket.
========================================================================================
"""

import os
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

logger = logging.getLogger("SajimPositionState")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.environ.get("SAJIM_STATE_DIR", os.path.join(ROOT_DIR, "state"))


class PositionStateStore:
    """Small JSON-backed store of per-ticket risk state."""

    def __init__(self, name: str, path: Optional[str] = None, persist: bool = True):
        self.name = name
        self.persist = persist
        self.path = path or os.path.join(STATE_DIR, f"{name}_positions.json")
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = {}
        if self.persist:
            self._load()

    # ------------------------------------------------------------------ io
    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._data = {str(k): v for k, v in data.items() if isinstance(v, dict)}
        except FileNotFoundError:
            self._data = {}
        except Exception as e:
            logger.warning(f"[{self.name}] Could not read position state {self.path}: {e}")
            self._data = {}

    def save(self) -> None:
        if not self.persist:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp, self.path)
        except Exception as e:
            logger.warning(f"[{self.name}] Could not persist position state {self.path}: {e}")

    # -------------------------------------------------------------- accessors
    def get(self, ticket: int) -> Dict[str, Any]:
        return dict(self._data.get(str(ticket), {}))

    def _update(self, ticket: int, **fields: Any) -> None:
        with self._lock:
            rec = self._data.setdefault(str(ticket), {})
            rec.update(fields)
            self.save()

    def record_entry(
        self,
        ticket: int,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        bot: str = "",
    ) -> Optional[float]:
        """Records the initial risk of a freshly opened position."""
        risk = abs(float(entry_price) - float(stop_loss)) if stop_loss else 0.0
        if risk <= 0:
            logger.warning(f"[{self.name}] #{ticket} {symbol}: no valid initial SL; R-management disabled for it.")
            return None
        self._update(
            ticket,
            symbol=symbol,
            entry_price=float(entry_price),
            initial_sl=float(stop_loss),
            initial_risk=risk,
            stage="INITIAL",
            bot=bot,
            source="entry",
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        return risk

    def get_stage(self, ticket: int, default: str = "INITIAL") -> str:
        return str(self._data.get(str(ticket), {}).get("stage", default))

    def set_stage(self, ticket: int, stage: str) -> None:
        self._update(ticket, stage=stage)

    def is_harvested(self, ticket: int) -> bool:
        return bool(self._data.get(str(ticket), {}).get("harvested", False))

    def mark_harvested(self, ticket: int) -> None:
        self._update(ticket, harvested=True)

    def stages(self) -> Dict[int, str]:
        out: Dict[int, str] = {}
        for k, v in self._data.items():
            try:
                out[int(k)] = str(v.get("stage", "INITIAL"))
            except (TypeError, ValueError):
                continue
        return out

    def harvested_tickets(self) -> Iterable[int]:
        out = []
        for k, v in self._data.items():
            if v.get("harvested"):
                try:
                    out.append(int(k))
                except (TypeError, ValueError):
                    pass
        return out

    def forget(self, ticket: int) -> None:
        with self._lock:
            if self._data.pop(str(ticket), None) is not None:
                self.save()

    def prune(self, open_tickets: Iterable[int]) -> None:
        """Drops state for tickets that are no longer open."""
        keep = {str(t) for t in open_tickets}
        with self._lock:
            stale = [k for k in self._data if k not in keep]
            if stale:
                for k in stale:
                    self._data.pop(k, None)
                self.save()

    # ---------------------------------------------------------- initial risk
    def initial_risk(self, pos: Any, mt5_module: Any = None, default_rr: Optional[float] = None) -> Optional[float]:
        """
        Returns the initial risk (price distance) for an open position, resolving and
        persisting it if needed. Returns None if it cannot be determined reliably.
        """
        ticket = int(getattr(pos, "ticket", 0))
        rec = self._data.get(str(ticket))
        if rec and float(rec.get("initial_risk", 0.0) or 0.0) > 0:
            return float(rec["initial_risk"])

        open_price = float(getattr(pos, "price_open", 0.0) or 0.0)
        symbol = str(getattr(pos, "symbol", ""))

        # 1. Opening order SL from MT5 history
        if mt5_module is not None and hasattr(mt5_module, "history_orders_get"):
            try:
                orders = mt5_module.history_orders_get(position=ticket) or []
                orders = sorted(orders, key=lambda o: getattr(o, "time_setup_msc", getattr(o, "time_setup", 0)))
                for o in orders:
                    o_sl = float(getattr(o, "sl", 0.0) or 0.0)
                    if o_sl > 0 and open_price > 0 and abs(open_price - o_sl) > 0:
                        risk = abs(open_price - o_sl)
                        self._update(ticket, symbol=symbol, entry_price=open_price, initial_sl=o_sl,
                                     initial_risk=risk, source="order_history")
                        logger.info(f"[{self.name}] #{ticket} initial risk recovered from order history: {risk}")
                        return risk
            except Exception as e:
                logger.debug(f"[{self.name}] order history lookup failed for #{ticket}: {e}")

        # 2. TP distance / known R:R
        tp = float(getattr(pos, "tp", 0.0) or 0.0)
        if default_rr and default_rr > 0 and tp > 0 and open_price > 0:
            risk = abs(tp - open_price) / float(default_rr)
            if risk > 0:
                self._update(ticket, symbol=symbol, entry_price=open_price, initial_risk=risk, source="tp_rr")
                logger.info(f"[{self.name}] #{ticket} initial risk derived from TP / {default_rr}R: {risk}")
                return risk

        # 3. Unknown -> skip R-based management
        return None


_stores: Dict[str, PositionStateStore] = {}


def get_position_store(name: str) -> PositionStateStore:
    """Process-wide singleton per bot name so entry and management share one store."""
    if name not in _stores:
        _stores[name] = PositionStateStore(name)
    return _stores[name]
