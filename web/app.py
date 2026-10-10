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
import re
import sys
import hmac
import json
import time
import logging
import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.supabase_bridge import SupabaseBridge, public_account
from core.credential_vault import encrypt_password, CredentialVaultError
from core.ctrader_bridge import CTraderBridge
from core.investor_reporting import InvestorReporting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SajimFastAPI")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
# Absolute server-side lot cap, applied on top of each account's max_lot.
ABSOLUTE_MAX_LOT = float(os.environ.get("ABSOLUTE_MAX_LOT", "1.0"))

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
# Input validation
# ---------------------------------------------------------------------------
_ACCOUNT_ID_RE = re.compile(r"^\d{3,20}$")
_BROKER_SERVER_RE = re.compile(r"^[A-Za-z0-9 ._\-]{1,64}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._#\-]{1,32}$")
_MAX_TICKET = 2 ** 63 - 1


def validate_account_id(raw: Any) -> str:
    """MT5 logins are numeric. Rejects anything else (defence in depth vs filter injection)."""
    account_id = str(raw if raw is not None else "").strip()
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id is required")
    if not _ACCOUNT_ID_RE.match(account_id):
        raise HTTPException(status_code=400, detail="account_id must be a numeric MT5 login")
    return account_id


def validate_ticket(raw: Any) -> int:
    if isinstance(raw, bool):
        raise HTTPException(status_code=400, detail="ticket must be a positive integer")
    try:
        ticket = int(str(raw).strip())
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="ticket must be a positive integer")
    if ticket <= 0 or ticket > _MAX_TICKET:
        raise HTTPException(status_code=400, detail="ticket must be a positive integer")
    return ticket


def validate_broker_server(raw: Any) -> str:
    server = str(raw if raw is not None else "").strip()
    if not _BROKER_SERVER_RE.match(server):
        raise HTTPException(status_code=400, detail="broker_server is invalid")
    return server


def _optional_price(raw: Any, name: str) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{name} must be a number")
    if val != val or val < 0:  # NaN or negative
        raise HTTPException(status_code=400, detail=f"{name} must be a non-negative number")
    return val or None


def get_owned_account(account_id: str, user: dict) -> dict:
    """Fetch a trading account and verify it belongs to the caller (404 otherwise)."""
    acc = bridge.get_trading_account(account_id, user_id=user["id"])
    if not acc or acc.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


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


def get_optional_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> Optional[dict]:
    if cred is None:
        return None
    try:
        user = fetch_supabase_user(cred.credentials)
    except HTTPException:
        return None
    return user if user and user.get("id") else None


def require_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    if not ADMIN_KEY:
        raise HTTPException(status_code=503, detail="Admin key not configured")
    if not x_admin_key or not hmac.compare_digest(x_admin_key.encode("utf-8"), ADMIN_KEY.encode("utf-8")):
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
    account_id = validate_account_id(account_id)
    acc = get_owned_account(account_id, user)
    positions = bridge.list_open_positions(account_id, user_id=user["id"])
    out = public_account(acc)
    out["open_positions"] = [_to_client_trade(o) for o in positions]
    return out


@app.get("/api/client/accounts")
def list_accounts(user: dict = Depends(get_current_user)):
    accounts = [public_account(a) for a in bridge.list_user_accounts(user["id"])]
    return {"accounts": accounts}


@app.post("/api/client/connect")
def connect(body: dict, user: dict = Depends(get_current_user)):
    account_id = validate_account_id(body.get("account_id"))
    broker_server = validate_broker_server(body.get("broker_server") or "Headway-Real")
    risk_mode = str(body.get("risk_mode") or "ULTRA_SAFE")
    if risk_mode not in ("ULTRA_SAFE", "PRO_SCALP", "MAX_YIELD"):
        raise HTTPException(status_code=400, detail="risk_mode is invalid")
    payload = {
        "user_id": user["id"],
        "account_id": account_id,
        "account_name": str(body.get("account_name") or f"Account #{account_id}")[:80],
        "broker_server": broker_server,
        "broker_name": str(body.get("broker_name") or broker_server.split("-")[0])[:64],
        "autopilot_enabled": bool(body.get("autopilot_enabled", False)),
        "risk_mode": risk_mode,
        "currency": str(body.get("currency") or "USD")[:8],
        "is_demo": "demo" in broker_server.lower(),
        "terminal_connected": False,
    }
    password = body.get("password")
    if password:
        try:
            payload["encrypted_password"] = encrypt_password(str(password))
        except CredentialVaultError as e:
            logger.error("Credential encryption unavailable: %s", e)
            raise HTTPException(
                status_code=503,
                detail="Credential storage is not configured on the server. Please try again later.",
            )
    res = bridge.upsert_trading_account(payload)
    if not res.get("success"):
        status_code = 409 if res.get("status") == 409 else 400
        raise HTTPException(status_code=status_code, detail=res.get("error", "connect failed"))
    return {"success": True, "account": public_account(res["account"])}


