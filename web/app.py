"""
========================================================================================
        SAJIM TRADERS — FASTAPI GATEWAY (web/app.py)
========================================================================================
Replaces the stdlib http.server gateway with a typed, JWT-authenticated API backed by
Supabase. The browser authenticates with Supabase, sends its access token, and this
server scopes all data to that user (auth.uid()).

Client data endpoints (account, signals, orders, positions) are Supabase-backed and
user-scoped. Admin endpoints require an X-ADMIN-KEY.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.supabase_bridge import SupabaseBridge
from core.credential_vault import encrypt_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SajimFastAPI")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

app = FastAPI(title="Sajim Traders API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

bridge = SupabaseBridge()
bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def fetch_supabase_user(token: str) -> Optional[dict]:
    """Validate a Supabase access token and return the user object (or None)."""
    if not SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    try:
        r = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if cred is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    user = fetch_supabase_user(cred.credentials)
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    if not ADMIN_KEY:
        raise HTTPException(status_code=503, detail="Admin key not configured")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ---------------------------------------------------------------------------
# Client account
# ---------------------------------------------------------------------------
def _to_client_trade(order: dict) -> dict:
    """Map an orders_queue row to the ClientTrade shape the frontend expects."""
    return {
        "ticket": int(order.get("mt5_ticket") or 0),
        "symbol": order.get("symbol", ""),
        "type": order.get("action", "BUY"),
        "volume": float(order.get("volume") or 0),
        "open_price": float(order.get("open_price") or 0),
        "current_price": float(order.get("current_price") or 0),
        "sl": float(order.get("sl") or 0),
        "tp": float(order.get("tp") or 0),
        "pnl": float(order.get("floating_pnl") or 0),
        "time": order.get("executed_at"),
        "comment": order.get("comment"),
    }


@app.get("/api/client/account")
def get_account(account_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id required")
    acc = bridge.get_trading_account(str(account_id), user_id=user["id"])
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    positions = bridge.list_open_positions(str(account_id))
    acc["open_positions"] = [_to_client_trade(o) for o in positions]
    return acc


@app.get("/api/client/accounts")
def list_accounts(user: dict = Depends(get_current_user)):
    res = bridge._request(
        f"trading_accounts?user_id=eq.{user['id']}&order=created_at.desc&select=*",
        method="GET",
    )
    accounts = res if isinstance(res, list) else []
    return {"accounts": accounts}


@app.post("/api/client/connect")
def connect(body: dict, user: dict = Depends(get_current_user)):
    account_id = str(body.get("account_id", "")).strip()
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required")

    broker_server = body.get("broker_server", "Headway-Real")
    payload = {
        "user_id": user["id"],
        "account_id": account_id,
        "account_name": body.get("account_name", f"Account #{account_id}"),
        "broker_server": broker_server,
        "broker_name": body.get("broker_name", str(broker_server).split("-")[0]),
        "autopilot_enabled": bool(body.get("autopilot_enabled", False)),
        "risk_mode": body.get("risk_mode", "ULTRA_SAFE"),
        "currency": body.get("currency", "USD"),
        "is_demo": "demo" in str(broker_server).lower(),
        "terminal_connected": False,
    }
    password = body.get("password")
    if password:
        payload["encrypted_password"] = encrypt_password(str(password))
    res = bridge.upsert_trading_account(payload)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "connect failed"))
    return {"success": True, "account": res["account"]}


@app.post("/api/client/delete-account")
def delete_account(body: dict, user: dict = Depends(get_current_user)):
    account_id = str(body.get("account_id", "")).strip()
    acc = bridge.get_trading_account(account_id, user_id=user["id"])
    if not acc or not acc.get("id"):
        raise HTTPException(status_code=404, detail="Account not found")
    bridge._request(f"trading_accounts?id=eq.{acc['id']}", method="DELETE")
    return {"success": True, "removed": account_id}


@app.post("/api/client/switch-account")
def switch_account(body: dict, user: dict = Depends(get_current_user)):
    # Active-account selection is a client-side concern in the Supabase model.
    account_id = str(body.get("account_id", "")).strip()
    return {"success": True, "active_account_id": account_id}


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
@app.get("/api/client/signals")
def get_signals(user: dict = Depends(get_current_user)):
    signals = bridge.get_active_signals(30)
    return {"count": len(signals), "signals": signals}


# ---------------------------------------------------------------------------
# Orders / execution
# ---------------------------------------------------------------------------
@app.post("/api/client/execute")
def execute(body: dict, user: dict = Depends(get_current_user)):
    symbol = str(body.get("symbol", "")).strip()
    action = str(body.get("action", "")).strip().upper()
    account_id = str(body.get("account_id", "")).strip()

    if not symbol or not action:
        raise HTTPException(status_code=400, detail="symbol and action are required")
    if action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="action must be BUY or SELL")
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required")

    res = bridge.create_order({
        "user_id": user["id"],
        "account_id": account_id,
        "symbol": symbol,
        "action": action,
        "volume": float(body.get("volume", 0.01) or 0.01),
        "sl": body.get("sl"),
        "tp": body.get("tp"),
        "comment": str(body.get("comment", "Sajim_1Tap"))[:31],
    })
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "execute failed"))
    return {
        "success": True,
        "status": "QUEUED",
        "order_id": res["order"].get("id"),
    }


@app.post("/api/client/close-trade")
def close_trade(body: dict, user: dict = Depends(get_current_user)):
    ticket = body.get("ticket")
    account_id = str(body.get("account_id", "")).strip()
    symbol = str(body.get("symbol", "")).strip()
    if not ticket:
        raise HTTPException(status_code=400, detail="ticket is required")

    res = bridge.create_order({
        "user_id": user["id"],
        "account_id": account_id,
        "symbol": symbol,
        "action": "CLOSE",
        "volume": 0.0,
        "close_ticket": int(ticket),
        "comment": f"Close_{ticket}"[:31],
    })
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "close failed"))
    return {"success": True, "status": "QUEUED", "order_id": res["order"].get("id")}


@app.post("/api/client/toggle-autopilot")
def toggle_autopilot(body: dict, user: dict = Depends(get_current_user)):
    account_id = str(body.get("account_id", "")).strip()
    enabled = bool(body.get("enabled", False))
    acc = bridge.get_trading_account(account_id, user_id=user["id"])
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    res = bridge.upsert_trading_account({**acc, "autopilot_enabled": enabled})
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "toggle failed"))
    return {"success": True, "autopilot_enabled": enabled, "account_id": account_id}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
@app.post("/api/client/log")
def client_log(body: dict):
    event = body.get("event", "UNKNOWN_EVENT")
    details = body.get("details", {})
    logger.info("USER_ACTION event=%s details=%s", event, details)
    return {"success": True, "event": event}


# ---------------------------------------------------------------------------
# Public status / admin
# ---------------------------------------------------------------------------
@app.get("/api/status")
def status():
    res = bridge._request("trading_accounts?select=balance,equity,today_pnl,today_pnl_percent", "GET")
    accounts = res if isinstance(res, list) else []
    total_pnl = round(sum(float(a.get("today_pnl") or 0) for a in accounts), 2)
    filled = bridge._request("orders_queue?status=eq.FILLED&select=id", "GET")
    active_count = len(filled) if isinstance(filled, list) else 0
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_online": bridge.configured,
        "pnl": {"combined_daily_net": total_pnl},
        "concurrency": {"total_open": active_count},
    }


@app.get("/api/sammy-check")
def sammy_check(
    symbol: str = "XAUUSD",
    direction: str = "BUY",
    current_price: float = 0.0,
    b_t: float = 0.0,
    sl: float = 0.0,
    lot_size: float = 0.10,
    m_t: float = 45.0,
    lambda_pct: float = 15.0,
    user: dict = Depends(get_current_user),
):
    abs_m = abs(m_t)
    check_1 = abs_m >= 35.0
    tier = "RARE" if abs_m >= 55.0 else ("CERTIFIED" if abs_m >= 35.0 else "SUB-THRESHOLD")
    if direction.upper() == "BUY":
        check_2 = sl < current_price and (b_t == 0 or sl <= b_t * 1.002)
    else:
        check_2 = sl > current_price and (b_t == 0 or sl >= b_t * 0.998)
    check_3 = 0.01 <= lot_size <= 0.25
    check_4 = lambda_pct >= 10.0
    decision = "GO" if (check_1 and check_2 and check_3 and check_4) else "STOP"
    return {"decision": decision, "tier": tier, "symbol": symbol, "direction": direction.upper()}


@app.post("/api/toggles")
def toggles(body: dict, _: None = Depends(require_admin)):
    return {"status": "SUCCESS", "toggles": body}
