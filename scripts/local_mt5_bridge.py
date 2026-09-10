"""
Sajim Holdings — Windows MetaTrader 5 Bridge Worker
Bridges the local MT5 desktop terminal with the Sajim Traders cloud backend (Render / Supabase).
"""

import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import MetaTrader5 as mt5
    MT5_INSTALLED = True
except ImportError:
    MT5_INSTALLED = False


def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def post_json(url: str, payload: dict, timeout: int = 5) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "SajimMT5Bridge/1.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_json(url: str, timeout: int = 5) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SajimMT5Bridge/1.0"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_filling_type(symbol: str):
    """Determines the appropriate order filling type supported by the broker for this symbol."""
    info = mt5.symbol_info(symbol)
    if not info:
        return mt5.ORDER_FILLING_IOC

    filling_mode = info.filling_mode
    if filling_mode & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    elif filling_mode & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def execute_market_order(order: dict) -> dict:
    """Executes a market order on MT5 directly."""
    symbol = order.get("symbol", "").upper()
    action = order.get("action", "").upper()
    volume = float(order.get("volume", 0.01))
    sl = float(order.get("sl", 0.0))
    tp = float(order.get("tp", 0.0))
    comment = str(order.get("comment", "Sajim_1Tap"))

    if not mt5.symbol_select(symbol, True):
        return {"success": False, "error": f"Failed to select symbol {symbol}"}

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"success": False, "error": f"Failed to fetch market tick for {symbol}"}

    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if action == "BUY" else tick.bid
    filling = get_filling_type(symbol)

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 777001,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    log(f"⚡ Dispatching MT5 Order: {action} {volume} {symbol} @ {price} (SL: {sl}, TP: {tp})")
    res = mt5.order_send(req)

    if res is None:
        err = mt5.last_error()
        return {"success": False, "error": f"order_send failed: {err}"}

    if res.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"✅ Order Executed Successfully! Ticket #{res.order} filled at {res.price}")
        return {
            "success": True,
            "ticket": res.order,
            "deal": res.deal,
            "price": res.price,
            "volume": res.volume
        }
    else:
        err_msg = f"Broker rejected: {res.comment} (code {res.retcode})"
        log(f"❌ Order Rejected: {err_msg}")
        return {"success": False, "error": err_msg, "retcode": res.retcode}


def run_bridge(args):
    if not MT5_INSTALLED:
        log("❌ MetaTrader5 python package is not installed. Run: pip install MetaTrader5")
        sys.exit(1)

    log(f"🚀 Initializing MT5 Terminal Connection...")
    init_kwargs = {}
    if args.login:
        init_kwargs["login"] = int(args.login)
    if args.password:
        init_kwargs["password"] = args.password
    if args.server:
        init_kwargs["server"] = args.server

    if not mt5.initialize(**init_kwargs):
        err = mt5.last_error()
        log(f"⚠️ Initializing with credentials returned {err}. Attempting fallback attach...")
        if not mt5.initialize():
            log(f"❌ Failed to attach to MT5 terminal: {mt5.last_error()}")
            sys.exit(1)

    # Verify or switch account if specified
    if args.login and args.password and args.server:
        acc = mt5.account_info()
        if not acc or str(acc.login) != str(args.login):
            log(f"🔄 Switching MT5 session to Account #{args.login} on {args.server}...")
            login_res = mt5.login(login=int(args.login), password=args.password, server=args.server)
            if not login_res:
                log(f"❌ MT5 login failed: {mt5.last_error()}")
                sys.exit(1)

    account = mt5.account_info()
    if not account:
        log("❌ Could not read MT5 account info. Please make sure MT5 terminal is running and logged in.")
        sys.exit(1)

    log(f"======================================================")
    log(f"✅ CONNECTED TO METATRADER 5 TERMINAL")
    log(f"   👤 Account Name  : {account.name}")
    log(f"   🔑 Account Login : {account.login}")
    log(f"   🌐 Broker Server : {account.server}")
    log(f"   💰 Live Balance  : ${account.balance:,.2f} {account.currency}")
    log(f"   📈 Live Equity   : ${account.equity:,.2f} {account.currency}")
    log(f"   🛡️ Free Margin   : ${account.margin_free:,.2f} {account.currency}")
    log(f"   📡 Cloud Endpoint: {args.endpoint}")
    log(f"======================================================")

    consecutive_errors = 0

    while True:
        try:
            acc = mt5.account_info()
            if not acc:
                log("⚠️ MT5 connection dropped. Reinitializing...")
                mt5.initialize()
                time.sleep(2)
                continue

            # 1. Collect open positions
            positions = mt5.positions_get()
            pos_list = []
            floating_pnl = 0.0

            if positions:
                for p in positions:
                    pnl = round(p.profit, 2)
                    floating_pnl += pnl
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
                        "comment": p.comment or ""
                    })

            # 2. Build telemetry payload
            telemetry_payload = {
                "account_id": str(acc.login),
                "account_name": acc.name or f"Account #{acc.login}",
                "broker_server": acc.server,
                "balance": round(acc.balance, 2),
                "equity": round(acc.equity, 2),
                "free_margin": round(acc.margin_free, 2),
                "margin_level": round(acc.margin_level, 1) if acc.margin_level else 0.0,
                "currency": acc.currency or "USD",
                "open_positions": pos_list,
                "floating_pnl": round(floating_pnl, 2),
                "terminal_connected": True
            }

            # 3. Push telemetry to cloud backend
            sync_url = f"{args.endpoint.rstrip('/')}/api/client/bridge/sync"
            res = post_json(sync_url, telemetry_payload)
            if res.get("success"):
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                if consecutive_errors % 10 == 1:
                    log(f"⚠️ Telemetry push warning: {res.get('error')}")

            # 4. Poll for pending 1-tap orders
            orders_url = f"{args.endpoint.rstrip('/')}/api/client/bridge/orders?account_id={acc.login}"
            orders_res = get_json(orders_url)
            pending_orders = orders_res.get("orders", [])

            for order in pending_orders:
                order_id = order.get("order_id")
                log(f"📥 Received Pending Order from Web Cockpit: {order_id} ({order.get('action')} {order.get('symbol')})")
                exec_result = execute_market_order(order)

                # Report result back to cloud
                res_url = f"{args.endpoint.rstrip('/')}/api/client/bridge/order-result"
                result_payload = {
                    "order_id": order_id,
                    "success": exec_result.get("success", False),
                    "ticket": exec_result.get("ticket"),
                    "error": exec_result.get("error")
                }
                post_json(res_url, result_payload)

            if args.once:
                log(f"🏁 One-shot sync completed successfully. Balance: ${acc.balance:,.2f}")
                break

            time.sleep(args.interval)

        except KeyboardInterrupt:
            log("🛑 Bridge stopped by user.")
            break
        except Exception as e:
            log(f"⚠️ Bridge loop exception: {e}")
            time.sleep(args.interval)

    mt5.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sajim Traders MetaTrader 5 Bridge Worker")
    parser.add_argument("--account", dest="login", default="5808860", help="MT5 Account Login")
    parser.add_argument("--password", default="FZdCC$Y3", help="MT5 Account Password")
    parser.add_argument("--server", default="Headway-Demo", help="Broker Server Name")
    parser.add_argument("--endpoint", default="https://sajim-traders.onrender.com", help="Sajim Cloud API endpoint")
    parser.add_argument("--interval", type=float, default=2.0, help="Sync interval in seconds")
    parser.add_argument("--once", action="store_true", help="Execute a single sync and exit")

    args = parser.parse_args()
    run_bridge(args)
