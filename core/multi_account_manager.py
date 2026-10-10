"""
========================================================================================
            SAJIM TRADERS — MULTI-ACCOUNT TRADE & COPY ENGINE
========================================================================================
Chief Quantitative Architect: Jimmy Mathu
Organization: Sajim Holdings Quant Labs
Brand: Sajim Traders (@sajimtraders)

Purpose:
  Centralized multi-account manager enabling:
  1. Client MT5 account registration, secure credential caching, and risk profiling
  2. 1-Tap direct trade execution via MT5 API
  3. Hands-free Auto-Pilot copy-trading: mirrors verified Sajim V2 signals across all
     enrolled accounts with dynamic, balance-proportional lot sizing
  4. Real-time account balance, equity, and open position synchronization
========================================================================================
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = logging.getLogger("MultiAccountManager")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "config", "client_accounts.json")
AUTOPILOT_LOG_FILE = os.path.join(BASE_DIR, "autopilot_executions.json")

# Manual / 1-Tap trades get their OWN magic number so neither the V1 (777999) nor the
# V2 (888222) risk managers ever trail, harvest or close them.
MAGIC_MANUAL = 555111
DEFAULT_MANUAL_RISK_FRACTION = 0.01


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Parses a float; returns default for None/''; raises ValueError for garbage."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    return float(value)


class MultiAccountManager:
    """Manages multiple client trading accounts, risk limits, and trade dispatches."""

    def __init__(self, accounts_path: str = ACCOUNTS_FILE):
        self.accounts_path = accounts_path
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.accounts_path), exist_ok=True)
        if not os.path.exists(self.accounts_path):
            default_data = {
                "default_account_id": "",
                "accounts": {},
                "global_settings": {
                    "auto_mirror_v2_signals": True,
                    "default_max_lot_cap": 0.05,
                    "enforce_stop_loss": True
                }
            }
            with open(self.accounts_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.accounts_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
            return {"default_account_id": "", "accounts": {}, "global_settings": {}}

    def _save_data(self, data: Dict[str, Any]):
        try:
            with open(self.accounts_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Returns list of public account summaries (without sensitive secrets)."""
        data = self._load_data()
        accounts = list(data.get("accounts", {}).values())
        return accounts

    def get_account(self, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Gets account profile by ID or returns default operator account."""
        data = self._load_data()
        acc_id = account_id or data.get("default_account_id")
        if not acc_id:
            return None
        return data.get("accounts", {}).get(str(acc_id))

    def register_or_update_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Registers a new client account or updates settings."""
        data = self._load_data()
        acc_id = str(account_data.get("account_id", "")).strip()
        if not acc_id:
            return {"success": False, "error": "Account ID is required"}

        accounts = data.setdefault("accounts", {})
        existing = accounts.get(acc_id, {})

        password = account_data.get("password")
        broker_server = account_data.get("broker_server", existing.get("broker_server"))
        auth_verified = False

        try:
            balance = _to_float(account_data.get("balance"), _to_float(existing.get("balance"), None))
            equity = _to_float(account_data.get("equity"), _to_float(existing.get("equity"), balance))
            free_margin = _to_float(account_data.get("free_margin"), _to_float(existing.get("free_margin"), None))
            max_lot = _to_float(account_data.get("max_lot"), _to_float(existing.get("max_lot"), 0.01))
            fixed_lot = _to_float(account_data.get("fixed_lot"), _to_float(existing.get("fixed_lot"), 0.01))
            max_open_trades = int(account_data.get("max_open_trades", existing.get("max_open_trades", 3)))
        except (TypeError, ValueError) as e:
            return {"success": False, "error": f"Invalid numeric account field: {e}"}
        account_name = account_data.get("account_name", existing.get("account_name", f"Account #{acc_id}"))

        if MT5_AVAILABLE and password:
            if not broker_server:
                return {"success": False, "error": "broker_server is required to verify the login"}
            # The terminal is SHARED with the live bots: remember the current login and
            # switch back after verification so the bots are never left on a client account.
            original = None
            try:
                if not mt5.initialize():
                    return {"success": False, "error": f"MT5 initialization failed: {mt5.last_error()}"}
                original = mt5.account_info()
                login_ok = mt5.login(login=int(acc_id), password=password, server=broker_server)
                if login_ok:
                    acc_info = mt5.account_info()
                    if acc_info and str(acc_info.login) == acc_id:
                        auth_verified = True
                        account_name = acc_info.name or f"Account #{acc_id}"
                        balance = round(acc_info.balance, 2)
                        equity = round(acc_info.equity, 2)
                        free_margin = round(acc_info.margin_free, 2)
                        logger.info(f"Verified MT5 login for {acc_id} on {broker_server}: Balance {acc_info.balance}")
                else:
                    err = mt5.last_error()
                    logger.warning(f"MT5 login failed for {acc_id} on {broker_server}: {err}")
                    return {
                        "success": False,
                        "error": f"Broker rejected login ({err[0]}): {err[1]}. Please verify your login number, password, and broker server name."
                    }
            except Exception as e:
                logger.error(f"MT5 login exception for {acc_id}: {e}")
                return {"success": False, "error": f"MT5 login verification failed: {e}"}
            finally:
                self._restore_terminal_login(original)

        updated = {
            "account_id": acc_id,
            "account_name": account_name,
            "broker_server": broker_server,
            "broker_name": account_data.get("broker_name", existing.get("broker_name", (broker_server or "").split("-")[0] or None)),
            "autopilot_enabled": account_data.get("autopilot_enabled", existing.get("autopilot_enabled", False)),
            "risk_mode": account_data.get("risk_mode", existing.get("risk_mode", "ULTRA_SAFE")),
            "balance": balance,
            "equity": equity,
            "free_margin": free_margin,
            "currency": account_data.get("currency", existing.get("currency")),
            "open_positions": account_data.get("open_positions", existing.get("open_positions", [])),
            "max_lot": max_lot,
            "fixed_lot": fixed_lot,
            "max_open_trades": max_open_trades,
            "auth_verified": auth_verified or bool(existing.get("auth_verified", False)),
            "connected_at": existing.get("connected_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "last_synced": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "ACTIVE"
        }

        accounts[acc_id] = updated
        data["default_account_id"] = acc_id  # Set as active account

        self._save_data(data)
        logger.info(f"Registered/Updated client account: {acc_id} ({updated['broker_server']}) - Balance: {balance}")
        return {"success": True, "account": updated}

    @staticmethod
    def _restore_terminal_login(original: Any) -> None:
        """Logs the shared terminal back into the account it was on before verification."""
        if not MT5_AVAILABLE or original is None:
            return
        try:
            current = mt5.account_info()
            if current is not None and current.login == original.login:
                return
            ok = mt5.login(original.login, server=original.server)
            if ok:
                logger.info(f"Restored shared MT5 terminal to account {original.login} ({original.server}).")
            else:
                logger.critical(
                    f"Could NOT restore MT5 terminal to account {original.login} ({original.server}): "
                    f"{mt5.last_error()}. Bots on this terminal will refuse to trade until it is re-logged."
                )
        except Exception as e:
            logger.critical(f"Error restoring MT5 terminal login to {getattr(original, 'login', '?')}: {e}")

    def update_account_telemetry(self, account_id: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Updates live balance, equity, positions for an account from external sync/bridge."""
        data = self._load_data()
        acc_id = str(account_id).strip()
        accounts = data.setdefault("accounts", {})
        account = accounts.setdefault(acc_id, {
            "account_id": acc_id,
            "account_name": telemetry.get("account_name", f"Account #{acc_id}"),
            "broker_server": telemetry.get("broker_server"),
            "status": "ACTIVE"
        })

        if "balance" in telemetry:
            account["balance"] = float(telemetry["balance"])
        if "equity" in telemetry:
            account["equity"] = float(telemetry["equity"])
        if "free_margin" in telemetry:
            account["free_margin"] = float(telemetry["free_margin"])
        if "margin_level" in telemetry:
            account["margin_level"] = float(telemetry["margin_level"])
        if "currency" in telemetry:
            account["currency"] = str(telemetry["currency"])
        if "open_positions" in telemetry:
            account["open_positions"] = telemetry["open_positions"]
        if "floating_pnl" in telemetry:
            account["floating_pnl"] = float(telemetry["floating_pnl"])
        if "today_pnl" in telemetry:
            account["today_pnl"] = float(telemetry["today_pnl"])
        if "today_pnl_percent" in telemetry:
            account["today_pnl_percent"] = float(telemetry["today_pnl_percent"])
        if "account_name" in telemetry and telemetry["account_name"]:
            account["account_name"] = telemetry["account_name"]
        if "broker_server" in telemetry and telemetry["broker_server"]:
            account["broker_server"] = telemetry["broker_server"]
        account["terminal_connected"] = bool(telemetry.get("terminal_connected", True))
        account["last_synced"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._save_data(data)
        return {"success": True, "account": account}

    def queue_trade_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Queues a 1-tap trade order for execution by local bridge or terminal worker."""
        data = self._load_data()
        action = str(order_data.get("action", "")).upper()
        if action not in ("BUY", "SELL"):
            return {"success": False, "error": f"Invalid action: {order_data.get('action')}"}
        symbol = str(order_data.get("symbol", "")).strip()
        if not symbol:
            return {"success": False, "error": "Symbol is required"}
        try:
            volume = _to_float(order_data.get("volume"), None)
            sl = _to_float(order_data.get("sl"), None)
            tp = _to_float(order_data.get("tp"), None)
        except (TypeError, ValueError) as e:
            return {"success": False, "error": f"Invalid numeric order field: {e}"}
        if volume is not None and volume <= 0:
            return {"success": False, "error": "Volume must be positive (or omitted to use the account fixed lot)"}
        if volume is None:
            acc_profile = self.get_account(str(order_data.get("account_id", ""))) or {}
            volume = float(acc_profile.get("fixed_lot", 0.01) or 0.01)
        if data.get("global_settings", {}).get("enforce_stop_loss", True) and not (sl and sl > 0):
            return {"success": False, "error": "Stop loss is required (enforce_stop_loss is enabled)"}

        orders = data.setdefault("pending_orders", [])
        order_id = f"ORD_{int(time.time()*1000)}"
        order_entry = {
            "order_id": order_id,
            "account_id": str(order_data.get("account_id", "")),
            "symbol": symbol,
            "action": action,
            "volume": volume,
            "sl": sl or 0.0,
            "tp": tp or 0.0,
            "comment": str(order_data.get("comment", "Sajim_1Tap")),
            "status": "PENDING",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        orders.append(order_entry)
        self._save_data(data)
        logger.info(f"Queued trade order {order_id} for account {order_entry['account_id']}")
        return {"success": True, "order_id": order_id, "status": "QUEUED"}

    def get_pending_orders(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches pending trade orders waiting for bridge execution."""
        data = self._load_data()
        orders = data.get("pending_orders", [])
        if account_id:
            return [o for o in orders if str(o.get("account_id")) == str(account_id) and o.get("status") == "PENDING"]
        return [o for o in orders if o.get("status") == "PENDING"]

    def complete_trade_order(self, order_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Marks a pending trade order as completed or failed."""
        data = self._load_data()
        orders = data.setdefault("pending_orders", [])
        for o in orders:
            if o.get("order_id") == order_id:
                o["status"] = "COMPLETED" if result.get("success") else "FAILED"
                o["ticket"] = result.get("ticket")
                o["error"] = result.get("error")
                o["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save_data(data)
                return {"success": True, "order": o}
        return {"success": False, "error": f"Order {order_id} not found"}

    def switch_active_account(self, account_id: str) -> Dict[str, Any]:
        """Switches the active trading account."""
        data = self._load_data()
        acc_id = str(account_id).strip()
        if acc_id not in data.get("accounts", {}):
            return {"success": False, "error": f"Account {acc_id} not found"}

        data["default_account_id"] = acc_id
        self._save_data(data)
        logger.info(f"Switched default active account to: {acc_id}")
        return {"success": True, "active_account_id": acc_id}

    def remove_account(self, account_id: str) -> Dict[str, Any]:
        """Removes an account from the registry."""
        data = self._load_data()
        acc_id = str(account_id).strip()
        accounts = data.get("accounts", {})
        if acc_id in accounts:
            del accounts[acc_id]
            if data.get("default_account_id") == acc_id:
                data["default_account_id"] = next(iter(accounts.keys())) if accounts else ""
            self._save_data(data)
            return {"success": True, "removed": acc_id}
        return {"success": False, "error": f"Account {acc_id} not found"}

    def set_autopilot(self, account_id: str, enabled: bool) -> Dict[str, Any]:
        """Toggles hands-free copy trading for a specific account."""
        data = self._load_data()
        acc_id = str(account_id or data.get("default_account_id", ""))
        account = data.get("accounts", {}).get(acc_id)

        if account:
            account["autopilot_enabled"] = bool(enabled)
            account["last_synced"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_data(data)
            status_str = "ENABLED (Auto-Pilot ON)" if enabled else "DISABLED (Manual 1-Tap Only)"
            logger.info(f"Account {acc_id} Auto-Pilot set to: {status_str}")
            return {"success": True, "account_id": acc_id, "autopilot_enabled": bool(enabled)}

        return {"success": False, "error": f"Account {acc_id} not found"}

    def calculate_lot_size(self, account_id: str, symbol: str, entry_price: float, sl_price: float) -> float:
        """
        Calculates a safe lot size:
        - MICRO_FIXED / ULTRA_SAFE: the account's fixed lot (max 0.02)
        - otherwise: 1% equity risk over the real stop distance using the symbol's tick value
          (core/lot_calculator.py), capped at the account max_lot. Returns 0.0 if it cannot be
          sized within the risk budget (callers must then refuse the trade).
        """
        account = self.get_account(account_id) or {}
        risk_mode = account.get("risk_mode", "ULTRA_SAFE")
        fixed_lot = float(account.get("fixed_lot", 0.01) or 0.01)

        if risk_mode in ("MICRO_FIXED", "ULTRA_SAFE"):
            return max(0.01, min(fixed_lot, 0.02))

        if not MT5_AVAILABLE:
            return 0.0
        try:
            acc_info = mt5.account_info()
        except Exception:
            acc_info = None
        if not acc_info or not sl_price or abs(entry_price - sl_price) <= 0:
            return 0.0

        try:
            from core.lot_calculator import UniversalLotCalculator
            lot, _, specs = UniversalLotCalculator.calculate_lot(
                symbol=symbol,
                equity=float(acc_info.equity),
                risk_fraction=DEFAULT_MANUAL_RISK_FRACTION,
                entry_price=float(entry_price),
                stop_price=float(sl_price),
                account_currency=getattr(acc_info, "currency", None),
            )
        except Exception as e:
            logger.error(f"Lot sizing failed for {symbol}: {e}")
            return 0.0
        if lot <= 0:
            logger.info(f"1-Tap sizing rejected for {symbol}: {specs.get('rejected')}")
            return 0.0
        return min(lot, float(account.get("max_lot", 0.10) or 0.10))

    def execute_one_tap_trade(
        self,
        account_id: str,
        symbol: str,
        action: str,
        volume: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "Sajim_1Tap"
    ) -> Dict[str, Any]:
        """
        Executes a 1-Tap trade on the connected MT5 terminal.
        Refuses unless the terminal is logged into `account_id`. Uses MAGIC_MANUAL so the
        bots' risk managers never touch it. A stop loss is mandatory when the global
        `enforce_stop_loss` setting is on (default).
        """
        action = action.upper()
        if action not in ("BUY", "SELL"):
            return {"success": False, "error": f"Invalid action: {action}"}

        if not MT5_AVAILABLE:
            return {
                "success": False,
                "error": "MetaTrader 5 library not available in current environment"
            }

        from v2.safety import kill_switch_active
        if kill_switch_active():
            return {"success": False, "error": "Global kill switch is engaged; new trades are blocked"}

        try:
            sl = _to_float(sl, None)
            tp = _to_float(tp, None)
            volume = _to_float(volume, None)
        except (TypeError, ValueError) as e:
            return {"success": False, "error": f"Invalid numeric field: {e}"}

        settings = self._load_data().get("global_settings", {})
        if settings.get("enforce_stop_loss", True) and not (sl and sl > 0):
            return {"success": False, "error": "Stop loss is required (enforce_stop_loss is enabled)"}

        try:
            if not mt5.initialize():
                return {"success": False, "error": f"MT5 initialization failed: {mt5.last_error()}"}
        except Exception as e:
            return {"success": False, "error": f"MT5 initialization failed: {e}"}

        # The order goes to whatever account the terminal is logged into: verify it.
        acc = mt5.account_info()
        if acc is None or str(acc.login) != str(account_id).strip():
            return {
                "success": False,
                "error": (
                    f"Terminal is logged into account {getattr(acc, 'login', None)}, not {account_id}. "
                    f"Trade refused."
                ),
            }

        # Check symbol
        sym_info = mt5.symbol_info(symbol)
        if not sym_info:
            for suffix in [".c", "m", "", "_i"]:
                candidate = f"{symbol.split('.')[0]}{suffix}"
                sym_info = mt5.symbol_info(candidate)
                if sym_info:
                    symbol = candidate
                    break

        if not sym_info:
            return {"success": False, "error": f"Symbol {symbol} not available on broker"}

        if not sym_info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"success": False, "error": f"Failed to retrieve current price tick for {symbol}"}
        price = tick.ask if action == "BUY" else tick.bid

        if sl and ((action == "BUY" and sl >= price) or (action == "SELL" and sl <= price)):
            return {"success": False, "error": f"Stop loss {sl} is on the wrong side of price {price}"}

        from v2.execution.mt5_exec import send_market_order, floor_volume

        # Calculate lot size
        if volume is None or volume <= 0:
            volume = self.calculate_lot_size(account_id, symbol, price, sl or price)
        account = self.get_account(account_id) or {}
        max_lot = float(account.get("max_lot", settings.get("default_max_lot_cap", 0.05)) or 0.05)
        volume = floor_volume(min(float(volume or 0.0), max_lot), sym_info)
        if volume <= 0:
            return {"success": False, "error": "Volume could not be sized within risk / broker minimum lot"}

        ok, result, fill_price = send_market_order(
            symbol=symbol,
            action=action,
            volume=volume,
            sl=round(sl, sym_info.digits) if sl else 0.0,
            tp=round(tp, sym_info.digits) if tp else 0.0,
            magic=MAGIC_MANUAL,
            comment=comment[:31],
            dry_run=False,
            bot_name="1-TAP",
        )
        if not ok:
            if result is None:
                return {"success": False, "error": f"Order not sent: {mt5.last_error()}"}
            return {
                "success": False,
                "retcode": result.retcode,
                "error": f"Execution rejected by broker ({result.retcode}): {result.comment}"
            }

        logger.info(
            f"⚡ [1-TAP EXECUTION SUCCESS] Account {account_id} | Ticket: #{result.order} | "
            f"{action} {volume} {symbol} @ {fill_price} | SL: {sl} | TP: {tp}"
        )

        return {
            "success": True,
            "ticket": result.order,
            "volume": result.volume,
            "price": result.price,
            "symbol": symbol,
            "action": action,
            "sl": sl,
            "tp": tp,
            "magic": MAGIC_MANUAL,
            "comment": comment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def close_position_by_ticket(self, ticket: int) -> Dict[str, Any]:
        """Closes an open position by ticket number."""
        if not MT5_AVAILABLE:
            return {"success": False, "error": "MT5 not available"}

        try:
            positions = mt5.positions_get(ticket=int(ticket))
            if not positions:
                return {"success": False, "error": f"Position #{ticket} not found"}

            pos = positions[0]
            from v2.execution.mt5_exec import close_position
            if close_position(pos, magic=pos.magic, comment="Sajim_WebClose", dry_run=False, bot_name="WEB"):
                return {"success": True, "ticket": ticket}
            return {"success": False, "error": f"Close failed: {mt5.last_error()}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_live_account_telemetry(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches live balance, equity, margin, and positions for an account."""
        account = self.get_account(account_id) or {}
        acc_id = account.get("account_id", str(account_id) if account_id else None)

        def _stored(key: str) -> Optional[float]:
            try:
                return _to_float(account.get(key), None)
            except (TypeError, ValueError):
                return None

        stored_bal = _stored("balance")
        stored_equity = _stored("equity")
        stored_margin = _stored("free_margin")

        base_info = {
            "account_id": acc_id,
            "account_name": account.get("account_name", f"Account #{acc_id}" if acc_id else None),
            "broker_server": account.get("broker_server"),
            "autopilot_enabled": account.get("autopilot_enabled", False),
            "risk_mode": account.get("risk_mode", "ULTRA_SAFE"),
            "balance": round(stored_bal, 2) if stored_bal is not None else None,
            "equity": round(stored_equity, 2) if stored_equity is not None else None,
            "free_margin": round(stored_margin, 2) if stored_margin is not None else None,
            "margin_level": _stored("margin_level"),
            "currency": account.get("currency"),
            "open_positions": account.get("open_positions", []),
            "floating_pnl": _stored("floating_pnl"),
            "terminal_connected": bool(account.get("terminal_connected", False))
        }

        if MT5_AVAILABLE:
            try:
                acc = mt5.account_info()
                if acc:
                    if str(acc.login) == str(acc_id) or not account_id:
                        base_info.update({
                            "account_id": str(acc.login),
                            "account_name": acc.name or account.get("account_name", f"Account #{acc.login}"),
                            "broker_server": acc.server or account.get("broker_server"),
                            "balance": round(acc.balance, 2),
                            "equity": round(acc.equity, 2),
                            "free_margin": round(acc.margin_free, 2),
                            "margin_level": round(acc.margin_level, 1) if acc.margin_level else 0.0,
                            "currency": acc.currency or None,
                            "terminal_connected": True
                        })

                        positions = mt5.positions_get()
                        if positions is not None:
                            pos_list = []
                            total_pnl = 0.0
                            for p in positions:
                                pnl = round(p.profit, 2)
                                total_pnl += pnl
                                pos_list.append({
                                    "ticket": p.ticket,
                                    "symbol": p.symbol,
                                    "type": "BUY" if p.type == 0 else "SELL",
                                    "volume": round(p.volume, 2),
                                    "open_price": round(p.price_open, 5),
                                    "current_price": round(p.price_current, 5),
                                    "sl": round(p.sl, 5) if p.sl else 0.0,
                                    "tp": round(p.tp, 5) if p.tp else 0.0,
                                    "pnl": pnl,
                                    "time": datetime.fromtimestamp(p.time).strftime("%H:%M:%S") if p.time else "",
                                    "comment": p.comment
                                })
                            base_info["open_positions"] = pos_list
                            base_info["floating_pnl"] = round(total_pnl, 2)
            except Exception as e:
                logger.warning(f"Error reading MT5 telemetry: {e}")

        server_str = str(base_info.get("broker_server", "")).lower()
        is_demo = "demo" in server_str or "demo" in str(base_info.get("account_name", "")).lower()

        today_pnl = _stored("today_pnl")
        today_pnl_pct = _stored("today_pnl_percent")

        if MT5_AVAILABLE and base_info.get("terminal_connected"):
            try:
                from v2.safety import utc_day_start, utc_now
                deals = mt5.history_deals_get(utc_day_start(), utc_now())
                if deals is not None:
                    closed_pnl = sum(
                        float(d.profit) + float(d.swap) + float(d.commission) + float(getattr(d, "fee", 0.0) or 0.0)
                        for d in deals if getattr(d, 'type', 0) in (0, 1)
                    )
                    today_pnl = round(closed_pnl, 2)
                    bal = float(base_info.get("balance") or 0.0)
                    start_bal = bal - closed_pnl
                    today_pnl_pct = round((today_pnl / start_bal) * 100, 1) if start_bal > 0 else None
            except Exception:
                pass

        base_info["today_pnl"] = today_pnl
        base_info["today_pnl_percent"] = today_pnl_pct
        base_info["is_demo"] = is_demo

        return base_info


# Global Singleton
account_manager = MultiAccountManager()


def get_multi_account_manager() -> MultiAccountManager:
    """Returns the singleton instance of MultiAccountManager."""
    return account_manager

