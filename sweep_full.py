import sys, json, time
sys.path.insert(0, "/root/forex-grid")
from pathlib import Path
import broker as _b

BASEDIR = Path("/root/forex-grid")
all_kf = []
for fname, res in [("gcf_daily.json",86400)]:
    p = BASEDIR / fname
    if p.exists():
        data = json.loads(p.read_text())
        for d in data:
            y = d["date"][:4]
            if y in ("2022","2023","2024","2025","2026") and not (d["open"]==d["high"]==d["low"]==d["close"]):
                all_kf.append(d)

print("Loaded %d keyframes (2022-2026)" % len(all_kf))

TEST = [1,3,7,14,30,60,90,180,365,9999]

for idx, mtd in enumerate(TEST):
    _b.MAX_TRADE_DAYS = mtd
    _b.orders.clear()
    _b.trades.clear()
    _b.hit_log.clear()
    _b.closed_trades.clear()
    _b.price_history.clear()
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

    t0 = time.time()
    result = _b.simulate_from_keyframes(all_kf, init_bal=1000000.0, spacing=200, tick_scale=96)
    el = time.time() - t0
    to_cnt = sum(1 for h in _b.hit_log if h.get("side","") == "TIMEOUT")
    pnl = result.get("total_pnl",0)
    ret = result.get("return_pct",0)
    dd = result.get("max_dd",0)
    trades = result.get("total_trades",0)
    wins = result.get("wins",0)
    losses = result.get("losses",0)
    tp_cnt = sum(1 for h in _b.hit_log if h.get("side","").startswith("TP"))
    print("[%d/%d] MTD=%5d: P&L=%+.2f  ret=%+.2f%%  DD=%.1f%%  tr=%d  w=%d  l=%d  TP=%d  TO=%d  (%.1fs)" % (
        idx+1, len(TEST), mtd, pnl, ret, dd, trades, wins, losses, tp_cnt, to_cnt, el))
