"""
========================================================================================
        SAJIM HOLDINGS — V2 SIGNAL GENERATOR (scripts/signal_generator.py)
========================================================================================
Runs the V2 cartridge engine continuously in SIGNAL-ONLY mode: scans the market,
broadcasts, and publishes signals to Supabase. It NEVER places orders — execution
happens per-account via each client's bridge worker (autopilot).

Every confirmed V2 signal is written to the Supabase `signals` table via
SupabaseBridge.publish_signal with an expires_at of now + SIGNAL_TTL_MINUTES (default
15). The bridge worker only mirrors active, unexpired, recent signals.

Requires a running MT5 terminal (to read symbol data). Set SIGNAL_INTERVAL (seconds)
to control the scan cadence (default 60).

The V2 engine depends on the proprietary BEEP modules (core.beep_*). If they are not
deployed, this script exits with a clear error instead of crashing on import.
"""

import os
import sys
import time
import hashlib
import logging
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT_DIR, os.path.join(ROOT_DIR, "core"), os.path.join(ROOT_DIR, "v2"), os.path.join(ROOT_DIR, "bots")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.supabase_bridge import SupabaseBridge
from core.mt5_login import get_login_kwargs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SIGNAL] %(message)s")
log = logging.getLogger("SignalGenerator")

SIGNAL_TTL_MINUTES = float(os.environ.get("SIGNAL_TTL_MINUTES", "15"))


def _signal_id(symbol: str, timeframe: str, action: str, strategy: str) -> str:
    """Stable id per (setup, minute) so re-broadcasts of the same setup upsert one row."""
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    digest = hashlib.sha1(f"{symbol}|{timeframe}|{action}|{strategy}|{minute}".encode("utf-8")).hexdigest()[:10]
    return f"SIG_{symbol}_{timeframe}_{action}_{digest}"[:64]


def build_signal_row(
    symbol, timeframe, action, strategy_name, entry, sl, tp, rr,
    phase="UNKNOWN", reason="", **_ignored,
) -> dict:
    """Map a V2 broadcast payload to a `signals` table row."""
    action = str(action).upper()
    return {
        "id": _signal_id(str(symbol), str(timeframe), action, str(strategy_name)),
        "symbol": str(symbol),
        "timeframe": str(timeframe),
        "action": action,
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
        "rr": f"1:{float(rr):.1f}" if rr else None,
        "strategy": str(strategy_name),
        "phase": str(phase or "UNKNOWN"),
        "trade_explainer": str(reason or "")[:500],
        "is_active": True,
    }


def make_publisher(supabase: SupabaseBridge, original=None):
    """Wrap a broadcast function so every V2 signal is also published to Supabase."""
    def publish(*args, **kwargs):
        if original is not None:
            try:
                original(*args, **kwargs)
            except Exception as e:
                log.warning(f"broadcast error: {e}")
        try:
            row = build_signal_row(*args, **kwargs)
            if row["action"] not in ("BUY", "SELL"):
                return
            res = supabase.publish_signal(row, ttl_minutes=SIGNAL_TTL_MINUTES)
            if isinstance(res, dict) and res.get("error"):
                log.warning(f"publish_signal failed for {row['id']}: {res.get('error')}")
            else:
                log.info(f"Published {row['action']} {row['symbol']} {row['timeframe']} ({row['id']})")
        except Exception as e:
            log.warning(f"publish_signal error: {e}")
    return publish


def main():
    os.environ["MUTE_TELEGRAM"] = "1"  # signal generator publishes to Supabase, not Telegram

    supabase = SupabaseBridge()
    if not supabase.configured:
        log.error("Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY); signals cannot be published.")
        return 1

    try:
        import MetaTrader5 as mt5
    except ImportError:
        log.error("MetaTrader5 package not installed; the signal generator needs a local MT5 terminal.")
        return 1

    try:
        from v2.sajim_v2_dual_bot import SajimV2DualBot
    except ImportError as e:
        log.error(f"V2 engine unavailable ({e}). Deploy the BEEP modules (core.beep_*) to generate signals.")
        return 1

    kwargs = get_login_kwargs()
    ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
    if not ok:
        time.sleep(2)
        ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
    if not ok:
        log.error(f"MT5 init failed: {mt5.last_error()}")
        return 1

    bot = SajimV2DualBot(dry_run=True)

    # Build the tradable universe from the whitelist (attach to running terminal only).
    bot.universe = []
    for target in bot.target_symbols:
        for cand in (target, f"{target}.c", f"{target}_c", f"{target}c"):
            si = mt5.symbol_info(cand)
            if si and si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                if not si.visible:
                    mt5.symbol_select(cand, True)
                bot.universe.append(cand)
                break

    # SIGNAL-ONLY: never execute orders here.
    bot.execute_signal = lambda sig: False

    # Publish every confirmed signal to Supabase alongside the existing broadcast.
    bus = getattr(bot, "bus", None)
    if bus is not None and hasattr(bus, "broadcast_v2_signal"):
        bus.broadcast_v2_signal = make_publisher(supabase, bus.broadcast_v2_signal)
    else:
        log.error("V2 bot has no broadcast bus to hook; cannot publish signals.")
        return 1

    log.info(f"V2 signal generator running. Universe ({len(bot.universe)}): {bot.universe} "
             f"| signal TTL {SIGNAL_TTL_MINUTES:g} min")

    interval = float(os.environ.get("SIGNAL_INTERVAL", "60"))
    while True:
        try:
            bot.scan_and_evaluate()
        except Exception as e:
            log.warning(f"scan error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
