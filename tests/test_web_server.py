"""
Unit and Integration Test Suite for Sajim Traders Web App Server
"""

import threading
import time
import urllib.request
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from web.server import ThreadingHTTPServer, SajimTradersHandler

def test_web_server():
    port = 8095
    server = ThreadingHTTPServer(('127.0.0.1', port), SajimTradersHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{port}"

    try:
        print("[*] 1. Testing GET / (Static HTML)...")
        with urllib.request.urlopen(f"{base_url}/") as res:
            assert res.status == 200
            html = res.read().decode('utf-8')
            assert 'Sajim Traders' in html or 'SAJIM' in html
            print("    [+] HTML delivered successfully.")

        print("[*] 2. Testing GET /styles.css...")
        with urllib.request.urlopen(f"{base_url}/styles.css") as res:
            assert res.status == 200
            css = res.read().decode('utf-8')
            assert '--bg-dark' in css or '--bg-primary' in css
            print("    [+] CSS delivered successfully.")

        print("[*] 3. Testing GET /app.js...")
        with urllib.request.urlopen(f"{base_url}/app.js") as res:
            assert res.status == 200
            js = res.read().decode('utf-8')
            assert 'fetchAccount' in js or 'fetchSignals' in js or 'fetchTelemetry' in js
            print("    [+] JS delivered successfully.")

        print("[*] 4. Testing GET /api/status...")
        with urllib.request.urlopen(f"{base_url}/api/status") as res:
            assert res.status == 200
            status_data = json.loads(res.read().decode('utf-8'))
            assert "account" in status_data
            assert "concurrency" in status_data
            print(f"    [+] Status API: Balance = {status_data['account']['balance_usc']} USC | Server = {status_data['broker']['server']}")

        print("[*] 5. Testing GET /api/positions...")
        with urllib.request.urlopen(f"{base_url}/api/positions") as res:
            assert res.status == 200
            pos_data = json.loads(res.read().decode('utf-8'))
            assert "trades" in pos_data
            print(f"    [+] Positions API: {pos_data['total_open']} active positions reported.")

        print("[*] 6. Testing GET /api/signals...")
        with urllib.request.urlopen(f"{base_url}/api/signals") as res:
            assert res.status == 200
            sig_data = json.loads(res.read().decode('utf-8'))
            assert "signals" in sig_data
            print(f"    [+] Signals API: {sig_data['count']} signals streaming.")

        print("[*] 7. Testing GET /api/edge-matrix...")
        with urllib.request.urlopen(f"{base_url}/api/edge-matrix") as res:
            assert res.status == 200
            edge_data = json.loads(res.read().decode('utf-8'))
            assert "top_edges" in edge_data
            print(f"    [+] Edge Matrix API: {len(edge_data['top_edges'])} top approved pairs loaded.")

        print("[*] 8. Testing POST /api/sammy-check (Passing Check)...")
        passing_payload = {
            "symbol": "XAUUSD.c",
            "direction": "BUY",
            "current_price": 2315.5,
            "b_t": 2312.0,
            "sl": 2311.0,
            "lot_size": 0.10,
            "m_t": 58.5,
            "lambda_pct": 18.5
        }
        req = urllib.request.Request(
            f"{base_url}/api/sammy-check",
            data=json.dumps(passing_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as res:
            assert res.status == 200
            sammy_res = json.loads(res.read().decode('utf-8'))
            assert sammy_res["decision"] == "GO"
            print(f"    [+] Sammy Gatekeeper Pass: Decision = {sammy_res['decision']} ({sammy_res['tier']})")

        print("[*] 9. Testing POST /api/sammy-check (Failing Check)...")
        failing_payload = {
            "symbol": "XAUUSD.c",
            "direction": "BUY",
            "current_price": 2315.5,
            "b_t": 2312.0,
            "sl": 2320.0, # SL above buy price!
            "lot_size": 0.10,
            "m_t": 12.0,  # Low momentum!
            "lambda_pct": 5.0
        }
        req2 = urllib.request.Request(
            f"{base_url}/api/sammy-check",
            data=json.dumps(failing_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req2) as res:
            assert res.status == 200
            sammy_res2 = json.loads(res.read().decode('utf-8'))
            assert sammy_res2["decision"] == "STOP"
        print("[*] 10. Testing GET /api/landing...")
        with urllib.request.urlopen(f"{base_url}/api/landing") as res:
            assert res.status == 200
            landing_data = json.loads(res.read().decode('utf-8'))
            assert "brand" in landing_data
            assert "stats" in landing_data
            print(f"    [+] Landing API: Brand = {landing_data['brand']} | Rare WR = {landing_data['stats']['rare_layer_winrate']}")

        print("\n===========================================================")
        print("   ALL 10 END-TO-END SAJIM TRADERS WEB APP TESTS PASSED!")
        print("===========================================================\n")

    finally:
        server.shutdown()

if __name__ == "__main__":
    test_web_server()
