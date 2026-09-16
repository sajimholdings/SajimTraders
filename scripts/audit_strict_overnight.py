import MetaTrader5 as mt5
from datetime import datetime
from collections import defaultdict
import os

headway_path = r"C:\Program Files\Headway MT5 Terminal\terminal64.exe"
if os.path.exists(headway_path):
    init_ok = mt5.initialize(path=headway_path, timeout=10000)
else:
    init_ok = mt5.initialize()

# Query strictly since 2026-09-09 21:57:00 (when task-2852 started)
d_from = datetime(2026, 9, 9, 21, 57, 0)
d_to = datetime.now()
deals = mt5.history_deals_get(d_from, d_to)

records = []
if deals:
    for d in deals:
        if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT) and d.magic == 888222:
            records.append({
                "ticket": d.ticket,
                "time": datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": d.symbol,
                "volume": d.volume,
                "profit": d.profit,
                "comment": d.comment
            })

print(f"=== STRICT OVERNIGHT RUN (After 21:57) ===")
print(f"Total Deals: {len(records)}")
if records:
    wins = [r for r in records if r['profit'] > 0]
    losses = [r for r in records if r['profit'] < 0]
    total_pnl = sum(r['profit'] for r in records)
    win_pnl = sum(r['profit'] for r in wins)
    loss_pnl = sum(r['profit'] for r in losses)
    avg_w = win_pnl / len(wins) if wins else 0
    avg_l = loss_pnl / len(losses) if losses else 0
    print(f"Wins: {len(wins)} ({(len(wins)/len(records))*100:.1f}%) | Loss: {len(losses)} ({(len(losses)/len(records))*100:.1f}%)")
    print(f"Net PnL: ${total_pnl:.2f} USD")
    print(f"Avg Win: +${avg_w:.2f} | Avg Loss: -${abs(avg_l):.2f}")

    by_sym = defaultdict(list)
    for r in records:
        by_sym[r['symbol']].append(r)
    for sym, s_recs in sorted(by_sym.items()):
        sw = [r for r in s_recs if r['profit'] > 0]
        sl = [r for r in s_recs if r['profit'] < 0]
        p = sum(r['profit'] for r in s_recs)
        print(f"  {sym:<12}: {len(sw)}W / {len(sl)}L ({(len(sw)/len(s_recs))*100:.0f}%) | Net: ${p:.2f}")

mt5.shutdown()
