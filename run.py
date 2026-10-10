"""
========================================================================================
                      SAJIM HOLDINGS — MASTER QUANT RUNNER
                                   (run.py)
========================================================================================
Architect & Lead Quant: Jimmy Mathu
Operational Command Center:
  v1 / server : Sajim V1 production engine / overnight daemon (MT5)
  v2          : Sajim V2 edge-driven bot (MT5)
  dual        : V1 + V2 coexistence orchestrator (MT5, or cTrader with --broker ctrader)
  propfirm    : Prop Firm Challenge Bot (DD-preservation engine)
  scanner     : Cross-asset matrix scanner (requires private BEEP modules)
  backtest    : Quantitative backtesting engine (requires private BEEP modules)
  edge        : Edge verification matrix (MT5 history; --oos-split for out-of-sample)
  test, api, web, concierge, digest, ctrader, investor : support tooling

Safety:
  - Every bot runs in DRY RUN unless --live is passed (dry run never sends orders).
  - GLOBAL KILL SWITCH: create a file named KILL_SWITCH in the repo root, or set
    SAJIM_KILL_SWITCH=1, and every bot stops opening new trades (open positions are
    still managed). Remove it to resume.
  - Commands that need the private BEEP modules (core/beep_*, vault_original_beep) exit
    with status 1 and a clear message when those modules are absent.
========================================================================================
"""

import os
import sys
import time
import logging
import argparse

# Bootstrap all project modules on sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (
    ROOT_DIR,
    os.path.join(ROOT_DIR, "core"),
    os.path.join(ROOT_DIR, "bots"),
    os.path.join(ROOT_DIR, "bots", "prop_firm"),
    os.path.join(ROOT_DIR, "tests"),
):
    if p not in sys.path:
        sys.path.insert(0, p)


def print_banner():
    banner = """
================================================================================
                    SAJIM HOLDINGS QUANTITATIVE LABS
                Scale-Invariant Institutional Trading Systems
================================================================================
"""
    print(banner)


PRIVATE_MODULE_PREFIXES = ("core.beep_", "beep_", "vault_original_beep", "core.tick_beep_engine", "tick_beep_engine")


class CommandUnavailable(Exception):
    """Raised by a command that cannot run in this checkout."""


def _is_private_module_error(err: ImportError) -> bool:
    name = getattr(err, "name", None) or ""
    text = str(err)
    return any(name.startswith(p) for p in PRIVATE_MODULE_PREFIXES) or "private BEEP" in text or any(
        f"'{p}" in text for p in PRIVATE_MODULE_PREFIXES
    )


def cmd_propfirm(args):
    print(f"[*] Launching Prop Firm Challenge Bot (Account Size: ${args.size:,.2f})...")
    from bots.prop_firm.prop_firm_challenge_bot import PropFirmChallengeBot
    import MetaTrader5 as mt5
    bot = PropFirmChallengeBot(
        account_size=args.size,
        dry_run=not args.live,
    )
    if not bot.connect():
        raise CommandUnavailable("Failed to connect to MT5 terminal.")
    try:
        bot.run_single_iteration()
    finally:
        mt5.shutdown()


def cmd_v1(args):
    print("[*] Launching Sajim V1 Quant Engine...")
    from bots.sajim_server_overnight import SajimOvernightServer
    import MetaTrader5 as mt5
    server = SajimOvernightServer(
        scan_interval_seconds=getattr(args, 'interval', 30),
        max_concurrent_positions=getattr(args, 'max_positions', 3),
        base_risk_fraction=getattr(args, 'risk', 0.01),
        dry_run=not args.live,
    )
    target_acc = getattr(args, 'account', None)
    if not server.connect(target_account=target_acc):
        raise CommandUnavailable("Failed to connect Sajim V1 to the MT5 terminal / target account.")
    try:
        server.run_forever()
    finally:
        mt5.shutdown()


def cmd_server(args):
    cmd_v1(args)


