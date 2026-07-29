import sys, time
sys.path.insert(0, "/root/forex-grid")
import broker as brk

def run(label, atr_val, total_move_pips=10000):
    brk.reset(5000.0)
    brk.MIN_SPACING = 2500
    brk.micro_atr = atr_val
    brk.current_atr = atr_val
    brk.atr_source = "micro"
    brk.apply_atr_spacing()
    brk.place_orders(5000.0)
    target = 5000.0 + total_move_pips * 0.01
    pos = 5000.0
    while pos < target - 0.001:
        pos = round(pos + 1, 2)
        brk.tick_prices(pos - 1, pos + 1, time.time())
        brk.update_trade_ages(pos - 1, pos + 1, atr_val)
    tps = sum(1 for h in brk.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    exp = sum(1 for h in brk.hit_log if "EXPIRY" in h.get("side",""))
    stops = sum(1 for h in brk.hit_log if "ATR-STOP" in h.get("side",""))
    tot = sum(h["pnl"] for h in brk.hit_log)
    print("%s: spacing=%d tp=%d trades=%d tp=%d exp=%d stops=%d net=$%.2f" % (
        label, brk.current_spacing, brk.current_tp, len(brk.hit_log), tps, exp, stops, tot))

print("===== NEAR-ZERO ATR =====")
run("atr=0.1 (near zero)", 0.1)
run("atr=5.0 (normal)", 5.0)
run("atr=50.0 (high vol)", 50.0)
print()
print("FINDING: ATR_STOP_MULTIPLIER=%.1f, MIN_SPACING=%d sets floor" % (brk.ATR_STOP_MULTIPLIER, brk.MIN_SPACING))
print("===== DONE =====")
