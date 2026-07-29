import sys
sys.path.insert(0, "/root/forex-grid")
import broker as b

def sweep(pips, d, start=5000.0, spread=20):
    sign = 1 if d == "up" else -1
    total = pips * 0.01 * sign
    pos = start
    while (pos - start) * sign < total - 0.001:
        pos += 1 * 0.01 * sign
        b.tick_prices(pos - spread/200, pos + spread/200, None)
    return pos

def summary(phase):
    w = sum(1 for h in b.hit_log if h["pnl"] > 0)
    l = sum(1 for h in b.hit_log if h["pnl"] < 0)
    tp = sum(h["pnl"] for h in b.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    hl = sum(h["pnl"] for h in b.hit_log if "HEDGE" in h.get("side","") and h["pnl"] < 0)
    tot = round(sum(h["pnl"] for h in b.hit_log), 2)
    print(f"  [{phase}] trades={len(b.hit_log)} w/l={w}/{l} tp=${round(tp,2)} hedge=${round(abs(hl),2)} net=${tot} bal=${round(b.balance,2)}")

print("===== GAP + REVERSAL =====")
print("No spread/comm")
b.reset(5000.0)
b.MIN_SPACING = 2500
b.current_spacing = 2500
b.BASE_SPREAD = 0
b.COMMISSION = 0
b.place_orders(5000.0)
sweep(5000, "up")
summary("up")
sweep(5000, "down", 5050.0, 0)
summary("dn")
print()

print("With spread=20p comm=0.1")
b.reset(5000.0)
b.MIN_SPACING = 2500
b.current_spacing = 2500
b.BASE_SPREAD = 20
b.COMMISSION = 0.1
b.DYNAMIC_SPREAD = False
b.place_orders(5000.0)
sweep(5000, "up")
summary("up")
sweep(5000, "down", 5050.0, 20)
summary("dn")
print()

print("===== HIT LOG DETAIL (no cost) =====")
b.reset(5000.0)
b.MIN_SPACING = 2500
b.current_spacing = 2500
b.BASE_SPREAD = 0
b.COMMISSION = 0
b.place_orders(5000.0)
sweep(5000, "up")
sweep(5000, "down", 5050.0, 0)
print(f"Total trades: {len(b.hit_log)}")
for h in b.hit_log:
    print(f"  {h['side'][:10]:10s} pnl={h['pnl']:+.2f}  entry={h.get('entry','--')} exit={h.get('exit','--')}")
print("===== DONE =====")
