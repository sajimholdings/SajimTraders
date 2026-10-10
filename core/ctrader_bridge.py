"""
========================================================================================
            SAJIM HOLDINGS — CTRADER OPEN API PURE PYTHON BRIDGE
                            (core/ctrader_bridge.py)
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Mission:
  - Eliminates the MT5 desktop / Windows OS bottleneck.
  - Connects directly to cTrader Open API 2.0 via secure TLS / WebSockets.
  - Native Linux / Render / Docker compatible (pure Python, 0 Windows GUI/Wine).
  - Multi-bot attribution on a single account via `label` and `comment`:
      * Sajim V1 Flagship       -> label: "SAJIM_V1"
      * Sajim V2 Young Surge    -> label: "SAJIM_V2_SURGE"
      * Sajim V2 Mean Reversion -> label: "SAJIM_V2_REVERT"
  - Provides institutional telemetry, SL/TP management, and Hummingbird peak harvesting.

IMPLEMENTATION STATUS (read before relying on this module):
  - The cTrader Open API protobuf protocol (ProtoOAApplicationAuthReq / AccountAuthReq,
    order and execution events) is NOT implemented yet.
  - In real mode, connect() therefore returns False and send_order() returns
    success=False ("cTrader Open API execution not implemented"). No fake fills, no fake
    balances: balance/equity are None and is_connected is False.
  - An explicit SIMULATION mode exists for offline testing (CTraderBridge(simulation=True)
    or CTRADER_SIMULATION=1). Every simulated result carries simulated=True and status
    "SIMULATED"; it must never be presented as a broker fill.
========================================================================================
"""

import os
import sys
import time
import json
import ssl
import socket
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

logger = logging.getLogger("CTraderBridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [cTrader] %(message)s",
)

# Spotware cTrader Open API Endpoints
CTRADER_HOST_DEMO = "demo.ctraderapi.com"
CTRADER_HOST_LIVE = "live.ctraderapi.com"
CTRADER_PORT_SSL = 5035
CTRADER_PORT_WSS = 5036

# Common Symbol IDs (cTrader maps symbol names to integer IDs per broker)
# Default mapping for standard Spotware Open API Demo
DEFAULT_SYMBOL_MAP = {
    "EURUSD": 1,
    "GBPUSD": 2,
    "EURJPY": 3,
    "USDJPY": 4,
    "AUDUSD": 5,
    "USDCAD": 6,
    "NZDUSD": 7,
    "GBPJPY": 9,
    "XAUUSD": 41, # Gold spot
    "XAGUSD": 42, # Silver spot
    "BTCUSD": 22396,
}


NOT_IMPLEMENTED_MSG = "cTrader Open API execution not implemented"


