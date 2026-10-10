"""
========================================================================================
        SAJIM EXECUTION — SHARED MT5 ORDER HELPERS (v2/execution/mt5_exec.py)
========================================================================================
One place for every MT5 order_send call made by the bots:
  - DRY-RUN GATE: with dry_run=True nothing is sent; "[DRY RUN] would ..." is logged.
  - KILL SWITCH : new market entries are refused while the global kill switch is on
                  (closes and SL/TP modifications are still allowed).
  - FRESH PRICE : entries/closes are priced from symbol_info_tick at send time
                  (ask for BUY, bid for SELL), never from a signal bar's close.
  - RETRIES     : requote / price-changed / price-off retcodes are retried with a
                  refreshed price, bounded by max_attempts.
  - FILLING     : IOC -> FOK -> RETURN fallback on every DEAL request (entries AND closes).
  - LOGGING     : every failure is logged with retcode and comment.
========================================================================================
"""

import math
import time
import logging
from typing import Any, Optional, Tuple

import MetaTrader5 as mt5

from v2.safety import new_entries_allowed

logger = logging.getLogger("SajimMT5Exec")

RETCODE_DONE = getattr(mt5, "TRADE_RETCODE_DONE", 10009)
RETCODE_DONE_PARTIAL = getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)
RETCODE_REQUOTE = getattr(mt5, "TRADE_RETCODE_REQUOTE", 10004)
RETCODE_PRICE_CHANGED = getattr(mt5, "TRADE_RETCODE_PRICE_CHANGED", 10020)
RETCODE_PRICE_OFF = getattr(mt5, "TRADE_RETCODE_PRICE_OFF", 10021)
RETCODE_INVALID_FILL = getattr(mt5, "TRADE_RETCODE_INVALID_FILL", 10030)

SUCCESS_RETCODES = {RETCODE_DONE, RETCODE_DONE_PARTIAL}
PRICE_RETRY_RETCODES = {RETCODE_REQUOTE, RETCODE_PRICE_CHANGED, RETCODE_PRICE_OFF}


def _filling_modes():
    return [m for m in (getattr(mt5, "ORDER_FILLING_IOC", None),
                        getattr(mt5, "ORDER_FILLING_FOK", None),
                        getattr(mt5, "ORDER_FILLING_RETURN", None)) if m is not None]


def _is_fill_error(res: Any) -> bool:
    if res is None:
        return False
    return res.retcode == RETCODE_INVALID_FILL or "Unsupported filling mode" in (getattr(res, "comment", "") or "")


def _describe(res: Any) -> str:
    if res is None:
        try:
            return f"order_send returned None: {mt5.last_error()}"
        except Exception:
            return "order_send returned None"
    return f"retcode={res.retcode} comment={getattr(res, 'comment', '')}"


def step_decimals(step: float) -> int:
    """Number of decimals implied by a broker volume step (0.01 -> 2, 0.1 -> 1, 1 -> 0)."""
    if not step or step <= 0:
        return 2
    frac = f"{float(step):.10f}".rstrip("0").split(".")[1]
    return len(frac)


def floor_volume(volume: float, sym_info: Any) -> float:
    """Floors a volume to the broker volume_step (never rounds up). Returns 0.0 if below min."""
    step = float(getattr(sym_info, "volume_step", 0.01) or 0.01)
    vmin = float(getattr(sym_info, "volume_min", step) or step)
    vmax = float(getattr(sym_info, "volume_max", 0.0) or 0.0)
    if volume <= 0:
        return 0.0
    vol = math.floor((float(volume) + 1e-9) / step) * step
    if vmax > 0:
        vol = min(vol, math.floor((vmax + 1e-9) / step) * step)
    vol = round(vol, step_decimals(step))
    return vol if vol + 1e-12 >= vmin else 0.0


def fresh_price(symbol: str, action: str) -> Optional[float]:
    """Current executable price: ask for BUY, bid for SELL."""
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return None
    price = tick.ask if action.upper() == "BUY" else tick.bid
    return float(price) if price else None


