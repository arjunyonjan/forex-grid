c = open("/root/forex-grid/main.py").read()

# Move broker reset INSIDE while True — remove it from outside and put it as first thing inside
old_reset_outer = """    # Reset broker state so P&L starts at 0 every launch
    from broker import orders, trades, hit_log, closed_trades, price_history
    orders.clear()
    trades.clear()
    hit_log.clear()
    closed_trades.clear()
    price_history.clear()
    import broker as _b
    _b.balance = 1000000.0
    _b.start_balance = 1000000.0
    _b.daily_start_balance = 1000000.0
    _b.month_start_balance = 1000000.0
    _b.equity_peak = 1000000.0
    _b.daily_trade_count = 0
    _b.total_trades = 0
    _b.current_atr = 5.0
    _b.lot_size = _b.BASE_LOT
    _b.trading_halted = False
    _b.total_wins_cumulative = 0
    _b.total_losses_cumulative = 0
    _b.cumulative_win_pnl = 0.0
    _b.cumulative_loss_pnl = 0.0

    while True:"""

new_reset_inner = """    while True:
        from broker import orders, trades, hit_log, closed_trades, price_history
        orders.clear(); trades.clear(); hit_log.clear(); closed_trades.clear(); price_history.clear()
        import broker as _b
        _b.balance = 1000000.0; _b.start_balance = 1000000.0; _b.daily_start_balance = 1000000.0
        _b.month_start_balance = 1000000.0; _b.equity_peak = 1000000.0; _b.daily_trade_count = 0
        _b.total_trades = 0; _b.current_atr = 5.0; _b.lot_size = _b.BASE_LOT; _b.trading_halted = False
        _b.total_wins_cumulative = 0; _b.total_losses_cumulative = 0
        _b.cumulative_win_pnl = 0.0; _b.cumulative_loss_pnl = 0.0"""

c = c.replace(old_reset_outer, new_reset_inner, 1)

# Also fix indentation of remaining while True body (kf = keyframes etc.)
# The while True body already starts with kf = keyframes at correct indentation

open("/root/forex-grid/main.py", "w").write(c)
print("fixed: broker reset inside while True")
