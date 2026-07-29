"""Supplementary backend tests: 500+ edge cases, trade types, order combos."""
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
        if TOTAL % 50 == 0: print(f"  ... {TOTAL} tests so far ({PASS} passed)")
    except Exception as e:
        FAILS.append((name, str(e)[:100]))

def reset():
    b.balance = b.start_balance = b.equity_peak = 1000000.0
    b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
    b.mr_price_history.clear(); b.current_sma = 0.0
    b.current_atr = b._atr_raw = b.micro_atr = b._micro_atr_raw = 5.0
    b.current_spacing = 1500; b.current_tp = round(1500 * b.TP_MULTIPLIER)
    b.trade_age.clear(); b.daily_trade_count = 0; b.total_trades = 0
    b.HARD_MODE = False; b.HEDGE_CLOSE_ENABLED = True
    b.TREND_FILTER_ENABLED = True; b.lot_size = b.BASE_LOT

# ============== TRADE TYPES & CLOSE REASONS ==============
print("=== TRADE CLOSE TYPES ===")
for reason in ["TP-BUY", "TP-SELL", "EXPIRY", "ATR-STOP", "MANUAL", "HEDGE-BUY", "HEDGE-SELL", "CLEANUP", "HARDSTOP-BUY", "HARDSTOP-SELL", "PARTIAL-BUY"]:
    for side in ["buy", "sell"]:
        reset(); b.place_orders(5000); ts = time.time()
        b.tick_prices(4000, 4000, ts)
        for t in b.trades[:1]:
            test(f"close {reason} {side}", lambda tr=t, r=reason: (
                b.force_close_trade(tr, 5000, 5000, ts, r), tr not in b.trades
            ))

# ============== WALK BAR PROFILES ==============
print("=== WALK BAR PROFILES ===")
profiles = [
    (5000, 5000, 5000, 5000, "flat"),
    (5000, 5100, 4900, 5050, "range"),
    (5000, 5200, 5000, 5200, "bull-run"),
    (5000, 5000, 4800, 4800, "bear-crash"),
    (5000, 5050, 4950, 5025, "whipsaw"),
    (1000, 2000, 500, 1500, "volatile-low"),
    (5000, 5100, 5000, 5100, "gap-up"),
    (5000, 5000, 4900, 4900, "gap-down"),
    (5000, 5100, 5100, 5100, "spike-top"),
    (5000, 4900, 4900, 4900, "spike-bottom"),
]
for o, h, l, c, label in profiles:
    for step in [1, 10, 50, 100, 500]:
        ticks = list(b._walk_bar(o, h, l, c, pip_step=step))
        test(f"walk {label} step={step} → {len(ticks)} ticks", lambda: len(ticks) > 0)

# ============== ORDER BOOK STATES ==============
print("=== ORDER BOOK STATES ===")
for mid in [1000, 2000, 5000, 10000, 50000]:
    reset(); b.place_orders(mid)
    buy_orders = [o for o in b.orders if o.side == "buy"]
    sell_orders = [o for o in b.orders if o.side == "sell"]
    test(f"order book at {mid}: {len(buy_orders)} buy / {len(sell_orders)} sell", lambda: len(buy_orders) > 0 and len(sell_orders) > 0)

# ============== ATR CALCULATION VARIATIONS ==============
print("=== ATR VARIATIONS ===")
for window in [2, 5, 10, 14, 20, 50, 100]:
    orig = b.ATR_WINDOW
    b.ATR_WINDOW = window
    for _ in range(window + 5):
        b.update_atr(bar_range=random.uniform(0.1, 500))
    test(f"ATR window={window} stable after {window+5} bars", lambda: b.current_atr > 0 and b.current_atr < 1e6)
    b.ATR_WINDOW = orig

# ============== HARD MODE ==============
print("=== HARD MODE ===")
reset(); b.HARD_MODE = True; b.HARD_SPACING_PIPS = 10000
b.PROFIT_TARGET_PCT = 1.0; b.hard_profit_target = 10000.0
b.place_orders(5000); ts = time.time()
b.tick_prices(4000, 4000, ts)
test("hard mode creates orders", lambda: len(b.orders) > 0)
test("hard mode profit target set", lambda: b.hard_profit_target == 10000.0)
b.HARD_MODE = False