def send_market_order(
    symbol: str,
    action: str,
    volume: float,
    sl: float,
    tp: float,
    magic: int,
    comment: str,
    dry_run: bool,
    bot_name: str = "BOT",
    deviation: int = 20,
    max_attempts: int = 3,
) -> Tuple[bool, Any, Optional[float]]:
    """
    Opens a market position. Returns (success, result, fill_price).
    In dry run returns (True, None, current_price) after logging what would be sent.
    """
    action = action.upper()
    if not new_entries_allowed(bot_name):
        return False, None, None

    price = fresh_price(symbol, action)
    if price is None:
        logger.error(f"[{bot_name}] No live tick for {symbol}; entry skipped.")
        return False, None, None

    # Stop must be on the correct side of the executable price
    if sl and ((action == "BUY" and sl >= price) or (action == "SELL" and sl <= price)):
        logger.error(f"[{bot_name}] {symbol} {action}: SL {sl} is not beyond live price {price}; entry skipped.")
        return False, None, None

    if dry_run:
        logger.info(f"[DRY RUN] [{bot_name}] would {action} {volume} {symbol} @ ~{price} | SL {sl} | TP {tp} | {comment}")
        return True, None, price

    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    last_res = None
    for attempt in range(1, max_attempts + 1):
        price = fresh_price(symbol, action) or price
        retry_price = False
        for filling in _filling_modes():
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": float(price),
                "sl": float(sl or 0.0),
                "tp": float(tp or 0.0),
                "deviation": int(deviation),
                "magic": int(magic),
                "comment": str(comment)[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            res = mt5.order_send(req)
            last_res = res
            if res is not None and res.retcode in SUCCESS_RETCODES:
                fill = float(getattr(res, "price", 0.0) or price)
                return True, res, fill
            if _is_fill_error(res):
                continue
            if res is not None and res.retcode in PRICE_RETRY_RETCODES:
                retry_price = True
                break
            logger.error(f"[{bot_name}] Entry rejected on {symbol}: {_describe(res)}")
            return False, res, None
        if not retry_price:
            break
        logger.warning(f"[{bot_name}] {symbol}: {_describe(last_res)} (attempt {attempt}/{max_attempts}); re-pricing.")
        time.sleep(0.25)

    logger.error(f"[{bot_name}] Entry on {symbol} failed after retries: {_describe(last_res)}")
    return False, last_res, None


def close_position(
    pos: Any,
    magic: int,
    comment: str,
    dry_run: bool,
    volume: Optional[float] = None,
    bot_name: str = "BOT",
    deviation: int = 20,
    max_attempts: int = 3,
) -> bool:
    """Closes (fully or partially) an open position with filling-mode fallback and re-pricing."""
    is_buy = getattr(pos, "type", 0) == getattr(mt5, "POSITION_TYPE_BUY", 0)
    close_action = "SELL" if is_buy else "BUY"
    vol = float(volume if volume is not None else pos.volume)

    if dry_run:
        logger.info(f"[DRY RUN] [{bot_name}] would close {vol} of #{pos.ticket} {pos.symbol} ({comment})")
        return True

    order_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    last_res = None
    for attempt in range(1, max_attempts + 1):
        price = fresh_price(pos.symbol, close_action) or float(getattr(pos, "price_current", 0.0) or 0.0)
        retry_price = False
        for filling in _filling_modes():
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": int(pos.ticket),
                "symbol": pos.symbol,
                "volume": vol,
                "type": order_type,
                "price": float(price),
                "deviation": int(deviation),
                "magic": int(magic),
                "comment": str(comment)[:31],
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            res = mt5.order_send(req)
            last_res = res
            if res is not None and res.retcode in SUCCESS_RETCODES:
                return True
            if _is_fill_error(res):
                continue
            if res is not None and res.retcode in PRICE_RETRY_RETCODES:
                retry_price = True
                break
            logger.error(f"[{bot_name}] Close of #{pos.ticket} {pos.symbol} failed: {_describe(res)}")
            return False
        if not retry_price:
            break
        time.sleep(0.25)

    logger.error(f"[{bot_name}] Close of #{pos.ticket} {pos.symbol} failed after retries: {_describe(last_res)}")
    return False


def modify_sltp(pos: Any, sl: float, tp: Optional[float], dry_run: bool, bot_name: str = "BOT", digits: Optional[int] = None) -> bool:
    """Modifies a position's SL/TP; logs and returns False on failure."""
    if digits is not None:
        sl = round(float(sl), int(digits))
    tp_val = float(tp if tp is not None else getattr(pos, "tp", 0.0) or 0.0)
    if dry_run:
        logger.info(f"[DRY RUN] [{bot_name}] would move SL of #{pos.ticket} {pos.symbol} to {sl} (TP {tp_val})")
        return True
    req = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": int(pos.ticket),
        "symbol": pos.symbol,
        "sl": float(sl),
        "tp": tp_val,
    }
    res = mt5.order_send(req)
    if res is not None and res.retcode in SUCCESS_RETCODES:
        return True
    logger.error(f"[{bot_name}] SL/TP modify of #{pos.ticket} {pos.symbol} -> SL {sl} failed: {_describe(res)}")
    return False
