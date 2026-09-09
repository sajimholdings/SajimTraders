"""Full MT5 history - ALL deals, wider time window, zero filters."""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import time

mt5.initialize()
acc = mt5.account_info()

# Use the widest possible window
start = datetime(2026, 9, 7, 0, 0, 0)
end = datetime(2026, 9, 9, 0, 0, 0)

deals = mt5.history_deals_get(start, end)
print(f"=== FULL DEAL HISTORY (all time) ===")
print(f"Total deals found: {len(deals) if deals else 0}")
print()

if deals:
    wins = []
    losses = []
    be_exits = []
    entries = []
    other = []
    
    for d in deals:
        entry_map = {0: "IN", 1: "OUT", 2: "INOUT", 3: "OUT_BY"}
        type_map = {0: "BUY", 1: "SELL", 2: "BAL", 3: "CREDIT", 4: "CHARGE", 5: "CORR", 6: "BONUS"}
        
        entry_str = entry_map.get(d.entry, str(d.entry))
        type_str = type_map.get(d.type, str(d.type))
        time_str = datetime.fromtimestamp(d.time).strftime("%H:%M:%S")
        
        if d.type == 2:  # Balance operation
            print(f"  [DEPOSIT] {time_str} +{d.profit:.2f} {acc.currency}")
            continue
            
        if d.entry == 0:  # Entry
            entries.append(d)
        elif d.entry == 1:  # Exit
            net = d.profit + d.swap
            if net > 0.05:
                wins.append(d)
                tag = "WIN "
            elif net < -0.05:
                losses.append(d)
                tag = "LOSS"
            else:
                be_exits.append(d)
                tag = "BE  "
            
            # Determine how it closed
            close_reason = d.comment if d.comment else "unknown"
            
            print(f"  [{tag}] {time_str} {d.symbol:<12} {type_str:<4} Vol:{d.volume:<5} "
                  f"Close@{d.price:<12} PnL:{d.profit:>+8.2f} Swap:{d.swap:>+6.2f} "
                  f"Net:{net:>+8.2f}  Reason: {close_reason}")
        else:
            other.append(d)
    
    print()
    print(f"=" * 80)
    print(f"  ENTRIES PLACED : {len(entries)}")
    print(f"  TRADES CLOSED  : {len(wins) + len(losses) + len(be_exits)}")
    print(f"    Wins         : {len(wins)}")
    print(f"    Losses       : {len(losses)}")
    print(f"    Break-Even   : {len(be_exits)}")
    print()
    
    if wins:
        total_wins = sum(d.profit + d.swap for d in wins)
        avg_win = total_wins / len(wins)
        print(f"  Total Win PnL  : {total_wins:+.2f} {acc.currency}")
        print(f"  Avg Win        : {avg_win:+.2f} {acc.currency}")
    
    if losses:
        total_losses = sum(d.profit + d.swap for d in losses)
        avg_loss = total_losses / len(losses)
        print(f"  Total Loss PnL : {total_losses:+.2f} {acc.currency}")
        print(f"  Avg Loss       : {avg_loss:+.2f} {acc.currency}")
    
    total_closed = len(wins) + len(losses)
    if total_closed > 0:
        wr = len(wins) / total_closed * 100
        net_pnl = sum(d.profit + d.swap for d in wins) + sum(d.profit + d.swap for d in losses)
        print()
        print(f"  WIN RATE       : {wr:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"  NET CLOSED PnL : {net_pnl:+.2f} {acc.currency}")
        
        if wins and losses:
            pf = abs(sum(d.profit for d in wins)) / abs(sum(d.profit for d in losses))
            print(f"  PROFIT FACTOR  : {pf:.2f}")
            
            avg_w = sum(d.profit for d in wins) / len(wins)
            avg_l = abs(sum(d.profit for d in losses)) / len(losses)
            print(f"  AVG W:L RATIO  : {avg_w/avg_l:.2f}:1")
            
            expectancy = (wr/100 * avg_w) - ((100-wr)/100 * avg_l)
            print(f"  EXPECTANCY/TRD : {expectancy:+.2f} {acc.currency}")
    
    print()
    print(f"  ACCOUNT BALANCE: {acc.balance:.2f} {acc.currency}")
    print(f"  ACCOUNT EQUITY : {acc.equity:.2f} {acc.currency}")
    print(f"  UNREALIZED PnL : {acc.profit:+.2f} {acc.currency}")
    print(f"  OPEN POSITIONS : {mt5.positions_total()}")
    print(f"=" * 80)

mt5.shutdown()
