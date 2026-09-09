"""
Sajim Holdings — Live MT5 Terminal Bridge (mt5_bridge.py)
Connects MetaTrader 5 live ticks & candles to the BEEP Gateway API.
"""

import os
import sys
import time
import json
from typing import List, Dict, Any, Optional

# Add local directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import SajimBeepClient, display_sammy_card

# Default MT5 installation path detected on this PC
MT5_PATH_DEFAULT = r"C:\Program Files\MetaTrader 5\terminal64.exe"
MT5_HEADWAY_PATH = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"


class MetaTraderBridge:
    """Manages connection to MetaTrader 5 terminal and executes BEEP trades."""

    def __init__(self, terminal_path: Optional[str] = None):
        self.terminal_path = terminal_path or (
            MT5_PATH_DEFAULT if os.path.exists(MT5_PATH_DEFAULT) else MT5_HEADWAY_PATH
        )
        self.client = SajimBeepClient()
        self.mt5_available = False

        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.mt5_available = True
        except ImportError:
            self.mt5 = None
            self.mt5_available = False

    def initialize(self, login: Optional[int] = None, password: Optional[str] = None, server: Optional[str] = None) -> bool:
        """Initializes the MT5 terminal connection."""
        if not self.mt5_available:
            print("[!] Notice: MetaTrader5 Python package not found in current environment.")
            print("    Run: pip install MetaTrader5")
            print("    Operating in SIMULATION / DEMO MODE.")
            return False

        init_args = {}
        if os.path.exists(self.terminal_path):
            init_args["path"] = self.terminal_path
        if login:
            init_args["login"] = login
        if password:
            init_args["password"] = password
        if server:
            init_args["server"] = server

        if not self.mt5.initialize(**init_args):
            print(f"[!] MT5 initialization failed. Error: {self.mt5.last_error()}")
            return False

        account = self.mt5.account_info()
        if account:
            print(f"[+] MT5 Terminal Connected Successfully!")
            print(f"    - Broker Server : {account.server}")
            print(f"    - Account Login : {account.login}")
            print(f"    - Balance       : {account.balance} {account.currency}")
            print(f"    - Equity        : {account.equity} {account.currency}")
            print(f"    - Leverage      : 1:{account.leverage}")
        return True

    def fetch_live_rates(self, symbol: str = "XAUUSD", timeframe: str = "H1", count: int = 50) -> List[float]:
        """Fetches latest closing prices from MT5."""
        if not self.mt5_available:
            # Fallback simulated rates for testing
            return [
                2310.20, 2311.50, 2310.80, 2312.00, 2313.40,
                2314.10, 2315.50, 2317.20, 2319.80, 2322.50,
                2325.80, 2329.10, 2332.40, 2336.50
            ]

        tf_map = {
            "M1": self.mt5.TIMEFRAME_M1,
            "M5": self.mt5.TIMEFRAME_M5,
            "M15": self.mt5.TIMEFRAME_M15,
            "H1": self.mt5.TIMEFRAME_H1,
            "H4": self.mt5.TIMEFRAME_H4,
            "D1": self.mt5.TIMEFRAME_D1,
        }
        selected_tf = tf_map.get(timeframe.upper(), self.mt5.TIMEFRAME_H1)

        rates = self.mt5.copy_rates_from_pos(symbol, selected_tf, 0, count)
        if rates is None or len(rates) == 0:
            print(f"[!] Warning: Could not fetch rates for {symbol} from MT5. Error: {self.mt5.last_error()}")
            return []
        return [float(r['close']) for r in rates]

    def run_live_cycle(self, symbol: str = "XAUUSD", style: str = "INTRADAY", account_balance: float = 400.0):
        """Executes a complete scan -> BEEP Institutional Narrative -> Sammy 4-Check -> MT5 execution cycle."""
        print("\n" + "=" * 65)
        print(f"[*] Starting BEEP Institutional Narrative Scan for {symbol} [{style}]")
        print("=" * 65)

        # 1. Fetch Rates (M15 for Intraday, H1 for Swing)
        tf = "H1" if style == "SWING" else "M15"
        prices = self.fetch_live_rates(symbol=symbol, timeframe=tf, count=30)
        if not prices or len(prices) < 10:
            print("[!] Insufficient price data. Aborting cycle.")
            return

        # 2. Query BEEP Narrative API
        print(f"[*] Querying BEEP Institutional Narrative for {symbol}...")
        try:
            narrative = self.client.fetch_narrative(
                symbol=symbol,
                prices=prices,
                account_balance=account_balance,
            )
        except Exception as e:
            print(f"[!] BEEP Narrative API query failed: {e}")
            return

        print("\n" + "-" * 60)
        print(f"🏛️  ASSET REGIME : {narrative['regime']} ({narrative['quality']})")
        print(f"📖 CONTEXT      : {narrative['narrative_summary']}")
        print(f"🧭 ACTION       : {narrative['trade_action']}")
        print(f"📍 ENTRY        : {narrative['entry_price']}")
        print(f"🛑 INVALIDATION : {narrative['invalidation_sl']} (Protected Floor)")
        print(f"🎯 TARGET 1     : {narrative['target_1']} (1:2 R:R)")
        print(f"🚀 TARGET 2     : {narrative['target_2']} (1:3.5 Runner)")
        print(f"⚖️  R:R RATIO   : {narrative['rr_ratio']} | Lot: {narrative['lot_size']}")
        print("-" * 60)

        # 3. If action is STAND_BY, avoid retail noise
        if narrative["trade_action"] not in ["BUY", "SELL"]:
            print(f"[-] BEEP Decision: STAND_BY. Market is in compression or liquidity trap.")
            print("[-] Standing by — Zero capital risked on retail chop.")
            return

        # 4. Sammy's 4-Check Risk Gatekeeper
        print("\n[*] Auditing trade against Sammy's 4-Check...")
        risk = self.client.verify_sammy_4check(
            m_t=narrative["m_t"],
            current_price=narrative["entry_price"],
            b_t=narrative["b_t"],
            sl=narrative["invalidation_sl"],
            direction=narrative["trade_action"],
            lot_size=narrative["lot_size"],
            lambda_pct=narrative["lambda_pct"],
        )
        display_sammy_card(risk)

        if risk["decision"] != "GO":
            print("[!] Trade blocked by Sammy's 4-Check gatekeeper. Standing by.")
            return

        # 5. Dispatch Alert for Tete's Bot
        self.client.dispatch_broadcast(narrative["broadcast_message"], destination="WHATSAPP_VIP_BROADCAST")
        print("[+] Narrative broadcast alert queued for Tete's channel.")

        # 6. Place Order on MT5 with Asymmetric R:R
        print("[*] Placing order into MT5 terminal with 1:3.5 Target...")
        order_res = self.client.place_mt5_order(
            symbol=symbol,
            direction=narrative["trade_action"],
            lot=narrative["lot_size"],
            sl=narrative["invalidation_sl"],
            tp=narrative["target_2"],
        )
        print(f"[+] MT5 Order Execution: {order_res.get('status')} ({order_res.get('notice', 'Executed')})")


if __name__ == "__main__":
    bridge = MetaTraderBridge()
    bridge.initialize()
    bridge.run_live_cycle(symbol="XAUUSD", style="SWING", account_balance=1000.0)
