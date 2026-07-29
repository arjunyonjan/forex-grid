import sys
sys.path.insert(0, "/root/forex-grid")
import broker as b

def run(label, start, levels, spread=20, comm=0.1):
    b.reset(start)
    b.MIN_SPACING = 2500
    b.current_spacing = 2500
    b.BASE_SPREAD = spread
    b.COMMISSION = comm
    b.DYNAMIC_SPREAD = False
    b.place_orders(start)
    ob = len(b.orders)
    for p in levels:
        b.tick_prices(p - spread/200, p + spread/200, None)
    w = sum(1 for h in b.hit_log if h["pnl"] > 0)
    l = sum(1 for h in b.hit_log if h["pnl"] < 0)
    tp = sum(h["pnl"] for h in b.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    hl = sum(h["pnl"] for h in b.hit_log if "HEDGE" in h.get("side","") and h["pnl"] < 0)
    tot = round(sum(h["pnl"] for h in b.hit_log), 2)
    print(f"{label}: orders={ob} hits={len(b.hit_log)} w/l={w}/{l} tp=${round(tp,2)} hedge=${round(abs(hl),2)} net=${tot} bal=${round(b.balance,2)}")
    for h in b.hit_log:
        print(f"    {h['side'][:12]:12s} pnl={h['pnl']:+.2f} entry={h.get('entry','--')}")

print("===== STRADDLE OPEN =====")
print("Price opens exactly at grid level")
print()

# Grid levels at multiples of 25 (2500 pips spacing from 5000)
# So levels: ... 4975, 5000, 5025 ...
# If price = 5000.00 exactly, both the 4975 buy and 5025 sell orders fire
run("Straddle=5000.00 (exact level)", 5000.0, [5000.0], 0, 0)
print()

# Just below level
run("Just below=4999.99", 5000.0, [4999.99], 0, 0)
print()

# Just above level
run("Just above=5000.01", 5000.0, [5000.01], 0, 0)
print()

# Multiple straddles in a row (choppy at level)
b.reset(5000.0)
b.MIN_SPACING = 2500
b.BASE_SPREAD = 0
b.COMMISSION = 0
b.place_orders(5000.0)
for _ in range(5):
    b.tick_prices(5000.0, 5000.0, None)
w = sum(1 for h in b.hit_log if h["pnl"] > 0)
l = sum(1 for h in b.hit_log if h["pnl"] < 0)
tot = round(sum(h["pnl"] for h in b.hit_log), 2)
print(f"5x straddle at 5000: trades={len(b.hit_log)} w/l={w}/{l} net=${tot} bal=${round(b.balance,2)}")
for h in b.hit_log:
    print(f"    {h['side'][:12]:12s} pnl={h['pnl']:+.2f}")

print()
print("===== WITH SPREAD/COMM =====")
run("Straddle=5000 spread=20 comm=0.1", 5000.0, [5000.0], 20, 0.1)
print()

print("===== DONE =====")
