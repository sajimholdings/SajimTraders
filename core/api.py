"""
BEEP Commercial Gateway API (api.py)
CONFIDENTIAL GATEWAY — SAJIM HOLDINGS LICENSE & COMMUNICATION INTERFACE

Exposes:
  - Multi-Style Signals (Scalp, Intraday, Swing)
  - Collective Portfolio Evaluation (Multi-Asset)
  - Sammy's 4-Check Risk Gatekeeper
  - Communication API (Signal broadcast for Tete)
  - MT5 Integration Status & Order Bridge
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, BASE_DIR, os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from core.beep_core import BeepCoreEngine
    from core.beep_narrative import BeepNarrativeEngine
    from core.beep_matrix_scanner import BeepMatrixScanner
    from core.beep_broadcast import BeepBroadcastBus, BROADCAST_LOG
    from core.beep_signal_engine import BeepSignalEngine, get_market_session
except ImportError:
    from beep_core import BeepCoreEngine
    from beep_narrative import BeepNarrativeEngine
    from beep_matrix_scanner import BeepMatrixScanner
    from beep_broadcast import BeepBroadcastBus, BROADCAST_LOG
    from beep_signal_engine import BeepSignalEngine, get_market_session
from vault_original_beep.raw_beep_equations import OriginalRawBeep

# Configuration & Security Keys
API_PORT = int(os.environ.get("BEEP_API_PORT", 8080))
VALID_API_KEYS = {
    os.environ.get("BEEP_CLIENT_KEY", "sajim-tete-live-key-9921"): "Tete_CTO_Client",
    os.environ.get("BEEP_SAMMY_KEY", "sajim-sammy-risk-key-4412"): "Sammy_Risk_Client",
    os.environ.get("BEEP_MASTER_KEY", "jimmy-founder-master-secret-7700"): "Jimmy_CEO_Master",
}
MASTER_OVERRIDE_KEY = os.environ.get("BEEP_MASTER_KEY", "jimmy-founder-master-secret-7700")

# In-memory broadcast queue for Tete's communication API
DISPATCHED_ALERTS: List[Dict[str, Any]] = []

# Initialize isolated BEEP engines
engine = BeepCoreEngine()
narrative_engine = BeepNarrativeEngine()
matrix_scanner = BeepMatrixScanner()
broadcast_bus = BeepBroadcastBus()
signal_engine = BeepSignalEngine()
raw_beep = OriginalRawBeep()


class BeepApiHandler(BaseHTTPRequestHandler):
    """Secure HTTP Request Handler for BEEP Gateway."""

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-BEEP-API-KEY")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})

    def _authenticate(self) -> bool:
        """Verifies API key from header."""
        api_key = self.headers.get("X-BEEP-API-KEY")
        return bool(api_key and api_key in VALID_API_KEYS)

    def do_GET(self):
        if self.path in ["/", "/health"]:
            self._send_json(200, {
                "status": "online",
                "service": "BEEP Commercial Gateway API",
                "licensee": "Sajim Holdings (SAJIM Lab)",
                "licensor": "Jimmy Mathu (Sole IP Owner)",
                "version": "2.0.0-PROD",
                "styles_supported": ["SCALP", "INTRADAY", "SWING"],
                "portfolio_engine": "Active",
                "auth_required": True,
            })
            return

        # Tete can pull pending broadcast messages
        elif self.path == "/v1/broadcast/pending":
            if not self._authenticate():
                self._send_json(401, {"error": "Unauthorized."})
                return
            bus_events = broadcast_bus.get_pending_broadcasts(limit=50)
            self._send_json(200, {
                "count": len(bus_events),
                "broadcast_events": bus_events,
                "dispatched_alerts": DISPATCHED_ALERTS[-20:],
            })
            return

        # Real-time event stream from broadcast_stream.jsonl
        elif self.path == "/v1/broadcast/stream":
            if not self._authenticate():
                self._send_json(401, {"error": "Unauthorized."})
                return
            events = []
            if os.path.exists(BROADCAST_LOG):
                try:
                    with open(BROADCAST_LOG, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for line in lines[-100:]:
                            line = line.strip()
                            if line:
                                events.append(json.loads(line))
                except Exception as e:
                    logger.warning(f"Error reading broadcast log: {e}")
            self._send_json(200, {"total_stream_events": len(events), "events": events})
            return

        # 4-Regime Market State Taxonomy Matrix (Cross-Asset Reconnaissance)
        elif self.path.startswith("/v1/market/matrix"):
            if not self._authenticate():
                self._send_json(401, {"error": "Unauthorized."})
                return
            try:
                import MetaTrader5 as mt5
                if not mt5.initialize():
                    self._send_json(503, {"error": "MT5 terminal not accessible."})
                    return

                # Default 34 cent assets or all visible .c symbols
                all_syms = mt5.symbols_get() or []
                symbols = [s.name for s in all_syms if s.name.endswith(".c") and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL]
                if not symbols:
                    symbols = ["EURUSD.c", "GBPUSD.c", "USDJPY.c", "AUDUSD.c", "XAUUSD.c", "XAGUSD.c", "GBPNZD.c", "EURNZD.c"]

                matrix_results = []
                regime_counts = {
                    "ACTIVE_HUNT": 0,
                    "WAIT_COMPRESSION": 0,
                    "FALSE_TRUTH_REJECT": 0,
                    "BASELINE_RETEST": 0,
                }

                for sym in symbols[:34]:
                    reg = signal_engine.classify_regime(sym, "M15", mt5.TIMEFRAME_M15)
                    matrix_results.append(reg)
                    reg_name = reg.get("regime", "UNKNOWN")
                    if reg_name in regime_counts:
                        regime_counts[reg_name] += 1

                self._send_json(200, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "session": get_market_session(),
                    "total_fronts_scanned": len(matrix_results),
                    "regime_summary": regime_counts,
                    "matrix": matrix_results,
                })
            except Exception as e:
                self._send_json(500, {"error": "Failed to generate market matrix", "details": str(e)})
            return

        # MT5 Status check
        elif self.path == "/v1/mt5/status":
            if not self._authenticate():
                self._send_json(401, {"error": "Unauthorized."})
                return
            # Verify if MetaTrader5 module is accessible
            try:
                import MetaTrader5 as mt5
                initialized = mt5.initialize()
                info = mt5.account_info()._asdict() if initialized and mt5.account_info() else {}
                mt5.shutdown()
                self._send_json(200, {
                    "mt5_installed": True,
                    "connected": initialized,
                    "account_info": info,
                })
            except ImportError:
                self._send_json(200, {
                    "mt5_installed": False,
                    "connected": False,
                    "notice": "MetaTrader5 Python module not installed in current environment. Using simulation bridge.",
                })
            return

        # Real-time Cross-Asset Matrix Reconnaissance (20 assets across FX, Metals, Indices, Crypto)
        elif self.path == "/v1/matrix/scan":
            if not self._authenticate():
                self._send_json(401, {"error": "Unauthorized."})
                return
            try:
                matrix_report = matrix_scanner.scan_all_fronts()
                self._send_json(200, matrix_report)
            except Exception as e:
                self._send_json(500, {"error": "Matrix scan failure", "details": str(e)})
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        if not self._authenticate():
            self._send_json(401, {
                "error": "Unauthorized. Invalid or missing X-BEEP-API-KEY.",
                "message": "Contact Jimmy Mathu for authorized API credentials."
            })
            return

        caller_name = VALID_API_KEYS.get(self.headers.get("X-BEEP-API-KEY"), "Unknown")

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            body = json.loads(post_body.decode("utf-8")) if post_body else {}
        except Exception as e:
            self._send_json(400, {"error": "Invalid JSON payload", "details": str(e)})
            return

        # ---------------------------------------------------------------------
        # ROUTE 0: /v1/verify -> Official BEEP Stamp Verification Endpoint
        # ---------------------------------------------------------------------
        if self.path == "/v1/verify":
            symbol = body.get("symbol", "EURUSD.c")
            timeframe = body.get("timeframe", "M15")
            action = body.get("action", "BUY").upper()
            entry = float(body.get("entry", 0.0))
            sl = float(body.get("sl", 0.0))
            tp = float(body.get("tp", 0.0))
            prices = body.get("prices")

            tf_map = {
                "M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388, "D1": 16408
            }
            tf_enum = tf_map.get(timeframe, 15)

            try:
                import MetaTrader5 as mt5
                mt5_ok = mt5.initialize()
                rates = None
                sym_info = None

                if mt5_ok:
                    sym_info = mt5.symbol_info(symbol)
                    rates = mt5.copy_rates_from_pos(symbol, tf_enum, 0, 30)

                digits = sym_info.digits if sym_info else 5

                # Price series resolution: Caller-supplied prices take priority over live broker
                if prices and len(prices) >= 10:
                    close_prices = [float(p) for p in prices]
                    cur_price = close_prices[-1]
                    upper_wick_ratio = float(body.get("upper_wick_ratio", 0.20))
                    lower_wick_ratio = float(body.get("lower_wick_ratio", 0.20))
                    htf_align = int(body.get("htf_align", 1 if action == "BUY" else -1))
                elif rates is not None and len(rates) >= 21:
                    close_prices = [float(r["close"]) for r in rates]
                    cur_price = close_prices[-1]
                    bar = rates[-1]
                    bar_h, bar_l, bar_o, bar_c = float(bar["high"]), float(bar["low"]), float(bar["open"]), float(bar["close"])
                    bar_rng = max(1e-6, bar_h - bar_l)
                    upper_wick_ratio = (bar_h - max(bar_o, bar_c)) / bar_rng
                    lower_wick_ratio = (min(bar_o, bar_c) - bar_l) / bar_rng
                    htf_align = signal_engine.get_htf_trend(symbol, timeframe) if mt5_ok else 1
                else:
                    self._send_json(400, {"error": f"Cannot acquire market data for {symbol}. Supply 'prices' array."})
                    return

                # Calculate Huber Baseline and Kinetic Mass
                b_t = raw_beep.calculate_raw_baseline_B(close_prices[-21:] if len(close_prices)>=21 else close_prices)
                m_mag = raw_beep.calculate_raw_mass_M(close_prices[-21:] if len(close_prices)>=21 else close_prices, b_t)
                m_t = m_mag if cur_price > b_t else (-m_mag if cur_price < b_t else 0.0)

                # Calculate Risk:Reward
                calc_risk = abs(entry - sl) if entry > 0 and sl > 0 else 1e-4
                calc_reward = abs(tp - entry) if entry > 0 and tp > 0 else 0.0
                rr = calc_reward / calc_risk if calc_risk > 0 else 0.0

                # Scorecard (0 - 100)
                rejection_reasons = []
                score = 0.0

                # 1. Directional Alignment (30 pts)
                expected_dir = "BUY" if cur_price > b_t else ("SELL" if cur_price < b_t else "FLAT")
                if action == expected_dir:
                    score += 30.0
                else:
                    rejection_reasons.append(f"Direction mismatch: Trade proposes {action}, but price is {'below' if expected_dir=='SELL' else 'above'} baseline B(t)")

                # 2. Kinetic Mass Strength (30 pts)
                abs_m = abs(m_mag)
                if abs_m >= 55.0:
                    score += 30.0
                elif abs_m >= 35.0:
                    score += 20.0
                elif abs_m >= 25.0:
                    score += 10.0
                else:
                    rejection_reasons.append(f"Insufficient kinetic energy: |M(t)|={abs_m:.1f} < 25.0 (Market in compression)")

                # 3. Gamma Macro Gate (15 pts)
                if (action == "BUY" and htf_align == 1) or (action == "SELL" and htf_align == -1):
                    score += 15.0
                elif htf_align == 0:
                    score += 8.0
                else:
                    rejection_reasons.append(f"Macro HTF trend diverges from trade direction")

                # 4. Candle Anatomy False-Truth Fader (15 pts)
                wick_trap = (action == "BUY" and upper_wick_ratio > 0.45) or (action == "SELL" and lower_wick_ratio > 0.45)
                if not wick_trap:
                    score += 15.0
                else:
                    rejection_reasons.append(f"Retail FOMO trap: Candle wick absorption > 45% ({max(upper_wick_ratio, lower_wick_ratio)*100:.1f}%)")

                # 5. Risk:Reward Quality (10 pts)
                if rr >= 2.5:
                    score += 10.0
                elif rr >= 1.5:
                    score += 5.0
                else:
                    rejection_reasons.append(f"Sub-standard R:R ratio: 1:{rr:.2f} < 1:2.5 minimum required")

                # Regime Classification
                if abs_m < 25.0:
                    regime = "WAIT_COMPRESSION"
                elif wick_trap or (action == "BUY" and htf_align == -1) or (action == "SELL" and htf_align == 1):
                    regime = "FALSE_TRUTH_REJECT"
                elif abs_m >= 55.0:
                    regime = "ACTIVE_HUNT"
                else:
                    regime = "BASELINE_RETEST"

                # Stamp Verdict
                if score >= 70.0 and regime == "ACTIVE_HUNT":
                    beep_stamp = "CERTIFIED_INSTITUTIONAL_FIT"
                    verdict = f"APPROVED. The trade setup on {symbol} ({action}) aligns with institutional order flow (BEEP Score: {score:.1f}/100). Certified for execution."
                else:
                    beep_stamp = "REJECTED_RETAIL_TRAP"
                    verdict = f"REJECTED. The trade setup on {symbol} ({action}) fails institutional criteria (BEEP Score: {score:.1f}/100). Violations: {'; '.join(rejection_reasons)}."

                self._send_json(200, {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "proposed_action": action,
                    "beep_stamp": beep_stamp,
                    "beep_score": round(score, 1),
                    "regime": regime,
                    "session": get_market_session(),
                    "mathematical_proof": {
                        "current_price": cur_price,
                        "robust_baseline_b_t": round(b_t, digits),
                        "kinetic_mass_m_t": round(m_t, 2),
                        "gamma_htf_alignment": htf_align,
                        "upper_wick_ratio": round(upper_wick_ratio, 3),
                        "lower_wick_ratio": round(lower_wick_ratio, 3),
                        "calculated_rr": round(rr, 2),
                        "score_breakdown": {
                            "direction_pts": 30.0 if action == expected_dir else 0.0,
                            "mass_pts": 30.0 if abs_m >= 55 else (20.0 if abs_m >= 35 else (10.0 if abs_m >= 25 else 0.0)),
                            "gamma_pts": 15.0 if ((action == "BUY" and htf_align == 1) or (action == "SELL" and htf_align == -1)) else (8.0 if htf_align == 0 else 0.0),
                            "wick_pts": 0.0 if wick_trap else 15.0,
                            "rr_pts": 10.0 if rr >= 2.5 else (5.0 if rr >= 1.5 else 0.0),
                        },
                    },
                    "verdict_statement": verdict,
                    "authenticated_caller": caller_name,
                })
            except Exception as e:
                self._send_json(500, {"error": "BEEP Verification Engine failure", "details": str(e)})
            return

        # ---------------------------------------------------------------------
        # ROUTE 1: /v1/signal -> Multi-Style Quantitative Signal
        # ---------------------------------------------------------------------
        elif self.path == "/v1/signal":
            prices = body.get("prices")
            symbol = body.get("symbol", "XAUUSD")
            style = body.get("style", "INTRADAY")
            balance = float(body.get("account_balance", 400.0))

            if not prices or not isinstance(prices, list) or len(prices) < 10:
                self._send_json(400, {"error": "Parameter 'prices' (list >= 10 points) is required."})
                return

            try:
                sig = engine.analyze_market(
                    prices=prices,
                    style=style,
                    symbol=symbol,
                    account_balance=balance,
                    m1_vel=body.get("m1_vel"),
                    m5_vel=body.get("m5_vel"),
                    m15_vel=body.get("m15_vel"),
                )

                # Pre-evaluate Sammy's 4-Check
                risk_eval = engine.evaluate_sammy_4check(
                    m_t=sig["M_t"],
                    current_price=sig["current_price"],
                    b_t=sig["B_t"],
                    sl=sig["suggested_sl"],
                    direction=sig["direction"],
                    lot_size=sig["lot_size"],
                    lambda_pct=sig["Lambda_pct"],
                )

                sig["sammy_4check_decision"] = risk_eval["decision"]
                sig["authenticated_caller"] = caller_name
                self._send_json(200, sig)
            except Exception as e:
                self._send_json(500, {"error": "BEEP analysis error", "details": str(e)})
            return

        # ---------------------------------------------------------------------
        # ROUTE 1B: /v1/narrative -> Institutional Market Narrative & VIP Broadcast
        # ---------------------------------------------------------------------
        elif self.path == "/v1/narrative":
            prices = body.get("prices")
            symbol = body.get("symbol", "XAUUSD")
            balance = float(body.get("account_balance", 400.0))

            if not prices or not isinstance(prices, list) or len(prices) < 10:
                self._send_json(400, {"error": "Parameter 'prices' (list >= 10 points) is required."})
                return

            try:
                narrative_data = narrative_engine.generate_narrative(
                    symbol=symbol,
                    prices=prices,
                    account_balance=balance,
                )
                narrative_data["authenticated_caller"] = caller_name

                # Automatically queue for Tete's broadcast bot if it's a trade action
                if narrative_data.get("trade_action") in ["BUY", "SELL"]:
                    entry = {
                        "id": len(DISPATCHED_ALERTS) + 1,
                        "destination": "WHATSAPP_VIP_BROADCAST",
                        "content": narrative_data["broadcast_message"],
                        "dispatched_by": caller_name,
                        "status": "QUEUED_FOR_BROADCAST",
                    }
                    DISPATCHED_ALERTS.append(entry)
                    narrative_data["broadcast_queued"] = True

                self._send_json(200, narrative_data)
            except Exception as e:
                self._send_json(500, {"error": "Narrative formulation error", "details": str(e)})
            return

        # ---------------------------------------------------------------------
        # ROUTE 2: /v1/portfolio/evaluate -> Collective Multi-Asset Evaluation
        # ---------------------------------------------------------------------
        elif self.path == "/v1/portfolio/evaluate":
            assets = body.get("assets", {})
            if not isinstance(assets, dict) or not assets:
                self._send_json(400, {"error": "Parameter 'assets' (dict of symbol -> price_list) required."})
                return

            try:
                portfolio_result = engine.evaluate_portfolio(assets)
                portfolio_result["caller"] = caller_name
                self._send_json(200, portfolio_result)
            except Exception as e:
                self._send_json(500, {"error": "Portfolio evaluation error", "details": str(e)})
            return

        # ---------------------------------------------------------------------
        # ROUTE 3: /v1/sammy-4check -> Sammy Risk Verification Gatekeeper
        # ---------------------------------------------------------------------
        elif self.path == "/v1/sammy-4check":
            required = ["M_t", "current_price", "B_t", "sl", "direction", "lot_size", "Lambda_pct"]
            for field in required:
                if field not in body:
                    self._send_json(400, {"error": f"Missing required parameter: {field}"})
                    return

            eval_res = engine.evaluate_sammy_4check(
                m_t=float(body["M_t"]),
                current_price=float(body["current_price"]),
                b_t=float(body["B_t"]),
                sl=float(body["sl"]),
                direction=str(body["direction"]),
                lot_size=float(body["lot_size"]),
                lambda_pct=float(body["Lambda_pct"]),
            )
            eval_res["caller"] = caller_name
            self._send_json(200, eval_res)
            return

        # ---------------------------------------------------------------------
        # ROUTE 4: /v1/broadcast/dispatch -> Tete's Signal Communication Dispatcher
        # ---------------------------------------------------------------------
        elif self.path == "/v1/broadcast/dispatch":
            alert_payload = body.get("alert")
            destination = body.get("destination", "WHATSAPP_BOT")

            if not alert_payload:
                self._send_json(400, {"error": "Missing 'alert' content."})
                return

            entry = {
                "id": len(DISPATCHED_ALERTS) + 1,
                "destination": destination,
                "content": alert_payload,
                "dispatched_by": caller_name,
                "status": "QUEUED_FOR_BROADCAST",
            }
            DISPATCHED_ALERTS.append(entry)
            self._send_json(200, {"status": "SUCCESS", "message": "Signal queued for broadcast", "entry": entry})
            return

        # ---------------------------------------------------------------------
        # ROUTE 5: /v1/mt5/order -> Order Execution Gateway
        # ---------------------------------------------------------------------
        elif self.path == "/v1/mt5/order":
            symbol = body.get("symbol", "XAUUSD")
            direction = body.get("direction", "BUY")
            lot = float(body.get("lot", 0.01))
            sl = float(body.get("sl", 0.0))
            tp = float(body.get("tp", 0.0))

            # Attempt live MT5 execution if available, else simulate
            try:
                import MetaTrader5 as mt5
                if mt5.initialize():
                    action = mt5.ORDER_BUY if direction.upper() == "BUY" else mt5.ORDER_SELL
                    price = mt5.symbol_info_tick(symbol).ask if direction.upper() == "BUY" else mt5.symbol_info_tick(symbol).bid
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": lot,
                        "type": action,
                        "price": price,
                        "sl": sl,
                        "tp": tp,
                        "deviation": 20,
                        "magic": 777123,
                        "comment": "BEEP Signal Execution",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    result = mt5.order_send(request)
                    mt5.shutdown()
                    self._send_json(200, {
                        "status": "LIVE_MT5_EXECUTED",
                        "retcode": result.retcode if result else -1,
                        "order": result._asdict() if result else {},
                    })
                    return
            except Exception:
                pass

            # Simulation fallback
            self._send_json(200, {
                "status": "SIMULATED_ORDER_CONFIRMED",
                "execution_mode": "SIMULATION_BRIDGE",
                "symbol": symbol,
                "direction": direction,
                "volume": lot,
                "sl": sl,
                "tp": tp,
                "notice": "Simulated execution confirmed. Ready for live terminal binding.",
            })
            return

        # ---------------------------------------------------------------------
        # ROUTE 6: /v1/override -> Founder Unilateral Override
        # ---------------------------------------------------------------------
        elif self.path == "/v1/override":
            provided_key = self.headers.get("X-BEEP-API-KEY")
            if provided_key != MASTER_OVERRIDE_KEY:
                self._send_json(403, {"error": "Forbidden: Founder master override key required."})
                return

            trade_id = body.get("trade_id", "MANUAL_OVERRIDE")
            reason = body.get("reason", "Founder override pursuant to Section 3.3.")
            self._send_json(200, {
                "decision": "OVERRIDE_GO",
                "trade_id": trade_id,
                "authorized_by": "Jimmy Mathu (Founder / CEO)",
                "reason": reason,
            })
            return

        self._send_json(404, {"error": "Endpoint not found"})


def run_api_server():
    server_address = ("", API_PORT)
    httpd = HTTPServer(server_address, BeepApiHandler)
    print("=" * 70)
    print(f"[*] BEEP Gateway API v2.0 running on http://localhost:{API_PORT}")
    print(f"[*] Licensor & Chief Architect: Jimmy Mathu")
    print(f"[*] Licensee: Sajim Holdings (SAJIM Lab)")
    print(f"[*] Features: Multi-Style (Scalp/Intraday/Swing) + Collective Portfolio")
    print(f"[*] Communication API: Ready for Tete's Bot & MT5 Bridge")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down BEEP Gateway API.")
        httpd.server_close()


if __name__ == "__main__":
    run_api_server()