@app.post("/api/client/delete-account")
def delete_account(body: dict, user: dict = Depends(get_current_user)):
    account_id = validate_account_id(body.get("account_id"))
    acc = get_owned_account(account_id, user)
    if not acc.get("id"):
        raise HTTPException(status_code=404, detail="Account not found")
    bridge.delete_trading_account(acc["id"])
    return {"success": True, "removed": account_id}


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
@app.get("/api/client/signals")
def get_signals(user: dict = Depends(get_current_user)):
    """Active, unexpired signals only (expiry enforced in SupabaseBridge.get_active_signals)."""
    signals = []
    for sig in bridge.get_active_signals(30):
        sig = dict(sig)
        sig.setdefault("timestamp", sig.get("created_at"))
        sig.setdefault("one_tap_ready", True)
        signals.append(sig)
    return {"count": len(signals), "signals": signals}


# ---------------------------------------------------------------------------
# Orders / execution
# ---------------------------------------------------------------------------
@app.post("/api/client/execute")
def execute(body: dict, user: dict = Depends(get_current_user)):
    symbol = str(body.get("symbol", "")).strip().upper()
    action = str(body.get("action", "")).strip().upper()

    if not symbol or not action:
        raise HTTPException(status_code=400, detail="symbol and action are required")
    if not _SYMBOL_RE.match(symbol):
        raise HTTPException(status_code=400, detail="symbol is invalid")
    if action not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="action must be BUY or SELL")
    account_id = validate_account_id(body.get("account_id"))

    raw_volume = body.get("volume", 0.01)
    try:
        volume = float(0.01 if raw_volume is None else raw_volume)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="volume must be a number")
    if not (volume > 0):  # also rejects NaN
        raise HTTPException(status_code=400, detail="volume must be positive")

    acc = get_owned_account(account_id, user)

    # Server-side lot cap: clamp to (0, min(account max_lot, absolute cap)].
    try:
        account_max = float(acc.get("max_lot") or 0) or ABSOLUTE_MAX_LOT
    except (TypeError, ValueError):
        account_max = ABSOLUTE_MAX_LOT
    lot_cap = min(account_max, ABSOLUTE_MAX_LOT)
    volume = round(min(volume, lot_cap), 2)
    if volume <= 0:
        raise HTTPException(status_code=400, detail="volume must be positive")

    res = bridge.create_order({
        "user_id": user["id"],
        "account_id": account_id,
        "trading_account_id": acc.get("id"),
        "symbol": symbol,
        "action": action,
        "volume": volume,
        "sl": _optional_price(body.get("sl"), "sl"),
        "tp": _optional_price(body.get("tp"), "tp"),
        "comment": str(body.get("comment", "Sajim_1Tap"))[:31],
    })
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "execute failed"))
    return {
        "success": True,
        "status": "QUEUED",
        "order_id": res["order"].get("id"),
        "volume": volume,
    }


@app.post("/api/client/close-trade")
def close_trade(body: dict, user: dict = Depends(get_current_user)):
    if body.get("ticket") in (None, ""):
        raise HTTPException(status_code=400, detail="ticket is required")
    ticket = validate_ticket(body.get("ticket"))
    account_id = validate_account_id(body.get("account_id"))
    symbol = str(body.get("symbol") or "").strip().upper()
    if symbol and not _SYMBOL_RE.match(symbol):
        raise HTTPException(status_code=400, detail="symbol is invalid")

    acc = get_owned_account(account_id, user)

    res = bridge.create_order({
        "user_id": user["id"],
        "account_id": account_id,
        "trading_account_id": acc.get("id"),
        "symbol": symbol or "-",
        "action": "CLOSE",
        "volume": 0.0,
        "close_ticket": ticket,
        "comment": f"Close_{ticket}"[:31],
    })
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "close failed"))
    return {"success": True, "status": "QUEUED", "order_id": res["order"].get("id")}


@app.get("/api/client/trade-history")
def trade_history(account_id: Optional[str] = None, limit: int = 100, user: dict = Depends(get_current_user)):
    account_id = validate_account_id(account_id)
    get_owned_account(account_id, user)
    limit = max(1, min(int(limit), 500))
    trades = bridge.list_trade_history(account_id, user_id=user["id"], limit=limit)
    return {"count": len(trades), "trades": trades}


@app.post("/api/client/toggle-autopilot")
def toggle_autopilot(body: dict, user: dict = Depends(get_current_user)):
    account_id = validate_account_id(body.get("account_id"))
    enabled = bool(body.get("enabled", False))
    acc = get_owned_account(account_id, user)
    res = bridge.update_trading_account(acc["id"], {"autopilot_enabled": enabled})
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "toggle failed"))
    return {"success": True, "autopilot_enabled": enabled, "account_id": account_id}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_LOG_MAX_BYTES = 4096
