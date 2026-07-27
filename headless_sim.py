import json, time, sys
sys.path.insert(0, "/root/forex-grid")
import broker as b

with open("/root/forex-grid/gcf_5m.json") as f:
    raw = json.load(f)
kf = raw if isinstance(raw, list) else raw.get("data", raw)
kf = [x for x in kf if x["date"] >= "2026-01-15" and x["date"] < "2026-02-15"]

b.balance = b.start_balance = b.equity_peak = 1000000.0
b.current_atr = b._atr_raw = 5.0
b.current_spacing = 1500
b.current_tp = round(b.current_spacing * b.TP_MULTIPLIER)
b.mr_price_history.clear(); b.current_sma = 0.0
b.trades.clear(); b.orders.clear(); b.hit_log.clear(); b.closed_trades.clear()
b.place_orders(kf[0]["open"])

PIP = b.PIP; t0 = time.time()

for idx, bar in enumerate(kf):
    o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
    bar_range = max(h - l, 0.1)
    b.update_atr(bar_range=bar_range)
    spread = max(20, min(150, b.current_atr * 0.1)) if b.DYNAMIC_SPREAD else b.BASE_SPREAD
    ts = __import__("datetime").datetime.strptime(bar["date"][:16], "%Y-%m-%d %H:%M")

    # Walk bar with 1000pip steps = 0-2 ticks per bar (fast)
    for mid_p in b._walk_bar(o, h, l, c, pip_step=1000):
        bid = mid_p - spread/2; ask = mid_p + spread/2
        b.update_sma(mid_p)
        b.tick_prices(bid, ask, ts)

    if idx % 500 == 0:
        sys.stdout.write(f"\r  Bar {idx}/{len(kf)} trades={len(b.trades)} pos={len([t for t in b.trades if t.pnl<0])}loss ")
        sys.stdout.flush()

t1 = time.time()
acct = b.account_summary()
wins = sum(1 for h in b.hit_log if h.get("pnl",0) > 0)
losses = sum(1 for h in b.hit_log if h.get("pnl",0) < 0)
won = sum(h["pnl"] for h in b.hit_log if h["pnl"] > 0)
lost = sum(h["pnl"] for h in b.hit_log if h["pnl"] < 0)
expc = sum(1 for h in b.hit_log if "HARDSTOP" in h.get("side","") or "EXPCLOSE" in h.get("side",""))
tpw = sum(1 for h in b.hit_log if "TP-" in h.get("side",""))

print(f"\n{'='*50}")
print(f"  Bars: {len(kf)}  Trades: {acct['total_trades']}")
print(f"  W/L: {wins}/{losses}", end="")
if wins+losses: print(f" ({100*wins/(wins+losses):.1f}%)", end="")
print()
if wins+losses:
    net = won+lost; pf = abs(won/lost) if lost else float("inf")
    print(f"  P&L: +${won:.2f} / -${lost:.2f} = ${net:.2f}  PF: {pf:.2f}")
print(f"  TP: {tpw}  Expired: {expc}  Ret: {acct['return_pct']:.2f}%  DD: {acct['drawdown']:.1f}%")
print(f"  ATR:{b.current_atr:.0f} Sp:{b.current_spacing} TP:{b.current_tp} SMA:{b.current_sma:.1f}")
print(f"  Wall: {t1-t0:.1f}s")
print(f"{'='*50}")
