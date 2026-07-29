import sys, time
sys.path.insert(0, "/root/forex-grid")
import broker as brk

def spike_ticks(open_px, spike_high, close_px, pip_step=1):
    """Generate intra-bar ticks: open -> spike_high -> close."""
    ticks = []
    step = pip_step * 0.01
    # up swing
    pos = open_px
    while pos < spike_high - 0.001:
        pos = round(pos + step, 2)
        ticks.append(pos)
    # down swing to close
    while pos > close_px + 0.001:
        pos = round(pos - step, 2)
        ticks.append(pos)
    # final close
    ticks.append(round(close_px, 2))
    return ticks

def sim_spike(label, ticks, spread=20):
    brk.reset(5000.0)
    brk.MIN_SPACING = 2500
    brk.current_spacing = 2500
    brk.BASE_SPREAD = spread
    brk.COMMISSION = 0
    brk.expiry_bars = 99999
    brk.TIME_STOP_FRAC = 1.0
    brk.place_orders(5000.0)
    for tp in ticks:
        brk.tick_prices(tp - spread/200, tp + spread/200, time.time())
        brk.update_trade_ages(tp - spread/200, tp + spread/200, brk.current_atr)
    expired = sum(1 for h in brk.hit_log if "EXPIRY" in h.get("side",""))
    tps = sum(1 for h in brk.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    hedges = sum(1 for h in brk.hit_log if "HEDGE" in h.get("side",""))
    tot = round(sum(h["pnl"] for h in brk.hit_log), 2)
    print("%s: trades=%d tp=%d hedges=%d expired=%d net=$%.2f bal=$%.2f open=%d" % (
        label, len(brk.hit_log), tps, hedges, expired, tot, round(brk.balance,2), len(brk.trades)))
    return {"trades": len(brk.hit_log), "tp": tps, "hedges": hedges, "net": tot, "open": len(brk.trades)}

print("===== FLASH SPIKE + RECOVERY =====")
print()

# Scenario 1: spike up 5000p then back to open
t1 = spike_ticks(5000.0, 5050.0, 5000.0, pip_step=1)
sim_spike("5000p spike->open", t1)

# Scenario 2: spike up 5000p then back to 25p below (overshoot)
t2 = spike_ticks(5000.0, 5050.0, 4999.75, pip_step=1)
sim_spike("5000p spike->below", t2)

# Scenario 3: double spike (up-down-up)
t3_list = spike_ticks(5000.0, 5025.0, 4975.0, pip_step=1)
t3_list += spike_ticks(4975.0, 5025.0, 5000.0, pip_step=1)[1:]
sim_spike("double spike (up-down-up)", t3_list)

# Scenario 4: spike up 10000p (4 grid levels) then back
t4 = spike_ticks(5000.0, 5100.0, 5000.0, pip_step=1)
sim_spike("10000p spike->open (4 levels)", t4)

print()
print("FINDING:")
print("  Spike-and-return: grid buys+sells both sides, net should be $0 per pair")
print("  Residual risk: only if close != open after spike")
print("===== DONE =====")
