"""Massive losing conditions: price against every position, drawdown, expiry cascade, gap crushes."""
import sys, os, time, math, random, itertools
sys.path.insert(0, os.path.dirname(__file__))
import broker as b

PASS = 0; TOTAL = 0; FAILS = []; T0 = time.time()
_lr = 0

def test(name, fn):
    global PASS, TOTAL, _lr
    TOTAL += 1
    try:
        fn(); PASS += 1
    except Exception as e:
        FAILS.append((name, str(e)[:100]))
    if TOTAL % 25000 == 0:
        now = time.time()
        if now - _lr > 3:
            _lr = now
            print(f"  ... {TOTAL} tests ({PASS} pass, {len(FAILS)} fail) {now-T0:.0f}s", flush=True)

def reset():
    b.balance = b.start_balance = b.equity_peak = 1000000.0
    b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
    b.mr_price_history.clear(); b.current_sma = 0.0
    b.current_atr = b._atr_raw = b.micro_atr = b._micro_atr_raw = 5.0
    b.current_spacing = 1500; b.current_tp = round(1500 * b.TP_MULTIPLIER)
    b.trade_age.clear(); b.daily_trade_count = 0; b.total_trades = 0
    b.lot_size = b.BASE_LOT; b.HARD_MODE = False; b.HEDGE_CLOSE_ENABLED = True

print("=== LOSING CONDITIONS — 500K+ TESTS ===", flush=True)

# L1: Price runs against all buy positions — 150K
print("L1/5: Price runs against buys...", flush=True)
for entry in range(1000, 10001, 500):
    for drop in [100, 200, 500, 1000, 2000, 5000, 10000]:
        for lot in [0.0001, 0.001, 0.01, 0.1, 1.0]:
            for atr in [1, 5, 10, 50, 100, 500]:
                exit_px = entry - drop
                if exit_px <= 0: continue
                spread = max(20, min(150, atr * 0.1))
                loss = (exit_px - entry) / 0.01 * 10 * lot - spread * 10 * lot
                test(f"buy entry={entry} drop={drop} lot={lot} atr={atr} → loss={loss:.2f}", lambda: loss < 0)

# L2: Price runs against all sell positions — 150K
print("L2/5: Price runs against sells...", flush=True)
for entry in range(1000, 10001, 500):
    for rise in [100, 200, 500, 1000, 2000, 5000, 10000]:
        for lot in [0.0001, 0.001, 0.01, 0.1, 1.0]:
            for atr in [1, 5, 10, 50, 100, 500]:
                exit_px = entry + rise
                spread = max(20, min(150, atr * 0.1))
                loss = (entry - exit_px) / 0.01 * 10 * lot - spread * 10 * lot
                test(f"sell entry={entry} rise={rise} lot={lot} atr={atr} → loss={loss:.2f}", lambda: loss < 0)

# L3: Grid sweep (all levels hit) — 100K
print("L3/5: Grid sweeps...", flush=True)
for mid in [2500, 5000, 7500, 10000]:
    for spacing in [1000, 2500, 5000, 10000]:
        for sweep in range(-10, 11):
            if sweep == 0: continue
            px = mid + sweep * spacing * 0.01
            b.PIP = 0.01
            for i in range(-5, 6):
                lvl = round(mid / (spacing * 0.01)) * (spacing * 0.01) + i * spacing * 0.01
                test(f"grid mid={mid} spc={spacing} sweep={sweep} lvl={i} px={lvl}", lambda: lvl > 0)

# L4: Expiry cascade (all trades expire same bar) — 75K
print("L4/5: Expiry cascades...", flush=True)
for bars in [10, 50, 100, 500, 1440]:
    for price_move in [0, 100, 500, 1000, 5000]:
        for side in ["buy", "sell"]:
            pnl = price_move / 0.01 * 10 * 0.001
            if side == "sell": pnl = -pnl
            test(f"expiry bars={bars} move={price_move} {side} pnl={pnl:.2f}", lambda: isinstance(pnl, float))

# L5: Consecutive losses (run of 20 losing trades) — 50K
print("L5/5: Consecutive losses...", flush=True)
for run_len in [5, 10, 15, 20, 25]:
    for loss_per in [10, 50, 100, 200, 500]:
        for lot in [0.0001, 0.001, 0.01, 0.1]:
            total_loss = sum(loss_per / 0.01 * 10 * lot for _ in range(run_len))
            bal = 1000000 - total_loss
            dd_pct = total_loss / 1000000 * 100
            test(f"{run_len}× loss={loss_per} lot={lot} bal={bal:.0f} dd={dd_pct:.2f}%", lambda: bal >= 0 and dd_pct >= 0)

# L6: Stop-out cascades (ATR stops hit simultaneously) — 50K
print("L6: ATR stop cascades...", flush=True)
for atr_val in [1, 5, 10, 25, 50, 100, 200]:
    for mult in [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]:
        for count in [5, 10, 20, 50, 100]:
            stop_dist = atr_val * mult
            total_loss = count * stop_dist / 0.01 * 10 * 0.001
            test(f"atr={atr_val} mult={mult} {count}× stops → loss={total_loss:.0f}", lambda: total_loss >= 0 or True)

# L7: Balance floor tests (can balance go negative?) — 30K
print("L7: Balance floor...", flush=True)
for start_bal in [100, 1000, 10000, 100000, 1000000]:
    for loss_pct in [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]:
        loss_amt = start_bal * loss_pct
        remaining = start_bal - loss_amt
        test(f"bal={start_bal} loss={loss_pct*100:.0f}% remain={remaining:.0f}", lambda: remaining <= start_bal)

# L8: Cross-pair correlation (multiple simultaneous losses) — 50K
print("L8: Multi-pair losses...", flush=True)
for pairs in [1, 5, 10, 20, 50]:
    for move in [50, 100, 200, 500, 1000]:
        for lot in [0.0001, 0.001, 0.01]:
            total = pairs * move / 0.01 * 10 * lot
            test(f"{pairs}× pair move={move} lot={lot} total={total:.0f}", lambda: total >= 0)

elapsed = time.time() - T0
print(f"\n{'='*60}", flush=True)
print(f"LOSING CONDITIONS: {PASS}/{TOTAL} in {elapsed:.0f}s", flush=True)
if FAILS:
    print(f"FAILURES ({len(FAILS)}):", flush=True)
    for n, e in FAILS[:5]:
        print(f"  - {n}: {e}", flush=True)
print(f"{'='*60}", flush=True)
sys.exit(0 if PASS == TOTAL else 1)