def cmd_v2(args):
    import MetaTrader5 as mt5
    print("[*] Launching Sajim V2 Edge-Driven Production Bot...")
    from bots.sajim_v2_bot import SajimV2Bot
    bot = SajimV2Bot(
        max_concurrent_positions=getattr(args, 'max_positions', 5),
        base_risk_fraction=getattr(args, 'risk', 0.012),
        dry_run=not args.live,
    )
    target_acc = getattr(args, 'account', None)
    if not bot.connect(target_account=target_acc):
        raise CommandUnavailable("Failed to connect Sajim V2 to the MT5 terminal / target account.")

    interval = getattr(args, 'interval', 15)
    if getattr(args, 'loop', False):
        print(f"[+] Sajim V2 running in continuous loop (interval: {interval}s | dry_run: {not args.live})...")
        log = logging.getLogger("RunV2")
        failures = 0
        try:
            while True:
                try:
                    bot.run_iteration()
                    failures = 0
                    time.sleep(interval)
                except KeyboardInterrupt:
                    raise
                except Exception as loop_err:
                    failures += 1
                    backoff = min(300, interval * (2 ** min(failures, 5)))
                    log.error(f"[!] V2 iteration failed ({failures} in a row): {loop_err}. Retrying in {backoff}s.", exc_info=True)
                    time.sleep(backoff)
        except KeyboardInterrupt:
            print("\n[+] Sajim V2 stopped.")
        finally:
            mt5.shutdown()
    else:
        print("[+] Running single Sajim V2 scan & execution pass...")
        bot.run_iteration()
        mt5.shutdown()


def cmd_dual(args):
    print("[*] Launching Sajim V1 & V2 Dual Coexistence Orchestrator...")
    from v2.dual_orchestrator import SajimDualOrchestrator
    import MetaTrader5 as mt5

    orchestrator = SajimDualOrchestrator(
        scan_interval_seconds=getattr(args, 'interval', 15),
        max_combined_positions=getattr(args, 'max_combined', 12),
        max_v1_positions=getattr(args, 'max_v1', 6),
        max_v2_positions=getattr(args, 'max_v2', 6),
        base_risk_v1=getattr(args, 'risk_v1', 0.01),
        base_risk_v2=getattr(args, 'risk_v2', 0.01),
        dry_run=not args.live,
        target_account=getattr(args, 'account', None),
        broker=getattr(args, 'broker', 'mt5'),
    )

    if not orchestrator.connect():
        raise CommandUnavailable(f"Dual orchestrator failed to connect (broker: {orchestrator.broker}).")
    try:
        if getattr(args, 'once', False):
            print("[+] Executing single dual pass (V1 + V2)...")
            orchestrator.execute_dual_pass()
        else:
            orchestrator.run_continuous()
    except KeyboardInterrupt:
        print("\n[+] Dual Orchestrator stopped by operator.")
    finally:
        if orchestrator.broker != "ctrader":
            try:
                mt5.shutdown()
            except Exception:
                pass
        else:
            orchestrator.ctrader.disconnect()


def cmd_edge(args):
    print("[*] Launching Quantitative Edge Verification Matrix...")
    import subprocess
    script = os.path.join(ROOT_DIR, "scripts", "run_edge_matrix_backtest.py")
    cmd = [sys.executable, script, "--bars", str(args.bars)]
    if args.oos_split:
        cmd += ["--oos-split", str(args.oos_split)]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        sys.exit(rc)


def cmd_scanner(args):
    print("[*] Launching Cross-Asset Real-Time Matrix Scanner (20+ Fronts)...")
    from core.beep_matrix_scanner import BeepMatrixScanner
    scanner = BeepMatrixScanner()
    scanner.scan_all_fronts()


def cmd_backtest(args):
    print("[*] Launching Quantitative Backtesting Harness...")
    from core.backtester import BeepCoreEngine, execute_test_001, execute_test_002, execute_test_003
    if BeepCoreEngine is None:
        raise ImportError("backtest requires the private BEEP module beep_core (core/beep_*), not in this repo", name="beep_core")
    tests = {"001": execute_test_001, "002": execute_test_002, "003": execute_test_003}
    tests[args.test_id](allow_synthetic=args.allow_synthetic)


def cmd_test(args):
    print("[*] Running End-to-End System Verification Suite...")
    from tests.test_system import run_full_verification
    run_full_verification()


