"""Unit tests for forex-grid broker.py"""
import sys, os, json, math

sys.path.insert(0, "/root/forex-grid")
import broker as b


def reset():
    b.balance = 1000000.0
    b.orders.clear()
    b.trades.clear()
    b.hit_log.clear()
    b.total_trades = 0
    b._atr_raw = 5.0
    b.current_atr = 5.0
    b.current_spacing = b.MIN_SPACING
    b.current_tp = b.MIN_SPACING + 1
    b.daily_trades = 0


PASS = 0
FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f"  ({detail})" if detail else ""))


# --- ATR & Spacing ---
reset()
bars = [{"open": 4100, "high": 4120, "low": 4090, "close": 4110} for _ in range(20)]
for d in bars:
    rp = max(d["high"] - d["low"], 0.1) / b.PIP
    alpha = 2.0 / (b.ATR_WINDOW + 1)
    b._atr_raw = b._atr_raw + alpha * (rp - b._atr_raw) if b._atr_raw >= 0.01 else rp
b.current_atr = round(b._atr_raw, 1)
b.current_spacing = max(b.MIN_SPACING, min(b.MAX_SPACING, round(b.current_atr / b.ATR_DIVISOR)))
print("--- ATR & Spacing ---")
check("ATR computed > 0", b.current_atr > 0, str(b.current_atr))
check("Spacing clamped to MIN", b.current_spacing >= b.MIN_SPACING, str(b.current_spacing))
check("Spacing clamped to MAX", b.current_spacing <= b.MAX_SPACING, str(b.current_spacing))

# --- Get Params ---
print("\n--- Get Params ---")
p = b.get_params()
check("get_params returns dict", isinstance(p, dict))
check("params has atr", "atr" in p)
check("params has spacing", "spacing" in p)
check("params has base_spread", "base_spread" in p)
check("params has dynamic_spread", "dynamic_spread" in p)
check("params has min_spacing", "min_spacing" in p)
check("params has max_spacing", "max_spacing" in p)
check("params has atr_divisor", "atr_divisor" in p)
check("params has tp_multiplier", "tp_multiplier" in p)
check("params has base_lot", "base_lot" in p)

# --- Order Placement ---
print("\n--- Order Placement ---")
reset()
b.place_orders(4100.0)
check("orders placed", len(b.orders) > 0, str(len(b.orders)))

# --- Ticker ---
print("\n--- Ticker / Trade ---")
reset()
b.place_orders(4100.0)
b.tick_prices(4100.0, 4100.0)
check("tick_prices executes", True)
initial_trades = len(b.trades)
b.tick_prices(4105.0, 4105.0)
b.tick_prices(4095.0, 4095.0)

# --- Account Summary ---
print("\n--- Account Summary ---")
acct = b.account_summary()
check("summary has balance", "balance" in acct)
check("summary has equity", "equity" in acct)
check("summary has upnl", "upnl" in acct)
check("summary has open_orders", "open_orders" in acct)
check("summary has open_trades", "open_trades" in acct)
check("summary has drawdown", "drawdown" in acct)
check("summary has pnl_today", "pnl_today" in acct)
check("summary has wins", "wins" in acct)
check("summary has losses", "losses" in acct)
check("summary has return_pct", "return_pct" in acct)
check("summary has total_trades", "total_trades" in acct)

# --- Walk Bar ---
print("\n--- Walk Bar ---")
ticks = b._walk_bar(4100, 4120, 4090, 4110, 10)
check("walk_bar returns list", isinstance(ticks, list), str(type(ticks)))
check("walk_bar returns > 0 ticks", len(ticks) > 0, str(len(ticks)))
# with 20 pip range, 10 pip step = 2 ticks
check("ticks span range", len(ticks) >= 2, str(ticks[:5]))

# --- Open Positions ---
print("\n--- Open Positions ---")
reset()
b.place_orders(4100.0)
b.tick_prices(4101.0, 4101.0)
b.tick_prices(4102.0, 4102.0)
pos = b.open_positions(4105.0, 4105.0)
check("open_positions returns list", isinstance(pos, list))

# --- Trade Expiry ---
print("\n--- Trade Expiry Constants ---")
check("MIN_SPACING set", b.MIN_SPACING == 1000)
check("MAX_SPACING set", b.MAX_SPACING == 10000)
check("ATR_DIVISOR set", b.ATR_DIVISOR == 2.0)
check("BASE_SPREAD exists", hasattr(b, "BASE_SPREAD"))
check("DYNAMIC_SPREAD exists", hasattr(b, "DYNAMIC_SPREAD"))

# --- Balance Integrity ---
print("\n--- Balance Integrity ---")
reset()
init_bal = b.balance
b.place_orders(4100.0)
for i in range(100):
    price = 4100 + (i % 10 - 5)
    b.tick_prices(price, price)
check("balance non-negative after ticker", b.balance >= 0, f"{b.balance}")

# Final
print(f"\n{'='*40}")
print(f"  PASS: {PASS}  FAIL: {FAIL}")
print(f"{'='*40}")
sys.exit(FAIL > 0)
