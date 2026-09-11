"""
========================================================================================
        SAJIM HOLDINGS — BRIDGE SUPERVISOR (scripts/bridge_supervisor.py)
========================================================================================
Watches the Supabase trading_accounts table and keeps ONE bridge worker running per
account that has stored (encrypted) MT5 credentials.

How it works:
  - Lists all registered accounts.
  - For each account with a decryptable password, launches a bridge subprocess with
    credentials passed via ENV (never in the process command line).
  - Restarts a worker if it crashes, with a minimum-restart backoff.

IMPORTANT (MT5 constraint): one MT5 terminal = one account. To supervise N accounts,
each needs its own MT5 terminal instance (portable copies). This supervisor manages
the *processes*; terminal provisioning is per-account infrastructure.

Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (and optionally
CREDENTIAL_ENCRYPTION_KEY to override the encryption secret).
"""

import os
import sys
import time
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


def main():
    interval = float(os.environ.get("SUPERVISOR_INTERVAL", "15"))
    bridge = SupabaseBridge()
    if not bridge.configured:
        log.error("Supabase not configured. Set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.")
        return 1

    workers = {}          # account_id -> subprocess.Popen
    last_start = {}       # account_id -> epoch time of last launch
    signal_proc = None    # signal generator subprocess
    signal_last_start = 0.0

    log("Bridge supervisor started. Watching trading_accounts...")
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

            for acc in accounts:
                acc_id = str(acc.get("account_id", "")).strip()
                if not acc_id:
                    continue

                enc = acc.get("encrypted_password")
                if not enc:
                    continue  # no credentials -> nothing to auto-login with

                pwd = decrypt_password(enc)
                if not pwd:
                    continue

                server = acc.get("broker_server") or "Headway-Real"

                proc = workers.get(acc_id)
                if proc is not None and proc.poll() is None:
                    continue  # still running

                # If it just crashed, back off to avoid a tight restart loop.
                if acc_id in last_start and (time.time() - last_start[acc_id]) < MIN_RESTART_SECONDS:
                    continue

                env = {**os.environ, "MT5_LOGIN": acc_id, "MT5_PASSWORD": pwd, "MT5_SERVER": server}
                cmd = [sys.executable, BRIDGE_SCRIPT]
                if acc.get("autopilot_enabled"):
                    cmd.append("--autopilot")

                proc = subprocess.Popen(cmd, env=env)
                workers[acc_id] = proc
                last_start[acc_id] = time.time()
                log.info(f"Started bridge worker for account {acc_id} on {server} "
                         f"(autopilot={'ON' if acc.get('autopilot_enabled') else 'OFF'})")

        except KeyboardInterrupt:
            log.info("Supervisor stopped.")
            break
        except Exception as e:
            log.warning(f"Supervisor loop error: {e}")

        time.sleep(interval)

    for acc_id, proc in workers.items():
        if proc.poll() is None:
            proc.terminate()
    if signal_proc is not None and signal_proc.poll() is None:
        signal_proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
