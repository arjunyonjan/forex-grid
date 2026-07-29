import sys
sys.path.insert(0, "/root/forex-grid")
import broker as b

def sweep(pips_per_step, total_pips, d, start=5000.0):
    b.reset(start)
    b.MIN_SPACING = 2500
    b.current_spacing = 2500
    b.place_orders(start)
    ob = len(b.orders)
    sign = 1 if d == "up" else -1
    step = pips_per_step * 0.01 * sign
    total = total_pips * 0.01 * sign
    pos = start
    while (pos - start) * sign < total - 0.001:
        pos += step
        b.tick_prices(pos - 10, pos + 10, None)
    w = sum(1 for h in b.hit_log if h["pnl"] > 0)
    l = sum(1 for h in b.hit_log if h["pnl"] < 0)
    tot = round(sum(h["pnl"] for h in b.hit_log), 2)
    hl = sum(h["pnl"] for h in b.hit_log if "HEDGE" in h.get("side","") and h["pnl"] < 0)
    tp = sum(h["pnl"] for h in b.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    return {"w":w,"l":l,"tot":tot,"hl":round(abs(hl),2),"tp":round(tp,2),"trades":len(b.hit_log)}

print("===== GAP LEVEL-CROSSING TEST =====")
r1 = sweep(1, 2500, "up")
print(f"2500p sweep: trades={r1['trades']} w/l={r1['w']}/{r1['l']} tp=${r1['tp']} hedge=${r1['hl']} net=${r1['tot']}")
r2 = sweep(1, 5000, "up")
print(f"5000p sweep: trades={r2['trades']} w/l={r2['w']}/{r2['l']} tp=${r2['tp']} hedge=${r2['hl']} net=${r2['tot']}")
r3 = sweep(1, 7500, "up")
print(f"7500p sweep: trades={r3['trades']} w/l={r3['w']}/{r3['l']} tp=${r3['tp']} hedge=${r3['hl']} net=${r3['tot']}")
r4 = sweep(1, 2500, "down")
print(f"2500p down:  trades={r4['trades']} w/l={r4['w']}/{r4['l']} tp=${r4['tp']} hedge=${r4['hl']} net=${r4['tot']}")

# one-tick gap for comparison
b.reset(5000.0)
b.MIN_SPACING = 2500
b.current_spacing = 2500
b.place_orders(5000.0)
b.tick_prices(5075.0 - 10, 5075.0 + 10, None)
w2 = sum(1 for h in b.hit_log if h["pnl"] > 0)
l2 = sum(1 for h in b.hit_log if h["pnl"] < 0)
t2 = round(sum(h["pnl"] for h in b.hit_log), 2)
print(f"One-tick 7500p:   trades={len(b.hit_log)} w/l={w2}/{l2} net=${t2}")

print()
print("FINDING:")
print(f"  Swept 7500p: {r3['trades']} trades net=${r3['tot']}")
print(f"  One-tick:    {len(b.hit_log)} trades net=${t2}")
print(f"  Gap risk: multi-level hedge loss only if intermediate prices seen")
print("===== DONE =====")
