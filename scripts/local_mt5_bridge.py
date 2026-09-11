"""
========================================================================================
        SAJIM HOLDINGS — SUPABASE-BACKED METATRADER 5 BRIDGE WORKER
                     (one worker per trading account)
========================================================================================
Bridges a local MT5 terminal with the Sajim Traders cloud backend (Supabase).

Role:
  - Pulls PENDING orders from Supabase orders_queue (service role) and executes them
    on MT5, reporting FILLED / REJECTED.
  - Reconciles FILLED orders against live MT5 positions, marking closed trades and
    writing them to trade_history.
  - Pushes live balance / equity / margin telemetry to trading_accounts.
  - Optionally mirrors active V2 signals onto the account (Auto-Pilot).

Design note: this is one-worker-per-account. Launch one instance per client account,
each attaching to its own MT5 terminal. The same code runs unchanged on a local PC
(testing a few accounts) or a Windows VPS (scaling to many).

Secrets: broker credentials come from the environment / CLI (never hardcoded).
Supabase service-role key comes from SUPABASE_SERVICE_ROLE_KEY (server-side only).
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    import MetaTrader5 as mt5
    MT5_INSTALLED = True
except ImportError:
    MT5_INSTALLED = False

from core.supabase_bridge import SupabaseBridge

MAGIC_V2 = 888222


def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def get_filling_type(symbol: str):
    """Determines the order filling type supported by the broker for this symbol."""
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
    """Executes a market order on MT5 directly. `order` is a BUY/SELL order dict."""
    symbol = order.get("symbol", "").upper()
    action = order.get("action", "").upper()
    volume = float(order.get("volume", 0.01))
    sl = float(order.get("sl", 0.0) or 0.0)
    tp = float(order.get("tp", 0.0) or 0.0)
    comment = str(order.get("comment", "Sajim_1Tap"))[:31]

    if not mt5.symbol_select(symbol, True):
        return {"success": False, "error": f"Failed to select symbol {symbol}"}

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return {"success": False, "error": f"Failed to fetch market tick for {symbol}"}

    price = tick.ask if action == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    filling = get_filling_type(symbol)

    # Sanitize stops against live market price to prevent 10016 (Invalid stops)
    if action == "BUY":
        if sl > 0 and sl >= price:
            sl = 0.0
        if tp > 0 and tp <= price:
            tp = 0.0
    elif action == "SELL":
        if sl > 0 and sl <= price:
            sl = 0.0
        if tp > 0 and tp >= price:
            tp = 0.0

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC_V2,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    log(f"⚡ Dispatching MT5 Order: {action} {volume} {symbol} @ {price} (SL: {sl}, TP: {tp})")
    res = mt5.order_send(req)

    if res and res.retcode == 10016:
        log("⚠️ Broker rejected with Invalid stops (code 10016). Retrying with sl=0, tp=0...")
        req["sl"] = 0.0
        req["tp"] = 0.0
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
            "volume": res.volume,
        }
    err_msg = f"Broker rejected: {res.comment} (code {res.retcode})"
    log(f"❌ Order Rejected: {err_msg}")
    return {"success": False, "error": err_msg, "retcode": res.retcode}


def close_position_by_ticket(ticket: int) -> dict:
    """Closes an open position on MT5 by ticket number."""
    positions = mt5.positions_get(ticket=int(ticket))
    if not positions:
        return {"success": False, "error": f"Position #{ticket} not found"}

    pos = positions[0]
    sym_info = mt5.symbol_info(pos.symbol)
    if not sym_info:
        return {"success": False, "error": f"Symbol {pos.symbol} not found"}

    tick = mt5.symbol_info_tick(pos.symbol)
    if not tick:
        return {"success": False, "error": f"Failed to fetch tick for {pos.symbol}"}

    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos.ticket,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": "Sajim_WebClose",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_filling_type(pos.symbol),
    }
    res = mt5.order_send(req)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"✅ Closed position #{ticket} {pos.symbol} @ {res.price}")
        return {"success": True, "ticket": ticket, "close_price": res.price}
    return {"success": False, "error": f"Close failed: {res.comment if res else mt5.last_error()}"}


def get_closed_position_result(ticket: int) -> dict:
    """Returns (close_price, net_profit, close_time) for a position that has closed."""
    try:
        deals = mt5.history_deals_get(position=ticket)
        if not deals:
            return {}
        net = 0.0
        close_price = None
        close_time = None
        for d in deals:
            if getattr(d, "entry", None) == mt5.DEAL_ENTRY_OUT:
                net += float(d.profit) + float(d.swap) + float(d.commission)
                if close_price is None:
                    close_price = d.price
                if close_time is None and d.time:
                    close_time = datetime.fromtimestamp(d.time).isoformat()
        return {
            "close_price": close_price,
            "net_profit": round(net, 2),
            "close_time": close_time,
        }
    except Exception as e:
        log(f"⚠️ Could not read history for #{ticket}: {e}")
        return {}


def collect_telemetry() -> dict:
    """Reads current MT5 account + positions into a telemetry dict."""
    acc = mt5.account_info()
    if not acc:
        return {}
    positions = mt5.positions_get() or []
    pos_list = []
    floating_pnl = 0.0
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
            "comment": p.comment or "",
        })
    return {
        "balance": round(acc.balance, 2),
        "equity": round(acc.equity, 2),
        "free_margin": round(acc.margin_free, 2),
        "margin_level": round(acc.margin_level, 1) if acc.margin_level else 0.0,
        "currency": acc.currency or "USD",
        "open_positions": pos_list,
        "floating_pnl": round(floating_pnl, 2),
    }


def compute_today_pnl(account_currency: str = "USD") -> tuple:
    """Computes today's closed PnL from MT5 history deals."""
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(today_start, datetime.now())
        if not deals:
            return (0.0, 0.0)
        closed_pnl = sum(
            float(d.profit) + float(d.swap) + float(d.commission)
            for d in deals if getattr(d, "entry", 0) == 1
        )
        return (round(closed_pnl, 2), 0.0)
    except Exception:
        return (0.0, 0.0)


