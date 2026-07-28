import sys, time, itertools
sys.path.insert(0, "/root/forex-grid")
from main import PRESETS, load_keyframes, _parse_bar_date
import broker as _b

def run_preset(name, tp_mult, atr_div=2.0, min_sp=1000, trend_hedge=False):
    p = PRESETS[name]
    all_kf = load_keyframes()
    kf = [k for k in all_kf if p["start"] <= k["date"][:10] <= p["end"] and not (k["open"] == k["high"] == k["low"] == k["close"])]
    if len(kf) < 100:
        return None

    _b.TP_MULTIPLIER = tp_mult
    _b.ATR_DIVISOR = atr_div
    _b.MIN_SPACING = min_sp
    _b.TREND_HEDGE_DISABLE = trend_hedge
    _b.TREND_FILTER_ENABLED = True
    _b.HEDGE_CLOSE_ENABLED = not trend_hedge
    _b.balance = _b.start_balance = _b.equity_peak = 1000000.0
    _b.orders.clear(); _b.trades.clear(); _b.hit_log.clear(); _b.closed_trades.clear()
    _b.mr_price_history.clear(); _b.current_sma = 0.0
    _b.current_atr = _b._atr_raw = 5.0; _b.current_spacing = 1500
    _b.current_tp = round(_b.current_spacing * _b.TP_MULTIPLIER)
    _b.daily_trade_count = 0; _b.total_trades = 0; _b.lot_size = _b.BASE_LOT
    _b.place_orders(kf[0]["open"])

    for bar in kf:
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        spread = max(20, min(150, _b.current_atr * 0.1)) if _b.DYNAMIC_SPREAD else _b.BASE_SPREAD
        ts = _parse_bar_date(bar["date"])
        for mid_p in _b._walk_bar(o, h, l, c, pip_step=200):
            _b.update_sma(mid_p)
            _b.tick_prices(mid_p - spread/2, mid_p + spread/2, ts)
        _b.update_atr(bar_range=max(h - l, 0.1))

    ac = _b.account_summary()
    tp_hits = sum(1 for h in _b.hit_log if "TP-" in h.get("side",""))
    cl = sum(1 for h in _b.hit_log if "CLEANUP" in h.get("side",""))
    return {"return": ac["return_pct"], "pnl": _b.balance - 1000000,
            "trades": ac["total_trades"], "tp": tp_hits, "cleanups": cl,
            "dd": ac["drawdown"], "bars": len(kf)}

combos = [
    (0.75, 2.0, 1000, False),
    (1.0, 2.0, 1000, False),
    (1.0, 1.5, 1000, False),
    (0.75, 2.0, 1500, False),
    (1.0, 2.0, 1500, False),
    (0.75, 1.5, 1000, False),
    (1.0, 2.0, 1000, True),
    (0.75, 2.0, 1000, True),
]

presets = ["ukraine", "tariff2025", "rally2024", "july2026", "last7d"]

print("Tuning params against look-ahead fix + correct TP")
print("%-8s %5s %5s %5s %6s %5s | %6s %8s %4s %3s %5s %5s" % (
    "Preset", "TP_M", "ATR_D", "M_SP", "Hedge", "Bars",
    "Return", "P&L", "TP", "CL", "DD", "Time"))

for tp_m, atr_d, min_sp, hedge_d in combos:
    t0 = time.time()
    result = run_preset("ukraine", tp_m, atr_d, min_sp, hedge_d)
    if result:
        dt = time.time() - t0
        print("%-8s %5.2f %5.1f %5d %6s %5d | %+.2f%% %8s %4d %3d %5.1f%% %5ds" % (
            "ukraine", tp_m, atr_d, min_sp, str(hedge_d), result["bars"],
            result["return"], "$%+.0f" % result["pnl"], result["tp"], result["cleanups"],
            result["dd"], dt))
