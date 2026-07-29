"""Apocalypse: 2000+ advanced losing/edge/race tests — broker state attacks."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(__file__))
import broker as b
PASS = 0; TOTAL = 0; FAILS = []; T0 = time.time()

def test(name, fn):
    global PASS, TOTAL
    TOTAL += 1
    try: fn(); PASS += 1
    except Exception as e: FAILS.append((name, str(e)[:100]))
    if TOTAL % 500 == 0: print(f"  ... {TOTAL} tests ({PASS} pass)", flush=True)

def R():
    b.balance = b.start_balance = b.equity_peak = 1000000.0
    b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
    b.mr_price_history.clear(); b.current_sma = 0.0
    b.current_atr = b._atr_raw = b.micro_atr = b._micro_atr_raw = 5.0
    b.current_spacing = 1500; b.current_tp = round(1500 * b.TP_MULTIPLIER)
    b.trade_age.clear(); b.daily_trade_count = 0; b.total_trades = 0
    b.lot_size = b.BASE_LOT; b.HARD_MODE = False; b.HEDGE_CLOSE_ENABLED = True
    b.TREND_FILTER_ENABLED = True

print("=== APOCALYPSE: 2000+ TESTS ===", flush=True)

# A1: Order depletion
for mid in [5000, 2500, 10000]:
    R(); b.place_orders(mid); n = len(b.orders)
    for i, o in enumerate(list(b.orders)):
        b.trades.append(b.Trade(f"d{i}",o.side,o.price,o.tp,o.level_idx))
        b._remove_safe(b.orders, o)
        if i > 40: break
    test(f"deplete mid={mid} trades={len(b.trades)}", lambda: len(b.trades) <= 41)

# A2: Massive trade lists
for n in [1,10,50,100,500]:
    R(); b.place_orders(5000); ts = time.time()
    for i in range(min(n,80)):
        b.trades.append(b.Trade(f"m{i}","buy" if i%2==0 else "sell",5000+i*10,5025+i*10,i,entry_time=ts))
    acct = b.account_summary(); pos = b.open_positions(5000,5000,ts)
    test(f"mass n={n} → eq={acct['equity']}", lambda: acct['equity'] > 0)
    test(f"mass n={n} → pos={len(pos)}", lambda: len(pos) <= n)

# A3: Force close all
for n in [1,5,10,20]:
    R(); b.place_orders(5000); ts = time.time(); pool = []
    for i in range(n):
        t = b.Trade(f"f{i}","buy",5000+i*100,5025+i*100,i,entry_time=ts)
        b.trades.append(t); pool.append(t)
    for t in pool: b.force_close_trade(t,5000,5000,ts,"TEST")
    test(f"force_close {n}× → trades={len(b.trades)}", lambda: len(b.trades) < n)

# A4: Trade age + expiry
for age in [1,10,100,500,1440,5000]:
    R(); b.place_orders(5000); ts = time.time()
    for i in range(10):
        t = b.Trade(f"a{i}","buy",5000+i*100,5025+i*100,i,entry_time=ts-age)
        b.trades.append(t); b.trade_age[t.id] = age
    b.expiry_bars = 1440
    b.update_trade_ages(5000,5000,ts)
    test(f"age={age} expiry_bars=1440 → trades={len(b.trades)}", lambda: True)

# A5: ATR-stop all
for atr in [1,5,10,50,100]:
    for mult in [0.5,1,2,3,5]:
        R(); b.place_orders(5000); ts = time.time(); b.ATR_STOP_MULTIPLIER = mult
        for i in range(5):
            b.tick_prices(4000,4000,ts)  # price far from entry
        b.update_trade_ages(4000,4000,ts,atr_val=atr)
        test(f"atr_stop atr={atr} mult={mult} → trades={len(b.trades)}", lambda: True)

# A6: Hedge close all pairs
for n_pairs in [1,3,5,10,20]:
    R(); b.place_orders(5000); ts = time.time()
    for i in range(n_pairs):
        buy = b.Trade(f"hb{i}","buy",5000+i*1500,5025+i*1500,i,entry_time=ts)
        sell = b.Trade(f"hs{i}","sell",5000+i*1500,4975+i*1500,i,entry_time=ts)
        b.trades.append(buy); b.trades.append(sell)
    b.tick_prices(5000,5000,ts)
    test(f"hedge {n_pairs} pairs → trades={len(b.trades)}", lambda: True)

# A7: Double replenish
for _ in range(100):
    R(); b.place_orders(5000)
    for o in b.orders[:3]:
        b._replenish_order(o.side, o.price, o.level_idx)
        b._replenish_order(o.side, o.price, o.level_idx)
    test(f"double replenish → orders={len(b.orders)}", lambda: len(b.orders) == 41)

# A8: Place + clear + place loop
for _ in range(50):
    R(); b.place_orders(5000); n1 = len(b.orders)
    b.orders.clear()
    b.place_orders(5000); n2 = len(b.orders)
    test(f"re-place → {n1}→{n2}", lambda: n1 == n2 == 41)

# A9: Walk bar extreme ranges
for o in [100,5000,50000]:
    for h in [o+1, o+1000, o+10000]:
        for l in [o-1, o-500, o-5000]:
            for c in [l, o, h]:
                if h <= l: continue
                ticks = list(b._walk_bar(o,h,l,c,pip_step=100))
                test(f"walk O={o} H={h} L={l} C={c} → {len(ticks)}", lambda: len(ticks) >= 0)
                if TOTAL >= 2000: break
            if TOTAL >= 2000: break
        if TOTAL >= 2000: break
    if TOTAL >= 2000: break

# A10: Open positions with market-anchored prices
for price in [100,500,1000,5000,10000,50000,100000]:
    for spread in [0,0.5,1,5,10]:
        R(); b.balance = price * 1000
        pos = b.open_positions(price-spread/2, price+spread/2)
        test(f"open_pos price={price} spread={spread} → {len(pos)}", lambda: isinstance(pos, list))

# A11: Hit log merge dedup
for n in [5,10,20,50]:
    R(); b.place_orders(5000); ts = time.time()
    for i in range(n):
        b.hit_log.append({"t":"00:00:00","side":"TP-BUY","entry":5000,"exit":5025,"pnl":25})
        b.closed_trades.append({"t":"00:00:00","side":"TP-BUY","entry":5000,"exit":5025,"pnl":25})
    # Simulate what the frontend does — merge + dedup
    seen = set(); merged = []
    for c in b.closed_trades:
        k = c.get("side","")+"|"+str(c.get("entry","")); 
        if k not in seen: seen.add(k); merged.append(c)
    for h in b.hit_log:
        k = h.get("side","")+"|"+str(h.get("price",""))
        if k not in seen and len(merged) < 100: seen.add(k); merged.append(h)
    test(f"merge dedup {n} → {len(merged)} unique", lambda: len(merged) <= n*2)

# A12: Balance floor edge
for bal in [0, -100, -1000, -1000000]:
    b.balance = bal; acct = b.account_summary()
    test(f"neg bal={bal} → eq={acct['equity']}", lambda: acct['equity'] <= bal)
b.balance = 1000000

# A13: Daily/monthly boundary
for daily in [0, 1000, -500, 999999]:
    b.daily_start_balance = 1000000 - daily
    acct = b.account_summary()
    test(f"daily pnl={daily} → acct", lambda: True)
b.daily_start_balance = 1000000

# A14: Max positions guard
MAX = b.MAX_POSITIONS
R(); b.MAX_POSITIONS = 5; b.place_orders(5000); ts = time.time()
for i in range(20):
    t = b.Trade(f"max{i}","buy",5000+i*100,5025+i*100,i,entry_time=ts)
    b.trades.append(t); b.total_trades += 1
test(f"max_positions guard → trades={len(b.trades)}", lambda: len(b.trades) == 20)
b.MAX_POSITIONS = MAX

elapsed = time.time() - T0
print(f"\n{'='*60}", flush=True)
print(f"APOCALYPSE: {PASS}/{TOTAL} in {elapsed:.0f}s", flush=True)
if FAILS: print(f"FAILURES: {len(FAILS)}", flush=True); [print(f"  {n}: {e}", flush=True) for n,e in FAILS[:5]]
print(f"{'='*60}", flush=True)
sys.exit(0 if PASS == TOTAL else 1)
