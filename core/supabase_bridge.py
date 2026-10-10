"""
========================================================================================
            SAJIM TRADERS — SUPABASE BRIDGE & CLOUD EVENT BUS (core/supabase_bridge.py)
========================================================================================
Connects the Python Quant Engine & MT5 Bridge with Supabase (PostgreSQL + Realtime).

This is the single source of truth for the multi-tenant product:
  1. Client trading accounts (trading_accounts)
  2. Live quantitative signals (signals)
  3. Order execution queue (orders_queue) — 1-Tap orders, autopilot mirroring
  4. Closed-trade history (trade_history)

Security model:
  - The browser talks to Supabase directly with Row-Level Security (RLS) scoped to auth.uid().
  - This class uses the SERVICE-ROLE key and must only run server-side (API / bridge) —
    never in the browser.
"""

import os
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("SajimSupabaseBridge")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Columns that must never leave the server (stripped by public_account()).
SECRET_ACCOUNT_COLUMNS = ("encrypted_password",)


def q(value: Any) -> str:
    """URL-encode a value interpolated into a PostgREST filter (prevents filter injection:
    e.g. an account_id of '123&user_id=...' or '123#' can no longer alter/truncate the query)."""
    return urllib.parse.quote(str(value), safe="")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_account(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a copy of a trading_accounts row with secret columns removed."""
    if not isinstance(row, dict):
        return row
    return {k: v for k, v in row.items() if k not in SECRET_ACCOUNT_COLUMNS}


class SupabaseBridge:
    """Service-role REST client for Supabase database operations."""

    def __init__(self, base_url: str = SUPABASE_URL, api_key: str = SUPABASE_KEY):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Any] = None,
        headers_extra: Optional[Dict[str, str]] = None,
    ) -> Any:
        if not self.configured:
            return {"error": "Supabase not configured (missing SUPABASE_URL / SERVICE_ROLE_KEY)"}
        url = f"{self.base_url}/rest/v1/{endpoint.lstrip('/')}"
        headers = self._headers()
        if headers_extra:
            headers.update(headers_extra)

        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8")
            logger.error(f"Supabase HTTP Error ({e.code}) on {endpoint}: {err}")
            return {"error": err, "status": e.code}
        except Exception as e:
            logger.error(f"Supabase Connection Error on {endpoint}: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def check_health(self) -> bool:
        """Verifies connection to the Supabase REST gateway."""
        if not self.configured:
            return False
        res = self._request("", method="GET")
        return "error" not in res

    # ------------------------------------------------------------------
    # Trading accounts
    # ------------------------------------------------------------------
    def get_trading_account(
        self,
        account_id: str,
        user_id: Optional[str] = None,
        broker_server: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a trading_accounts row by account_id (and optionally user_id / broker_server)."""
        row, _ok = self.fetch_trading_account(account_id, user_id=user_id, broker_server=broker_server)
        return row

    def fetch_trading_account(
        self,
        account_id: str,
        user_id: Optional[str] = None,
        broker_server: Optional[str] = None,
    ):
        """Like get_trading_account but returns (row_or_None, ok). ok=False means the
        lookup itself failed (network / HTTP error), so callers can tell 'deleted' apart
        from 'could not check'."""
        endpoint = f"trading_accounts?account_id=eq.{q(account_id)}&select=*&order=created_at.asc&limit=1"
        if user_id:
            endpoint += f"&user_id=eq.{q(user_id)}"
        if broker_server:
            endpoint += f"&broker_server=eq.{q(broker_server)}"
        res = self._request(endpoint, method="GET")
        if isinstance(res, list):
            return (res[0] if res else None), True
        return None, False

    def upsert_trading_account(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a trading_accounts row keyed on (account_id, broker_server).

        MT5 account ownership is exclusive: if the (account_id, broker_server) pair is
        already linked to a different user, the upsert is refused.
        """
        account_id = payload.get("account_id")
        user_id = payload.get("user_id")
        broker_server = payload.get("broker_server")
        if not account_id:
            return {"success": False, "error": "account_id is required"}

        existing = self.get_trading_account(str(account_id), broker_server=broker_server)
        if existing and user_id and existing.get("user_id") and existing.get("user_id") != user_id:
            return {"success": False, "error": "This MT5 account is already linked to another user", "status": 409}
        if existing and existing.get("id"):
            res = self._request(
                f"trading_accounts?id=eq.{q(existing['id'])}",
                method="PATCH",
                data=payload,
                headers_extra={"Prefer": "return=representation"},
            )
            row = res[0] if isinstance(res, list) and res else existing
        else:
            res = self._request(
                "trading_accounts",
                method="POST",
                data=payload,
                headers_extra={"Prefer": "return=representation"},
            )
            row = res[0] if isinstance(res, list) and res else res

        if isinstance(row, dict) and "error" not in row:
            return {"success": True, "account": row}
        return {"success": False, "error": row.get("error", "upsert failed") if isinstance(row, dict) else "upsert failed"}

    def list_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch all trading accounts owned by a user (newest first)."""
        res = self._request(
            f"trading_accounts?user_id=eq.{q(user_id)}&order=created_at.desc&select=*",
            method="GET",
        )
        return res if isinstance(res, list) else []

    def update_trading_account(self, row_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH specific columns of a trading_accounts row by its UUID."""
        res = self._request(
            f"trading_accounts?id=eq.{q(row_id)}",
            method="PATCH",
            data=fields,
            headers_extra={"Prefer": "return=representation"},
        )
        row = res[0] if isinstance(res, list) and res else res
        if isinstance(row, dict) and row and "error" not in row:
            return {"success": True, "account": row}
        return {"success": False, "error": row.get("error", "update failed") if isinstance(row, dict) else "update failed"}

    def delete_trading_account(self, row_id: str) -> Any:
        return self._request(f"trading_accounts?id=eq.{q(row_id)}", method="DELETE")

    def get_enrolled_autopilot_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all client accounts that have Auto-Pilot enabled."""
        res = self._request("trading_accounts?autopilot_enabled=eq.true&select=*", method="GET")
        return res if isinstance(res, list) else []

    def list_trading_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all registered trading accounts (service role)."""
        res = self._request("trading_accounts?select=*&order=created_at.asc", method="GET")
        return res if isinstance(res, list) else []

    def sync_account_telemetry(
        self,
        account_id: str,
        balance: float,
        equity: float,
        free_margin: float,
        today_pnl: float,
        today_pnl_percent: float,
        terminal_connected: bool = True,
        broker_server: Optional[str] = None,
        floating_pnl: Optional[float] = None,
        margin_level: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Pushes real-time balance and performance into Supabase for client view.

        Scoped to the (account_id, broker_server) row so the same login number on a
        different broker server is never overwritten.
        """
        endpoint = f"trading_accounts?account_id=eq.{q(account_id)}"
        if broker_server:
            endpoint += f"&broker_server=eq.{q(broker_server)}"
        payload = {
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "free_margin": round(free_margin, 2),
            "today_pnl": round(today_pnl, 2),
            "today_pnl_percent": round(today_pnl_percent, 2),
            "terminal_connected": terminal_connected,
            "last_sync_at": utc_now_iso(),
        }
        if floating_pnl is not None:
            payload["floating_pnl"] = round(float(floating_pnl), 2)
        if margin_level is not None:
            payload["margin_level"] = round(float(margin_level), 2)
        return self._request(endpoint, method="PATCH", data=payload)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    def publish_signal(self, signal: Dict[str, Any], ttl_minutes: Optional[float] = None) -> Dict[str, Any]:
        """Publishes a live quantitative signal for all subscribers.

        If ttl_minutes is given and the signal has no expires_at, one is set so stale
        signals drop out of get_active_signals() (and are never mirrored by autopilot).
        """
        signal = dict(signal)
        if ttl_minutes and not signal.get("expires_at"):
            signal["expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=float(ttl_minutes))).isoformat()
        headers_extra = {"Prefer": "resolution=merge-duplicates"}
        return self._request("signals", method="POST", data=signal, headers_extra=headers_extra)

    def get_active_signals(self, limit: int = 30, max_age_minutes: Optional[float] = None) -> List[Dict[str, Any]]:
        """Fetch currently active, unexpired signals (newest first).

        max_age_minutes additionally restricts to signals created within that window.
        """
        now = datetime.now(timezone.utc)
        endpoint = (
            f"signals?is_active=eq.true&order=created_at.desc&limit={int(limit)}&select=*"
            f"&or={q(f'(expires_at.is.null,expires_at.gt.{now.isoformat()})')}"
        )
        if max_age_minutes is not None:
            since = (now - timedelta(minutes=float(max_age_minutes))).isoformat()
            endpoint += f"&created_at=gt.{q(since)}"
        res = self._request(endpoint, method="GET")
        return res if isinstance(res, list) else []

    # ------------------------------------------------------------------
    # Orders queue
    # ------------------------------------------------------------------
    def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Insert an order into orders_queue. Returns the created row (with UUID id)."""
        res = self._request(
            "orders_queue",
            method="POST",
            data=payload,
            headers_extra={"Prefer": "return=representation"},
        )
        row = res[0] if isinstance(res, list) and res else res
        if isinstance(row, dict) and "error" not in row:
            return {"success": True, "order": row}
        return {"success": False, "error": row.get("error", "create_order failed") if isinstance(row, dict) else "create_order failed"}

    def list_orders(
        self,
        account_id: str,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch orders for an account, optionally filtered by status / owner."""
        endpoint = f"orders_queue?account_id=eq.{q(account_id)}&order=created_at.asc&select=*"
        if status:
            endpoint += f"&status=eq.{q(status)}"
        if user_id:
            endpoint += f"&user_id=eq.{q(user_id)}"
        res = self._request(endpoint, method="GET")
        return res if isinstance(res, list) else []

    def list_open_positions(self, account_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Open positions = FILLED BUY/SELL orders that have not yet been closed.

        FILLED CLOSE orders are close *requests*, not positions, and are excluded.
        """
        return [
            o for o in self.list_orders(account_id, status="FILLED", user_id=user_id)
            if str(o.get("action", "")).upper() in ("BUY", "SELL")
        ]

    def get_pending_orders(self, account_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pull PENDING orders waiting for bridge execution."""
        endpoint = "orders_queue?status=eq.PENDING&order=created_at.asc&select=*"
        if account_id:
            endpoint += f"&account_id=eq.{q(account_id)}"
        if user_id:
            endpoint += f"&user_id=eq.{q(user_id)}"
        res = self._request(endpoint, method="GET")
        return res if isinstance(res, list) else []

    def claim_order(self, order_id: str) -> bool:
        """Atomically move a PENDING order to PROCESSING. Returns False if another worker
        (or a previous run) already claimed it, preventing double execution."""
        res = self._request(
            f"orders_queue?id=eq.{q(order_id)}&status=eq.PENDING",
            method="PATCH",
            data={"status": "PROCESSING"},
            headers_extra={"Prefer": "return=representation"},
        )
        return isinstance(res, list) and len(res) > 0

    def fail_stale_processing_orders(self, account_id: str, older_than_minutes: float = 5.0) -> List[Dict[str, Any]]:
        """Mark orders stuck in PROCESSING (worker crashed mid-execution) as FAILED.

        They are NOT retried automatically: the order may or may not have reached the
        broker, so retrying risks a double execution. The user must check the terminal.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=float(older_than_minutes))).isoformat()
        res = self._request(
            f"orders_queue?status=eq.PROCESSING&account_id=eq.{q(account_id)}&created_at=lt.{q(cutoff)}",
            method="PATCH",
            data={
                "status": "FAILED",
                "error_message": (
                    f"Stuck in PROCESSING > {older_than_minutes:g} min (bridge interrupted). "
                    "Not retried to avoid double execution — verify on the MT5 terminal."
                ),
            },
            headers_extra={"Prefer": "return=representation"},
        )
        return res if isinstance(res, list) else []

    def update_order_status(
        self,
        order_id: str,
        status: str,
        mt5_ticket: Optional[int] = None,
        open_price: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an order's status once processed by the MT5 bridge."""
        payload = {
            "status": status,
            "mt5_ticket": mt5_ticket,
            "open_price": open_price,
            "error_message": error_message,
            "executed_at": utc_now_iso() if status == "FILLED" else None,
        }
        return self._request(f"orders_queue?id=eq.{q(order_id)}", method="PATCH", data=payload)

    def mark_order_closed(
        self,
        order_id: str,
        close_price: float,
        profit: float,
    ) -> Dict[str, Any]:
        """Mark a FILLED order as CLOSED with final price and realized PnL."""
        payload = {
            "status": "CLOSED",
            "current_price": round(close_price, 5),
            "floating_pnl": round(profit, 2),
            "closed_at": utc_now_iso(),
        }
        return self._request(f"orders_queue?id=eq.{q(order_id)}", method="PATCH", data=payload)

    def update_position_pnl(
        self,
        order_id: str,
        current_price: float,
        floating_pnl: float,
    ) -> Dict[str, Any]:
        """Update the live price and floating PnL of a still-open FILLED order."""
        payload = {
            "current_price": round(current_price, 5),
            "floating_pnl": round(floating_pnl, 2),
        }
        return self._request(f"orders_queue?id=eq.{q(order_id)}", method="PATCH", data=payload)

    # ------------------------------------------------------------------
    # Trade history
    # ------------------------------------------------------------------
    def insert_trade_history(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Record a closed trade in trade_history.

        Idempotent on (account_id, mt5_ticket) (unique constraint in schema.sql): a
        duplicate reconciliation is ignored instead of creating a second row.
        """
        res = self._request(
            "trade_history?on_conflict=account_id,mt5_ticket",
            method="POST",
            data=trade,
            headers_extra={"Prefer": "return=representation,resolution=ignore-duplicates"},
        )
        return res[0] if isinstance(res, list) and res else res

    def list_trade_history(self, account_id: str, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Closed trades for an account owned by user_id (newest first)."""
        res = self._request(
            f"trade_history?account_id=eq.{q(account_id)}&user_id=eq.{q(user_id)}"
            f"&order=close_time.desc&limit={int(limit)}&select=*",
            method="GET",
        )
        return res if isinstance(res, list) else []


# Global Bridge Instance
supabase_bridge = SupabaseBridge()
