"""
Sajim Holdings Client Application (app.py)
CONSUMER CLIENT & MT5 / COMMUNICATION BRIDGE

Operates strictly via BEEP API Gateway.
Used by:
  - Tete (CTO): MT5 execution & WhatsApp communication dispatch
  - Sammy: Risk verification & 4-Check gatekeeper audit
  - Jimmy: Multi-Style analysis & Collective portfolio monitoring
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

# Configuration
API_URL = os.environ.get("BEEP_API_URL", "http://localhost:8080")
API_KEY = os.environ.get("BEEP_API_KEY", "sajim-tete-live-key-9921")


class SajimBeepClient:
    """Client interface for communicating with Jimmy's BEEP Gateway API."""

    def __init__(self, base_url: str = API_URL, api_key: str = API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _request(self, endpoint: str, data: Optional[Dict[str, Any]] = None, method: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "X-BEEP-API-KEY": self.api_key,
            "User-Agent": "SajimHoldings-App/2.0",
        }

        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                raise RuntimeError(f"API Error ({e.code}): {err_json.get('error', err_body)}")
            except Exception:
                raise RuntimeError(f"HTTP Error {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot connect to BEEP API at {self.base_url}. Is api.py running? ({e.reason})"
            )

    def check_health(self) -> Dict[str, Any]:
        """Verifies connection to BEEP API Gateway."""
        return self._request("/health")

    def check_mt5_status(self) -> Dict[str, Any]:
        """Queries the API for MT5 terminal connection state."""
        return self._request("/v1/mt5/status")

    def fetch_signal(
        self,
        symbol: str,
        prices: List[float],
        style: str = "INTRADAY",
        account_balance: float = 400.0,
    ) -> Dict[str, Any]:
        """
        Queries BEEP API for trade signals.
        Supports styles: 'SCALP', 'INTRADAY', 'SWING'
        """
        payload = {
            "symbol": symbol,
            "prices": prices,
            "style": style,
            "account_balance": account_balance,
        }
        return self._request("/v1/signal", payload)

    def fetch_narrative(
        self,
        symbol: str,
        prices: List[float],
        account_balance: float = 400.0,
    ) -> Dict[str, Any]:
        """
        Queries BEEP API for institutional market narrative,
        asymmetric R:R parameters (1:3.5), and formatted VIP broadcast message.
        """
        payload = {
            "symbol": symbol,
            "prices": prices,
            "account_balance": account_balance,
        }
        return self._request("/v1/narrative", payload)

    def evaluate_portfolio(self, assets: Dict[str, List[float]]) -> Dict[str, Any]:
        """Queries collective portfolio evaluation across multiple assets."""
        return self._request("/v1/portfolio/evaluate", {"assets": assets})

    def verify_sammy_4check(
        self,
        m_t: float,
        current_price: float,
        b_t: float,
        sl: float,
        direction: str,
        lot_size: float,
        lambda_pct: float,
    ) -> Dict[str, Any]:
        """Queries the API to validate the trade against Sammy's 4-Check rules."""
        payload = {
            "M_t": m_t,
            "current_price": current_price,
            "B_t": b_t,
            "sl": sl,
            "direction": direction,
            "lot_size": lot_size,
            "Lambda_pct": lambda_pct,
        }
        return self._request("/v1/sammy-4check", payload)

    def dispatch_broadcast(self, alert_text: str, destination: str = "WHATSAPP_BOT") -> Dict[str, Any]:
        """Communication API: Queues signal for Tete's broadcast bot."""
        payload = {"alert": alert_text, "destination": destination}
        return self._request("/v1/broadcast/dispatch", payload)

    def place_mt5_order(
        self,
        symbol: str,
        direction: str,
        lot: float,
        sl: float,
        tp: float,
    ) -> Dict[str, Any]:
        """Sends trade execution request through the MT5 bridge."""
        payload = {
            "symbol": symbol,
            "direction": direction,
            "lot": lot,
            "sl": sl,
            "tp": tp,
        }
        return self._request("/v1/mt5/order", payload)

    def scan_matrix(self) -> Dict[str, Any]:
        """Requests real-time 20-asset matrix reconnaissance from Gateway."""
        return self._request("/v1/matrix/scan")


def display_sammy_card(check_result: Dict[str, Any]):
    """Renders the physical 4-Check Card in ASCII format for Sammy."""
    checks = check_result.get("checks", {})
    decision = check_result.get("decision", "STOP")

    c1 = checks.get("check_1_momentum", {})
    c2 = checks.get("check_2_sl_baseline", {})
    c3 = checks.get("check_3_lot_size", {})
    c4 = checks.get("check_4_lambda_energy", {})

    def icon(passed: bool) -> str:
        return "[PASS - YES]" if passed else "[FAIL - NO ]"

    print("\n" + "=" * 65)
    print("         SAMMY'S 4-CHECK RISK VERIFICATION CARD")
    print("=" * 65)
    print(f"1. M(t) > 40?          : {icon(c1.get('passed', False))} | {c1.get('detail', '')}")
    print(f"2. SL within B(t) band? : {icon(c2.get('passed', False))} | {c2.get('detail', '')}")
    print(f"3. Lot Size Safe?      : {icon(c3.get('passed', False))} | {c3.get('detail', '')}")
    print(f"4. Lambda > 10%?       : {icon(c4.get('passed', False))} | {c4.get('detail', '')}")
    print("-" * 65)
    if decision == "GO":
        print(">>> FINAL GATEKEEPER DECISION: [ *** GO *** ] — Approved for Execution")
    else:
        print(">>> FINAL GATEKEEPER DECISION: [ !!! STOP !!! ] — Blocked by Risk Gatekeeper")
    print("=" * 65 + "\n")


def run_full_system_demo():
    """Demonstrates complete signal fetch, Sammy check, MT5 bridge, and communication API."""
    print("\n" + "#" * 70)
    print("      SAJIM HOLDINGS — BEEP CLIENT PIPELINE (app.py)")
    print("#" * 70)

    client = SajimBeepClient()

    # 1. Health check
    try:
        health = client.check_health()
        print(f"[+] Gateway Connected: {health.get('service')} (v{health.get('version')})")
        print(f"[+] Styles Supported : {health.get('styles_supported')}")
    except Exception as e:
        print(f"[!] Warning: API is not running: {e}")
        print("[!] Start api.py in a separate terminal: python api.py")
        return

    # 2. MT5 Bridge Status
    print("\n[*] Checking MetaTrader 5 Bridge...")
    try:
        mt5_status = client.check_mt5_status()
        if mt5_status.get("connected"):
            print(f"[+] MT5 Connected! Account: {mt5_status.get('account_info', {}).get('login', 'Unknown')}")
        else:
            print(f"[-] MT5 Status: {mt5_status.get('notice', 'Terminal bridge ready in simulation mode.')}")
    except Exception as e:
        print(f"[!] MT5 check error: {e}")

    # 3. Multi-Style Signal Generation (e.g. Swing vs Intraday vs Scalp)
    simulated_xauusd_h1 = [
        2310.20, 2311.50, 2310.80, 2312.00, 2313.40,
        2314.10, 2315.50, 2317.20, 2319.80, 2322.50,
        2325.80, 2329.10, 2332.40, 2336.50
    ]

    style = "SWING"  # Can be SCALP, INTRADAY, or SWING
    print(f"\n[*] Evaluating XAUUSD Signal in [{style}] Mode...")
    try:
        sig = client.fetch_signal(
            symbol="XAUUSD",
            prices=simulated_xauusd_h1,
            style=style,
            account_balance=1000.0,
        )
        print(f"    * Direction       : {sig['direction']}")
        print(f"    * Current Price   : {sig['current_price']}")
        print(f"    * BEEP Tier       : {sig['tier']}")
        print(f"    * Mass M(t)       : {sig['M_t']}")
        print(f"    * Baseline B(t)   : {sig['B_t']}")
        print(f"    * Lambda Energy   : {sig['Lambda_pct']}%")
        print(f"    * Suggested SL    : {sig['suggested_sl']}")
        print(f"    * Suggested TP    : {sig['suggested_tp']}")
        print(f"    * Dynamic Lot Size: {sig['lot_size']} lot")
        print(f"    * Noise Rejection : {sig['noise_rejection']}")

        # 4. Sammy's 4-Check Gatekeeper
        print("\n[*] Running Sammy's 4-Check Gatekeeper via API...")
        risk = client.verify_sammy_4check(
            m_t=sig["M_t"],
            current_price=sig["current_price"],
            b_t=sig["B_t"],
            sl=sig["suggested_sl"],
            direction=sig["direction"],
            lot_size=sig["lot_size"],
            lambda_pct=sig["Lambda_pct"],
        )
        display_sammy_card(risk)

        if risk["decision"] == "GO":
            # 5. Communication API: Dispatch to Tete's broadcast queue
            print("[*] Dispatching Alert to Communication API (WhatsApp Bot Queue)...")
            alert_msg = (
                f"🚨 *BEEP FOREX SIGNAL: {sig['symbol']} [{style}]*\n\n"
                f"Direction: *{sig['direction']}*\n"
                f"Price: `{sig['current_price']}`\n"
                f"Stop Loss: `{sig['suggested_sl']}` (Protected by B(t))\n"
                f"Take Profit: `{sig['suggested_tp']}`\n"
                f"Lot Size: `{sig['lot_size']}`\n"
                f"Momentum M(t): `{sig['M_t']}` | {sig['tier']}\n\n"
                f"✅ *Sammy's 4-Check:* PASSED (All 4 conditions verified)\n"
                f"⚡ *Sajim Holdings — Powered by BEEP Protocol*"
            )
            dispatch_res = client.dispatch_broadcast(alert_msg, destination="WHATSAPP_BROADCAST")
            print(f"[+] Alert Queued Successfully! (Entry ID: {dispatch_res.get('entry', {}).get('id')})")

            # 6. Execute or Simulate Order on MT5
            print("\n[*] Sending Order Request to MT5 Execution Bridge...")
            order_res = client.place_mt5_order(
                symbol=sig["symbol"],
                direction=sig["direction"],
                lot=sig["lot_size"],
                sl=sig["suggested_sl"],
                tp=sig["suggested_tp"],
            )
            print(f"[+] MT5 Bridge Response: {order_res.get('status')} ({order_res.get('notice', 'Executed')})")

    except Exception as e:
        print(f"[!] Pipeline Error: {e}")

    # 7. Collective Multi-Asset Portfolio Scanner Demo
    print("\n" + "=" * 65)
    print("      COLLECTIVE MULTI-ASSET PORTFOLIO SCANNER DEMO")
    print("=" * 65)
    sample_portfolio = {
        "XAUUSD": [2310, 2312, 2315, 2318, 2322, 2325, 2328, 2332, 2335, 2338],
        "EURUSD": [1.0820, 1.0825, 1.0822, 1.0830, 1.0835, 1.0840, 1.0845, 1.0850, 1.0855, 1.0860],
        "GBPUSD": [1.2650, 1.2655, 1.2660, 1.2665, 1.2670, 1.2675, 1.2680, 1.2685, 1.2690, 1.2695],
        "US30":   [39100, 39120, 39110, 39150, 39180, 39200, 39220, 39250, 39280, 39310],
    }
    try:
        portfolio_eval = client.evaluate_portfolio(sample_portfolio)
        print(f"[*] Total Assets Scanned           : {portfolio_eval['total_assets_scanned']}")
        print(f"[*] High-Conviction Signals        : {portfolio_eval['high_conviction_signals']}")
        print(f"[*] Collective Portfolio Lambda    : {portfolio_eval['portfolio_lambda_pct']}%")
        print(f"[*] Circuit Breaker Active?        : {portfolio_eval['circuit_breaker_active']}")
        print(f"[*] Collective False-Positive Prob : {portfolio_eval['collective_false_positive_prob']}")
        print(f"[*] Portfolio Operational Status   : {portfolio_eval['status']}")
    except Exception as e:
        print(f"[!] Portfolio scan error: {e}")

    print("\n" + "#" * 70)
    print("              PIPELINE DEMONSTRATION COMPLETE")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    run_full_system_demo()
