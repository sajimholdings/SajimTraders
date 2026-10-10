"""
========================================================================================
           SAJIM TRADERS — ULTRA-LEAN HTTP GATEWAY (web/server.py)
========================================================================================
Modular Architecture: Main router strictly < 130 lines.
Decomposed Route Handlers:
  - web/routes/client.py : Client portal, accounts, 1-tap trade routing
  - web/routes/admin.py  : Institutional telemetry, signals, gatekeeper
  - web/routes/base.py   : Utility loaders and session helpers

LEGACY / LOCAL ONLY: production (render.yaml) serves web/app.py (FastAPI). This stdlib
gateway binds to 127.0.0.1 by default (override with WEB_SERVER_HOST), sends no
wildcard CORS headers, and requires an X-ADMIN-KEY header matching ADMIN_KEY on every
mutating / account-data route (denied when ADMIN_KEY is unset).
========================================================================================
"""

import os
import sys
import hmac
import json
import logging
from urllib.parse import urlparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from web.routes.base import STATIC_DIR
from web.routes.client import ClientRoutesMixin
from web.routes.admin import AdminRoutesMixin

logger = logging.getLogger("SajimWebServer")

MAX_BODY_BYTES = 64 * 1024


class SajimTradersHandler(SimpleHTTPRequestHandler, ClientRoutesMixin, AdminRoutesMixin):
    """
    Lightweight, high-concurrency HTTP handler for Sajim Traders Web Portal.
    Inherits modular route mixins for clean single-responsibility design.
    """

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def end_headers(self):
        if self.path.endswith(".html") or self.path in ["/", ""]:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        elif "/_next/static/" in self.path:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        super().end_headers()

    def log_message(self, format, *args):
        # Suppress routine static asset polling logs to keep terminal fast and clean
        if '"GET /api/' in (args[0] if args else "") or " 200 " in (args[1] if len(args) > 1 else ""):
            return
        logger.debug(f"{self.address_string()} - {format % args}")

    def _send_json(self, data: dict, status_code: int = 200):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        # Same-origin only: no CORS headers are emitted, so cross-origin preflights fail.
        self.send_response(204)
        self.end_headers()

    def _require_admin_key(self) -> bool:
        """Returns True if X-ADMIN-KEY matches ADMIN_KEY; otherwise sends 401/503 and returns False."""
        expected = os.environ.get("ADMIN_KEY", "")
        if not expected:
            self._send_json({"success": False, "error": "Admin key not configured"}, 503)
            return False
        provided = self.headers.get("X-ADMIN-KEY") or ""
        if not provided or not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
            self._send_json({"success": False, "error": "Invalid admin key"}, 401)
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Client Portal Endpoints
        if path == "/api/client/account":
            self.handle_client_account()
        elif path == "/api/client/accounts":
            self.handle_client_accounts()
        elif path == "/api/client/signals":
            self.handle_client_signals()
        elif path == "/api/client/active-trades":
            self.handle_client_active_trades()
        elif path == "/api/client/bridge/orders":
            self.handle_bridge_orders()

        # Institutional / Admin Endpoints
        elif path == "/api/status":
            self.handle_api_status()
        elif path == "/api/positions":
            self.handle_api_positions()
        elif path == "/api/signals":
            self.handle_api_signals()
        elif path == "/api/edge-matrix":
            self.handle_api_edge_matrix()
        elif path == "/api/community":
            self.handle_api_community()
        elif path == "/api/landing":
            self.handle_api_landing()
        elif path.startswith("/api/"):
            self._send_json({"error": "Endpoint not found", "path": path}, 404)
        else:
            req_path = parsed.path
            if req_path in ["", "/"]:
                self.path = "/index.html"
            else:
                local_file = os.path.join(STATIC_DIR, req_path.lstrip("/\\"))
                if not os.path.exists(local_file) and not os.path.splitext(req_path)[1]:
                    self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0
        if content_length > MAX_BODY_BYTES:
            self._send_json({"error": "Payload too large"}, 413)
            return
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}

        # Client Execution & Account Actions
        if path == "/api/client/execute":
            self.handle_client_execute(body)
        elif path == "/api/client/connect":
            self.handle_client_connect(body)
        elif path == "/api/client/switch-account":
            self.handle_client_switch_account(body)
        elif path == "/api/client/delete-account":
            self.handle_client_delete_account(body)
        elif path == "/api/client/toggle-autopilot":
            self.handle_client_toggle_autopilot(body)
        elif path == "/api/client/close-trade":
            self.handle_client_close_trade(body)
        elif path == "/api/client/bridge/sync":
            self.handle_bridge_sync(body)
        elif path == "/api/client/bridge/order-result":
            self.handle_bridge_order_result(body)
        elif path == "/api/client/log":
            self.handle_client_log(body)

        # Admin Actions
        elif path == "/api/sammy-check":
            self.handle_sammy_check(body)
        elif path == "/api/toggles":
            self.handle_toggles(body)
        else:
            self._send_json({"error": "Unknown POST route", "path": path}, 404)


def run_web_server(port: int = 8080, host: str = None):
    """Starts the multi-threaded web server (loopback-only unless WEB_SERVER_HOST is set)."""
    host = host or os.environ.get("WEB_SERVER_HOST", "127.0.0.1")
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, SajimTradersHandler)

    print("=" * 75)
    print(f"[*] SAJIM TRADERS — MODULAR WEB GATEWAY")
    print(f"[*] Server running on: http://{host}:{port}")
    print(f"[*] Static Assets   : {STATIC_DIR}")
    print("=" * 75)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Sajim Traders Web Server gracefully stopped.")
        httpd.server_close()


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    port_arg = int(env_port) if env_port else (int(sys.argv[1]) if len(sys.argv) > 1 else 8080)
    run_web_server(port=port_arg)
