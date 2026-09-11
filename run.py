"""
========================================================================================
                      SAJIM HOLDINGS — MASTER QUANT RUNNER
                                   (run.py)
========================================================================================
Architect & Lead Quant: Jimmy Mathu
Operational Command Center:
  1. omniverse : Universal Quant Omniverse Engine (M5, M15, H1 across all assets)
  2. cent      : Live Quant Cent Executor ($4 to $10 Cent Flip compounding ladder)
  3. propfirm  : Prop Firm Challenge Bot ($50k, $100k, $200k DD-Preservation Engine)
  4. server    : Overnight Dedicated Quant Server Daemon (telemetry to overnight_status.json)
  5. scanner   : Real-Time Cross-Asset Institutional Matrix Scanner (20+ global fronts)
  6. milker    : Market Milker & Reverse-FOMO Account Flipper
  7. backtest  : Quantitative Backtesting Engine ($400 baseline simulations)
  8. test      : End-to-End System & API Verification Suite
========================================================================================
"""

import os
import sys
import argparse

# Bootstrap all project modules on sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
for p in (
    ROOT_DIR,
    os.path.join(ROOT_DIR, "core"),
    os.path.join(ROOT_DIR, "bots"),
    os.path.join(ROOT_DIR, "bots", "prop_firm"),
    os.path.join(ROOT_DIR, "vault"),
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


def cmd_omniverse(args):
    print("[*] Launching Sajim Omniverse Quant Engine...")
    from bots.sajim_omniverse_bot import SajimOmniverseQuant
    import MetaTrader5 as mt5
    bot = SajimOmniverseQuant(
        base_risk_fraction=args.risk,
        dry_run=not args.live,
    )
    if not bot.connect_broker():
        print("[!] Failed to initialize MT5 terminal.")
        return
    try:
        if args.loop:
            bot.run_continuous_loop(interval_seconds=args.interval)
        else:
            bot.execute_top_opportunity()
    finally:
        mt5.shutdown()


def cmd_cent(args):
    print("[*] Launching Live Quant Cent Executor...")
    from bots.live_quant_cent_executor import LiveQuantExecutor
    executor = LiveQuantExecutor(
        symbol=args.symbol,
        timeframe_label=args.timeframe,
        dry_run=not args.live,
        target_flips=args.flips,
    )
    executor.run()


def cmd_propfirm(args):
    print(f"[*] Launching Prop Firm Challenge Bot (Account Size: ${args.size:,.2f})...")
    from bots.prop_firm.prop_firm_challenge_bot import PropFirmChallengeBot
    bot = PropFirmChallengeBot(
        account_size=args.size,
        dry_run=not args.live,
    )
    if bot.connect():
        bot.run_single_iteration()


def cmd_v1(args):
    print("[*] Launching Sajim V1 Quant Engine...")
    from bots.sajim_server_overnight import SajimOvernightServer
    import MetaTrader5 as mt5
    server = SajimOvernightServer(
        scan_interval_seconds=getattr(args, 'interval', 30),
        max_concurrent_positions=getattr(args, 'max_positions', 34),
        base_risk_fraction=getattr(args, 'risk', 0.02),
        dry_run=not args.live,
    )
    target_acc = getattr(args, 'account', None)
    if server.connect(target_account=target_acc):
        try:
            server.run_forever()
        finally:
            mt5.shutdown()


def cmd_server(args):
    cmd_v1(args)


def cmd_v2(args):
    import time
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
        return

    interval = getattr(args, 'interval', 15)
    if getattr(args, 'loop', False):
        print(f"[+] Sajim V2 running in continuous loop (interval: {interval}s | dry_run: {not args.live})...")
        try:
            while True:
                bot.run_iteration()
                time.sleep(interval)
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
        base_risk_v1=getattr(args, 'risk_v1', 0.012),
        base_risk_v2=getattr(args, 'risk_v2', 0.012),
        dry_run=not args.live,
        target_account=getattr(args, 'account', None),
    )

    if orchestrator.connect():
        try:
            if getattr(args, 'once', False):
                print("[+] Executing single dual pass (V1 + V2)...")
                orchestrator.execute_dual_pass()
            else:
                orchestrator.run_continuous()
        except KeyboardInterrupt:
            print("\n[+] Dual Orchestrator stopped by operator.")
        finally:
            mt5.shutdown()


