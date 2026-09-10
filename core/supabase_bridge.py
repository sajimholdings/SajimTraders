"""
========================================================================================
            SAJIM TRADERS — SUPABASE BRIDGE & CLOUD EVENT BUS (core/supabase_bridge.py)
========================================================================================
Connects the Python Quant Engine & MT5 Bridge with Supabase (PostgreSQL + Realtime).
Handles:
  1. Synchronizing live account telemetry (Balance, Equity, Today's PnL)
  2. Broadcasting live quantitative signals into Supabase
  3. Polling the 'orders_queue' for 1-Tap executions from the web portal
  4. Updating order statuses and trade flight records
========================================================================================
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
    """Enterprise REST client for Supabase database operations."""

    def __init__(self, base_url: str = SUPABASE_URL, api_key: str = SUPABASE_KEY):
        self.base_url = base_url
        self.api_key = api_key

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

    def check_health(self) -> bool:
        """Verifies connection to Supabase REST gateway."""
        res = self._request("", method="GET")
        return "error" not in res

    def get_enrolled_autopilot_accounts(self) -> List[Dict[str, Any]]:
        """Fetches all client accounts that have Auto-Pilot enabled."""
        endpoint = "trading_accounts?autopilot_enabled=eq.true&select=*"
        res = self._request(endpoint, method="GET")
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

    def publish_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Publishes a live quantitative signal to Supabase for all subscribers."""
        endpoint = "signals"
        headers_extra = {"Prefer": "resolution=merge-duplicates"}
        return self._request(endpoint, method="POST", data=signal, headers_extra=headers_extra)

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Pulls pending 1-Tap orders submitted by clients from the web portal."""
        endpoint = "orders_queue?status=eq.PENDING&order=created_at.asc&select=*"
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
        """Updates order status once processed by the MT5 bridge."""
        endpoint = f"orders_queue?id=eq.{order_id}"
        payload = {
            "status": status,
            "mt5_ticket": mt5_ticket,
            "open_price": open_price,
            "error_message": error_message,
            "executed_at": datetime.utcnow().isoformat() if status == "FILLED" else None,
        }
        return self._request(endpoint, method="PATCH", data=payload)


# Global Bridge Instance
supabase_bridge = SupabaseBridge()
