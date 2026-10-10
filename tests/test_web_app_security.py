"""Regression tests for the web/app.py security fixes (ownership, filter injection,
lot caps, secret stripping, admin gating, log scrubbing, credential vault)."""
import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
os.environ.setdefault("ADMIN_KEY", "adm1n")
from fastapi.testclient import TestClient  # noqa: E402
import web.app as W
from core.supabase_bridge import SupabaseBridge

USER_A = {"id": "uuid-a"}
USER_B = {"id": "uuid-b"}
ACC = {"id": "row1", "user_id": "uuid-a", "account_id": "17537803", "broker_server": "Headway-Real",
       "max_lot": 0.05, "encrypted_password": "SECRET", "balance": 10}

class FakeBridge(SupabaseBridge):
    def __init__(self):
        super().__init__("https://x.supabase.co", "svc")
        self.calls = []
        self.orders = []
    def _request(self, endpoint, method="GET", data=None, headers_extra=None):
        self.calls.append((method, endpoint, data))
        if endpoint.startswith("trading_accounts?account_id=eq."):
            if "17537803" in endpoint.split("&")[0] and ("user_id=eq.uuid-a" in endpoint or "user_id" not in endpoint):
                return [dict(ACC)]
            return []
        if endpoint.startswith("trading_accounts?user_id=eq."):
            return [dict(ACC)] if "uuid-a" in endpoint else []
        if endpoint == "orders_queue" and method == "POST":
            self.orders.append(data); return [{**data, "id": "ord1"}]
        if endpoint.startswith("orders_queue?account_id"):
            return [{"id": "o1", "action": "BUY", "status": "FILLED", "mt5_ticket": 5, "volume": 0.01},
                    {"id": "o2", "action": "CLOSE", "status": "FILLED", "mt5_ticket": 5}]
        if endpoint.startswith("signals?"):
            return [{"id": "S1", "created_at": "x"}]
        if endpoint.startswith("trade_history"):
            return []
        return []


def test_web_app_security(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))
    monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(W, "ADMIN_KEY", "adm1n", raising=False)
    fb = FakeBridge()
    W.bridge = fb
    current = {"u": USER_A}
    W.app.dependency_overrides[W.get_current_user] = lambda: current["u"]
    W.app.dependency_overrides[W.get_optional_user] = lambda: None
    c = TestClient(W.app)

    # injection encoding
    fb.get_trading_account("17537803#", user_id="uuid-a")
    ep = fb.calls[-1][1]
    assert "17537803%23" in ep and "user_id=eq.uuid-a" in ep, ep
    fb.get_trading_account("1&user_id=eq.x", user_id="u")
    assert "1%26user_id%3Deq.x" in fb.calls[-1][1], fb.calls[-1][1]

    # invalid account id rejected
    r = c.get("/api/client/account", params={"account_id": "17537803#"}); assert r.status_code == 400, r.text
    # owned account, no secret
    r = c.get("/api/client/account", params={"account_id": "17537803"}); assert r.status_code == 200, r.text
    assert "encrypted_password" not in r.json()
    assert len(r.json()["open_positions"]) == 1  # CLOSE row excluded
    r = c.get("/api/client/accounts"); assert all("encrypted_password" not in a for a in r.json()["accounts"])

    # execute: not owned -> 404
    current["u"] = USER_B
    r = c.post("/api/client/execute", json={"symbol": "XAUUSD", "action": "BUY", "account_id": "17537803"}); assert r.status_code == 404, r.text
    r = c.post("/api/client/close-trade", json={"ticket": 5, "account_id": "17537803"}); assert r.status_code == 404, r.text
    current["u"] = USER_A
    r = c.post("/api/client/close-trade", json={"ticket": 5}); assert r.status_code == 400, r.text
    r = c.post("/api/client/close-trade", json={"ticket": "abc", "account_id": "17537803"}); assert r.status_code == 400
    r = c.post("/api/client/close-trade", json={"ticket": 5, "account_id": "17537803"}); assert r.status_code == 200, r.text
    # volume cap
    r = c.post("/api/client/execute", json={"symbol": "XAUUSD", "action": "BUY", "account_id": "17537803", "volume": 50}); assert r.status_code == 200, r.text
    assert fb.orders[-1]["volume"] == 0.05 and r.json()["volume"] == 0.05
    r = c.post("/api/client/execute", json={"symbol": "XAUUSD", "action": "BUY", "account_id": "17537803", "volume": -1}); assert r.status_code == 400
    r = c.post("/api/client/execute", json={"symbol": "XAUUSD", "action": "BUY", "account_id": "17537803", "volume": 0}); assert r.status_code == 400

    # connect without key -> 503
    monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
    r = c.post("/api/client/connect", json={"account_id": "17537803", "password": "pw"}); assert r.status_code == 503, r.text
    # connect owned by another -> 409
    current["u"] = USER_B
    r = c.post("/api/client/connect", json={"account_id": "17537803", "broker_server": "Headway-Real"}); assert r.status_code == 409, r.text
    current["u"] = USER_A

    # status public = health only
    r = c.get("/api/status"); assert "pnl" not in r.json(), r.json()
    # admin routes
    r = c.get("/api/v2/investor/metrics"); assert r.status_code == 401
    W.ADMIN_KEY = ""
    r = c.get("/api/v2/ctrader/telemetry", headers={"X-ADMIN-KEY": ""}); assert r.status_code == 503
    W.ADMIN_KEY = "adm1n"
    # log sanitize + size
    r = c.post("/api/client/log", json={"event": "x", "url": "https://a.b/p?x=1#access_token=abc", "details": {"email": "a@b.c", "m": "hi a@b.com"}}); assert r.status_code == 200
    r = c.post("/api/client/log", content=b"{" + b" " * 5000 + b"}", headers={"content-type": "application/json"}); assert r.status_code == 413
    assert "access_token" not in str(W._sanitize_log_value("https://a.b/p?x=1#access_token=abc"))
    assert "a@b.com" not in str(W._sanitize_log_value({"email": "z", "m": "hi a@b.com"}))
    # trade history
    r = c.get("/api/client/trade-history", params={"account_id": "17537803"}); assert r.status_code == 200
    # signals expiry filter in URL
    fb.get_active_signals(5, max_age_minutes=10)
    assert "or=%28expires_at.is.null%2Cexpires_at.gt." in fb.calls[-1][1], fb.calls[-1][1]

    # vault
    from core import credential_vault as V
    from cryptography.fernet import Fernet
    import base64, hashlib
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "legacy")
    legacy = Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"legacy").digest())).encrypt(b"oldpw").decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "newkey")
    assert V.decrypt_password(legacy) == "oldpw"
    assert V.decrypt_password(V.encrypt_password("np")) == "np"
    W.app.dependency_overrides.clear()
