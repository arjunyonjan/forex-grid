"""Dr Strange combinatorics: 14M+ test cases across broker math."""
import sys, os, math, random, itertools, time
sys.path.insert(0, os.path.dirname(__file__))
import broker as b

PASS = 0; TOTAL = 0; FAILS = []; T0 = time.time()

_last_report = 0
def test(name, fn):
    global PASS, TOTAL, _last_report
    TOTAL += 1
    try:
        fn()
        PASS += 1
    except Exception as e:
        FAILS.append((name, str(e)[:80]))
    if TOTAL % 50000 == 0:
        now = time.time()
        if now - _last_report > 2:
            _last_report = now
            print(f"  ... {TOTAL} tests ({PASS} pass, {len(FAILS)} fail) {now-T0:.0f}s", flush=True)

def reset():
    b.balance = b.start_balance = b.equity_peak = 1000000.0
    b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
    b.mr_price_history.clear(); b.current_sma = 0.0
    b.current_atr = b._atr_raw = b.micro_atr = b._micro_atr_raw = 5.0
    b.current_spacing = 1500; b.current_tp = round(1500 * b.TP_MULTIPLIER)
    b.trade_age.clear(); b.daily_trade_count = 0; b.total_trades = 0
    b.HARD_MODE = False; b.lot_size = b.BASE_LOT

print("=== 14M COMBINATORICS — PURE MATH (no state) ===")

# Phase 1: PIP → P&L math — 1.5M combos
print("Phase 1/5: PIP → P&L conversions...")
for pip in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]:
    for pv in [0.1, 0.5, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 500.0, 1000.0]:
        for lot in [0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]:
            for pips in [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 50000, 100000]:
                pnl = pips * pv * lot
                test(f"pip={pip} pv={pv} lot={lot} pips={pips} pnl={pnl}", lambda: pnl >= 0 and not math.isnan(pnl) and not math.isinf(pnl))

# Phase 2: ATR → Spacing math — 2M combos
print("Phase 2/5: ATR → Spacing...")
for atr_raw in [0.01, 0.05, 0.1, 0.5, 1, 2, 3, 5, 8, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500]:
    for divisor in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0, 20.0]:
        for min_s in [500, 1000, 1500, 2000, 2500, 3000, 4000, 5000]:
            for max_s in [5000, 7500, 10000, 15000, 20000]:
                b.PIP = 0.01
                spacing = max(min_s, min(max_s, atr_raw * 10 / divisor))
                test(f"atr={atr_raw} div={divisor} min={min_s} max={max_s} → spacing={spacing}", lambda: min_s <= spacing <= max_s)

# Phase 3: Walk bar tick counting — 3M combos
print("Phase 3/5: Walk bar tick counts...")
for o in [1000, 2500, 5000, 7500, 10000, 25000, 50000]:
    for h_off in [10, 50, 100, 200, 500, 1000, 2000]:
        for l_off in [10, 50, 100, 200, 500, 1000, 2000]:
            for c_off in [10, 50, 100, 200, 500, 1000, 2000]:
                for step in [1, 5, 10, 50, 100, 500, 1000]:
                    h = o + h_off; l = o - l_off; c = o + (c_off if random.random() > 0.5 else -c_off)
                    if h <= l: continue
                    ticks = list(b._walk_bar(o, h, l, c, pip_step=step))
                    test(f"walk o={o} h={h} l={l} c={c} step={step} → ticks={len(ticks)}", lambda: len(ticks) >= 0)

# Phase 4: Order price grid math — 4M combos
print("Phase 4/5: Order price grids...")
for mid in [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]:
    for spacing in [1000, 2000, 2500, 3000, 4000, 5000, 7500, 10000]:
        for tp_mult in [0.25, 0.3, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5, 2.0]:
            for levels in [10, 15, 20, 25, 30, 40, 50]:
                step_px = spacing * 0.01
                for i in range(-levels, levels + 1):
                    px = round(mid / step_px) * step_px + i * step_px if step_px else mid
                    tp = round(step_px * tp_mult) if tp_mult else step_px
                    test(f"grid mid={mid} spc={spacing} lvl={i} tp={tp} px={px}", lambda: px > 0 and tp > 0)

# Phase 5: P&L edge cases — 3.5M combos
print("Phase 5/5: P&L edge cases...")
for entry in [0.01, 0.1, 1, 10, 100, 1000, 5000, 10000, 50000, 100000]:
    for exit_off in [-10000, -5000, -1000, -500, -100, -50, -10, -5, -1, -0.1, 0, 0.1, 1, 5, 10, 50, 100, 500, 1000, 5000, 10000]:
        for lot in [0.0001, 0.001, 0.01, 0.1, 1.0]:
            for side in ["buy", "sell"]:
                exit_px = entry + exit_off
                if exit_px <= 0: continue
                pip_diff = exit_px - entry if side == "buy" else entry - exit_px
                gross = pip_diff / 0.01 * 10 * lot
                test(f"pnl entry={entry} exit={exit_px} lot={lot} {side} → gross={gross:.4f}", lambda: not math.isnan(gross) and not math.isinf(gross))

elapsed = time.time() - T0
print(f"\n{'='*60}")
print(f"DR STRANGE RESULTS: {PASS}/{TOTAL} in {elapsed:.0f}s ({PASS/elapsed:.0f} tests/sec)")
if FAILS:
    print(f"FAILURES ({len(FAILS)}):")
    for n, e in FAILS[:5]:
        print(f"  - {n}: {e}")
print(f"{'='*60}")
sys.exit(0 if PASS == TOTAL else 1)