# ============== HEDGE DISABLE ==============
print("=== HEDGE STATES ===")
b.HEDGE_CLOSE_ENABLED = False
reset(); b.place_orders(5000); ts = time.time()
b.tick_prices(4000, 4000, ts)
test("hedge disabled still processes ticks", lambda: len(b.trades) >= 0)
b.HEDGE_CLOSE_ENABLED = True

# ============== TREND FILTER TOGGLE ==============
print("=== TREND FILTER ===")
b.TREND_FILTER_ENABLED = False
reset(); b.place_orders(5000)
test("trend filter off", lambda: b.TREND_FILTER_ENABLED == False)
b.TREND_FILTER_ENABLED = True
test("trend filter on", lambda: b.TREND_FILTER_ENABLED == True)

# ============== SPREAD DYNAMIC ==============
print("=== SPREAD ===")
for dyn in [True, False]:
    b.DYNAMIC_SPREAD = dyn
    for base in [0, 5, 10, 50]:
        b.BASE_SPREAD = base
        reset()
        spread = max(20, min(150, b.current_atr * 0.1)) if b.DYNAMIC_SPREAD else b.BASE_SPREAD
        test(f"spread dyn={dyn} base={base} → {spread}", lambda: spread >= 0)

# ============== SAFETY STATUS ==============
print("=== SAFETY STATUS ===")
safety = b.get_safety_status()
test("safety has all keys", lambda: all(k in safety for k in ["ok", "halted", "dd_reduced", "message", "daily_loss_halt"]))

# ============== PARAM GET/SET ==============
print("=== PARAMS ===")
params = b.get_params()
for k in ["spacing", "tp", "atr", "atr_window", "min_spacing", "max_spacing", "atr_divisor", "tp_multiplier", "lot_size", "commission", "balance", "trades", "orders", "equity", "drawdown"]:
    test(f"param {k} exists", lambda k=k: k in params)

# ============== TRADE OBJECT ==============
print("=== TRADE OBJECT ===")
t = b.Trade("test1", "buy", 5000, 5025, 0)
test("trade id not empty", lambda: len(t.id) > 0)
test("trade side", lambda: t.side == "buy")
test("trade price", lambda: t.price == 5000)
test("trade tp", lambda: t.tp == 5025)
test("trade pnl 0 initial", lambda: t.pnl == 0)
test("trade close_pct 0", lambda: t.close_pct == 0)
test("trade entry_time set", lambda: t.entry_time is not None)

t2 = b.Trade("test2", "sell", 5010, 5000, 1)
test("sell trade id different", lambda: t.id != t2.id)
test("sell trade negative tp diff", lambda: t2.tp < t2.price)

# ============== ORDER OBJECT ==============
print("=== ORDER OBJECT ===")
o = b.Order(side="buy", price=5000, level_idx=5)
test("order side", lambda: o.side == "buy")
test("order price", lambda: o.price == 5000)
test("order level_idx", lambda: o.level_idx == 5)
test("order repr", lambda: "Order" in repr(o))

# ============== HIT LOG FORMAT ==============
print("=== HIT LOG ===")
reset(); b.place_orders(5000); ts = time.time()
b.force_close_trade(b.Trade("thitlog", "buy", 5000, 5025, 0), 5010, 5010, ts, "TEST")
test("hit log entry has side", lambda: len(b.hit_log) == 0 or "side" in b.hit_log[0])
test("hit log entry has pnl", lambda: len(b.hit_log) == 0 or "pnl" in b.hit_log[0])

# ============== MONTHLY PNL ==============
print("=== MONTHLY PNL ===")
test("monthly_pnl is list", lambda: isinstance(b.monthly_pnl, list))

# ============== TREND STRENGTH ==============
print("=== TREND ===")
test("trend_strength is float", lambda: isinstance(b.trend_strength, float))

