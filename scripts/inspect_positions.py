import MetaTrader5 as mt5

import os

init_ok = mt5.initialize()
if not init_ok:
    headway_path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
    if os.path.exists(headway_path):
        init_ok = mt5.initialize(path=headway_path, timeout=10000)
    else:
        init_ok = mt5.initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe")

if not init_ok:
    print(f"MT5 init failed: {mt5.last_error()}")
    exit(1)

term = mt5.terminal_info()
acc = mt5.account_info()

print("================================================================================")
print("                       ACTIVE MT5 CONNECTION DIAGNOSTICS                        ")
print("================================================================================")
if term:
    print(f"  Terminal Path:      {term.path}")
    print(f"  Terminal Name:      {term.name} ({term.company})")
    print(f"  Connected:          {'[YES]' if term.connected else '[NO]'}")
    print(f"  AutoTrading Enabled:{'[YES] (Algo button is ON)' if term.trade_allowed else '[NO] (Algo button is OFF - click green button in toolbar!)'}")

if acc:
    print("\n  --- ACCOUNT CREDENTIALS & BALANCE ---")
    print(f"  Login / Account ID: {acc.login} ({acc.name})")
    print(f"  Broker Server:      {acc.server} ({acc.company})")
    print(f"  Currency:           {acc.currency}")
    print(f"  Balance:            ${acc.balance:.2f} {acc.currency}")
    print(f"  Equity:             ${acc.equity:.2f} {acc.currency}")
    print(f"  Free Margin:        ${acc.margin_free:.2f} {acc.currency}")
    print(f"  Margin Level:       {acc.margin_level:.1f}%" if acc.margin else "  Margin Level:       N/A (No margin used)")
    print(f"  Leverage:           1:{acc.leverage}")
    print(f"  Account Trading Allowed: {'[YES]' if acc.trade_allowed else '[NO]'}")
    print(f"  Expert Trading Allowed:  {'[YES]' if acc.trade_expert else '[NO]'}")

positions = mt5.positions_get()
print(f"\n  --- OPEN POSITIONS ({len(positions) if positions else 0}) ---")
if positions:
    for p in positions:
        direction = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        print(f"  • Ticket #{p.ticket} | {p.symbol} | {direction} {p.volume} lots @ {p.price_open} | Cur: {p.price_current} | SL: {p.sl} | TP: {p.tp} | PnL: ${p.profit:.2f} | '{p.comment}'")
else:
    print("  No open positions.")
print("================================================================================")

mt5.shutdown()
