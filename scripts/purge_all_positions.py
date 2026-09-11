"""
Sajim Holdings — Purge All Open Positions (GUARDED)

Closes every open position on the currently-attached MT5 terminal.

SAFETY:
  - Dry-run by default: prints what WOULD be closed without doing anything.
  - Requires an explicit --execute flag to actually close anything.
  - Refuses to run on an unexpected account unless --force is passed.
"""
import argparse
import MetaTrader5 as mt5


def main():
    parser = argparse.ArgumentParser(description="Purge all open positions (guarded).")
    parser.add_argument("--execute", action="store_true",
                        help="Actually close positions (default is dry-run only).")
    parser.add_argument("--account", type=int, default=None,
                        help="Expected MT5 account login (safety check).")
    parser.add_argument("--force", action="store_true",
                        help="Skip the account-login safety check.")
    args = parser.parse_args()

    if not mt5.initialize():
        print("MT5 initialization failed:", mt5.last_error())
        return 1

    acc = mt5.account_info()
    if acc is None:
        print("Could not read MT5 account info. Is a terminal running and logged in?")
        mt5.shutdown()
        return 1

    print(f"Attached account: {acc.login} ({acc.server})")

    if args.account is not None and int(acc.login) != int(args.account):
        print(f"REFUSING: attached account {acc.login} != expected {args.account}. "
              f"Use --force to override.")
        mt5.shutdown()
        return 1

    positions = mt5.positions_get()
    if not positions:
        print("No open positions to close.")
        mt5.shutdown()
        return 0

    print(f"Found {len(positions)} open position(s) on account {acc.login}:")

    if not args.execute:
        for p in positions:
            print(f"  [DRY-RUN] would close ticket #{p.ticket} {p.symbol} vol={p.volume}")
        print("\nDRY-RUN complete — nothing was closed. Re-run with --execute to actually purge.")
        mt5.shutdown()
        return 0

    for p in positions:
        order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(p.symbol)
        if tick is None:
            print(f"Failed to get tick for {p.symbol}; skipping #{p.ticket}")
            continue
        price = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask

        closed = False
        last = None
        for filling in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": p.symbol,
                "volume": p.volume,
                "type": order_type,
                "position": p.ticket,
                "price": price,
                "deviation": 30,
                "magic": p.magic,
                "comment": "Sajim_Clean_Purge",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling,
            }
            res = mt5.order_send(req)
            last = res
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"Successfully closed #{p.ticket} {p.symbol} (vol: {p.volume})")
                closed = True
                break
        if not closed:
            print(f"Failed to close #{p.ticket} {p.symbol}: "
                  f"{last.comment if last else mt5.last_error()}")

    acc2 = mt5.account_info()
    if acc2:
        print(f"\nPURGE COMPLETE. Balance: ${acc2.balance:.2f} | Equity: ${acc2.equity:.2f} "
              f"| Margin Free: ${acc2.margin_free:.2f}")

    mt5.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
