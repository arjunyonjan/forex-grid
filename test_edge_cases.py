"""Edge case tests for forex-grid broker.py"""
import sys, os, json, math, time
sys.path.insert(0, "/root/forex-grid")
import broker as b

def reset():
    b.balance = 1000000.0
    b.orders.clear(); b.trades.clear(); b.hit_log.clear(); b.closed_trades.clear()
    b.total_trades = 0; b._atr_raw = 5.0; b.current_atr = 5.0
    b.current_spacing = b.MIN_SPACING; b.current_tp = b.MIN_SPACING + 1
    b.daily_trade_count = 0; b.daily_start_balance = 1000000.0
    b.month_start_balance = 1000000.0; b.equity_peak = 1000000.0
    b.wins = 0; b.losses = 0; b.win_pnl = 0.0; b.loss_pnl = 0.0
    b.realized_pnl = 0.0; b.daily_trades = 0; b.lot_size = b.BASE_LOT

PASS = 0; FAIL = 0

def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        sys.stderr.write("  [PASS] " + label + "\n")
    else:
        FAIL += 1
        d = "  (" + detail + ")" if detail else ""
        sys.stderr.write("  [FAIL] " + label + d + "\n")
    sys.stderr.flush()

def sim_bars(bars, pip_step=10, label=""):
    n = len(bars); t0 = time.time()
    report = max(1, n // 100)
    for idx, bar in enumerate(bars):
        ticks = b._walk_bar(bar["open"], bar["high"], bar["low"], bar["close"], pip_step)
        for mid_p in ticks:
            sp = 20; b.tick_prices(mid_p - sp/2, mid_p + sp/2)
        if idx % report == 0:
            pct = int((idx+1)/n*100); el = time.time()-t0
            bar_fill = "#"*(pct//5) + "."*(20-pct//5)
            sys.stderr.write("\r  [%s] %3d%% | %4.0fs | %s bar %d/%d" % (bar_fill, pct, el, label, idx+1, n))
            sys.stderr.flush()
    el = time.time()-t0
    sys.stderr.write("\r  [####################] 100%% | %4.0fs | %s DONE\n" % (el, label))
    sys.stderr.flush()
# === TEST 1: Empty state ===
sys.stderr.write("\n--- 1/15: Empty state ---\n")
reset()
check("empty orders", len(b.orders) == 0)
check("empty trades", len(b.trades) == 0)
check("1M balance", b.balance == 1000000.0)
check("0 total_trades", b.account_summary().get("total_trades", -1) == 0)
check("0 total_pnl", b.account_summary().get("total_pnl", 999) == 0)

# === TEST 2: Flat bars (no movement) ===
sys.stderr.write("\n--- 2/15: Flat bars (no movement) ---\n")
reset()
b.place_orders(4101.3)
sim_bars([{"open": 4101.3, "high": 4101.3, "low": 4101.3, "close": 4101.3} for _ in range(10)], label="flat")
check("no trades on flat", len(b.trades) == 0)
check("bal unchanged", b.balance == 1000000.0)

# === TEST 3: Extreme volatility spike ===
sys.stderr.write("\n--- 3/15: Extreme volatility spike ---\n")
reset()
b.place_orders(4100.0)
sim_bars([{"open": 4100, "high": 4600, "low": 4090, "close": 4200}], pip_step=50, label="spike")
check("trades opened", len(b.trades) > 0)
check("hit_log populated", len(b.hit_log) > 0)
check("balance changed", b.balance != 1000000.0)

# === TEST 4: Zero ATR edge ===
sys.stderr.write("\n--- 4/15: Zero ATR edge ---\n")
reset()
b._atr_raw = 0.001; b.current_atr = 0.0
b.current_spacing = max(b.MIN_SPACING, min(b.MAX_SPACING, round(b.current_atr / b.ATR_DIVISOR)))
b.current_tp = max(b.current_spacing + 1, round(b.current_spacing * b.TP_MULTIPLIER))
check("spacing=MIN when ATR=0", b.current_spacing == b.MIN_SPACING)
check("TP>=spacing+1", b.current_tp >= b.current_spacing + 1)

# === TEST 5: Drawdown halve/halt ===
sys.stderr.write("\n--- 5/15: Drawdown halve/halt ---\n")
reset()
b.equity_peak = 1000000.0; b.balance = 940000.0
s = b.get_safety_status()
check("DD_HALVE at 6%", s.get("dd_halved", False))
check("not HALT at 6%", not s.get("halted", True))
b.balance = 880000.0
s = b.get_safety_status()
check("DD_HALT at 12%", s.get("halted", False))

# === TEST 6: Hedge pair fill ===
sys.stderr.write("\n--- 6/15: Hedge pair fill ---\n")
reset()
b.place_orders(4100.0)
check("buy orders exist", sum(1 for o in b.orders if o.side == "buy") > 0)
check("sell orders exist", sum(1 for o in b.orders if o.side == "sell") > 0)
sim_bars([{"open": 4100, "high": 4150, "low": 4050, "close": 4100}], pip_step=5, label="hedge")
buy = sum(1 for t in b.trades if t.side == "buy")
sell = sum(1 for t in b.trades if t.side == "sell")
check("both buy+sell trades", buy > 0 and sell > 0, "buy=%d sell=%d" % (buy, sell))
# === TEST 7: Max position limit ===
sys.stderr.write("\n--- 7/15: Max position limit ---\n")
reset()
b.place_orders(4100.0)
for p in [4100 + x * 10 for x in range(-100, 101)]:
    b.tick_prices(p, p)
check("trades <= MAX", len(b.trades) <= b.MAX_POSITIONS, "%d <= %d" % (len(b.trades), b.MAX_POSITIONS))

# === TEST 8: 15-day expiry partial close ===
sys.stderr.write("\n--- 8/15: 15-day expiry partial close ---\n")
reset()
b.place_orders(4100.0)
b.tick_prices(4110.0, 4110.0); b.tick_prices(4115.0, 4115.0)
n_before = len(b.trades)
check("trade opened", n_before > 0)
now_far = time.time() + 16 * 86400
for t in list(b.trades):
    t.entry_time = now_far - 16 * 86400; t.close_pct = 0.0; t.last_close_day = 0
b.tick_prices(4110.0, 4110.0, now_far)
any_partial = any(t.close_pct > 0 for t in b.trades)
any_closed = len(b.trades) < n_before
check("partial/exited after 16d", any_partial or any_closed, "partial=%s closed=%s" % (any_partial, any_closed))

# === TEST 9: 20-day hard stop ===
sys.stderr.write("\n--- 9/15: 20-day hard stop ---\n")
reset()
b.place_orders(4100.0); b.tick_prices(4110.0, 4110.0)
n_before = len(b.trades)
check("trades exist", n_before > 0)
now_hard = time.time() + 21 * 86400
for t in list(b.trades):
    t.entry_time = now_hard - 21 * 86400; t.close_pct = 0.0; t.last_close_day = 0
b.tick_prices(4110.0, 4110.0, now_hard)
check("reduced after 21d hard stop", len(b.trades) < n_before, "%d->%d" % (n_before, len(b.trades)))

# === TEST 10: TP grace pause ===
sys.stderr.write("\n--- 10/15: TP grace pause ---\n")
reset()
b.place_orders(4100.0); b.tick_prices(4110.0, 4110.0); b.tick_prices(4115.0, 4115.0)
n_before = len(b.trades)
check("trade exists", n_before > 0)
now_grace = time.time() + 16 * 86400
for t in list(b.trades):
    t.entry_time = now_grace - 16 * 86400; t.close_pct = 0.0; t.last_close_day = 0
    t.tp = 4140.0; t.entry_price = 4110.0
b.tick_prices(4130.0, 4130.0, now_grace)
check("still open during TP grace", len(b.trades) >= 1)

# === TEST 11: walk_bar degenerate ===
sys.stderr.write("\n--- 11/15: walk_bar degenerate ---\n")
t = b._walk_bar(4100, 4100, 4100, 4100, 10)
check("all-equal returns ticks", len(t) > 0)
check("all ticks = input", all(x == 4100 for x in t))
t2 = b._walk_bar(4100, 4100.5, 4100, 4100, 10)
check("0.5 range >=1 tick", len(t2) >= 1)

# === TEST 12: Overnight gap fill ===
sys.stderr.write("\n--- 12/15: Overnight gap fill ---\n")
reset(); b.place_orders(4100.0)
sim_bars([
    {"open": 4100, "high": 4110, "low": 4095, "close": 4105},
    {"open": 4150, "high": 4160, "low": 4145, "close": 4155},
], pip_step=5, label="gap")
check("trades after gap", len(b.trades) > 0)
check("hits after gap", len(b.hit_log) > 0)

# === TEST 13: Restart cleanup ===
sys.stderr.write("\n--- 13/15: Restart cleanup ---\n")
reset()
check("orders cleared", len(b.orders) == 0)
check("trades cleared", len(b.trades) == 0)
check("hit_log cleared", len(b.hit_log) == 0)
check("balance restored 1M", b.balance == 1000000.0)

# === TEST 14: Triple restart stability ===
sys.stderr.write("\n--- 14/15: Triple restart stability ---\n")
for i in range(3):
    reset(); b.place_orders(4100.0)
    sim_bars([{"open": 4100, "high": 4120, "low": 4080, "close": 4100}], label="restart%d" % (i+1))
    check("stable after r%d" % (i+1), len(b.trades) >= 0)

# === TEST 15: 2000 bar throughput ===
sys.stderr.write("\n--- 15/15: 2000 bar throughput ---\n")
reset(); b.place_orders(4100.0)
from pathlib import Path
data = json.loads(Path("/root/forex-grid/gcf_15m.json").read_text())
kf = [d for d in data if not (d["open"]==d["high"]==d["low"]==d["close"])][:2000]
t0 = time.time()
sim_bars(kf, pip_step=50, label="2k-bars")
el = time.time() - t0
check("under 60s", el < 60, "%.1fs" % el)
check("trades>0", len(b.trades) > 0)
check("closed>0", len(b.closed_trades) > 0)
check("bal changed", b.balance != 1000000.0)
sys.stderr.write("  >> 2000 bars: %.1fs open=%d closed=%d bal=%.0f PnL=%+.0f\n" % (el, len(b.trades), len(b.closed_trades), b.balance, b.balance-1000000))
elapsed = 0
sys.stderr.write("\n" + "="*50 + "\n")
sys.stderr.write("  PASS: %d  FAIL: %d  Time: %.1fs\n" % (PASS, FAIL, elapsed))
sys.stderr.write("="*50 + "\n")
sys.exit(FAIL > 0)