class CTraderBridge:
    """
    Headless cTrader Open API bridge (connection skeleton) with an explicit,
    clearly-flagged simulation mode. See module docstring for implementation status.
    """

    _instance = None

    @classmethod
    def get_instance(cls, **kwargs):
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None,
        environment: Optional[str] = None,
        dry_run: bool = False,
        simulation: Optional[bool] = None,
        simulation_balance: float = 10000.0,
    ):
        self.client_id = client_id or os.getenv("CTRADER_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("CTRADER_CLIENT_SECRET", "")
        self.access_token = access_token or os.getenv("CTRADER_ACCESS_TOKEN", "")
        self.account_id = str(account_id or os.getenv("CTRADER_ACCOUNT_ID", ""))
        self.environment = (environment or os.getenv("CTRADER_ENVIRONMENT", "demo") or "demo").lower()
        self.dry_run = dry_run

        if simulation is None:
            simulation = os.getenv("CTRADER_SIMULATION", "").strip().lower() in ("1", "true", "yes", "on")
        self.simulation_mode = bool(simulation)

        self.host = CTRADER_HOST_LIVE if self.environment == "live" else CTRADER_HOST_DEMO
        self.port = CTRADER_PORT_SSL

        # Connection & Threading State
        self.is_connected = False
        self.is_authenticated = False
        self.last_error: str = ""
        self.socket: Optional[ssl.SSLSocket] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # In-Memory Cache for Market Data & Portfolio State
        self.symbol_map: Dict[str, int] = dict(DEFAULT_SYMBOL_MAP)
        self.reverse_symbol_map: Dict[int, str] = {v: k for k, v in DEFAULT_SYMBOL_MAP.items()}
        self.spot_prices: Dict[str, Dict[str, float]] = {}  # symbol -> {'bid': x, 'ask': y, ...}
        self.open_positions: Dict[int, Dict[str, Any]] = {}  # position_id -> position dict
        self.closed_deals: List[Dict[str, Any]] = []
        self._sim_ticket_seq = int(time.time()) % 10000000 * 10  # unique simulated ticket ids

        # Account Financial State: unknown until a real account state is reconciled
        self.account_info: Dict[str, Any] = {
            "account_id": self.account_id or None,
            "balance": None,
            "equity": None,
            "free_margin": None,
            "margin_level_pct": None,
            "currency": None,
            "leverage": None,
            "broker": "cTrader Spotware Open API",
            "environment": self.environment.upper(),
            "mode": "SIMULATION" if self.simulation_mode else "HEADLESS_PURE_PYTHON",
        }

        if self.simulation_mode:
            logger.warning(
                "[cTrader Bridge] EXPLICIT SIMULATION MODE: all fills, balances and P&L are simulated "
                "(simulated=True). Nothing is sent to a broker."
            )
            self.account_info.update({
                "account_id": self.account_id or "SIMULATED",
                "balance": float(simulation_balance),
                "equity": float(simulation_balance),
                "free_margin": float(simulation_balance),
                "margin_level_pct": None,
                "currency": "USD",
            })
            self._init_sandbox_market_data()

    def _init_sandbox_market_data(self):
        """Static sample quotes used ONLY in explicit simulation mode."""
        self.spot_prices = {
            "XAUUSD": {"bid": 2685.40, "ask": 2685.65, "spread": 0.25, "point": 0.01, "digits": 2},
            "EURJPY": {"bid": 162.350, "ask": 162.365, "spread": 0.015, "point": 0.001, "digits": 3},
            "GBPJPY": {"bid": 194.200, "ask": 194.225, "spread": 0.025, "point": 0.001, "digits": 3},
            "USDJPY": {"bid": 150.000, "ask": 150.012, "spread": 0.012, "point": 0.001, "digits": 3},
            "USDCAD": {"bid": 1.39200, "ask": 1.39215, "spread": 0.00015, "point": 0.00001, "digits": 5},
            "EURUSD": {"bid": 1.08500, "ask": 1.08512, "spread": 0.00012, "point": 0.00001, "digits": 5},
        }

    # ---------------------------------------------------------------------------
    # Connection & Auth Handshake
    # ---------------------------------------------------------------------------
    def connect(self) -> bool:
        """
        Connects and authenticates. Returns True only when actually authenticated
        (or when explicit simulation mode was requested). Any failure returns False.
        """
        if self.simulation_mode:
            self.is_connected = True
            self.is_authenticated = True
            logger.warning(
                f"[cTrader Bridge] SIMULATED connection (no broker). "
                f"Simulated balance: {self.account_info['balance']:,.2f} {self.account_info['currency']}"
            )
            return True

        if not (self.client_id and self.client_secret and self.access_token and self.account_id):
            self.last_error = (
                "Missing cTrader credentials: set CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET, "
                "CTRADER_ACCESS_TOKEN and CTRADER_ACCOUNT_ID."
            )
            logger.error(f"[cTrader Bridge] {self.last_error}")
            return False

        logger.info(f"Connecting to cTrader Open API: {self.host}:{self.port} (SSL, {self.environment})...")
        try:
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(15.0)
            context = ssl.create_default_context()
            self.socket = context.wrap_socket(raw_socket, server_hostname=self.host)
            self.socket.connect((self.host, self.port))
        except Exception as e:
            self.last_error = f"Connection error: {e}"
            logger.error(f"[cTrader Bridge] {self.last_error}")
            self.disconnect()
            return False

        if not self._authenticate_session():
            logger.error(f"[cTrader Bridge] Authentication failed: {self.last_error}")
            self.disconnect()
            return False

        self.is_connected = True
        self.is_authenticated = True
        if not self._reconcile_account_state():
            logger.error(f"[cTrader Bridge] Account reconciliation failed: {self.last_error}")
            self.disconnect()
            return False
        return True

    def _authenticate_session(self) -> bool:
        """
        ProtoOAApplicationAuthReq + ProtoOAAccountAuthReq.
        Not implemented: returns False rather than pretending to authenticate.
        """
        self.last_error = "cTrader Open API authentication (protobuf) not implemented"
        return False

    def disconnect(self):
        """Gracefully shuts down connection."""
        self._stop_event.set()
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.is_connected = False
        self.is_authenticated = False
        logger.info("[cTrader Bridge] Disconnected.")

    # ---------------------------------------------------------------------------
    # Market Data & Rates
    # ---------------------------------------------------------------------------
    def fetch_live_rates(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "M15",
        count: int = 50,
    ) -> List[float]:
        """
        Historical closes for indicators. Not implemented for the real API (returns []);
        never fabricates price series.
        """
        logger.error(f"[cTrader Bridge] fetch_live_rates({symbol}, {timeframe}) not implemented; returning no data.")
        return []

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Tick specifications; None when unknown (no invented specs)."""
        clean_sym = symbol.replace(".c", "").upper()
        spec = self.spot_prices.get(clean_sym)
        if not spec:
            return None
        return {
            "symbol": symbol,
            "bid": spec["bid"],
            "ask": spec["ask"],
            "spread": spec["spread"],
            "point": spec["point"],
            "digits": spec["digits"],
            "trade_contract_size": 100.0 if "XAU" in clean_sym else 100000.0,
            "simulated": self.simulation_mode,
        }

    # ---------------------------------------------------------------------------
    # Multi-Bot Order Routing & Execution
    # ---------------------------------------------------------------------------
    def send_order(
        self,
        symbol: str,
        action: str,  # "BUY" or "SELL"
        volume: float,  # lots (e.g. 0.01)
        entry_price: float,
        sl: float,
        tp: float,
        label: str = "SAJIM_V2",
        comment: str = "Sajim_Order",
    ) -> Dict[str, Any]:
        """
        Sends order with label and comment for multi-bot attribution.
        Real mode: NOT implemented -> success=False. Simulation: simulated fill, flagged.
        """
        if not self.simulation_mode:
            logger.error(f"[cTrader Bridge] {NOT_IMPLEMENTED_MSG}: {action} {volume} {symbol} NOT sent.")
            return {"success": False, "error": NOT_IMPLEMENTED_MSG, "status": "NOT_IMPLEMENTED",
                    "simulated": False, "label": label}

        sym_info = self.get_symbol_info(symbol)
        if not sym_info:
            return {"success": False, "error": f"No simulated quote for {symbol}", "status": "REJECTED",
                    "simulated": True, "label": label}
        fill_price = sym_info["ask"] if action.upper() == "BUY" else sym_info["bid"]
        with self._lock:
            self._sim_ticket_seq += 1
            ticket = self._sim_ticket_seq

        position = {
            "ticket": ticket,
            "position_id": ticket,
            "symbol": symbol,
            "action": action.upper(),
            "volume": float(volume),
            "entry_price": float(fill_price),
            "sl": float(sl),
            "tp": float(tp),
            "initial_sl": float(sl),
            "open_time": datetime.now(timezone.utc).isoformat(),
            "label": label,        # Bot attribution: SAJIM_V1, SAJIM_V2_SURGE, SAJIM_V2_REVERT
            "comment": comment,
            "profit": 0.0,
            "r_multiple": 0.0,
            "status": "OPEN",
            "simulated": True,
        }
        with self._lock:
            self.open_positions[ticket] = position

        logger.info(
            f"[cTrader SIMULATED FILL] #{ticket} | [{label}] {action.upper()} {volume} {symbol} "
            f"@ {fill_price:.5f} | SL: {sl:.5f} | TP: {tp:.5f} | Comment: {comment}"
        )
        return {
            "success": True,
            "ticket": ticket,
            "order_id": ticket,
            "fill_price": fill_price,
            "label": label,
            "status": "SIMULATED",
            "simulated": True,
        }

    def modify_position(self, position_id: int, sl: float, tp: Optional[float] = None) -> bool:
        """Modifies SL/TP. Real mode not implemented -> False."""
        if not self.simulation_mode:
            logger.error(f"[cTrader Bridge] {NOT_IMPLEMENTED_MSG}: modify #{position_id} NOT sent.")
            return False
        with self._lock:
            pos = self.open_positions.get(position_id)
            if not pos:
                return False
            pos["sl"] = float(sl)
            if tp is not None:
                pos["tp"] = float(tp)
        logger.info(f"[cTrader SIMULATED MODIFY] #{position_id} [{pos['label']}] New SL: {sl:.5f}")
        return True

    def _quote_to_account_ccy(self, amount: float, symbol: str, price: float) -> Tuple[Optional[float], bool]:
        """
        Converts a P&L amount in the symbol's QUOTE currency to the (USD) account currency.
        Returns (amount_usd, converted_ok).
        """
        clean = symbol.replace(".c", "").upper()
        quote = clean[3:6] if len(clean) >= 6 else ""
        base = clean[:3]
        if quote == "USD":
            return amount, True
        if base == "USD" and price > 0:
            return amount / price, True
        # Cross: need QUOTEUSD or USDQUOTE
        q_usd = self.spot_prices.get(f"{quote}USD")
        if q_usd:
            return amount * q_usd["bid"], True
        usd_q = self.spot_prices.get(f"USD{quote}")
        if usd_q and usd_q["bid"] > 0:
            return amount / usd_q["bid"], True
        return None, False

    def close_position(
        self,
        position_id: int,
        reason: str = "MANUAL_OR_EXIT",
        close_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Closes position. Real mode not implemented -> success=False."""
        if not self.simulation_mode:
            logger.error(f"[cTrader Bridge] {NOT_IMPLEMENTED_MSG}: close #{position_id} NOT sent.")
            return {"success": False, "error": NOT_IMPLEMENTED_MSG, "simulated": False}

        with self._lock:
            pos = self.open_positions.pop(position_id, None)
            if not pos:
                return {"success": False, "error": "Position not found", "simulated": True}

            sym_info = self.get_symbol_info(pos["symbol"]) or {}
            exit_price = close_price or (sym_info.get("bid") if pos["action"] == "BUY" else sym_info.get("ask"))
            if not exit_price:
                self.open_positions[position_id] = pos
                return {"success": False, "error": "No simulated quote", "simulated": True}

            is_buy = pos["action"] == "BUY"
            price_diff = (exit_price - pos["entry_price"]) if is_buy else (pos["entry_price"] - exit_price)
            init_risk = abs(pos["entry_price"] - pos.get("initial_sl", pos["sl"])) if pos.get("initial_sl", pos["sl"]) > 0 else 0.0

            contract_size = sym_info.get("trade_contract_size", 100000.0)
            quote_profit = price_diff * pos["volume"] * contract_size
            usd_profit, converted = self._quote_to_account_ccy(quote_profit, pos["symbol"], exit_price)
            r_multiple = round(price_diff / init_risk, 2) if init_risk > 0 else None

            pos["exit_price"] = exit_price
            pos["close_time"] = datetime.now(timezone.utc).isoformat()
            pos["profit"] = round(usd_profit, 2) if usd_profit is not None else None
            pos["profit_quote_ccy"] = round(quote_profit, 2)
            pos["pnl_currency_converted"] = converted
            pos["r_multiple"] = r_multiple
            pos["close_reason"] = reason
            pos["status"] = "CLOSED"
            pos["simulated"] = True

            self.closed_deals.append(pos)
            if usd_profit is not None:
                self.account_info["balance"] = round(self.account_info["balance"] + usd_profit, 2)
                self.account_info["equity"] = self.account_info["balance"]

        logger.info(
            f"[cTrader SIMULATED CLOSE] #{position_id} [{pos['label']}] {pos['symbol']} @ {exit_price:.5f} | "
            f"PnL: {pos['profit']} USD (converted={converted}) | R: {r_multiple} | Reason: {reason}"
        )
        return {"success": True, "deal": pos, "simulated": True}

    # ---------------------------------------------------------------------------
    # Portfolio & Telemetry Queries
    # ---------------------------------------------------------------------------
    def get_positions(self, label: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns open positions, optionally filtered by bot label."""
        with self._lock:
            positions = list(self.open_positions.values())
        if label:
            return [p for p in positions if p.get("label") == label]
        return positions

    def get_deals(self, label: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns closed deal history for expectancy and performance analytics."""
        with self._lock:
            deals = list(self.closed_deals)
        if label:
            deals = [d for d in deals if d.get("label") == label]
        return deals[-limit:]

    def get_account_telemetry(self) -> Dict[str, Any]:
        """Account metrics. balance/equity are None unless known (connected or simulated)."""
        open_count = len(self.open_positions)
        floating_pnl = sum(float(p.get("profit") or 0.0) for p in self.open_positions.values())
        balance = self.account_info.get("balance")
        equity = round(balance + floating_pnl, 2) if balance is not None else None

        return {
            "account_id": self.account_info.get("account_id"),
            "broker": self.account_info.get("broker"),
            "environment": self.account_info.get("environment"),
            "balance": balance,
            "equity": equity,
            "currency": self.account_info.get("currency"),
            "floating_pnl": round(floating_pnl, 2),
            "total_open_positions": open_count,
            "bot_breakdown": {
                "sajim_v1": len(self.get_positions(label="SAJIM_V1")),
                "sajim_v2_surge": len(self.get_positions(label="SAJIM_V2_SURGE")),
                "sajim_v2_revert": len(self.get_positions(label="SAJIM_V2_REVERT")),
            },
            "is_connected": self.is_connected,
            "simulated": self.simulation_mode,
            "last_error": self.last_error,
            "mode": self.account_info.get("mode"),
        }

    def _reconcile_account_state(self) -> bool:
        """Queries broker for balances/positions. Not implemented -> False."""
        self.last_error = "cTrader account reconciliation not implemented"
        return False


if __name__ == "__main__":
    bridge = CTraderBridge()
    ok = bridge.connect()
    print("[+] cTrader Bridge connected:" if ok else "[!] cTrader Bridge NOT connected:", bridge.get_account_telemetry())
