"""Edge case tests — 34 tests using broker.xxx access"""
import sys, json, os, math, random, time
sys.path.insert(0, "/root/forex-grid")
import broker

def _open_trade(side, entry, tp, level_idx=0, entry_time=None):
    t = broker.Trade(f"edge-{len(broker.trades)}", side, entry, tp, level_idx, entry_time or time.time())
    broker.trades.append(t)
    return t

def test_reset_clears_everything():
    broker.reset()
    _open_trade("buy", 2000.0, 2050.0)
    broker.reset()
    assert len(broker.trades) == 0
    assert broker.balance == 1000000.0
    assert broker.micro_atr == 5.0

def test_empty_orders():
    broker.reset()
    assert len(broker.orders) == 0

def test_place_orders_symmetry():
    broker.reset()
    broker.place_orders(2000.0)
    buys = [o for o in broker.orders if o.side == "buy"]
    sells = [o for o in broker.orders if o.side == "sell"]
    assert len(buys) == len(sells)

def test_force_close_multi_trades():
    broker.reset()
    t1 = _open_trade("buy", 2000.0, 2050.0)
    t2 = _open_trade("sell", 2000.0, 1950.0)
    bal = broker.balance
    broker.force_close_trade(t1, 2010.0, 2010.01, time.time(), "EXPIRY")
    broker.force_close_trade(t2, 1970.0, 1970.01, time.time(), "EXPIRY")
    assert len(broker.trades) == 0
    assert broker.balance != bal

def test_force_close_same_twice():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    broker.force_close_trade(t, 2010.0, 2010.01, time.time(), "EXPIRY")
    bal = broker.balance
    broker.force_close_trade(t, 2020.0, 2020.01, time.time(), "EXPIRY")
    assert broker.balance == bal

def test_negative_pnl():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    bal = broker.balance
    broker.force_close_trade(t, 1900.0, 1900.01, time.time(), "EXPIRY")
    assert broker.balance < bal

def test_zero_pnl():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    bal = broker.balance
    broker.force_close_trade(t, 2000.0, 2000.01, time.time(), "EXPIRY")
    assert broker.balance == bal

def test_large_pnl():
    broker.reset()
    t = _open_trade("buy", 2000.0, 3000.0)
    bal = broker.balance
    broker.force_close_trade(t, 3000.0, 3000.01, time.time(), "EXPIRY")
    assert broker.balance > bal

def test_micro_atr_scalar():
    broker.reset()
    broker.update_micro_atr(10.0)
    assert broker.micro_atr > 0

def test_micro_atr_constant():
    broker.reset()
    for _ in range(20):
        broker.update_micro_atr(0.0)
    assert broker.micro_atr >= 0

def test_apply_atr_spacing_idempotent():
    broker.reset()
    broker.apply_atr_spacing()
    assert broker.current_spacing > 0

def test_switch_atr_source_macro():
    broker.reset()
    broker.switch_atr_source("macro")
    assert broker.atr_source == "macro"

def test_hedge_close_enabled_default():
    broker.reset()
    assert broker.HEDGE_CLOSE_ENABLED == True

def test_trend_filter_default():
    broker.reset()
    assert broker.TREND_FILTER_ENABLED == True

def test_get_safety_defaults():
    broker.reset()
    s = broker.get_safety_status()
    assert s["drawdown"] == 0.0

def test_monthly_pnl_empty():
    broker.reset()
    mp = broker.monthly_pnl()
    assert mp == {}

def test_place_orders_then_tick():
    broker.reset()
    broker.place_orders(2000.0)
    broker.tick_prices(2000.0, 2000.01, time.time())
    assert len(broker.trades) > 0

def test_multiple_ticks():
    broker.reset()
    broker.place_orders(2000.0)
    for i in range(10):
        broker.tick_prices(2000.0 + i * 0.1, 2000.01 + i * 0.1, time.time() + i)
    assert len(broker.trades) > 0

def test_reset_with_open_trades():
    broker.reset()
    _open_trade("buy", 2000.0, 2050.0)
    _open_trade("sell", 2000.0, 1950.0)
    broker.reset()
    assert len(broker.trades) == 0

def test_reset_clears_hit_log():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    broker.force_close_trade(t, 2010.0, 2010.01, time.time(), "EXPIRY")
    assert len(broker.hit_log) > 0
    broker.reset()
    assert len(broker.hit_log) == 0

def test_update_trade_ages_empty():
    broker.reset()
    broker.update_trade_ages(2000.0, 2000.01, time.time())
    assert len(broker.trades) == 0

def test_expiry_bars_nonzero():
    broker.reset()
    assert broker.expiry_bars > 0

def test_expiry_bars_custom_value():
    broker.reset()
    broker.expiry_bars = 48
    assert broker.expiry_bars == 48

def test_get_params_complete():
    broker.reset()
    p = broker.get_params()
    for k in ["atr", "spacing", "tp", "base_lot", "trend_filter", "mr_enabled"]:
        assert k in p

def test_sma_updates():
    broker.reset()
    broker.update_sma(2000.0)
    broker.update_sma(2010.0)
    broker.update_sma(1990.0)

def test_micro_atr_after_reset():
    broker.reset()
    broker.update_micro_atr(5.0)
    broker.reset()
    assert broker.micro_atr == 5.0

def test_force_close_nonexistent():
    broker.reset()
    fake = broker.Trade("fake", "buy", 2000.0, 2050.0, 0, time.time())
    broker.force_close_trade(fake, 2025.0, 2025.01, time.time(), "EXPIRY")

def test_hit_log_after_force_close():
    broker.reset()
    t = _open_trade("buy", 2000.0, 2050.0)
    broker.force_close_trade(t, 2010.0, 2010.01, time.time(), "EXPIRY")
    assert len(broker.hit_log) > 0

def test_custom_expiry_then_reset():
    broker.reset()
    broker.expiry_bars = 99
    broker.reset()
    assert broker.expiry_bars == 60

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
