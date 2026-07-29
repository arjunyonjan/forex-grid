import sys, time, random
sys.path.insert(0, "/root/forex-grid")
import broker as brk

def gen_bars(n, start_price=5000.0, vol=50.0, trend=0.0):
    bars = []
    p = start_price
    for i in range(n):
        o = round(p, 2)
        drift = trend * 0.01 * (i + 1) + random.gauss(0, vol * 0.01 * 0.3)
        c = round(o + drift, 2)
        half = vol * 0.01 * random.uniform(0.5, 1.5)
        h = round(max(o, c) + half, 2)
        l = round(min(o, c) - half * 0.6, 2)
        bars.append((o, h, l, c))
        p = c
    return bars

def sim_bars(bars, expiry_val, lot=0.001):
    brk.reset(5000.0)
    brk.MIN_SPACING = 2500
    brk.current_spacing = 2500
    brk.BASE_SPREAD = 0
    brk.lot_size = lot
    brk.atr_source = "micro"
    brk.micro_atr_window = "1m"
    brk.expiry_bars = expiry_val
    brk.TIME_STOP_FRAC = 1.0
    brk.place_orders(5000.0)
    for o, h, l, c in bars:
        brk.feed_micro_bar(h, l, sim_tf_seconds=60)
        ticks = brk._walk_bar(o, h, l, c, pip_step=50)
        for tp in ticks:
            brk.tick_prices(tp - 1, tp + 1, time.time())
            brk.update_trade_ages(tp - 1, tp + 1, brk.current_atr)
    expired = sum(1 for h in brk.hit_log if "EXPIRY" in h.get("side", ""))
    tps = sum(1 for h in brk.hit_log if "TP-" in h.get("side", "") and h["pnl"] > 0)
    tot = round(sum(h["pnl"] for h in brk.hit_log), 2)
    return {"trades": len(brk.hit_log), "expired": expired, "tp": tps, "net": tot, "bal": round(brk.balance, 2), "open": len(brk.trades), "_log": brk.hit_log}

print("===== EXPIRY CASCADE =====")
random.seed(42)
bars = gen_bars(500, 5000.0, 30.0, 0.1)

ra = sim_bars(bars, 10)
print("A: expiry=10 bars (cascade)")
print("  trades=%d expired=%d tp=%d net=$%.2f bal=$%.2f open=%d" % (ra["trades"], ra["expired"], ra["tp"], ra["net"], ra["bal"], ra["open"]))

rb = sim_bars(bars, 500)
print("B: expiry=500 bars (mostly TP)")
print("  trades=%d expired=%d tp=%d net=$%.2f bal=$%.2f open=%d" % (rb["trades"], rb["expired"], rb["tp"], rb["net"], rb["bal"], rb["open"]))

rc = sim_bars(bars, 99999)
print("C: no expiry (TP only)")
print("  trades=%d expired=%d tp=%d net=$%.2f bal=$%.2f open=%d" % (rc["trades"], rc["expired"], rc["tp"], rc["net"], rc["bal"], rc["open"]))

print()
print("FINDING: expiry cascade impact = $%.2f" % (ra["net"] - rc["net"]))
if ra["expired"] > 0:
    print("  avg per expired: $%.2f" % (ra["net"] / ra["expired"]))

print()
print("=== HIT LOG (scenario A cascade, first 10) ===")
for h in ra["_log"][:10]:
    print("  %-12s pnl=%+.2f" % (h.get("side", "?"), h.get("pnl", 0)))
print("===== DONE =====")