_LOG_RATE_LIMIT = 30          # events per window per client IP
_LOG_RATE_WINDOW = 60.0       # seconds
_log_hits = defaultdict(deque)
_log_lock = threading.Lock()
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s\"']+")
_TOKEN_RE = re.compile(r"((?:access|refresh|provider)?_?token|code)=[^&\s#]+", re.IGNORECASE)


def _strip_url(match: "re.Match") -> str:
    # Drop query + fragment (Supabase puts access_token in the URL fragment).
    try:
        parts = urlsplit(match.group(0))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return "[url]"


def _sanitize_log_value(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "[truncated]"
    if isinstance(value, str):
        value = _URL_RE.sub(_strip_url, value)
        value = value.split("#", 1)[0] if value.startswith("/") else value
        value = _TOKEN_RE.sub(lambda m: f"{m.group(1)}=[redacted]", value)
        value = _EMAIL_RE.sub("[email]", value)
        return value[:256]
    if isinstance(value, dict):
        return {
            str(k)[:64]: _sanitize_log_value(v, depth + 1)
            for k, v in list(value.items())[:20]
            if not any(s in str(k).lower() for s in ("password", "token", "secret", "email", "key"))
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_log_value(v, depth + 1) for v in list(value)[:20]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:64]


def _log_rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    with _log_lock:
        hits = _log_hits[client_ip]
        while hits and now - hits[0] > _LOG_RATE_WINDOW:
            hits.popleft()
        if len(hits) >= _LOG_RATE_LIMIT:
            return True
        hits.append(now)
        if len(_log_hits) > 10000:  # bound memory
            for ip in [ip for ip, h in _log_hits.items() if not h]:
                _log_hits.pop(ip, None)
        return False


@app.post("/api/client/log")
async def client_log(request: Request):
    """Unauthenticated client telemetry: size-limited, rate-limited and sanitized."""
    client_ip = request.client.host if request.client else "unknown"
    if _log_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Too many log events")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > _LOG_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Log payload too large")
    raw = await request.body()
    if len(raw) > _LOG_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Log payload too large")
    try:
        body = json.loads(raw.decode("utf-8")) if raw else {}
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON")
    event = re.sub(r"[^A-Za-z0-9_.:\-]", "", str(body.get("event", "UNKNOWN_EVENT")))[:64] or "UNKNOWN_EVENT"
    details = _sanitize_log_value(body.get("details", {}))
    url = _sanitize_log_value(str(body.get("url", ""))) if body.get("url") else ""
    logger.info("USER_ACTION event=%s url=%s details=%s", event, url, details)
    return {"success": True, "event": event}


# ---------------------------------------------------------------------------
# Public status / admin
# ---------------------------------------------------------------------------
@app.get("/api/status")
def status(user: Optional[dict] = Depends(get_optional_user)):
    """Health info for everyone; PnL / open-trade counts only for the caller's own accounts."""
    out = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_online": bridge.configured,
    }
    if user:
        accounts = bridge.list_user_accounts(user["id"])
        total_pnl = round(sum(float(a.get("today_pnl") or 0) for a in accounts), 2)
        active_count = 0
        for a in accounts:
            if a.get("account_id"):
                active_count += len(bridge.list_open_positions(str(a["account_id"]), user_id=user["id"]))
        out["pnl"] = {"combined_daily_net": total_pnl}
        out["concurrency"] = {"total_open": active_count}
    return out


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


# ---------------------------------------------------------------------------
# Institutional Investor & cTrader Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/v2/investor/metrics")
def investor_metrics(_: None = Depends(require_admin)):
    """Returns top-level mathematical edge verification for investors."""
    pkg = InvestorReporting.generate_investor_package()
    return pkg["evaluation"]["portfolio"]


@app.get("/api/v2/investor/bots")
def investor_bots(_: None = Depends(require_admin)):
    """Returns per-bot alpha attribution (V1 vs V2 Surge vs V2 Reversion)."""
    pkg = InvestorReporting.generate_investor_package()
    return pkg["evaluation"]["bots"]


@app.get("/api/v2/investor/projections")
def investor_projections(_: None = Depends(require_admin)):
    """Returns mathematical capital scaling projections (30d, 90d, 180d, 1yr)."""
    pkg = InvestorReporting.generate_investor_package()
    return pkg["evaluation"]["portfolio"]["investor_projections"]


@app.get("/api/v2/investor/package")
def investor_full_package(_: None = Depends(require_admin)):
    """Returns the full quantitative investor deck and account telemetry."""
    return InvestorReporting.generate_investor_package()


@app.get("/api/v2/ctrader/telemetry")
def ctrader_telemetry(_: None = Depends(require_admin)):
    """Provides live cTrader Cloud Bridge telemetry & open position breakdown."""
    bridge_inst = CTraderBridge.get_instance()
    return bridge_inst.get_account_telemetry()

