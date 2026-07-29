import sys, time
sys.path.insert(0, "/root/forex-grid")
import broker as brk

print("--- #14 Full Ticks (pip_step=1) ---")
brk.reset(5000.0)
brk.MIN_SPACING = 2500; brk.current_spacing = 2500; brk.BASE_SPREAD = 0
brk.expiry_bars = 99999
brk.place_orders(5000.0)

# sweep up 5000p at pip_step=1 (full tick-by-tick)
pos = 5000.0
while pos < 5050.0:
    pos = round(pos + 0.01, 2)
    brk.tick_prices(pos - 0.001, pos + 0.001, time.time())

tps = sum(1 for h in brk.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
hedges = sum(1 for h in brk.hit_log if "HEDGE" in h.get("side",""))
tot = sum(h["pnl"] for h in brk.hit_log)
print("  full ticks: trades=%d tp=%d hedges=%d net=$%.2f open=%d" % (
    len(brk.hit_log), tps, hedges, tot, len(brk.trades)))

# compare with pip_step=50 (coarse)
print("--- (comparison: pip_step=50 coarse) ---")
brk.reset(5000.0)
brk.MIN_SPACING = 2500; brk.current_spacing = 2500; brk.BASE_SPREAD = 0
brk.expiry_bars = 99999
brk.place_orders(5000.0)
pos = 5000.0
while pos < 5050.0:
    pos = round(pos + 0.5, 2)
    brk.tick_prices(pos - 0.001, pos + 0.001, time.time())
tps2 = sum(1 for h in brk.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
tot2 = sum(h["pnl"] for h in brk.hit_log)
print("  coarse ticks: trades=%d tp=%d net=$%.2f open=%d" % (
    len(brk.hit_log), tps2, tot2, len(brk.trades)))
print()
print("FINDING: full tick overshoot = $%.2f vs coarse = $%.2f" % (tot, tot2))
print("===== DONE =====")
