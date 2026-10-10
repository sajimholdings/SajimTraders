"""
========================================================================================
        SAJIM HOLDINGS — BRIDGE SUPERVISOR (scripts/bridge_supervisor.py)
========================================================================================
Watches the Supabase trading_accounts table and keeps ONE bridge worker running per
(account_id, broker_server) that has stored (encrypted) MT5 credentials.

How it works:
  - Lists all registered accounts every SUPERVISOR_INTERVAL seconds (default 15).
  - For each account with a decryptable password, launches a bridge subprocess with
    credentials passed via ENV (never in the process command line).
  - Restarts a worker if it crashes, with a minimum-restart backoff.
  - Reconciles running workers against the table: a worker is terminated when its
    account row is deleted or loses its credentials, and restarted with fresh args
    when its password, autopilot flag or terminal path changes.

MT5 constraint — one terminal per account
-----------------------------------------
One MT5 terminal process can only be logged into ONE account. If several workers share
a terminal, each mt5.initialize(login=...) silently switches the account under the
others, and orders can land on the wrong account. Each worker therefore gets its OWN
terminal, resolved in this order:

  1. MT5_TERMINAL_PATH_<account_id>   explicit terminal64.exe for that login
                                      (e.g. MT5_TERMINAL_PATH_17537803=C:\\MT5\\a\\terminal64.exe)
  2. MT5_TERMINALS_DIR convention      <MT5_TERMINALS_DIR>\\<account_id>\\terminal64.exe
                                      — a portable copy of the broker terminal per account
                                      (copy the install folder, then launch it once with
                                      /portable so its data dir lives next to the exe).
  3. No per-account terminal found     the account is SKIPPED (logged once), unless
                                      SUPERVISOR_ALLOW_SHARED_TERMINAL=1 (only safe when a
                                      single account is supervised).

The worker is launched with --terminal-path and --portable. local_mt5_bridge.py itself
re-checks the logged-in login on every loop and refuses to trade on a mismatch.

Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, CREDENTIAL_ENCRYPTION_KEY.
"""

import os
import sys
import time
import hashlib
import logging
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.supabase_bridge import SupabaseBridge
from core.credential_vault import decrypt_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SUPERVISOR] %(message)s")
log = logging.getLogger("BridgeSupervisor")

BRIDGE_SCRIPT = os.path.join(ROOT_DIR, "scripts", "local_mt5_bridge.py")
SIGNAL_SCRIPT = os.path.join(ROOT_DIR, "scripts", "signal_generator.py")
MIN_RESTART_SECONDS = 30.0
TERMINAL_EXE = "terminal64.exe"


def resolve_terminal_path(account_id: str):
    """Return the dedicated terminal64.exe path for this account, or None."""
    explicit = os.environ.get(f"MT5_TERMINAL_PATH_{account_id}")
    if explicit:
        return explicit
    terminals_dir = os.environ.get("MT5_TERMINALS_DIR")
    if terminals_dir:
        candidate = os.path.join(terminals_dir, account_id, TERMINAL_EXE)
        if os.path.exists(candidate):
            return candidate
    if os.environ.get("SUPERVISOR_ALLOW_SHARED_TERMINAL") == "1":
        return os.environ.get("MT5_TERMINAL_PATH") or ""
    return None


def _fingerprint(*parts) -> str:
    """Hash of the launch config so we can detect changes without keeping plaintext around."""
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def _stop(proc: subprocess.Popen, timeout: float = 10.0) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()


