"""
========================================================================================
           SAJIM WEB GATEWAY — CLIENT PORTAL API ROUTES (web/routes/client.py)
========================================================================================
Modular Web Architecture: All modules < 250 lines.
Handles:
  - Client account balance, equity, and telemetry.
  - Multi-account list, connect, switch, delete.
  - 1-Tap signals with Duration, Health, and Explainer.
  - 1-Tap order execution & position closure.
"""

import os
import re
import json
import sys
import logging
from datetime import datetime
from web.routes.base import (
    ROOT_DIR,
    load_json_safe,
    BROADCAST_ACTIVE_FILE,
)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logger = logging.getLogger("SajimWebClient")

account_manager = None

_ACCOUNT_ID_RE = re.compile(r"^\d{3,20}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._#\-]{1,32}$")
MAX_LEGACY_LOT = float(os.environ.get("ABSOLUTE_MAX_LOT", "1.0"))


def get_account_manager():
    """Lazily retrieves the MultiAccountManager instance, or None if unavailable.

    There is deliberately no in-memory fallback: a fake manager would report fake
    successes (e.g. fabricated tickets) for trades that never reached a broker.
    """
    global account_manager
    if account_manager is not None:
        return account_manager

    try:
        from core.multi_account_manager import get_multi_account_manager
        account_manager = get_multi_account_manager()
        if account_manager is not None:
            return account_manager
    except Exception as e:
        logger.warning(f"Could not load MultiAccountManager via get_multi_account_manager: {e}")

    try:
        from core.multi_account_manager import MultiAccountManager
        account_manager = MultiAccountManager()
        if account_manager is not None:
            return account_manager
    except Exception as e:
        logger.warning(f"Could not instantiate MultiAccountManager: {e}")

    return None


def _parse_number(raw, name: str, default: float):
    """Returns (value, error)."""
    if raw is None or raw == "":
        return default, None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None, f"{name} must be a number"
    if val != val or val < 0:
        return None, f"{name} must be a non-negative number"
    return val, None