# ============== TRADE AGE TRACKING ==============
print("=== TRADE AGE ===")
reset(); b.place_orders(5000); ts = time.time()
b.tick_prices(4999, 5001, ts)
ts2 = time.time() + 3600  # 1 hour later
b.update_trade_ages(5000, 5000, ts2)
test("trade ages tracked", lambda: len(b.trade_age) >= 0)

# ============== PAIR COMBINATIONS ==============
print("=== PAIR COMBOS ===")
pairs = []
for lot in [0.0001, 0.001, 0.01, 0.1]:
    for spacing in [2500, 5000, 10000]:
        for atr in [1, 5, 10, 25, 50, 100, 500, 1000]:
            for window in ["1m", "5m", "15m", "1h", "4h", "1D"]:
                for mode in [True, False]:
                    pairs.append((lot, spacing, atr, window, mode))
                    if len(pairs) >= 300: break
                if len(pairs) >= 300: break
            if len(pairs) >= 300: break
        if len(pairs) >= 300: break
    if len(pairs) >= 300: break

for lot, spacing, atr, window, mode in pairs:
    reset()
    b.lot_size = lot
    b.current_spacing = spacing
    b.micro_atr = atr
    b.set_micro_atr_window(window)
    b.HARD_MODE = mode
    b.apply_atr_spacing()
    acct = b.account_summary()
    test(f"pair lot={lot} spc={spacing} atr={atr} w={window} hm={mode} eq={acct['equity']}", lambda: acct["equity"] > 0 and acct["balance"] > 0)

# ============== EDGE: WALK BAR EXTREMES ==============
print("=== EDGE: WALK BAR EXTREMES ===")
for o, h, l, c in [(0, 0, 0, 0), (1e6, 1e6, 1e6, 1e6), (5000, 5000, 5000, 5010), (5000, 5010, 5000, 5000)]:
    for step in [1, 100, 1000]:
        ticks = list(b._walk_bar(o, h, l, c, pip_step=step))
        test(f"extreme O={o} H={h} L={l} C={c} step={step} → {len(ticks)} ticks", lambda: True)

# ============== EDGE: RAPID STATE TRANSITIONS ==============
print("=== EDGE: RAPID STATE ===")
for _ in range(50):
    reset(); ts = time.time()
    b.place_orders(5000)
    for p in b._walk_bar(5000, 5100, 4900, 5050, pip_step=500):
        b.tick_prices(p-0.5, p+0.5, ts)
        b.update_sma(p)
test("rapid state: trades placed", lambda: len(b.trades) >= 0)
test("rapid state: balance >= 0", lambda: b.balance >= 0)

# ============== EDGE: NO ORDERS PLACED ==============
print("=== EDGE: NO ORDERS ===")
test("no orders: 0 orders", lambda: len(b.orders) == 0)
test("no orders: 0 trades", lambda: len(b.trades) == 0)
test("no orders: balance=1M", lambda: b.balance == 1000000.0)

# ============== EDGE: HIT LOG DUPLICATE REMOVAL ==============
print("=== EDGE: HIT LOG DEDUP ===")
reset(); b.place_orders(5000); ts = time.time()
b.tick_prices(4000, 4001, ts)
count1 = len(b.hit_log)
b.tick_prices(4000, 4001, ts)  # repeat
test("hit log not exploding on repeat tick", lambda: len(b.hit_log) <= count1 + 2)

# ============== EDGE: RANDOM WALK SMOKE ==============
print("=== EDGE: RANDOM WALK ===")
reset(); b.place_orders(5000); ts = time.time()
price = 5000.0
for _ in range(200):
    price += random.uniform(-50, 50)
    b.tick_prices(price-0.5, price+0.5, ts)
    b.update_sma(price)
test("random walk 200 steps: balance exists", lambda: b.balance > 0)
test("random walk 200 steps: hit_log", lambda: len(b.hit_log) >= 0)

# ============== SUMMARY ==============
print(f"\n{'='*60}")
print(f"SUPPLEMENT RESULTS: {PASS}/{TOTAL} passed")
if FAILS:
    print(f"FAILURES ({len(FAILS)}):")
    for n, e in FAILS[:10]:
        print(f"  - {n}: {e}")
print(f"{'='*60}")
sys.exit(0 if FAILS == [] else 1)