def run_bridge(args):
    if not MT5_INSTALLED:
        log("❌ MetaTrader5 package is not installed. Run: pip install MetaTrader5")
        return 1

    bridge = SupabaseBridge()
    if not bridge.configured:
        log("❌ Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return 1

    # --- Connect to MT5 terminal ---
    attached = False
    init_kwargs = {}
    if args.terminal_path:
        init_kwargs["path"] = args.terminal_path
    if args.login:
        init_kwargs["login"] = int(args.login)
        if args.password:
            init_kwargs["password"] = args.password
        if args.server:
            init_kwargs["server"] = args.server

    for _ in range(3):
        try:
            if mt5.initialize(**init_kwargs):
                attached = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not attached and not init_kwargs:
        # Last resort: attach to whatever terminal is already running.
        attached = bool(mt5.initialize())

    if not attached:
        log(f"❌ Failed to attach to MT5 terminal: {mt5.last_error()}")
        return 1

    acc = mt5.account_info()
    if not acc:
        log("❌ Could not read MT5 account info. Is the terminal logged in?")
        mt5.shutdown()
        return 1

    account_id = str(acc.login)
    account = bridge.get_trading_account(account_id)
    user_id = account.get("user_id") if account else None

    log("=" * 60)
    log(f"✅ CONNECTED TO MT5 TERMINAL")
    log(f"   👤 Account       : {acc.name} (#{account_id})")
    log(f"   🌐 Broker Server : {acc.server}")
    log(f"   💰 Balance       : ${acc.balance:,.2f} {acc.currency}")
    log(f"   🔑 user_id       : {user_id or '(not found in Supabase yet)'}")
    log("=" * 60)

    while True:
        try:
            acc = mt5.account_info()
            if not acc:
                log("⚠️ MT5 connection dropped. Reconnecting...")
                mt5.initialize(**init_kwargs)
                time.sleep(2)
                continue

            # 1. Execute pending orders
            pending = bridge.get_pending_orders(account_id)
            for order in pending:
                oid = order.get("id")
                action = str(order.get("action", "")).upper()
                bridge.update_order_status(oid, "PROCESSING")

                if action == "CLOSE":
                    close_ticket = order.get("close_ticket")
                    if not close_ticket:
                        bridge.update_order_status(oid, "REJECTED", error_message="close_ticket missing")
                        continue
                    res = close_position_by_ticket(int(close_ticket))
                    if res.get("success"):
                        bridge.update_order_status(oid, "FILLED", mt5_ticket=int(close_ticket), open_price=res.get("close_price"))
                        log(f"📤 CLOSE order {oid} executed (closed #{close_ticket})")
                    else:
                        bridge.update_order_status(oid, "REJECTED", error_message=res.get("error"))
                        log(f"❌ CLOSE order {oid} rejected: {res.get('error')}")
                else:
                    res = execute_market_order(order)
                    if res.get("success"):
                        bridge.update_order_status(oid, "FILLED", mt5_ticket=int(res["ticket"]), open_price=res.get("price"))
                    else:
                        bridge.update_order_status(oid, "REJECTED", error_message=res.get("error"))

            # 2. Collect telemetry + reconcile FILLED orders against live positions
            tel = collect_telemetry()
            live_map = {p["ticket"]: p for p in tel.get("open_positions", [])} if tel else {}
            filled = bridge.list_open_positions(account_id)
            for o in filled:
                ticket = o.get("mt5_ticket")
                if not ticket:
                    continue
                if int(ticket) in live_map:
                    lp = live_map[int(ticket)]
                    bridge.update_position_pnl(o["id"], lp["current_price"], lp["pnl"])
                else:
                    closed = get_closed_position_result(int(ticket))
                    bridge.mark_order_closed(o["id"], closed.get("close_price") or 0.0, closed.get("net_profit") or 0.0)
                    if closed.get("net_profit") is not None:
                        bridge.insert_trade_history({
                            "user_id": o.get("user_id") or user_id,
                            "account_id": account_id,
                            "mt5_ticket": int(ticket),
                            "symbol": o.get("symbol", ""),
                            "action": o.get("action", "BUY"),
                            "volume": o.get("volume", 0.01),
                            "open_price": o.get("open_price") or 0.0,
                            "close_price": closed.get("close_price") or 0.0,
                            "profit": closed.get("net_profit", 0.0),
                            "net_pnl": closed.get("net_profit", 0.0),
                            "open_time": o.get("executed_at") or o.get("created_at"),
                            "close_time": closed.get("close_time") or datetime.now().isoformat(),
                            "comment": o.get("comment", ""),
                        })
                    log(f"🏁 Reconciled order {o['id']} -> CLOSED (ticket #{ticket}, PnL {closed.get('net_profit')})")

            # 3. Push telemetry
            if tel:
                today_pnl, today_pct = compute_today_pnl()
                bridge.sync_account_telemetry(
                    account_id=account_id,
                    balance=tel["balance"],
                    equity=tel["equity"],
                    free_margin=tel["free_margin"],
                    today_pnl=today_pnl,
                    today_pnl_percent=today_pct,
                    terminal_connected=True,
                )

            # 4. Auto-Pilot mirroring (conservative; opt-in via --autopilot)
            if args.autopilot and account and account.get("autopilot_enabled"):
                _autopilot_pass(bridge, account_id, account, tel)

            if args.once:
                log(f"🏁 One-shot sync complete. Balance: ${acc.balance:,.2f}")
                break

            time.sleep(args.interval)

        except KeyboardInterrupt:
            log("🛑 Bridge stopped by user.")
            break
        except Exception as e:
            log(f"⚠️ Bridge loop exception: {e}")
            time.sleep(args.interval)

    mt5.shutdown()
    return 0


def _autopilot_pass(bridge: SupabaseBridge, account_id: str, account: dict, tel: dict):
    """Mirrors active V2 signals onto the account, deduplicated by signal id in comment."""
    user_id = account.get("user_id")
    fixed_lot = float(account.get("fixed_lot") or 0.01)
    signals = bridge.get_active_signals(limit=5)
    if not signals:
        return

    existing_comments = {o.get("comment") for o in bridge.list_orders(account_id) if o.get("comment")}
    for s in signals:
        sig_id = s.get("id")
        comment = f"AUTO_{sig_id}"[:31]
        if not sig_id or comment in existing_comments:
            continue
        bridge.create_order({
            "user_id": user_id,
            "account_id": account_id,
            "symbol": s.get("symbol"),
            "action": s.get("action"),
            "volume": fixed_lot,
            "sl": s.get("sl"),
            "tp": s.get("tp"),
            "comment": comment,
        })
        log(f"🤖 Auto-Pilot queued signal {sig_id} ({s.get('action')} {s.get('symbol')})")
        existing_comments.add(comment)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sajim Traders Supabase MT5 Bridge Worker")
    parser.add_argument("--account", dest="login", default=os.environ.get("MT5_LOGIN"), help="MT5 Account Login")
    parser.add_argument("--password", default=os.environ.get("MT5_PASSWORD"), help="MT5 Account Password")
    parser.add_argument("--server", default=os.environ.get("MT5_SERVER"), help="Broker Server Name (only for auto-login)")
    parser.add_argument("--terminal-path", default=os.environ.get("MT5_TERMINAL_PATH"), help="Path to terminal64.exe (optional)")
    parser.add_argument("--interval", type=float, default=2.0, help="Sync interval in seconds")
    parser.add_argument("--once", action="store_true", help="Execute a single sync and exit")
    parser.add_argument("--autopilot", action="store_true", help="Enable Auto-Pilot signal mirroring")
    args = parser.parse_args()
    raise SystemExit(run_bridge(args))
