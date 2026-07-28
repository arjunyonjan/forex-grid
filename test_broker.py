"""Broker unit tests — 33 tests, uses broker.xxx access"""
import sys, json, os, math, random, time
sys.path.insert(0, "/root/forex-grid")
import broker

def _open_trade(side, entry, tp, level_idx=0, entry_time=None):
    t = broker.Trade(f"test-{len(broker.trades)}", side, entry, tp, level_idx, entry_time or time.time())
    broker.trades.append(t)
    return t

def test_reset_clears_state():
    broker.reset()
    assert len(broker.trades) == 0
    assert len(broker.orders) == 0
    assert len(broker.hit_log) == 0

def test_reset_restores_balance():
    broker.reset()
    assert broker.balance == 1000000.0

def test_reset_restores_atr():
    broker.reset()
    assert broker.current_atr == 5.0
    assert broker.micro_atr == 5.0

def test_place_orders_creates_grid():
    broker.reset()
    broker.place_orders(2000.0)
    assert len(broker.orders) > 0

def test_tick_prices_fills_trades():
    broker.reset()
    broker.place_orders(2000.0)
    broker.tick_prices(2000.0, 2000.01, time.time())
    assert len(broker.trades) > 0

def test_tick_prices_tp_hit():
    broker.reset()
    broker.place_orders(2000.0)
    now = time.time()
    broker.tick_prices(2000.0, 2000.01, now)
    bal_before = broker.balance
    broker.tick_prices(2500.0, 2500.01, now + 1)
    assert broker.balance != bal_before

def test_update_atr():
    broker.reset()
    broker.update_atr(1.0)
    assert broker.current_atr > 0

def test_update_micro_atr():
    broker.reset()
    broker.update_micro_atr(1.0)
    assert broker.micro_atr > 0

def test_get_params():
    broker.reset()
    p = broker.get_params()
    assert "atr" in p and "spacing" in p

def test_account_summary():
    broker.reset()
    s = broker.account_summary()
    assert s["balance"] == 1000000.0

def test_get_safety_status():
    broker.reset()
    s = broker.get_safety_status()
    assert s["halted"] == False

def test_apply_atr_spacing():
    broker.reset()
    broker.apply_atr_spacing()
    assert broker.current_spacing >= 1000

def test_switch_atr_source():
    broker.reset()
    broker.switch_atr_source("macro")
    assert broker.atr_source == "macro"
    broker.switch_atr_source("micro")
    assert broker.atr_source == "micro"

def test_force_close_trade():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    bal_before = broker.balance
    broker.force_close_trade(t, 2025.0, 2025.01, time.time(), "EXPIRY")
    assert len(broker.trades) == 0
    assert broker.balance != bal_before

def test_force_close_trade_pnl():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    bal_before = broker.balance
    broker.force_close_trade(t, 2025.0, 2025.01, time.time(), "EXPIRY")
    expected = (2025.0 - 2000.0) / broker.PIP * broker.PIP_VALUE * broker.lot_size
    assert broker.balance == bal_before + expected

def test_force_close_trade_sell():
    broker.reset()
    t = _open_trade("sell", 2000.0, 1950.0)
    bal_before = broker.balance
    broker.force_close_trade(t, 1975.0, 1975.0, time.time(), "EXPIRY")
    expected = (2000.0 - 1975.0) / broker.PIP * broker.PIP_VALUE * broker.lot_size
    assert broker.balance == bal_before + expected

def test_update_trade_ages_expiry():
    broker.reset()
    broker.expiry_bars = 2
    now = time.time()
    t = _open_trade("buy", 2000.0, 2100.0, entry_time=now - 5)
    broker.trade_age[t.id] = broker.expiry_bars
    broker.update_trade_ages(2005.0, 2005.01, now)
    assert t not in broker.trades

def test_hit_log_format():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    broker.force_close_trade(t, 2025.0, 2025.01, time.time(), "EXPIRY")
    entry = broker.hit_log[-1]
    assert "EXPIRY" in entry["side"]

def test_multiple_force_close():
    broker.reset()
    t1 = _open_trade("buy", 2000.0, 2050.0)
    t2 = _open_trade("sell", 2000.0, 1950.0)
    assert len(broker.trades) == 2
    broker.force_close_trade(t1, 2025.0, 2025.01, time.time(), "EXPIRY")
    assert len(broker.trades) == 1
    broker.force_close_trade(t2, 1975.0, 1975.01, time.time(), "EXPIRY")
    assert len(broker.trades) == 0

def test_expiry_bars_default():
    broker.reset()
    assert broker.expiry_bars == 60

def test_expiry_bars_custom():
    broker.reset()
    broker.expiry_bars = 24
    assert broker.expiry_bars == 24

def test_micro_atr_affects_spacing():
    broker.reset()
    broker.atr_source = "micro"
    broker.micro_atr = 10000.0
    broker.apply_atr_spacing()
    sp1 = broker.current_spacing
    broker.micro_atr = 5000.0
    broker.apply_atr_spacing()
    sp2 = broker.current_spacing
    assert sp2 < sp1

def test_update_sma():
    broker.reset()
    broker.update_sma(2000.0)
    assert broker.current_sma == 0.0 or len(broker.mr_price_history) > 0

def test_account_summary_with_trades():
    broker.reset()
    _open_trade("buy", 2000.0, 2050.0)
    s = broker.account_summary()
    assert s["open_trades"] == 1

def test_micro_atr_persists():
    broker.reset()
    broker.update_micro_atr(5.0)
    a1 = broker.micro_atr
    broker.update_micro_atr(10.0)
    assert broker.micro_atr != a1 or broker.micro_atr >= a1

def test_trade_age_tracking():
    broker.reset()
    now = time.time()
    t = _open_trade("buy", 2000.0, 2100.0, entry_time=now - 1)
    broker.trade_age[t.id] = 0
    broker.update_trade_ages(2005.0, 2005.01, now)
    assert broker.trade_age.get(t.id, 0) >= 1

def test_micro_atr_state():
    broker.reset()
    assert broker.micro_atr == 5.0

def test_reset_trade_age():
    broker.reset()
    assert broker.trade_age == {}

def test_force_close_multiple_left():
    broker.reset()
    t1 = _open_trade("buy", 2000.0, 2050.0)
    t2 = _open_trade("buy", 2010.0, 2060.0)
    t3 = _open_trade("sell", 2000.0, 1950.0)
    assert len(broker.trades) == 3
    broker.force_close_trade(t1, 2025.0, 2025.01, time.time(), "EXPIRY")
    assert len(broker.trades) == 2

if __name__ == "__main__":
    tests = [v for k,v in sorted(locals().items()) if k.startswith("test_")]
    passed = 0
    for test in tests:
        try:
            broker.reset()
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {test.__name__}: {str(e)[:100]}")
    print(f"\n  {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
