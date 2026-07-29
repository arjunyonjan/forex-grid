import sys, time, random
sys.path.insert(0, "/root/forex-grid")
import broker as brk

S = 0.001  # tiny spread so orders fire near grid levels

def tick(px):
    brk.tick_prices(px - S, px + S, time.time())

def summary(label):
    tps = sum(1 for h in brk.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    exp = sum(1 for h in brk.hit_log if "EXPIRY" in h.get("side",""))
    stops = sum(1 for h in brk.hit_log if "ATR-STOP" in h.get("side",""))
    tot = sum(h["pnl"] for h in brk.hit_log)
    print("  %s: trades=%d tp=%d exp=%d stops=%d net=$%.2f bal=$%.2f open=%d" % (
        label, len(brk.hit_log), tps, exp, stops, tot, brk.balance, len(brk.trades)))

def setup():
    brk.reset(5000.0)
    brk.MIN_SPACING = 2500
    brk.current_spacing = 2500
    brk.BASE_SPREAD = 0
    brk.expiry_bars = 99999
    brk.TIME_STOP_FRAC = 1.0
    brk.place_orders(5000.0)

print("===== EDGE CASES 7-15 =====\n")

print("--- #7 No TP (expiry only) ---")
setup()
brk.expiry_bars = 30
for i in range(200):
    drift = random.gauss(0, 0.3)
    pos = round(5000.0 + drift, 2)
    tick(pos)
    brk.update_trade_ages(pos - S, pos + S, brk.current_atr)
summary("no tp")

print("--- #8 Multi-Level Skip ---")
setup()
tick(5075.0)
summary("multi-level (3 levels)")

print("--- #9 TP Reversal ---")
setup()
for px in [5000.0, 5001.0, 5002.0, 5003.0, 5004.0, 5004.9, 5004.0, 5003.0]:
    tick(px)
summary("tp reversal")

print("--- #10 Consecutive Gaps ---")
setup()
for g in [5000.0, 5075.0, 5000.0, 5075.0, 5000.0, 5075.0]:
    tick(g)
summary("consec gaps")

print("--- #11 Vol Spike ---")
setup()
for i in range(0, 401, 10):
    px = round(5000.0 + i * 0.5, 2)
    tick(px)
for i in range(0, 401, 10):
    px = round(5200.0 - i * 0.5, 2)
    tick(px)
summary("vol spike")

print("--- #12 Zero Vol ---")
setup()
for i in range(1440):
    tick(5000.0)
summary("zero vol")

print("--- #13 Weekend Gap ---")
setup()
tick(5050.0)
summary("weekend gap 5000p")

print("--- #15 Negative Balance ---")
setup()
brk.MAX_POSITIONS = 999
tick(5100.0)
tick(5200.0)
tick(5300.0)
tick(5400.0)
tick(5500.0)
summary("neg bal test")
print("  balance=$%.2f (negative=%s)" % (brk.balance, brk.balance < 0))

print("\n===== DONE =====")
