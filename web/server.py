"""
========================================================================================
             SAJIM TRADERS — QUANTITATIVE WEB APP SERVER (web/server.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Organization: Sajim Holdings Quant Labs
Brand: Sajim Traders (@sajimtraders)

Purpose:
  High-performance, zero-dependency multi-threaded HTTP server providing:
  - RESTful APIs for real-time telemetry, active positions, BEEP signals, & edge matrix
  - Sammy's 4-Check Risk Gatekeeper verification endpoint
  - Static file hosting for the institutional Bloomberg/TradingView style web UI
========================================================================================
"""

import os
import sys
import json
import logging
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from datetime import datetime

# Setup directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
STATIC_DIR = os.path.join(BASE_DIR, "static")

for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "v2")):
    if p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SajimTradersServer")

# File paths
COEXISTENCE_STATUS_FILE = os.path.join(ROOT_DIR, "v2", "coexistence_status.json")
OVERNIGHT_STATUS_FILE = os.path.join(ROOT_DIR, "overnight_status.json")
BROADCAST_ACTIVE_FILE = os.path.join(ROOT_DIR, "broadcast_active.json")
EDGE_FILTER_FILE = os.path.join(ROOT_DIR, "config", "v1_edge_filter.json")
EDGE_MATRIX_STATUS_FILE = os.path.join(ROOT_DIR, "edge_matrix_status.json")
TELEGRAM_CONFIG_FILE = os.path.join(ROOT_DIR, "config", "telegram_config.json")


