"""
Self-Contained Verification Suite for BEEP Gateway, App, and Risk Gatekeeper
Run this script to verify end-to-end functionality locally.
"""

import sys
import os
import time
import threading
from http.server import HTTPServer

# Add local directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "bots"), os.path.join(ROOT_DIR, "vault"), BASE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from api import BeepApiHandler, API_PORT
from app import SajimBeepClient, display_sammy_card


def run_test_server(server: HTTPServer):
    try:
        server.serve_forever()
    except Exception:
        pass


def run_full_verification():
    print("=" * 70)
    print("      SAJIM HOLDINGS — BEEP END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    # 1. Spin up API in background thread
    server = HTTPServer(("", API_PORT), BeepApiHandler)
    server_thread = threading.Thread(target=run_test_server, args=(server,), daemon=True)
    server_thread.start()
    time.sleep(0.5)

    client = SajimBeepClient(base_url=f"http://localhost:{API_PORT}")

    # 2. Test Gateway Health
    print("[1/5] Testing Gateway Health...")
    health = client.check_health()
    assert health["status"] == "online", "Gateway health failed"
    print(f"      [PASS] Gateway Online (v{health['version']})")

    # 3. Test Signal Generation across Styles
    print("[2/5] Testing Multi-Style Signals (Scalp, Intraday, Swing)...")
    simulated_prices = [
        2310.2, 2311.5, 2310.8, 2312.0, 2313.4,
        2314.1, 2315.5, 2317.2, 2319.8, 2322.5,
        2325.8, 2329.1, 2332.4, 2336.5
    ]

    for style in ["SCALP", "INTRADAY", "SWING"]:
        sig = client.fetch_signal(symbol="XAUUSD", prices=simulated_prices, style=style, account_balance=1000.0)
        assert sig["direction"] in ["BUY", "SELL", "HOLD"], f"Invalid direction in {style}"
        assert sig["M_t"] >= 0.0, "Invalid M(t)"
        print(f"      [PASS] Style: {style:<8} -> Dir: {sig['direction']:<4} | M(t): {sig['M_t']:<5} | B(t): {sig['B_t']:<8} | Lot: {sig['lot_size']}")

    # 4. Test Sammy's 4-Check Gatekeeper
    print("[3/5] Testing Sammy's 4-Check Risk Gatekeeper...")
    sig = client.fetch_signal(symbol="XAUUSD", prices=simulated_prices, style="SWING", account_balance=400.0)
    risk = client.verify_sammy_4check(
        m_t=sig["M_t"],
        current_price=sig["current_price"],
        b_t=sig["B_t"],
        sl=sig["suggested_sl"],
        direction=sig["direction"],
        lot_size=sig["lot_size"],
        lambda_pct=sig["Lambda_pct"],
    )
    assert risk["decision"] in ["GO", "STOP"], "Invalid risk decision"
    print(f"      [PASS] Sammy 4-Check Decision: {risk['decision']} ({risk['summary']})")

    # 5. Test Communication API (Signal Dispatch for Tete's Bot)
    print("[4/5] Testing Communication API Dispatch...")
    alert_text = f"BEEP ALERT: {sig['symbol']} {sig['direction']} @ {sig['current_price']}"
    dispatch_res = client.dispatch_broadcast(alert_text, destination="WHATSAPP_BROADCAST")
    assert dispatch_res["status"] == "SUCCESS", "Communication dispatch failed"
    print(f"      [PASS] Queued for WhatsApp Broadcast (ID: {dispatch_res['entry']['id']})")

    # 6. Test Collective Portfolio Scanner
    print("[5/6] Testing Collective Portfolio Scanner (Multi-Asset)...")
    portfolio_data = {
        "XAUUSD": simulated_prices,
        "EURUSD": [1.0820, 1.0825, 1.0822, 1.0830, 1.0835, 1.0840, 1.0845, 1.0850, 1.0855, 1.0860],
        "US30":   [39100, 39120, 39110, 39150, 39180, 39200, 39220, 39250, 39280, 39310],
    }
    p_eval = client.evaluate_portfolio(portfolio_data)
    assert p_eval["total_assets_scanned"] == 3, "Portfolio scan count mismatch"
    print(f"      [PASS] Assets Scanned: {p_eval['total_assets_scanned']} | High Conviction: {p_eval['high_conviction_signals']} | Portfolio Lambda: {p_eval['portfolio_lambda_pct']}%")

    # 7. Test Institutional Narrative Engine (/v1/narrative)
    print("[6/6] Testing Institutional Narrative Engine (/v1/narrative)...")
    narrative_res = client.fetch_narrative(symbol="XAUUSD", prices=simulated_prices, account_balance=400.0)
    assert "regime" in narrative_res, "Regime missing from narrative"
    assert "broadcast_message" in narrative_res, "Broadcast message missing"
    print(f"      [PASS] Narrative Regime: {narrative_res['regime']} ({narrative_res['quality']})")
    print(f"             Action: {narrative_res['trade_action']} | R:R: {narrative_res['rr_ratio']} | Lot: {narrative_res['lot_size']}")
    print(f"             Auto-Queued for VIP Broadcast: {narrative_res.get('broadcast_queued', False)}")

    # Shutdown server
    server.shutdown()
    print("\n" + "=" * 70)
    print("      ALL END-TO-END TESTS COMPLETED SUCCESSFULLY (100% PASS)")
    print("=" * 70)


if __name__ == "__main__":
    run_full_verification()
