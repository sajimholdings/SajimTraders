import MetaTrader5 as mt5
from datetime import datetime, timedelta
from collections import defaultdict
import os

headway_path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
if os.path.exists(headway_path):
    init_ok = mt5.initialize(path=headway_path, timeout=10000)
else:
    init_ok = mt5.initialize()

if not init_ok:
    print(f"MT5 init failed: {mt5.last_error()}")
    exit(1)

# Query deals since yesterday 20:00 (overnight run)
d_from = datetime.now() - timedelta(hours=14)
d_to = datetime.now() + timedelta(minutes=5)
deals = mt5.history_deals_get(d_from, d_to)

if not deals:
    print("No deals found in history.")
    mt5.shutdown()
    exit(0)

records = []
for d in deals:
    if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT) and d.magic == 888222:
        records.append({
            "ticket": d.ticket,
            "order": d.order,
            "position_id": d.position_id,
            "time": datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": d.symbol,
            "type": "SELL" if d.type == mt5.DEAL_TYPE_SELL else "BUY",
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "comment": d.comment
        })

print(f"=== OVERNIGHT SAJIM V2 AUDIT (Magic 888222) ===")
print(f"Total Closed Deals: {len(records)}")

if records:
    wins = [r for r in records if r['profit'] > 0]
    losses = [r for r in records if r['profit'] < 0]
    
    total_pnl = sum(r['profit'] for r in records)
    win_pnl = sum(r['profit'] for r in wins)
    loss_pnl = sum(r['profit'] for r in losses)
    
    avg_win = (win_pnl / len(wins)) if wins else 0
    avg_loss = (loss_pnl / len(losses)) if losses else 0
    win_rate = (len(wins) / len(records)) * 100
    ratio = abs(avg_loss / avg_win) if avg_win > 0 else 0

    print(f"Total Wins:   {len(wins)} ({win_rate:.1f}%) | Total Win PnL:   +${win_pnl:.2f} USD")
    print(f"Total Losses: {len(losses)} ({len(losses)/len(records)*100:.1f}%) | Total Loss PnL: -${abs(loss_pnl):.2f} USD")
    print(f"Net Realized PnL: ${total_pnl:.2f} USD")
    print(f"Average Win:  +${avg_win:.2f} USD")
    print(f"Average Loss: -${abs(avg_loss):.2f} USD")
    print(f"Realized Asymmetry (Win : Loss): 1 : {ratio:.2f} (Loss is {ratio:.2f}x bigger than Win!)")

    # Group by symbol
    by_sym = defaultdict(list)
    for r in records:
        by_sym[r['symbol']].append(r)

    print("\n--- PERFORMANCE BY SYMBOL ---")
    print(f"{'Symbol':<12} | {'Trades':<6} | {'Wins':<5} | {'Losses':<6} | {'WinRate%':<8} | {'Net PnL':<10} | {'Avg Win':<8} | {'Avg Loss':<8}")
    print("-" * 75)
    for sym, s_recs in sorted(by_sym.items()):
        s_wins = [r for r in s_recs if r['profit'] > 0]
        s_losses = [r for r in s_recs if r['profit'] < 0]
        s_pnl = sum(r['profit'] for r in s_recs)
        s_win_pnl = sum(r['profit'] for r in s_wins)
        s_loss_pnl = sum(r['profit'] for r in s_losses)
        s_avg_w = s_win_pnl / len(s_wins) if s_wins else 0
        s_avg_l = s_loss_pnl / len(s_losses) if s_losses else 0
        s_wr = (len(s_wins) / len(s_recs)) * 100
        print(f"{sym:<12} | {len(s_recs):<6} | {len(s_wins):<5} | {len(s_losses):<6} | {s_wr:>7.1f}% | ${s_pnl:>8.2f} | +${s_avg_w:>6.2f} | -${abs(s_avg_l):>6.2f}")

    print("\n--- EXIT REASONS (Comments) ---")
    by_cmt = defaultdict(list)
    for r in records:
        key = r['comment'].split('_')[0] if r['comment'] else "NO_COMMENT"
        by_cmt[key].append(r)
    for cmt, c_recs in sorted(by_cmt.items()):
        c_pnl = sum(r['profit'] for r in c_recs)
        c_wins = sum(1 for r in c_recs if r['profit'] > 0)
        c_losses = sum(1 for r in c_recs if r['profit'] < 0)
        print(f"Exit Type: {cmt:<20} | Total: {len(c_recs):<4} | Wins: {c_wins:<3} | Losses: {c_losses:<3} | Net PnL: ${c_pnl:>7.2f}")

mt5.shutdown()