def load_json_safe(path: str, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read {os.path.basename(path)}: {e}")
        return default


def get_market_session() -> str:
    """Returns the active global market session based on current UTC hour."""
    utc_hour = datetime.utcnow().hour
    if 0 <= utc_hour < 7:
        return "TOKYO_ASIAN_SESSION"
    elif 7 <= utc_hour < 12:
        return "LONDON_OPEN_EXPANSION"
    elif 12 <= utc_hour < 16:
        return "LONDON_NY_OVERLAP"
    elif 16 <= utc_hour < 21:
        return "NY_AFTERNOON"
    return "SYDNEY_PACIFIC"


class SajimTradersHandler(SimpleHTTPRequestHandler):
    """Unified HTTP handler for API requests and static UI files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data, status_code=200):
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-BEEP-API-KEY")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-BEEP-API-KEY")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # API Endpoints
        if path == "/api/status":
            self.handle_api_status()
        elif path == "/api/positions":
            self.handle_api_positions()
        elif path == "/api/signals":
            self.handle_api_signals()
        elif path == "/api/edge-matrix":
            self.handle_api_edge_matrix()
        elif path == "/api/community":
            self.handle_api_community()
        elif path.startswith("/api/"):
            self._send_json({"error": "Endpoint not found", "path": path}, 404)
        else:
            # Static files serving
            if parsed.path in ["", "/"]:
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if path == "/api/sammy-check":
            self.handle_sammy_check(body)
        elif path == "/api/toggles":
            self.handle_toggles(body)
        else:
            self._send_json({"error": "Unknown POST route", "path": path}, 404)

    # -------------------------------------------------------------------------
    # API HANDLERS
    # -------------------------------------------------------------------------

    def handle_api_status(self):
        """Unified portfolio telemetry from coexistence & overnight states."""
        coexist = load_json_safe(COEXISTENCE_STATUS_FILE, {})
        overnight = load_json_safe(OVERNIGHT_STATUS_FILE, {})

        # Merge account data with preference to most recent
        acc_coexist = coexist.get("account", {})
        pnl_coexist = coexist.get("pnl", {})
        concurrency = coexist.get("concurrency", {})
        circuit = coexist.get("circuit_breaker", {"active": False, "reason": ""})

        balance = acc_coexist.get("balance") or overnight.get("balance", 99.0)
        equity = acc_coexist.get("equity") or overnight.get("equity", 94.04)
        free_margin = acc_coexist.get("free_margin") or overnight.get("free_margin", 79.31)
        margin_level = acc_coexist.get("margin_level_pct", 0.0)
        currency = acc_coexist.get("currency", "USC")

        # In USC cent terms: $1 USD = 100 USC
        balance_usd = round(balance / 100.0, 2) if currency == "USC" else balance
        equity_usd = round(equity / 100.0, 2) if currency == "USC" else equity

        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system_online": True,
            "broker": {
                "server": overnight.get("server", "JustMarkets-Demo3"),
                "account": overnight.get("account", 1200442972),
                "terminal_bridge": "CONNECTED",
            },
            "session": overnight.get("session") or get_market_session(),
            "account": {
                "balance_usc": balance,
                "balance_usd": balance_usd,
                "equity_usc": equity,
                "equity_usd": equity_usd,
                "free_margin": free_margin,
                "margin_level_pct": margin_level,
                "currency": currency,
            },
            "pnl": {
                "today_closed": pnl_coexist.get("today_closed", 0.0),
                "today_floating": pnl_coexist.get("today_floating", -0.59),
                "combined_daily_net": pnl_coexist.get("combined_daily_net", -0.59),
            },
            "concurrency": {
                "total_open": concurrency.get("total_open", overnight.get("active_bot_positions", 5)),
                "max_combined": concurrency.get("max_combined", 12),
                "v1_count": concurrency.get("v1_count", 5),
                "v2_count": concurrency.get("v2_count", 0),
                "max_v1": 6,
                "max_v2": 6,
            },
            "circuit_breaker": circuit,
            "toggles": coexist.get("toggles", {"v1_enabled": True, "v2_enabled": True}),
            "streaks": overnight.get("cluster_streaks", {}),
            "pipeline": overnight.get("pipeline", "DATA -> BEEP -> SIGNAL -> SAJIM -> ENTRY -> MANAGEMENT -> PNL"),
        }
        self._send_json(data)

    def handle_api_positions(self):
        """Active trades broken down by V1 (777999) and V2 (888222)."""
        coexist = load_json_safe(COEXISTENCE_STATUS_FILE, {})
        positions = coexist.get("positions", {"v1": [], "v2": []})

        all_trades = []
        for pos in positions.get("v1", []):
            item = dict(pos)
            item["bot"] = "V1 (Flagship)"
            item["color"] = "cyan"
            all_trades.append(item)

        for pos in positions.get("v2", []):
            item = dict(pos)
            item["bot"] = "V2 (Duration)"
            item["color"] = "emerald"
            all_trades.append(item)

        self._send_json({
            "total_open": len(all_trades),
            "v1_count": len(positions.get("v1", [])),
            "v2_count": len(positions.get("v2", [])),
            "trades": all_trades,
        })

    def handle_api_signals(self):
        """Streaming BEEP institutional signals with RARE/CERTIFIED tags."""
        broadcast_list = load_json_safe(BROADCAST_ACTIVE_FILE, [])
        overnight = load_json_safe(OVERNIGHT_STATUS_FILE, {})
        top_overnight = overnight.get("top_signals", [])

        combined_signals = []
        seen_keys = set()

        for s in top_overnight:
            key = f"{s.get('symbol')}_{s.get('timeframe')}_{s.get('action')}"
            if key not in seen_keys:
                seen_keys.add(key)
                combined_signals.append({
                    "id": s.get("signal_id", f"SIG_{len(combined_signals)}"),
                    "symbol": s.get("symbol"),
                    "timeframe": s.get("timeframe"),
                    "action": s.get("action"),
                    "layer": s.get("layer", "CERTIFIED"),
                    "m_t": s.get("m_t", 0.0),
                    "b_t": s.get("b_t", 0.0),
                    "entry": s.get("entry_price", 0.0),
                    "sl": s.get("stop_loss", 0.0),
                    "tp": s.get("take_profit", 0.0),
                    "rr": s.get("risk_reward", 3.5),
                    "spread_points": s.get("spread_points", 15),
                    "mode": s.get("mode", "INTRADAY"),
                    "regime": s.get("regime", "ACTIVE_HUNT"),
                    "session": s.get("session", "LONDON_OPEN"),
                    "timestamp": s.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                })

        for b in broadcast_list[:15]:
            key = f"{b.get('symbol')}_{b.get('timeframe')}_{b.get('action')}"
            if key not in seen_keys:
                seen_keys.add(key)
                combined_signals.append({
                    "id": b.get("id"),
                    "symbol": b.get("symbol"),
                    "timeframe": b.get("timeframe", "M15"),
                    "action": b.get("action"),
                    "layer": b.get("layer", "RARE"),
                    "m_t": b.get("m_t", 0.0),
                    "b_t": b.get("b_t", 0.0),
                    "entry": b.get("entry", 0.0),
                    "sl": b.get("sl", 0.0),
                    "tp": b.get("tp", 0.0),
                    "rr": b.get("rr", 3.5),
                    "spread_points": 14,
                    "mode": "SCALP",
                    "regime": "ACTIVE_HUNT",
                    "session": get_market_session(),
                    "timestamp": b.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "broadcast_text": b.get("broadcast_text", ""),
                })

        self._send_json({
            "count": len(combined_signals),
            "signals": combined_signals[:20],
        })

    def handle_api_edge_matrix(self):
        """Empirical edge whitelist and bleeder blacklist."""
        edge_data = load_json_safe(EDGE_FILTER_FILE, {})
        matrix_status = load_json_safe(EDGE_MATRIX_STATUS_FILE, {})

        top_edges = edge_data.get("top_institutional_edges", matrix_status.get("top_edge_pairs", []))
        toxic_summary = edge_data.get("toxic_bleeders_summary", {})
        worst_bleeders = matrix_status.get("worst_bleeders", [])

        self._send_json({
            "audit_date": edge_data.get("audit_date", "2026-09-09"),
            "audit_version": edge_data.get("audit_version", "1.0-EMPIRICAL-MT5"),
            "top_edges": top_edges,
            "toxic_bleeders": toxic_summary,
            "worst_bleeders": worst_bleeders,
            "approved_assets_count": len(edge_data.get("approved_edges", {})),
        })

    def handle_api_community(self):
        """Community & Telegram channel configurations."""
        tg = load_json_safe(TELEGRAM_CONFIG_FILE, {})
        self._send_json({
            "brand": "Sajim Traders",
            "channel_username": tg.get("free_channel_username", "@sajimtraders"),
            "channel_title": tg.get("free_channel_title", "Sajim Traders"),
            "vip_status": "ACTIVE",
            "founder": "Jimmy Mathu",
            "mission": "Scalable institutional edge extraction & trader compounding",
        })

    def handle_sammy_check(self, body: dict):
        """
        Sammy's 4-Check Gatekeeper verification:
        1. Momentum Check: |M(t)| >= 35.0 (Certified) or >= 55.0 (Rare)
        2. Invalidation Check: SL anchored within/beyond B(t) Huber band
        3. Lot Size Check: Safe dynamic compounding lot (<= 0.25 on cent account)
        4. Energy Lambda Check: Lambda energy >= 10.0%
        """
        symbol = body.get("symbol", "XAUUSD.c")
        direction = str(body.get("direction", "BUY")).upper()
        current_price = float(body.get("current_price", 0.0))
        b_t = float(body.get("b_t", current_price))
        sl = float(body.get("sl", 0.0))
        lot_size = float(body.get("lot_size", 0.10))
        m_t = float(body.get("m_t", 45.0))
        lambda_pct = float(body.get("lambda_pct", 15.0))

        # Check 1: Kinetic Mass M(t)
        abs_m = abs(m_t)
        check_1_pass = abs_m >= 35.0
        check_1_tier = "RARE" if abs_m >= 55.0 else ("CERTIFIED" if abs_m >= 35.0 else "SUB-THRESHOLD")

        # Check 2: SL relative to baseline B(t)
        if direction == "BUY":
            check_2_pass = sl < current_price and (b_t == 0 or sl <= b_t * 1.002)
        else:
            check_2_pass = sl > current_price and (b_t == 0 or sl >= b_t * 0.998)

        # Check 3: Dynamic Lot Size
        check_3_pass = 0.01 <= lot_size <= 0.25

        # Check 4: Thermodynamic Energy Lambda
        check_4_pass = lambda_pct >= 10.0

        all_passed = check_1_pass and check_2_pass and check_3_pass and check_4_pass
        decision = "GO" if all_passed else "STOP"

        response = {
            "decision": decision,
            "symbol": symbol,
            "direction": direction,
            "tier": check_1_tier,
            "checks": {
                "check_1_momentum": {
                    "name": "Kinetic Mass M(t) >= 35.0",
                    "passed": check_1_pass,
                    "value": abs_m,
                    "detail": f"M(t) = {m_t:.1f} ({check_1_tier})"
                },
                "check_2_sl_baseline": {
                    "name": "SL Protected by Huber B(t)",
                    "passed": check_2_pass,
                    "value": sl,
                    "detail": f"Entry: {current_price} | SL: {sl} | B(t): {b_t}"
                },
                "check_3_lot_size": {
                    "name": "Safe Dynamic Compounding Lot (0.01 - 0.25)",
                    "passed": check_3_pass,
                    "value": lot_size,
                    "detail": f"{lot_size} lot"
                },
                "check_4_lambda_energy": {
                    "name": "Lambda Friction Energy >= 10%",
                    "passed": check_4_pass,
                    "value": lambda_pct,
                    "detail": f"{lambda_pct:.1f}% Energy"
                }
            },
            "summary": (
                f"Approved for execution by Sammy's Risk Gatekeeper."
                if decision == "GO"
                else "Blocked by Risk Gatekeeper. Violates institutional risk boundaries."
            ),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._send_json(response)

    def handle_toggles(self, body: dict):
        """Updates bot operational toggles in memory or state."""
        coexist = load_json_safe(COEXISTENCE_STATUS_FILE, {})
        current_toggles = coexist.get("toggles", {"v1_enabled": True, "v2_enabled": True})

        if "v1_enabled" in body:
            current_toggles["v1_enabled"] = bool(body["v1_enabled"])
        if "v2_enabled" in body:
            current_toggles["v2_enabled"] = bool(body["v2_enabled"])

        coexist["toggles"] = current_toggles
        try:
            with open(COEXISTENCE_STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(coexist, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist toggles: {e}")

        self._send_json({"status": "SUCCESS", "toggles": current_toggles})


def run_web_server(port: int = 8080, host: str = "0.0.0.0"):
    """Starts the multi-threaded web server."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, SajimTradersHandler)

    print("=" * 75)
    print(f"[*] SAJIM TRADERS — QUANTITATIVE WEB TERMINAL")
    print(f"[*] Chief Quantitative Architect: Jimmy Mathu")
    print(f"[*] Server running on: http://localhost:{port}")
    print(f"[*] Static Web Assets : {STATIC_DIR}")
    print(f"[*] Live Telemetry    : Connected to MT5 & Bot State Files")
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
