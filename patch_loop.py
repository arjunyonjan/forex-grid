c = open("/root/forex-grid/main.py").read()

# After halt, restart from beginning (loop mode)
old = '''    import broker as _b
    _b.trading_halted = True
    acct = account_summary()
    msg = {"bid": round(bid, 2), "ask": round(ask, 2), "mid": round(mid_p, 2), "spread": round(spread, 2), "grid": grid, "positions": pos, "hit_log": list(__import__("broker").hit_log[-20:]), "speed": speed_multiplier, "tick": tick_count, "elapsed_seconds": int((dt - sim_start).total_seconds()), "eta_seconds": 0, "sim_time": dt.strftime("%b %d %H:%M:%S NST"), **acct}
    asyncio.ensure_future(broadcast(msg))
    print(f"HALT: multi-resolution sim complete — {total_kf} keyframes, {tick_count} ticks")
    return'''

new = '''    import broker as _b
    print(f"RESTART: {total_kf} keyframes, {tick_count} ticks — restarting")
    _b.orders.clear(); _b.trades.clear(); _b.hit_log.clear(); _b.closed_trades.clear(); _b.price_history.clear()
    _b.balance = 1000000.0; _b.start_balance = 1000000.0; _b.daily_start_balance = 1000000.0
    _b.month_start_balance = 1000000.0; _b.equity_peak = 1000000.0; _b.daily_trade_count = 0
    _b.total_trades = 0; _b.current_atr = 5.0; _b.lot_size = _b.BASE_LOT; _b.trading_halted = False
    _b.total_wins_cumulative = 0; _b.total_losses_cumulative = 0
    _b.cumulative_win_pnl = 0.0; _b.cumulative_loss_pnl = 0.0
    return'''

c = c.replace(old, new, 1)
open("/root/forex-grid/main.py", "w").write(c)
print("looping mode patched")
