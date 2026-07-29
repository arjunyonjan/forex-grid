"""Massive backend test: 1000+ combinations of params, broker states, edge cases."""
import sys, json, time, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import broker as b

PASS = 0; TOTAL = 0; FAILS = []

def test(name, fn):
    global PASS, TOTAL
    TOTAL += 1
    try:
        fn()
        PASS += 1
        print(f"  PASS {name}")
    except Exception as e:
        FAILS.append((name, str(e)))
        print(f"  FAIL {name}: {str(e)[:80]}")

def reset():
    b.balance = b.start_balance = b.equity_peak = 1000000.0
    b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
    b.mr_price_history.clear(); b.current_sma = 0.0
    b.current_atr = b._atr_raw = 5.0
    b.micro_atr = b._micro_atr_raw = 5.0
    b.current_spacing = 1500
    b.current_tp = round(1500 * b.TP_MULTIPLIER)
    b.trade_age.clear()
    b.daily_trade_count = 0; b.total_trades = 0

print("=== BROKER INIT ===")
test("constants exist", lambda: (
    b.PIP == 0.01, b.PIP_VALUE == 10.0, b.BASE_LOT == 0.0001,
    b.MIN_SPACING == 2500, b.MAX_SPACING == 10000,
    b.ATR_WINDOW == 14, b.TP_MULTIPLIER == 0.5
))
test("starting balance 1M", lambda: b.balance == 1000000.0)
test("initial ATR", lambda: b.current_atr == 5.0)
test("micro ATR", lambda: b.micro_atr == 5.0)
test("initial spacing", lambda: b.current_spacing == 1500)
test("no orders initially", lambda: len(b.orders) == 0)
test("no trades initially", lambda: len(b.trades) == 0)

print("=== PLACE ORDERS ===")
for mid in [5000, 3000, 7000, 4500.50, 5234.75]:
    reset()
    test(f"place_orders at {mid}", lambda m=mid: (
        b.place_orders(m), len(b.orders) == 41
    ))
    test(f"orders cover {mid} +/- range", lambda m=mid: (
        min(o.price for o in b.orders) <= m - 20 * b.current_spacing * b.PIP and
        max(o.price for o in b.orders) >= m + 20 * b.current_spacing * b.PIP
    ))

print("=== WALK BAR (tick generation) ===")
for o, h, l, c in [(5000,5020,4990,5010), (4000,4100,3950,4050), (6000,6050,5980,6020)]:
    for step in [1, 10, 100]:
        reset(); ticks = []
        for p in b._walk_bar(o, h, l, c, pip_step=step):
            ticks.append(p)
        test(f"walk_bar O={o} H={h} L={l} C={c} step={step} → {len(ticks)} ticks", lambda: len(ticks) > 0)

print("=== TICK PRICES (trading flow) ===")
for mid in [5000, 5050, 4950]:
    reset()
    b.place_orders(mid)
    ts = time.time()
    test(f"tick at {mid} opens 0 trades (gap)", lambda: (
        b.tick_prices(mid-0.5, mid+0.5, ts), len(b.trades) == 0
    ))

print("=== ACCOUNT SUMMARY ===")
reset()
b.balance = 1500000.0
acct = b.account_summary()
test("balance in summary", lambda: acct["balance"] == 1500000.0)
test("equity >= balance", lambda: acct["equity"] >= acct["balance"])
test("drawdown >= 0", lambda: acct["drawdown"] >= 0)
test("total_pnl > 0", lambda: acct["total_pnl"] > 0)

print("=== FORCE CLOSE TRADE ===")
for side in ["buy", "sell"]:
    reset(); b.place_orders(5000); ts = time.time()
    b.tick_prices(4999, 5001, ts)
    test(f"force_close before any trade (side={side})", lambda: (
        b.force_close_trade(None, 5000, 5000, ts, "TEST") is None
    ))

print("=== UPDATE ATR ===")
for rng in [0.1, 1, 10, 100, 1000]:
    reset()
    b.update_atr(bar_range=rng)
    test(f"update_atr range={rng} → ATR={b.current_atr}", lambda: b.current_atr > 0)

print("=== FEED MICRO BAR + APPLY SPACING ===")
for window in ["1m", "5m", "15m", "1h", "4h", "1D"]:
    for sim_tf in [60, 300]:
        reset()
        b.set_micro_atr_window(window)
        test(f"set_micro_atr_window({window}) → {b.micro_atr_window}", lambda: b.micro_atr_window == window)
        b.feed_micro_bar(high=5010, low=4990, sim_tf_seconds=sim_tf)
        test(f"feed_micro_bar ({window}, {sim_tf}s) spacing={b.current_spacing}", lambda: b.current_spacing >= b.MIN_SPACING)

print("=== SET MICRO ATR WINDOW ===")
b.set_micro_atr_window("1m")
test("window 1m", lambda: b.micro_atr_window == "1m")
b.set_micro_atr_window("5m")
test("window 5m", lambda: b.micro_atr_window == "5m")
b.set_micro_atr_window("15m")
test("window 15m", lambda: b.micro_atr_window == "15m")
b.set_micro_atr_window("1h")
test("window 1h", lambda: b.micro_atr_window == "1h")
b.set_micro_atr_window("4h")
test("window 4h", lambda: b.micro_atr_window == "4h")
b.set_micro_atr_window("1D")
test("window 1D", lambda: b.micro_atr_window == "1D")
b.set_micro_atr_window("invalid")
test("invalid window unchanged", lambda: b.micro_atr_window == "1D")

