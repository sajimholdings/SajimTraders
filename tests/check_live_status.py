"""Quick snapshot of live account, open positions, and closed deals."""
import MetaTrader5 as mt5
from datetime import datetime, timedelta

mt5.initialize()
acc = mt5.account_info()
print("=" * 80)
print("                    SAJIM HOLDINGS — LIVE STATUS SNAPSHOT")
print("=" * 80)
print(f"  Account  : {acc.login} ({acc.server})")
print(f"  Holder   : {acc.name}")
print(f"  Balance  : {acc.balance:.2f} {acc.currency}")
print(f"  Equity   : {acc.equity:.2f} {acc.currency}")
print(f"  Profit   : {acc.profit:+.2f} {acc.currency}")
print(f"  Margin   : {acc.margin:.2f} {acc.currency}")
print(f"  Free Mrg : {acc.margin_free:.2f} {acc.currency}")
print(f"  Leverage : 1:{acc.leverage}")
print()

positions = mt5.positions_get()
if positions:
    bot_pos = [p for p in positions if p.magic == 777999]
    other_pos = [p for p in positions if p.magic != 777999]

    print(f"  === BOT POSITIONS (magic=777999): {len(bot_pos)} ===")
    total_profit = 0.0
    for p in bot_pos:
        total_profit += p.profit
        direction = "BUY" if p.type == 0 else "SELL"
        print(f"    #{p.ticket}  {p.symbol:<10} {direction:<4} Vol:{p.volume:<5} "
              f"Open:{p.price_open:<10} Cur:{p.price_current:<10} "
              f"SL:{p.sl:<10} TP:{p.tp:<10} PnL:{p.profit:+.2f} {acc.currency}")
    print()
    print(f"    Total Bot Positions : {len(bot_pos)}")
    print(f"    Total Unrealized PnL: {total_profit:+.2f} {acc.currency}")
    if other_pos:
        print(f"\n  === OTHER POSITIONS: {len(other_pos)} ===")
        for p in other_pos:
            direction = "BUY" if p.type == 0 else "SELL"
            print(f"    #{p.ticket}  {p.symbol:<10} {direction:<4} PnL:{p.profit:+.2f}")
else:
    print("  No open positions.")

# Closed deals
deals = mt5.history_deals_get(datetime.now() - timedelta(hours=8), datetime.now())
if deals:
    closed = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT and d.magic == 777999]
    if closed:
        print()
        print(f"  === CLOSED DEALS (Last 8h): {len(closed)} ===")
        wins = []
        losses = []
        be_exits = []
        for d in closed:
            net = d.profit + d.swap
            if net > 0.05:
                wins.append(d)
                tag = "WIN"
            elif net < -0.05:
                losses.append(d)
                tag = "LOSS"
            else:
                be_exits.append(d)
                tag = "BE"
            print(f"    #{d.ticket}  {d.symbol:<10} [{tag:<4}] PnL:{d.profit:+.2f}  Swap:{d.swap:+.2f}  Net:{net:+.2f}")
        net_closed = sum(d.profit + d.swap for d in closed)
        print()
        print(f"    Wins: {len(wins)} | Losses: {len(losses)} | BE: {len(be_exits)}")
        print(f"    Net Closed PnL: {net_closed:+.2f} {acc.currency}")
        if wins or losses:
            wr = len(wins) / max(1, len(wins) + len(losses)) * 100
            print(f"    Win Rate: {wr:.1f}%")
    else:
        print("\n  No closed bot deals in last 8 hours.")

print("=" * 80)
mt5.shutdown()