def cmd_edge(args):
    print("[*] Launching Quantitative Edge Verification Matrix...")
    import subprocess
    script = os.path.join(ROOT_DIR, "scripts", "run_edge_matrix_backtest.py")
    subprocess.run([sys.executable, script])


def cmd_scanner(args):
    print("[*] Launching Cross-Asset Real-Time Matrix Scanner (20+ Fronts)...")
    from core.beep_matrix_scanner import BeepMatrixScanner
    scanner = BeepMatrixScanner()
    scanner.scan_all_fronts()


def cmd_milker(args):
    print("[*] Launching Market Milker & Account Flipper...")
    from bots.market_milker import MarketMilkerEngine
    milker = MarketMilkerEngine(initial_balance=args.balance)
    print(f"[+] MarketMilkerEngine initialized with balance ${args.balance:.2f}")


def cmd_backtest(args):
    print("[*] Launching Quantitative Backtesting Harness...")
    from core.backtester import BeepBacktester, execute_test_001, execute_test_002, execute_test_003
    if args.test_id == "001":
        execute_test_001()
    elif args.test_id == "002":
        execute_test_002()
    elif args.test_id == "003":
        execute_test_003()
    else:
        print("[+] Running Baseline Test 001:")
        execute_test_001()


def cmd_test(args):
    print("[*] Running End-to-End System Verification Suite...")
    from tests.test_system import run_full_verification
    run_full_verification()