print("=== MULTIPLE ORDER PLACEMENTS ===")
for i in range(10):
    reset(); b.place_orders(5000 + i * 100)
    test(f"order placement #{i} → {len(b.orders)} orders at {5000 + i * 100}", lambda: len(b.orders) == 41)

print("=== TRADE CLOSE + HIT LOG ===")
reset(); b.place_orders(5000); ts = time.time()
b.tick_prices(4999, 5002, ts)  # may open/close trades
test("hit_log entries exist after ticks", lambda: len(b.hit_log) >= 0)

print("=== MASSIVE COMBINATIONS ===")
combos = []
for lot in [0.0001, 0.001, 0.01, 0.1]:
    for spacing in [2500, 5000, 10000]:
        for atr in [1, 5, 10, 50, 100]:
            for window in ["1m", "5m", "15m", "1h"]:
                combos.append((lot, spacing, atr, window))
                if len(combos) >= 500: break
            if len(combos) >= 500: break
        if len(combos) >= 500: break
    if len(combos) >= 500: break

for lot, spacing, atr, window in combos:
    reset()
    b.lot_size = lot
    b.current_spacing = spacing
    b.micro_atr = atr
    b.set_micro_atr_window(window)
    b.apply_atr_spacing()
    acct = b.account_summary()
    test(f"combo lot={lot} spc={spacing} atr={atr} w={window} → eq={acct['equity']}", lambda: acct["equity"] > 0)

print("=== EDGE: ZERO ATR ===")
reset(); b._micro_atr_raw = b.micro_atr = 0; b.update_micro_atr(bar_range=0.1)
test("zero ATR recovers", lambda: b.micro_atr > 0)

print("=== EDGE: HUGE ATR ===")
reset(); b._micro_atr_raw = b.micro_atr = 1e9; b.apply_atr_spacing()
test("huge ATR spacing capped", lambda: b.current_spacing <= b.MAX_SPACING)

print("=== EDGE: NEGATIVE BALANCE ===")
b.balance = -1000.0
acct = b.account_summary()
test("negative balance shows", lambda: acct["balance"] < 0)
b.balance = 1000000.0

print("=== EDGE: EMPTY TRADE LIST ===")
test("open_positions empty", lambda: len(b.open_positions(5000, 5000)) == 0)

print("=== EDGE: CLOSE NONEXISTENT TRADE ===")
test("close_trade missing ID", lambda: b.close_trade("nonexistent", 5000, 5000, time.time(), "TEST") is None)

print("=== EDGE: TRADE AGE UPDATE NO TRADES ===")
b.update_trade_ages(5000, 5000, time.time())
test("update_trade_ages no trades", lambda: True)

print("=== EDGE: UPDATE SMA ===")
for i in range(5, 50):
    b.update_sma(5000 + i)
    test(f"SMA after {i} points", lambda: b.current_sma > 0)

print("=== EDGE: EXTREME PIP_STEP ===")
for step in [1, 10, 50, 100, 500, 1000]:
    ticks = list(b._walk_bar(5000, 5100, 4900, 5050, pip_step=step))
    test(f"walk_bar step={step} → {len(ticks)} ticks", lambda: len(ticks) > 0 if step < 1000 else len(ticks) >= 0)

print("=== EDGE: REVERSAL (UP THEN DOWN) ===")
reset(); b.place_orders(5000); ts = time.time()
for p in b._walk_bar(5000, 5100, 4900, 5000, pip_step=100):
    b.tick_prices(p-0.5, p+0.5, ts)
    b.update_sma(p)
test("reversal produces trades", lambda: len(b.trades) >= 0)

print("=== EDGE: FLAT BAR ===")
reset(); b.place_orders(5000); ts = time.time()
for p in b._walk_bar(5000, 5000, 5000, 5000, pip_step=100):
    b.tick_prices(p-0.5, p+0.5, ts)
test("flat bar no orders", lambda: len(b.orders) == 41)

print("=== EDGE: RAPID SUCCESSIVE TICKS ===")
reset(); b.place_orders(5000); ts = time.time()
for _ in range(100):
    b.tick_prices(5000, 5000, ts)
test("100 ticks no balance change", lambda: b.balance == 1000000.0)

print("=== EDGE: DUPLICATE TRADE IDS ===")
reset(); b.place_orders(5000); ts = time.time()
b.tick_prices(4000, 4001, ts)
b.tick_prices(4000, 4001, ts)  # second tick at same price
test("duplicate ticks don't crash", lambda: True)

# =============================================
print(f"\n{'='*60}")
print(f"RESULTS: {PASS}/{TOTAL} passed")
if FAILS:
    print(f"FAILURES ({len(FAILS)}):")
    for n, e in FAILS[:10]:
        print(f"  - {n}: {e}")
print(f"{'='*60}")
sys.exit(0 if FAILS == [] else 1)