def main():
    interval = float(os.environ.get("SUPERVISOR_INTERVAL", "15"))
    bridge = SupabaseBridge()
    if not bridge.configured:
        log.error("Supabase not configured. Set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.")
        return 1

    workers = {}          # (account_id, broker_server) -> subprocess.Popen
    fingerprints = {}     # key -> launch-config fingerprint
    last_start = {}       # key -> epoch time of last launch
    skipped_logged = set()
    signal_proc = None    # signal generator subprocess
    signal_last_start = 0.0

    log.info("Bridge supervisor started. Watching trading_accounts...")
    while True:
        try:
            accounts = bridge.list_trading_accounts()

            # Keep the V2 signal generator running (opt-out via SIGNAL_GENERATOR=0)
            if os.environ.get("SIGNAL_GENERATOR", "1") != "0":
                if (signal_proc is None or signal_proc.poll() is not None) and \
                        (time.time() - signal_last_start) >= MIN_RESTART_SECONDS:
                    signal_proc = subprocess.Popen([sys.executable, SIGNAL_SCRIPT], env=os.environ.copy())
                    signal_last_start = time.time()
                    log.info("Started V2 signal generator")

            desired = {}  # key -> (acc, pwd, terminal_path, fingerprint)
            for acc in accounts:
                acc_id = str(acc.get("account_id", "")).strip()
                if not acc_id or not acc_id.isdigit():
                    continue
                server = acc.get("broker_server") or "Headway-Real"
                key = (acc_id, server)

                enc = acc.get("encrypted_password")
                if not enc:
                    continue  # no credentials -> nothing to auto-login with
                pwd = decrypt_password(enc)
                if not pwd:
                    continue

                terminal_path = resolve_terminal_path(acc_id)
                if terminal_path is None:
                    if key not in skipped_logged:
                        log.warning(
                            f"No dedicated MT5 terminal for account {acc_id} ({server}); skipping. "
                            f"Set MT5_TERMINAL_PATH_{acc_id} or MT5_TERMINALS_DIR."
                        )
                        skipped_logged.add(key)
                    continue
                skipped_logged.discard(key)

                fp = _fingerprint(enc, bool(acc.get("autopilot_enabled")), terminal_path, acc.get("user_id"))
                desired[key] = (acc, pwd, terminal_path, fp)

            # Stop workers whose account was deleted / lost credentials / changed config.
            for key in list(workers.keys()):
                proc = workers[key]
                if key not in desired:
                    log.info(f"Stopping worker for {key[0]} on {key[1]} (account removed or credentials cleared)")
                    _stop(proc)
                    workers.pop(key, None)
                    fingerprints.pop(key, None)
                elif fingerprints.get(key) != desired[key][3]:
                    log.info(f"Restarting worker for {key[0]} on {key[1]} (password / autopilot / terminal changed)")
                    _stop(proc)
                    workers.pop(key, None)
                    fingerprints.pop(key, None)
                    last_start.pop(key, None)  # config change -> no crash backoff

            for key, (acc, pwd, terminal_path, fp) in desired.items():
                acc_id, server = key
                proc = workers.get(key)
                if proc is not None and proc.poll() is None:
                    continue  # still running

                # If it just crashed, back off to avoid a tight restart loop.
                if key in last_start and (time.time() - last_start[key]) < MIN_RESTART_SECONDS:
                    continue

                env = {**os.environ, "MT5_LOGIN": acc_id, "MT5_PASSWORD": pwd, "MT5_SERVER": server}
                env.pop("MT5_TERMINAL_PATH", None)
                cmd = [sys.executable, BRIDGE_SCRIPT, "--account", acc_id, "--server", server]
                if terminal_path:
                    cmd += ["--terminal-path", terminal_path, "--portable"]
                if acc.get("autopilot_enabled"):
                    cmd.append("--autopilot")

                proc = subprocess.Popen(cmd, env=env)
                workers[key] = proc
                fingerprints[key] = fp
                last_start[key] = time.time()
                log.info(f"Started bridge worker for account {acc_id} on {server} "
                         f"(terminal={terminal_path or 'shared'}, "
                         f"autopilot={'ON' if acc.get('autopilot_enabled') else 'OFF'})")

        except KeyboardInterrupt:
            log.info("Supervisor stopped.")
            break
        except Exception as e:
            log.warning(f"Supervisor loop error: {e}")

        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            log.info("Supervisor stopped.")
            break

    for proc in workers.values():
        _stop(proc)
    _stop(signal_proc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