def cmd_api(args):
    print("[*] Launching BEEP Commercial Gateway API Server...")
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


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Sajim Holdings — Master Quant Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # API Server parser
    p_api = subparsers.add_parser("api", help="Launch BEEP Commercial Gateway API & Verification Service")
    p_api.add_argument("--port", type=int, default=8080, help="Port to bind API server (default: 8080)")

    # 1. Omniverse Bot
    p_omni = subparsers.add_parser("omniverse", help="Run Universal Omniverse Quant Bot")
    p_omni.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_omni.add_argument("--loop", action="store_true", help="Run continuous scanning loop")
    p_omni.add_argument("--interval", type=int, default=15, help="Scan interval in seconds (default: 15)")
    p_omni.add_argument("--risk", type=float, default=0.05, help="Risk fraction (default: 0.05)")

    # 2. Cent Executor
    p_cent = subparsers.add_parser("cent", help="Run Live Quant Cent Executor ($4 compounding)")
    p_cent.add_argument("--symbol", type=str, default="XAUUSD", help="Target symbol (default: XAUUSD)")
    p_cent.add_argument("--timeframe", type=str, default="M15", help="Timeframe (default: M15)")
    p_cent.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_cent.add_argument("--flips", type=int, default=3, help="Target compounding flips")

    # 3. Prop Firm Bot
    p_prop = subparsers.add_parser("propfirm", help="Run Prop Firm Challenge Bot ($50k-$200k)")
    p_prop.add_argument("--size", type=float, default=100000.0, help="Account size (e.g. 50000, 100000)")
    p_prop.add_argument("--live", action="store_true", help="Execute real MT5 challenge orders (default: Dry Run)")

    # 0. Flagship Sajim V1 Bot
    p_v1 = subparsers.add_parser("v1", help="Run Flagship Sajim V1 Quantitative Production Engine")
    p_v1.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_v1.add_argument("--interval", type=int, default=30, help="Scan interval in seconds (default: 30)")
    p_v1.add_argument("--risk", type=float, default=0.02, help="Base risk fraction per asset (default: 0.02 = 2.0%%)")
    p_v1.add_argument("--max-positions", type=int, default=34, help="Max concurrent open positions (default: 34)")
    p_v1.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: Active Terminal Account)")

    # 0B. Flagship Sajim V2 Bot (Edge-Driven, Asymmetric Payoff)
    p_v2 = subparsers.add_parser("v2", help="Run Sajim V2 Edge-Driven Asymmetric Production Bot")
    p_v2.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_v2.add_argument("--loop", action="store_true", help="Run continuous execution loop")
    p_v2.add_argument("--interval", type=int, default=15, help="Scan interval in seconds (default: 15)")
    p_v2.add_argument("--risk", type=float, default=0.012, help="Base risk fraction per asset (default: 0.012 = 1.2%%)")
    p_v2.add_argument("--max-positions", type=int, default=5, help="Max concurrent open positions (default: 5)")
    p_v2.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: Active Terminal Account)")

    # 0A. Flagship Sajim Dual Concurrency Runner (V1 + V2 Coexistence)
    p_dual = subparsers.add_parser("dual", help="Run Sajim V1 and V2 concurrently side-by-side on same terminal")
    p_dual.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_dual.add_argument("--once", action="store_true", help="Run single pass and exit (default: continuous loop)")
    p_dual.add_argument("--interval", type=int, default=15, help="Scan interval in seconds (default: 15)")
    p_dual.add_argument("--max-combined", type=int, default=12, help="Max combined open positions across V1 and V2 (default: 12)")
    p_dual.add_argument("--max-v1", type=int, default=6, help="Max concurrent open positions for V1 (default: 6)")
    p_dual.add_argument("--max-v2", type=int, default=6, help="Max concurrent open positions for V2 (default: 6)")
    p_dual.add_argument("--risk-v1", type=float, default=0.05, help="Base risk fraction for V1 per trade (default: 0.05 = 5.0%%)")
    p_dual.add_argument("--risk-v2", type=float, default=0.05, help="Base risk fraction for V2 per trade (default: 0.05 = 5.0%%)")
    p_dual.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: Active Terminal Account)")

    # 0C. Edge Matrix Backtest
    p_edge = subparsers.add_parser("edge", help="Run Quantitative Edge Verification Matrix across all assets & TFs")

    # 4. Overnight Server
    p_srv = subparsers.add_parser("server", help="Run Overnight Quant Server Daemon")
    p_srv.add_argument("--live", action="store_true", help="Execute real MT5 orders (default: Dry Run)")
    p_srv.add_argument("--interval", type=int, default=30, help="Scan interval in seconds (default: 30)")
    p_srv.add_argument("--risk", type=float, default=0.02, help="Base risk fraction per asset (default: 0.02 = 2.0%%)")
    p_srv.add_argument("--max-positions", type=int, default=34, help="Max concurrent open positions (default: 34)")
    p_srv.add_argument("--account", type=int, default=None, help="Target MT5 account login (default: Active Terminal Account)")

    # 5. Matrix Scanner
    p_scan = subparsers.add_parser("scanner", help="Run 20+ Global Cross-Asset Matrix Scanner")

    # 6. Market Milker
    p_milk = subparsers.add_parser("milker", help="Run Market Milker & Account Flipper Engine")
    p_milk.add_argument("--balance", type=float, default=400.0, help="Account balance (default: 400)")

    # 7. Backtester
    p_back = subparsers.add_parser("backtest", help="Run Quantitative Backtests")
    p_back.add_argument("--test_id", type=str, default="001", choices=["001", "002", "003"], help="Test iteration ID")

    # 8. Test Suite
    p_test = subparsers.add_parser("test", help="Run End-to-End Test Suite")

    # 9. Concierge AI
    p_concierge = subparsers.add_parser("concierge", help="Run 24/7 Telegram Community Concierge AI")

    # 10. Daily Market Digest
    p_digest = subparsers.add_parser("digest", help="Generate & Publish Daily Market and Pair Health Digest")
    p_digest.add_argument("--no-broadcast", action="store_true", help="Calculate digest without publishing to Telegram")

    # 11. Sajim Traders Web Terminal
    p_web = subparsers.add_parser("web", help="Launch Sajim Traders Institutional Web App Terminal")
    p_web.add_argument("--port", type=int, default=8080, help="Port to bind web server (default: 8080)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nQuick Start Examples:")
        print("  python run.py web                   # Launch Sajim Traders Web Terminal")
        print("  python run.py omniverse             # Run Omniverse Anomaly Scanner (Dry Run)")
        print("  python run.py cent --symbol XAUUSD  # Run Cent Flip Executor on Gold")
        print("  python run.py propfirm --size 100000 # Run Prop Firm Challenge Bot")
        print("  python run.py scanner               # Run Institutional Cross-Asset Matrix Scanner")
        print("  python run.py server                # Run Overnight Server Daemon")
        print("  python run.py digest                # Publish Daily Market & Pair Health Digest")
        print("  python run.py test                  # Run Full Verification Suite\n")
        return

    commands = {
        "web": cmd_web,
        "dual": cmd_dual,
        "v2": cmd_v2,
        "edge": cmd_edge,
        "v1": cmd_v1,
        "server": cmd_server,
        "concierge": cmd_concierge,
        "api": cmd_api,
        "test": cmd_test,
        "scanner": cmd_scanner,
        "backtest": cmd_backtest,
        "digest": cmd_digest,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        cmd_fn(args)


if __name__ == "__main__":
    main()