class ClientRoutesMixin:
    """Mixin containing all client portal endpoints for SajimTradersHandler.

    Every handler that reads account data or mutates state is gated by
    self._require_admin_key() (defined on SajimTradersHandler).
    """

    def _manager_or_503(self):
        mgr = get_account_manager()
        if mgr is None:
            self._send_json({"success": False, "error": "Account manager unavailable"}, 503)
        return mgr

    def handle_client_account(self):
        """Returns live account balance, equity, and telemetry for the active user."""
        from urllib.parse import parse_qs, urlparse
        query_params = parse_qs(urlparse(self.path).query)
        account_id = query_params.get("account_id", [None])[0]
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        data = mgr.get_live_account_telemetry(account_id=account_id)
        self._send_json(data)

    def handle_client_accounts(self):
        """Returns all registered client accounts."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        accounts = [
            {k: v for k, v in a.items() if k not in ("password", "encrypted_password")}
            if isinstance(a, dict) else a
            for a in (mgr.get_all_accounts() or [])
        ]
        self._send_json({"accounts": accounts})

    def handle_client_signals(self):
        """
        Returns clean, retail-friendly signals formatted for 1-tap direct execution.
        Includes Duration, Health Meter %, and plain-English Explainer.
        """
        broadcast_list = load_json_safe(BROADCAST_ACTIVE_FILE, [])
        client_signals = []
        seen = set()

        for b in list(reversed(broadcast_list))[:30]:
            symbol = b.get("symbol")
            action = b.get("action")
            if not symbol or not action:
                continue

            key = f"{symbol}_{b.get('timeframe')}_{action}"
            if key in seen:
                continue
            seen.add(key)

            entry = float(b.get("entry", 0.0))
            sl = float(b.get("sl", 0.0))
            tp = float(b.get("tp", 0.0))
            rr = float(b.get("rr", 1.5))
            timeframe = b.get("timeframe", "M15")
            strategy = b.get("strategy", "Sajim Momentum Edge")
            timestamp = b.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            diff_tp = abs(tp - entry)
            diff_sl = abs(entry - sl)

            if "JPY" in symbol:
                gain_usd = round(diff_tp * 100 * 0.01 / 1.5, 2)
                risk_usd = round(diff_sl * 100 * 0.01 / 1.5, 2)
            elif "XAU" in symbol or "GOLD" in symbol:
                gain_usd = round(diff_tp * 1.0, 2)
                risk_usd = round(diff_sl * 1.0, 2)
            elif "100" in symbol or "30" in symbol:
                gain_usd = round(diff_tp * 0.1, 2)
                risk_usd = round(diff_sl * 0.1, 2)
            else:
                gain_usd = round(diff_tp * 1000, 2)
                risk_usd = round(diff_sl * 1000, 2)

            if gain_usd < 1.0: gain_usd = round(diff_tp * 10, 2) if diff_tp > 0 else 3.50
            if risk_usd < 0.5: risk_usd = round(diff_sl * 10, 2) if diff_sl > 0 else 1.50
            if gain_usd > 50.0 and "100" not in symbol and "30" not in symbol: gain_usd = 12.50
            if risk_usd > 30.0 and "100" not in symbol and "30" not in symbol: risk_usd = 4.50

            phase = b.get("phase", "YOUNG_SURGE")
            win_prob = 89 if "Young" in strategy else (92 if "Mirage" in strategy else 86)

            # Calculate duration expectancy
            tf_mins = 1 if "M1" in timeframe else (5 if "M5" in timeframe else (15 if "M15" in timeframe else 30))
            probable_bars = float(b.get("probable_length", 20.0))
            trend_count = float(b.get("trend_count", 5.0))
            bars_left = max(4, int(probable_bars - trend_count))
            mins_left_min = max(5, int(bars_left * tf_mins * 0.6))
            mins_left_max = max(12, int(bars_left * tf_mins * 1.3))
            expected_duration = f"{mins_left_min}-{mins_left_max} mins"

            # Calculate trade health
            maturity = float(b.get("maturity_ratio", 0.35))
            health_pct = max(20, min(95, int((1.0 - (maturity * 0.7)) * 100)))
            health_status = "PRIME HEALTH" if health_pct >= 75 else ("HEALTHY" if health_pct >= 50 else "MODERATE")

            # Plain-English Explainer
            if "Young" in strategy:
                explainer = "Early trend surge detected on dynamic baseline. Enters at low maturity with +0.35R Breakeven Shield protection."
            elif "Mirage" in strategy:
                explainer = "Institutional liquidity sweep detected. Trapped breakout traders flushed; rapid snapback expected."
            else:
                explainer = "Trend reached statistical exhaustion ceiling. Capturing high-probability reversion back to mean."

            client_signals.append({
                "id": b.get("id", f"SIG_{len(client_signals)}"),
                "symbol": symbol,
                "timeframe": timeframe,
                "action": action,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "rr": f"1:{rr:.1f}" if rr else "1:2.0",
                "strategy": strategy,
                "phase": phase,
                "win_probability": f"{win_prob}%",
                "gain_estimate_usd": f"+${gain_usd:.2f}",
                "risk_estimate_usd": f"-${risk_usd:.2f}",
                "expected_duration": expected_duration,
                "expected_bars": f"{bars_left} bars",
                "trade_health_pct": health_pct,
                "trade_health_status": health_status,
                "trade_explainer": explainer,
                "timestamp": timestamp,
                "one_tap_ready": True
            })

        self._send_json({"count": len(client_signals), "signals": client_signals})

    def handle_client_active_trades(self):
        """Returns open trades on the connected account."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        telemetry = mgr.get_live_account_telemetry() or {}
        trades = telemetry.get("open_positions", [])
        self._send_json({"count": len(trades), "trades": trades})

    def handle_client_connect(self, body: dict):
        """Connects or updates client MT5 account credentials and risk preference."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        res = mgr.register_or_update_account(body)
        self._send_json(res)

    def handle_client_switch_account(self, body: dict):
        """Switches the active trading account."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        account_id = body.get("account_id")
        res = mgr.switch_active_account(account_id)
        self._send_json(res)

    def handle_client_delete_account(self, body: dict):
        """Removes an account from the multi-account registry."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        account_id = body.get("account_id")
        res = mgr.remove_account(account_id)
        self._send_json(res)

    def handle_client_toggle_autopilot(self, body: dict):
        """Enables/disables Auto-Pilot copy trading for a user account."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        account_id = body.get("account_id")
        enabled = bool(body.get("enabled", False))
        res = mgr.set_autopilot(account_id, enabled)
        self._send_json(res)

    def handle_client_execute(self, body: dict):
        """Executes a 1-Tap trade directly onto the connected MT5 account."""
        if not self._require_admin_key():
            return

        account_id = str(body.get("account_id") or "").strip()
        symbol = str(body.get("symbol") or "").strip()
        action = str(body.get("action") or "").strip().upper()
        comment = str(body.get("comment") or "Sajim_1Tap")[:31]

        if not symbol or not action:
            self._send_json({"success": False, "error": "symbol and action are required"}, 400)
            return
        if action not in ("BUY", "SELL"):
            self._send_json({"success": False, "error": "action must be BUY or SELL"}, 400)
            return
        if not _SYMBOL_RE.match(symbol):
            self._send_json({"success": False, "error": "symbol is invalid"}, 400)
            return
        if not _ACCOUNT_ID_RE.match(account_id):
            self._send_json({"success": False, "error": "account_id must be a numeric MT5 login"}, 400)
            return

        volume, err = _parse_number(body.get("volume"), "volume", 0.01)
        if err is None and not volume > 0:
            err = "volume must be positive"
        sl, err_sl = _parse_number(body.get("sl"), "sl", 0.0)
        tp, err_tp = _parse_number(body.get("tp"), "tp", 0.0)
        err = err or err_sl or err_tp
        if err:
            self._send_json({"success": False, "error": err}, 400)
            return
        volume = round(min(volume, MAX_LEGACY_LOT), 2)

        mgr = self._manager_or_503()
        if mgr is None:
            return

        res = mgr.execute_one_tap_trade(
            account_id=account_id,
            symbol=symbol,
            action=action,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=comment
        )

        # If MT5 is not directly installed in this environment (e.g. Linux cloud container),
        # queue the trade order so the local Windows MT5 bridge can execute it!
        if not res.get("success") and "not available" in str(res.get("error", "")):
            if hasattr(mgr, "queue_trade_order"):
                queue_res = mgr.queue_trade_order({
                    "account_id": account_id,
                    "symbol": symbol,
                    "action": action,
                    "volume": volume,
                    "sl": sl,
                    "tp": tp,
                    "comment": comment
                })
                if queue_res.get("success"):
                    res = {
                        "success": True,
                        "status": "QUEUED_FOR_BRIDGE",
                        "order_id": queue_res.get("order_id"),
                        "message": "Order queued for Windows MT5 Terminal Bridge"
                    }

        status_code = 200 if res.get("success") else 400
        self._send_json(res, status_code=status_code)

    def handle_client_close_trade(self, body: dict):
        """Closes an open position by ticket number."""
        if not self._require_admin_key():
            return
        try:
            ticket = int(str(body.get("ticket", "")).strip())
        except (TypeError, ValueError):
            ticket = 0
        if ticket <= 0:
            self._send_json({"success": False, "error": "Ticket is required"}, 400)
            return

        mgr = self._manager_or_503()
        if mgr is None:
            return
        res = mgr.close_position_by_ticket(ticket)
        status_code = 200 if res.get("success") else 400
        self._send_json(res, status_code=status_code)

    def handle_bridge_sync(self, body: dict):
        """Receives live telemetry push from the Windows MT5 bridge (admin key required)."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        account_id = body.get("account_id")
        if not account_id:
            self._send_json({"success": False, "error": "account_id is required"}, 400)
            return

        # If bridge includes live market signals from the BEEP engine, cache them for client_signals
        if "signals" in body and isinstance(body["signals"], list) and len(body["signals"]) > 0:
            try:
                os.makedirs(os.path.dirname(BROADCAST_ACTIVE_FILE), exist_ok=True)
                with open(BROADCAST_ACTIVE_FILE, "w", encoding="utf-8") as f:
                    json.dump(body["signals"], f, indent=2)
            except Exception as e:
                logger.warning(f"Could not persist bridge signals: {e}")

        res = mgr.update_account_telemetry(account_id, body)
        self._send_json(res)

    def handle_bridge_orders(self):
        """Returns pending orders queued for the Windows MT5 bridge to execute."""
        from urllib.parse import parse_qs, urlparse
        query_params = parse_qs(urlparse(self.path).query)
        account_id = query_params.get("account_id", [None])[0]
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        orders = mgr.get_pending_orders(account_id) if hasattr(mgr, "get_pending_orders") else []
        self._send_json({"count": len(orders), "orders": orders})

    def handle_bridge_order_result(self, body: dict):
        """Receives trade execution confirmation or failure from the Windows MT5 bridge."""
        if not self._require_admin_key():
            return
        mgr = self._manager_or_503()
        if mgr is None:
            return
        order_id = body.get("order_id")
        if not order_id:
            self._send_json({"success": False, "error": "order_id is required"}, 400)
            return
        if not hasattr(mgr, "complete_trade_order"):
            self._send_json({"success": False, "error": "Order completion not supported"}, 501)
            return
        res = mgr.complete_trade_order(order_id, body)
        self._send_json(res)

    def handle_client_log(self, body: dict):
        """Logs user interactions to logs/client_actions.log (sanitized, size-limited)."""
        event_name = re.sub(r"[^A-Za-z0-9_.:\-]", "", str(body.get("event", "UNKNOWN_EVENT")))[:64] or "UNKNOWN_EVENT"
        details = body.get("details", {})
        try:
            details_json = json.dumps(details)[:1024]
        except (TypeError, ValueError):
            details_json = "{}"
        # Never persist URL fragments / query strings (tokens) or email addresses.
        details_json = re.sub(r"#[^\s\"]*", "", details_json)
        details_json = re.sub(r"\?[^\s\"]*", "", details_json)
        details_json = re.sub(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "[email]", details_json)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client_ip = self.address_string()

        log_line = f"[{timestamp}] [{client_ip}] [EVENT: {event_name}] {details_json}\n"
        log_path = os.path.join(ROOT_DIR, "logs", "client_actions.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logger.warning(f"Could not write to client_actions.log: {e}")

        logger.info(f"[USER_ACTION] {event_name} from {client_ip}")
        self._send_json({"success": True, "event": event_name})
