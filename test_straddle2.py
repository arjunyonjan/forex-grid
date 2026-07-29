import sys
sys.path.insert(0, "/root/forex-grid")
import broker as b

b.reset(5000.0)
b.MIN_SPACING = 2500
b.current_spacing = 2500
b.current_tp = 2500
b.BASE_SPREAD = 0
b.COMMISSION = 0
b.DYNAMIC_SPREAD = False
b.place_orders(5000.0)

print("Orders at/around 5000:")
for o in b.orders:
    if abs(o.price - 5000.0) < 1:
        print(f"  {o.side} price={o.price} tp={o.tp}")

print(f"\nTotal orders: {len(b.orders)}")
print(f"current_spacing = {b.current_spacing}")
print(f"current_tp = {b.current_tp}")
print(f"step = {b.current_spacing * 0.01}")

print("\n--- tick_prices(5000.0, 5000.0) ---")
b.tick_prices(5000.0, 5000.0, None)
print(f"Trades after tick: {len(b.trades)}")
print(f"Hits after tick: {len(b.hit_log)}")
for t in b.trades:
    print(f"  Trade: {t.side} entry={t.price} tp={t.tp} id={t.id}")
for h in b.hit_log:
    print(f"  Hit: {h['side']} pnl={h.get('pnl',0)}")

print("\n--- tick_prices(5000.01, 5000.01) ---")
b.tick_prices(5000.01, 5000.01, None)
print(f"Trades: {len(b.trades)} Hits: {len(b.hit_log)}")

print("\n--- tick_prices(4999.99, 4999.99) ---")
b.tick_prices(4999.99, 4999.99, None)
print(f"Trades: {len(b.trades)} Hits: {len(b.hit_log)}")
print("===== DONE =====")
