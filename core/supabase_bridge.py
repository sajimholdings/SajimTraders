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
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("SajimSupabaseBridge")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


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
    def get_trading_account(self, account_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch a trading_accounts row by account_id (and optionally user_id)."""
        endpoint = f"trading_accounts?account_id=eq.{account_id}&select=*&limit=1"
        if user_id:
            endpoint += f"&user_id=eq.{user_id}"
        res = self._request(endpoint, method="GET")
        if isinstance(res, list) and res:
            return res[0]
        return None

    def upsert_trading_account(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a trading_accounts row keyed on (user_id, account_id, broker_server)."""
        account_id = payload.get("account_id")
        user_id = payload.get("user_id")
        if not account_id:
            return {"success": False, "error": "account_id is required"}

        existing = self.get_trading_account(str(account_id), user_id=user_id)
        if existing and existing.get("id"):
            res = self._request(
                f"trading_accounts?id=eq.{existing['id']}",
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
        return {"success": False, "error": row.get("error", "upsert failed")}

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
    ) -> Dict[str, Any]:
        """Pushes real-time balance and performance into Supabase for client view."""
        endpoint = f"trading_accounts?account_id=eq.{account_id}"
        payload = {
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "free_margin": round(free_margin, 2),
            "today_pnl": round(today_pnl, 2),
            "today_pnl_percent": round(today_pnl_percent, 2),
            "terminal_connected": terminal_connected,
            "last_sync_at": datetime.utcnow().isoformat(),
        }
        return self._request(endpoint, method="PATCH", data=payload)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------
    def publish_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes a live quantitative signal for all subscribers."""
        headers_extra = {"Prefer": "resolution=merge-duplicates"}
        return self._request("signals", method="POST", data=signal, headers_extra=headers_extra)

    def get_active_signals(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetch currently active signals (newest first)."""
        endpoint = f"signals?is_active=eq.true&order=created_at.desc&limit={limit}&select=*"
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
        return {"success": False, "error": row.get("error", "create_order failed")}

    def list_orders(self, account_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch orders for an account, optionally filtered by status."""
        endpoint = f"orders_queue?account_id=eq.{account_id}&order=created_at.asc&select=*"
        if status:
            endpoint += f"&status=eq.{status}"
        res = self._request(endpoint, method="GET")
        return res if isinstance(res, list) else []

    def list_open_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """Open positions = FILLED orders that have not yet been closed."""
        return self.list_orders(account_id, status="FILLED")

    def get_pending_orders(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pull PENDING orders waiting for bridge execution."""
        endpoint = "orders_queue?status=eq.PENDING&order=created_at.asc&select=*"
        if account_id:
            endpoint = f"orders_queue?status=eq.PENDING&account_id=eq.{account_id}&order=created_at.asc&select=*"
        res = self._request(endpoint, method="GET")
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
            "executed_at": datetime.utcnow().isoformat() if status == "FILLED" else None,
        }
        return self._request(f"orders_queue?id=eq.{order_id}", method="PATCH", data=payload)

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
            "closed_at": datetime.utcnow().isoformat(),
        }
        return self._request(f"orders_queue?id=eq.{order_id}", method="PATCH", data=payload)

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
        return self._request(f"orders_queue?id=eq.{order_id}", method="PATCH", data=payload)

    # ------------------------------------------------------------------
    # Trade history
    # ------------------------------------------------------------------
    def insert_trade_history(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Record a closed trade in trade_history."""
        res = self._request(
            "trade_history",
            method="POST",
            data=trade,
            headers_extra={"Prefer": "return=representation"},
        )
        return res[0] if isinstance(res, list) and res else res


# Global Bridge Instance
supabase_bridge = SupabaseBridge()