def cmd_api(args):
    print(f"[*] Launching BEEP Commercial Gateway API Server on port {args.port}...")
    # core.api reads its port from BEEP_API_PORT at import time
    os.environ["BEEP_API_PORT"] = str(args.port)
    from core.api import run_api_server
    run_api_server()


def cmd_concierge(args):
    print("[*] Launching Sajim Community Concierge & Conversion AI...")
    from core.sajim_community_concierge import get_concierge
    import time
    concierge = get_concierge()
    concierge.start()
    print("[+] Concierge AI is running 24/7. Monitoring member interactions on Telegram...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        concierge.stop()


def cmd_digest(args):
    print("[*] Generating Daily Market & Pair Health Digest...")
    from core.market_digest_generator import MarketDigestGenerator
    gen = MarketDigestGenerator()
    gen.generate_and_broadcast(publish_telegram=not args.no_broadcast)
    print("[+] Digest published successfully.")


def cmd_web(args):
    print(f"[*] Launching Sajim Traders FastAPI Gateway on http://localhost:{args.port}...")
    import uvicorn
    from web.app import app
    uvicorn.run(app, host="0.0.0.0", port=args.port)


def cmd_ctrader(args):
    print("[*] Initializing cTrader Open API Cloud Bridge...")
    from core.ctrader_bridge import CTraderBridge
    simulate = getattr(args, 'simulate', False)
    bridge = CTraderBridge.get_instance(simulation=simulate) if simulate else CTraderBridge.get_instance()
    if not bridge.connect():
        raise CommandUnavailable(f"Failed to connect to cTrader Open API: {bridge.last_error or 'see log'}")
    telemetry = bridge.get_account_telemetry()
    tag = " [SIMULATED - no broker]" if telemetry.get("simulated") else ""
    print(f"[+] cTrader Connected{tag}")
    print(f"    - Broker Environment : {telemetry['broker']} ({telemetry['environment']})")
    print(f"    - Account ID         : {telemetry['account_id']}")
    print(f"    - Equity / Balance   : {telemetry['equity']} / {telemetry['balance']} {telemetry['currency']}")
    print(f"    - Active Positions   : {telemetry['total_open_positions']}")

    if getattr(args, 'test', False):
        if not telemetry.get("simulated"):
            raise CommandUnavailable("--test only runs against the simulator; add --simulate.")
        print("\n[*] Exercising SIMULATED multi-bot order test (nothing is sent to a broker)...")
        o1 = bridge.send_order("XAUUSD", "BUY", 0.01, 2685.50, 2675.0, 2700.0, label="SAJIM_V1", comment="Test_V1")
        o2 = bridge.send_order("EURJPY", "SELL", 0.02, 162.35, 163.0, 161.0, label="SAJIM_V2_SURGE", comment="Test_V2_Surge")
        for o in (o1, o2):
            print(f"[+] {o.get('label')}: success={o.get('success')} ticket={o.get('ticket')} status={o.get('status')} simulated={o.get('simulated')}")
        if o1.get("success"):
            c1 = bridge.close_position(o1['ticket'], reason="Hummingbird_Harvest_Test", close_price=2688.0)
            if c1.get("success"):
                print(f"[+] Simulated close #{o1['ticket']} | PnL: {c1['deal']['profit']} USD | R: {c1['deal']['r_multiple']}")
        updated = bridge.get_account_telemetry()
        print(f"\n[+] Simulated equity: {updated['equity']} | Bot Breakdown: {updated['bot_breakdown']}")


def cmd_investor(args):
    print("[*] Generating Quantitative Investor Deck & Raw Math Audit...")
    from core.investor_reporting import InvestorReporting
    pkg = InvestorReporting.generate_investor_package(initial_capital=getattr(args, 'capital', 10000.0))
    print(InvestorReporting.render_executive_card(pkg))


def main():
    print_banner()

    try:
        from v2.safety import kill_switch_active, KILL_SWITCH_FILE, KILL_SWITCH_ENV
        if kill_switch_active():
            print(f"[!] GLOBAL KILL SWITCH ENGAGED ({KILL_SWITCH_FILE} or {KILL_SWITCH_ENV}=1): bots will NOT open new trades.\n")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Sajim Holdings — Master Quant Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # API Server parser
    p_api = subparsers.add_parser("api", help="Launch BEEP Commercial Gateway API & Verification Service")
    p_api.add_argument("--port", type=int, default=8080, help="Port to bind API server (default: 8080)")

    # Prop Firm Bot
    p_prop = subparsers.add_parser("propfirm", help="Run Prop Firm Challenge Bot (requires private BEEP vault)")
    p_prop.add_argument("--size", type=float, default=100000.0, help="Challenge initial balance / DD baseline (e.g. 50000, 100000)")
    p_prop.add_argument("--live", action="store_true", help="Execute real MT5 challenge orders (default: Dry Run)")

    # Flagship Sajim V1 Bot (MT5 only)
    p_v1 = subparsers.add_parser("v1", help="Run Flagship Sajim V1 Quantitative Production Engine (MT5)")
    p_v1.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_v1.add_argument("--interval", type=int, default=30, help="Scan interval in seconds (default: 30)")
    p_v1.add_argument("--risk", type=float, default=0.01, help="Base risk fraction per trade (default: 0.01 = 1.0%%)")
    p_v1.add_argument("--max-positions", type=int, default=3, help="Max concurrent open positions (default: 3)")
    p_v1.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: MT5_LOGIN / broker_config / active terminal account)")

    # Flagship Sajim V2 Bot (MT5 only)
    p_v2 = subparsers.add_parser("v2", help="Run Sajim V2 Edge-Driven Asymmetric Production Bot (MT5)")
    p_v2.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_v2.add_argument("--loop", action="store_true", help="Run continuous execution loop")
    p_v2.add_argument("--interval", type=int, default=15, help="Scan interval in seconds (default: 15)")
    p_v2.add_argument("--risk", type=float, default=0.012, help="Base risk fraction per asset (default: 0.012 = 1.2%%)")
    p_v2.add_argument("--max-positions", type=int, default=5, help="Max concurrent open positions (default: 5)")
    p_v2.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: Active Terminal Account)")

    # Dual Concurrency Runner (V1 + V2 Coexistence)
    p_dual = subparsers.add_parser("dual", help="Run Sajim V1 and V2 concurrently side-by-side on same terminal")
    p_dual.add_argument("--live", action="store_true", help="Execute real orders (default: Dry Run)")
    p_dual.add_argument("--once", action="store_true", help="Run single pass and exit (default: continuous loop)")
    p_dual.add_argument("--interval", type=int, default=15, help="Scan interval in seconds (default: 15)")
    p_dual.add_argument("--max-combined", type=int, default=12, help="Max combined open positions across V1 and V2 (default: 12)")
    p_dual.add_argument("--max-v1", type=int, default=6, help="Max concurrent open positions for V1 (default: 6)")
    p_dual.add_argument("--max-v2", type=int, default=6, help="Max concurrent open positions for V2 (default: 6)")
    p_dual.add_argument("--risk-v1", type=float, default=0.01, help="Base risk fraction for V1 per trade (default: 0.01 = 1.0%%)")
    p_dual.add_argument("--risk-v2", type=float, default=0.01, help="Base risk fraction for V2 per trade (default: 0.01 = 1.0%%)")
    p_dual.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: MT5_LOGIN / broker_config / active terminal account)")
    p_dual.add_argument("--broker", type=str, choices=["mt5", "ctrader"], default="mt5",
                        help="Execution backend (default: mt5). cTrader must be explicit; there is no automatic fallback.")

    # Edge Matrix Backtest
    p_edge = subparsers.add_parser("edge", help="Run Quantitative Edge Verification Matrix across all assets & TFs")
    p_edge.add_argument("--oos-split", type=float, default=0.3, help="Out-of-sample hold-out fraction (default: 0.3; 0 = in-sample only)")
    p_edge.add_argument("--bars", type=int, default=1500, help="Bars per front (default: 1500)")

    # Overnight Server (alias of v1)
    p_srv = subparsers.add_parser("server", help="Run Overnight Quant Server Daemon (alias of v1, MT5)")
    p_srv.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_srv.add_argument("--interval", type=int, default=30, help="Scan interval in seconds (default: 30)")
    p_srv.add_argument("--risk", type=float, default=0.01, help="Base risk fraction per trade (default: 0.01 = 1.0%%)")
    p_srv.add_argument("--max-positions", type=int, default=3, help="Max concurrent open positions (default: 3)")
    p_srv.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: MT5_LOGIN / broker_config / active terminal account)")

    # Matrix Scanner
    subparsers.add_parser("scanner", help="Run Cross-Asset Matrix Scanner (requires private BEEP modules)")

    # Backtester
    p_back = subparsers.add_parser("backtest", help="Run Quantitative Backtests (requires private BEEP modules)")
    p_back.add_argument("--test_id", type=str, default="001", choices=["001", "002", "003"], help="Test iteration ID")
    p_back.add_argument("--allow-synthetic", action="store_true",
                        help="Allow clearly-labelled SYNTHETIC data if real data cannot be fetched (default: fail)")

    # Test Suite
    subparsers.add_parser("test", help="Run End-to-End Test Suite")

    # Concierge AI
    subparsers.add_parser("concierge", help="Run 24/7 Telegram Community Concierge AI")

    # Daily Market Digest
    p_digest = subparsers.add_parser("digest", help="Generate & Publish Daily Market and Pair Health Digest")
    p_digest.add_argument("--no-broadcast", action="store_true", help="Calculate digest without publishing to Telegram")

    # Sajim Traders Web Terminal
    p_web = subparsers.add_parser("web", help="Launch Sajim Traders Institutional Web App Terminal")
    p_web.add_argument("--port", type=int, default=8080, help="Port to bind web server (default: 8080)")

    # cTrader Open API Bridge
    p_ct = subparsers.add_parser("ctrader", help="cTrader Open API bridge status (execution not implemented yet)")
    p_ct.add_argument("--simulate", action="store_true", help="Use the explicit offline simulator (results flagged simulated)")
    p_ct.add_argument("--test", action="store_true", help="Run a simulated multi-bot order test (requires --simulate)")

    # Investor Audit Deck
    p_inv = subparsers.add_parser("investor", help="Generate Quantitative Investor Deck & Raw Math Audit")
    p_inv.add_argument("--capital", type=float, default=10000.0, help="Starting capital base (default: 10000.0)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nQuick Start Examples:")
        print("  python run.py v1                    # Sajim V1 (dry run)")
        print("  python run.py v2 --loop             # Sajim V2 continuous loop (dry run)")
        print("  python run.py dual --once           # V1 + V2 single pass (dry run)")
        print("  python run.py propfirm --size 100000 # Prop Firm Challenge Bot (dry run)")
        print("  python run.py edge --oos-split 0.3  # Edge matrix with out-of-sample validation")
        print("  python run.py web                   # Launch Sajim Traders Web Terminal")
        print("  python run.py test                  # Run Full Verification Suite\n")
        print("  Kill switch: touch KILL_SWITCH (repo root) or export SAJIM_KILL_SWITCH=1\n")
        return

    commands = {
        "web": cmd_web,
        "ctrader": cmd_ctrader,
        "investor": cmd_investor,
        "dual": cmd_dual,
        "v2": cmd_v2,
        "edge": cmd_edge,
        "v1": cmd_v1,
        "server": cmd_server,
        "propfirm": cmd_propfirm,
        "concierge": cmd_concierge,
        "api": cmd_api,
        "test": cmd_test,
        "scanner": cmd_scanner,
        "backtest": cmd_backtest,
        "digest": cmd_digest,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn is None:
        print(f"[!] Unknown or unavailable command: {args.command}")
        sys.exit(1)

    try:
        cmd_fn(args)
    except ImportError as e:
        if _is_private_module_error(e):
            print(f"[!] '{args.command}' requires private BEEP modules (core/beep_*), not in this repo. ({e})")
        else:
            print(f"[!] '{args.command}' is unavailable: missing dependency ({e})")
        sys.exit(1)
    except CommandUnavailable as e:
        print(f"[!] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
