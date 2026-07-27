
import json, math, random, sys, time
from pathlib import Path
import broker as _b

BASEDIR = Path("/root/forex-grid")

def load_all_kf():
    sources = []
    for fname, res in [("gcf_1m.json",60),("gcf_15m.json",900),("gcf_1h.json",3600),("gcf_daily.json",86400)]:
        p = BASEDIR / fname
        if p.exists():
            data = json.loads(p.read_text())
            for d in data:
                d["res"] = res
            sources.extend(data)
    sources.sort(key=lambda x: (x["date"], x["res"]))
    seen = set()
    merged = []
    for d in sources:
        k = d["date"]
        if k not in seen:
            seen.add(k)
            merged.append(d)
    return merged

all_kf = load_all_kf()
kf_2022 = [k for k in all_kf if "2022" in k["date"][:10] and not (k["open"]==k["high"]==k["low"]==k["close"])]
print("Loaded %d keyframes for 2022" % len(kf_2022))

TEST_DAYS = [1, 3, 7, 14, 30, 60, 90, 180, 365, 999999]
results = []

for td in TEST_DAYS:
    _b.MAX_TRADE_DAYS = td
    _b.orders.clear()
    _b.trades.clear()
    _b.hit_log.clear()
    _b.closed_trades.clear()
    _b.price_history.clear()
    _b.balance = 1000000.0
    _b.start_balance = 1000000.0
    _b.daily_start_balance = 1000000.0
    _b.month_start_balance = 1000000.0
    _b.equity_peak = 1000000.0
    _b.daily_trade_count = 0
    _b.total_trades = 0
    _b.current_atr = 5.0
    _b.lot_size = _b.BASE_LOT
    _b.trading_halted = False
    _b.total_wins_cumulative = 0
    _b.total_losses_cumulative = 0
    _b.cumulative_win_pnl = 0.0
    _b.cumulative_loss_pnl = 0.0

    t0 = time.time()
    result = _b.simulate_from_keyframes(kf_2022, init_bal=1000000.0, spacing=200, tick_scale=240)
    elapsed = time.time() - t0

    timeout_count = sum(1 for h in _b.hit_log if h.get("side","") == "TIMEOUT")
    tp_count = sum(1 for h in _b.hit_log if h.get("side","").startswith("TP"))
    pnl = result.get("total_pnl",0)
    ret = result.get("return_pct",0)
    trades = result.get("total_trades",0)
    wins = result.get("wins",0)
    losses = result.get("losses",0)
    dd = result.get("max_dd",0)

    print("  MTD=%6d: P&L=%+.2f  ret=%+.2f%%  tr=%d  w=%d  l=%d  TP=%d  TO=%d  DD=%.1f%%  (%.1fs)" % (
        td, pnl, ret, trades, wins, losses, tp_count, timeout_count, dd, elapsed))
    results.append((td, pnl, ret, trades, wins, losses, tp_count, timeout_count, dd))

print()
hdr = "DAYS  | P&L             | RET%        | TRADES  WINS  LOSS   TP   TO | DD%%"
print(hdr)
print("-" * len(hdr))
for td, pnl, ret, trades, wins, losses, tp, to, dd in results:
    print("%5d  $%+10.2f  %+7.2f%% | %6d  %4d  %4d  %4d  %4d | %.1f%%" % (
        td, pnl, ret, trades, wins, losses, tp, to, dd))

best = max(results, key=lambda r: r[1])
best_rr = max(results, key=lambda r: r[1] / max(r[8], 0.1))
print()
print("Best by P&L:       MTD=%d, P&L=$%.2f, DD=%.1f%%" % (best[0], best[1], best[8]))
print("Best ret/risk:     MTD=%d, P&L=$%.2f, DD=%.1f%%, ratio=%.1f" % (
    best_rr[0], best_rr[1], best_rr[8], best_rr[1]/max(best_rr[8],0.1)))
