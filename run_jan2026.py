import broker as b, json, sys
from datetime import datetime, timedelta

def walk_bar(o, h, l, c, step=10):
    pts = []
    spread = h - l
    if spread < 0.01:
        return [o]
    mid = (h + l) / 2
    step_px = step * b.PIP
    n = max(2, int(spread / step_px))
    for i in range(n):
        frac = i / (n - 1)
        px = o + (c - o) * frac
        noise = (spread * 0.3) * (1 if hash(str(i)) % 2 == 0 else -1) * 0.5
        px = max(l, min(h, px + noise))
        pts.append(round(px, 2))
    return pts

with open('/root/forex-grid/micro_1m_2004-06-11_2026-07-24.json') as f:
    all_data = json.load(f)

start_d, end_d = '2026-01-02', '2026-01-31'
filtered = [d for d in all_data if start_d <= d["date"][:10] <= end_d]
if not filtered:
    print("NO DATA"); sys.exit(1)

bars = []
for i in range(0, len(filtered)-4, 5):
    grp = filtered[i:i+5]
    bars.append({"date": grp[-1]["date"], "o": grp[0]["open"],
        "h": max(x["high"] for x in grp), "l": min(x["low"] for x in grp),
        "c": grp[-1]["close"]})

print(f"Loaded {len(bars)} 5m bars")
print(f"Range: ${min(x['l'] for x in bars):.2f} - ${max(x['h'] for x in bars):.2f}")

b.balance = b.start_balance = b.equity_peak = 1000000.0
b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
b.mr_price_history.clear(); b.current_sma = 0.0
b.current_atr = b._atr_raw = 5.0
b.current_spacing = 2500
b.current_tp = round(2500 * b.TP_MULTIPLIER)
print(f"TP_MULT={b.TP_MULTIPLIER} spacing={b.current_spacing} tp={b.current_tp}")

b.place_orders(bars[0]["o"])

for idx, bar in enumerate(bars):
    o, h, l, c = bar["o"], bar["h"], bar["l"], bar["c"]
    b.update_atr(bar_range=max(h - l, 0.1))
    b.current_tp = round(b.current_spacing * b.TP_MULTIPLIER)
    b.place_orders(c)
    ticks = walk_bar(o, h, l, c, 10)
    for mid_p in ticks:
        b.tick_prices(mid_p, mid_p, datetime.fromisoformat(bar["date"].replace("Z","")))
    if (idx+1) % 500 == 0:
        eq = b.balance + sum(t.pnl for t in b.trades)
        print(f"  bar {idx+1}: bal=${b.balance:.2f} eq=${eq:.2f} trades={len(b.trades)} closed={len(b.closed_trades)} atr={b.current_atr:.0f}")

cw = [t for t in b.closed_trades if t["pnl"] > 0]
cl = [t for t in b.closed_trades if t["pnl"] < 0]
tp = sum(t["pnl"] for t in b.closed_trades)
print(f"\n=== JAN 2026 ({len(b.closed_trades)} trades) ===")
print(f"Balance: ${b.balance:.2f}  PnL: ${tp:.2f}")
print(f"Win: {len(cw)} ({len(cw)/max(len(b.closed_trades),1)*100:.0f}%) Loss: {len(cl)} ({len(cl)/max(len(b.closed_trades),1)*100:.0f}%)")
if cw: print(f"Win $: ${sum(t['pnl'] for t in cw):.2f}")
if cl: print(f"Loss $: ${sum(t['pnl'] for t in cl):.2f}")
print(f"Open: {len(b.trades)}  ATR: {b.current_atr:.0f}")
print(f"Hits ({len(b.hit_log)}):")
for h in b.hit_log[-30:]:
    s = h.get("side","?")
    p = h.get("pnl",0)
    if "TP" in s:
        print(f"  WIN {s} pnl=${p}")
    elif "HEDGE" in s or "CLOSE" in s or "CLEANUP" in s:
        print(f"  LOSS {s} pnl=${p}")
    else:
        print(f"  {s} pnl=${p}")
