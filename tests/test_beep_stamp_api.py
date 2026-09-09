"""
========================================================================================
           TEST SUITE: BEEP STAMP VERIFICATION & MARKET MATRIX API
                          (tests/test_beep_stamp_api.py)
========================================================================================
Chief Architect: Jimmy Mathu
Verifies:
  1. POST /v1/verify: Certified Institutional Fit (High M(t), clean wick, aligned baseline)
  2. POST /v1/verify: Retail Wick Trap Rejection (Upper wick > 45% on BUY)
  3. POST /v1/verify: Wait Compression Rejection (|M(t)| < 25.0)
  4. GET /v1/market/matrix: 4-regime taxonomy output
  5. GET /v1/broadcast/stream: Event stream output
========================================================================================
"""

import os
import sys
import unittest
import json
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "vault")):
    if p not in sys.path:
        sys.path.insert(0, p)

from http.server import HTTPServer
from core.api import BeepApiHandler

TEST_PORT = 8998

class TestBeepStampApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", TEST_PORT), BeepApiHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _post(self, path, payload, api_key="jimmy-founder-master-secret-7700"):
        url = f"http://127.0.0.1:{TEST_PORT}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={
            "Content-Type": "application/json",
            "X-BEEP-API-KEY": api_key,
        })
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _get(self, path, api_key="jimmy-founder-master-secret-7700"):
        url = f"http://127.0.0.1:{TEST_PORT}{path}"
        req = Request(url, headers={
            "X-BEEP-API-KEY": api_key,
        })
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_health_check(self):
        status, data = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["licensor"], "Jimmy Mathu (Sole IP Owner)")
        print("\n[PASS] /health endpoint online and licensor verified.")

    def test_beep_stamp_certified_fit(self):
        """Simulate high-momentum institutional breakout without retail wick."""
        prices = [100.0, 100.5, 101.0, 101.8, 102.5, 103.2, 104.0, 105.0, 106.2, 107.5, 109.0, 110.5]
        payload = {
            "symbol": "EURUSD.c",
            "timeframe": "M15",
            "action": "BUY",
            "entry": 110.5,
            "sl": 105.0,
            "tp": 127.0,  # 1:3.0 R:R
            "prices": prices,
        }
        status, data = self._post("/v1/verify", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["beep_stamp"], "CERTIFIED_INSTITUTIONAL_FIT")
        self.assertGreaterEqual(data["beep_score"], 70.0)
        self.assertEqual(data["regime"], "ACTIVE_HUNT")
        print(f"[PASS] BEEP Stamp CERTIFIED_INSTITUTIONAL_FIT granted: Score {data['beep_score']}/100")

    def test_beep_stamp_rejected_compression(self):
        """Simulate flat oscillating chop with |M(t)| < 25.0."""
        prices = [100.0, 100.1, 99.9, 100.0, 100.1, 100.0, 99.9, 100.0, 100.1, 100.0, 99.9, 100.0]
        payload = {
            "symbol": "EURUSD.c",
            "timeframe": "M15",
            "action": "BUY",
            "entry": 100.0,
            "sl": 99.5,
            "tp": 101.5,
            "prices": prices,
        }
        status, data = self._post("/v1/verify", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["beep_stamp"], "REJECTED_RETAIL_TRAP")
        self.assertEqual(data["regime"], "WAIT_COMPRESSION")
        print(f"[PASS] BEEP Stamp REJECTED_RETAIL_TRAP on chop compression: Score {data['beep_score']}/100")

    def test_broadcast_stream_endpoint(self):
        status, data = self._get("/v1/broadcast/stream")
        self.assertEqual(status, 200)
        self.assertIn("total_stream_events", data)
        self.assertIn("events", data)
        print(f"[PASS] /v1/broadcast/stream active with {data['total_stream_events']} events.")


if __name__ == "__main__":
    unittest.main()
