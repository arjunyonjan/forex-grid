import time
from collections import deque

PIP = 0.01
PIP_VALUE = 10.0
BASE_LOT = 0.0001
LOT = 0.01
COMMISSION = 0.0
BASE_SPREAD = 0
DYNAMIC_SPREAD = False
ATR_WINDOW = 14
MIN_SPACING = 2500
MAX_SPACING = 10000
ATR_DIVISOR = 2.0
TP_MULTIPLIER = 0.5
MR_ENABLED = True
MR_LOOKBACK = 20
MR_THRESHOLD = 0.3

TREND_FILTER_ENABLED = True
HEDGE_CLOSE_ENABLED = True
TREND_STRENGTH_THRESHOLD = 0.2
TREND_HEDGE_DISABLE = False

DD_HALVE_THRESHOLD = 5.0
DD_STOP_THRESHOLD = 10.0
MAX_POSITIONS = 500

ATR_STOP_MULTIPLIER = 9999
TIME_STOP_FRAC = 1.0
EXPIRY_DAYS = 15
HARD_STOP_DAYS = 20

balance = 1000000.0
start_balance = 1000000.0
daily_start_balance = balance
month_start_balance = balance
equity_peak = balance
daily_trade_count = 0
total_trades = 0

price_history = deque(maxlen=ATR_WINDOW)
mr_price_history = deque(maxlen=MR_LOOKBACK)
current_sma = 0.0
current_atr = 5.0
_atr_raw = 5.0
current_spacing = MIN_SPACING
current_tp = current_spacing * TP_MULTIPLIER

lot_size = BASE_LOT
trading_halted = False

orders = []
trades = []
hit_log = []
closed_trades = []

# Micro-mode vars (1-min sim)
expiry_bars = 1440
trade_age = {}
micro_atr = 5.0
_micro_atr_raw = 5.0
atr_source = "micro"
micro_atr_window = "1m"
_micro_atr_bar_buffer = []

# Hard-mode vars (10000 pip dual-side grid, no TP/SL, profit target)
HARD_MODE = False
HARD_SPACING_PIPS = 10000
PROFIT_TARGET_PCT = 0.1
hard_profit_target = 0.0
cumulative_pnl = 0.0

class Order:
    def __init__(self, side, price, tp, level_idx):
        self.id = f"ord-{len(orders)+len(trades)+1}"
        self.side = side
        self.price = price
        self.tp = tp
        self.level_idx = level_idx
        self.created = time.time()

class Trade:
    def __init__(self, oid, side, entry, tp, level_idx, entry_time=None, entry_atr=None):
        self.id = f"trd-{len(trades)+1}"
        self.side = side
        self.price = entry
        self.tp = tp
        self.level_idx = level_idx
        self.entry_time = entry_time or time.time()
        self.entry_atr = entry_atr or 5.0
        self.pnl = 0
        self.cost = 0
        self.close_pct = 0.0
        self.last_close_day = -1

def update_atr(bar_range=None):
    global current_atr, current_spacing, current_tp, _atr_raw
    if bar_range is None:
        return
    pips = bar_range / PIP
    alpha = 2.0 / (ATR_WINDOW + 1)
    _atr_raw = _atr_raw + alpha * (pips - _atr_raw) if _atr_raw >= 0.01 else pips
    _atr_raw = max(_atr_raw, 0.01)
    current_atr = _atr_raw
    spacing = max(MIN_SPACING, min(MAX_SPACING, round(current_atr / ATR_DIVISOR)))
    if spacing != current_spacing:
        current_spacing = spacing
        current_tp = max(current_spacing + 1, round(current_spacing * TP_MULTIPLIER))

def update_micro_atr(bar_range=None):
    global micro_atr, _micro_atr_raw
    if bar_range is None:
        return
    pips = bar_range / PIP
    alpha = 2.0 / (ATR_WINDOW + 1)
    _micro_atr_raw = _micro_atr_raw + alpha * (pips - _micro_atr_raw) if _micro_atr_raw >= 0.01 else pips
    _micro_atr_raw = max(_micro_atr_raw, 0.01)
    micro_atr = _micro_atr_raw

def apply_atr_spacing():
    global current_spacing, current_tp
    atr_val = micro_atr if atr_source == "micro" else current_atr
    min_s = MIN_SPACING if atr_source == "micro" else MIN_SPACING
    spacing = max(min_s, min(MAX_SPACING, round(atr_val / ATR_DIVISOR)))
    if spacing != current_spacing:
        current_spacing = spacing
        current_tp = max(current_spacing + 1, round(current_spacing * TP_MULTIPLIER))

def switch_atr_source(source="micro"):
    global atr_source
    atr_source = source
    apply_atr_spacing()

def force_close_trade(trade, bid, ask, now_ts, reason="EXPIRY"):
    global balance
    if trade not in trades:
        return
    remaining = 1.0 - trade.close_pct
    if remaining <= 0:
        return
    if trade.side == "buy":
        gross = (bid - trade.price) / PIP * PIP_VALUE * lot_size * remaining
    else:
        gross = (trade.price - ask) / PIP * PIP_VALUE * lot_size * remaining
    balance += gross
    exit_px = bid if trade.side == "buy" else ask
    if isinstance(now_ts, (int, float)):
        now_str = time.strftime("%H:%M:%S", time.localtime(now_ts))
        ts_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))
        et_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(trade.entry_time)) if isinstance(trade.entry_time, (int, float)) else trade.entry_time.strftime("%Y-%m-%d %H:%M")
    else:
        now_str = now_ts.strftime("%H:%M:%S")
        ts_str = now_ts.strftime("%Y-%m-%d %H:%M")
        et_str = trade.entry_time.strftime("%Y-%m-%d %H:%M") if hasattr(trade.entry_time, "strftime") else time.strftime("%Y-%m-%d %H:%M", time.localtime(trade.entry_time))
    hit_log.append({"t": now_str, "side": reason + "-" + trade.side.upper(), "entry": round(trade.price, 2), "exit": round(exit_px, 2), "price": round(exit_px, 2), "pnl": round(gross, 2), "dur": _fmt_dur(trade.entry_time, now_ts), "entry_time": et_str, "exit_time": ts_str})
    closed_trades.append({"t": now_str, "side": reason + "-" + trade.side.upper(), "entry": round(trade.price, 2), "exit": round(exit_px, 2), "pnl": round(gross, 2), "dur": _fmt_dur(trade.entry_time, now_ts), "entry_time": et_str, "exit_time": ts_str})
    trade.close_pct = 1.0
    _remove_safe(trades, trade)
    _replenish_order(trade.side, trade.price, trade.level_idx)
    if trade.id in trade_age:
        del trade_age[trade.id]



def close_trade(trade_id, bid, ask, now_ts, reason="MANUAL"):
    global balance, cumulative_pnl
    for t in list(trades):
        if t.id != trade_id:
            continue
        if t.side == "buy":
            gross = (bid - t.price) / PIP * PIP_VALUE * lot_size
        else:
            gross = (t.price - ask) / PIP * PIP_VALUE * lot_size
        balance += gross
        cumulative_pnl += gross
        now_str = now_ts.strftime("%H:%M:%S") if hasattr(now_ts, "strftime") else time.strftime("%H:%M:%S", time.localtime(now_ts))
        ts_str = now_ts.strftime("%Y-%m-%d %H:%M") if hasattr(now_ts, "strftime") else time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))
        et_str = t.entry_time.strftime("%Y-%m-%d %H:%M") if hasattr(t.entry_time, "strftime") else time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time))
        exit_px = bid if t.side == "buy" else ask
        hit_log.append({"t": now_str, "side": reason + "-" + t.side.upper(), "entry": round(t.price, 2), "exit": round(exit_px, 2), "price": round(exit_px, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": et_str, "exit_time": ts_str})
        closed_trades.append({"t": now_str, "side": reason + "-" + t.side.upper(), "entry": round(t.price, 2), "exit": round(exit_px, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": et_str, "exit_time": ts_str})
        trades.remove(t)
        if t.id in trade_age:
            del trade_age[t.id]
        return round(gross, 2)
    return 0.0

def close_all_trades(bid, ask, now_ts, reason="PROFIT-TARGET"):
    global balance, cumulative_pnl
    total_closed = 0.0
    for t in list(trades):
        if t.side == "buy":
            gross = (bid - t.price) / PIP * PIP_VALUE * lot_size
        else:
            gross = (t.price - ask) / PIP * PIP_VALUE * lot_size
        balance += gross
        total_closed += gross
        if isinstance(now_ts, (int, float)):
            now_str = time.strftime("%H:%M:%S", time.localtime(now_ts))
            ts_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))
            et_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)) if isinstance(t.entry_time, (int, float)) else t.entry_time.strftime("%Y-%m-%d %H:%M")
        else:
            now_str = now_ts.strftime("%H:%M:%S")
            ts_str = now_ts.strftime("%Y-%m-%d %H:%M")
            et_str = t.entry_time.strftime("%Y-%m-%d %H:%M") if hasattr(t.entry_time, "strftime") else time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time))
        exit_px = bid if t.side == "buy" else ask
        hit_log.append({"t": now_str, "side": reason + "-" + t.side.upper(), "entry": round(t.price, 2), "exit": round(exit_px, 2), "price": round(exit_px, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": et_str, "exit_time": ts_str})
        closed_trades.append({"t": now_str, "side": reason + "-" + t.side.upper(), "entry": round(t.price, 2), "exit": round(exit_px, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": et_str, "exit_time": ts_str})
    trades.clear()
    orders.clear()
    cumulative_pnl += total_closed
    return total_closed

def update_trade_ages(bid, ask, now_ts, atr_val=None):
    for t in trades[:]:
        if t.id not in trade_age:
            trade_age[t.id] = 0
        trade_age[t.id] += 1
        # ATR stop-out: if price moved 3x ATR against entry
        if atr_val and atr_val > 0:
            atr_dist = atr_val * PIP * ATR_STOP_MULTIPLIER
            if t.side == "buy":
                if bid < t.price - atr_dist:
                    force_close_trade(t, bid, ask, now_ts, "ATR-STOP")
                    continue
            else:
                if ask > t.price + atr_dist:
                    force_close_trade(t, bid, ask, now_ts, "ATR-STOP")
                    continue
        # Bar-based expiry
        if trade_age[t.id] >= expiry_bars:
            force_close_trade(t, bid, ask, now_ts, "EXPIRY")

def update_sma(mid_price):
    global current_sma
    mr_price_history.append(mid_price)
    if len(mr_price_history) >= MR_LOOKBACK:
        current_sma = sum(mr_price_history) / len(mr_price_history)
    else:
        current_sma = 0.0

trend_strength = 0.0

_prev_hedge_state = True

def update_trend_filter(mid_price):
    global trend_strength, HEDGE_CLOSE_ENABLED, _prev_hedge_state
    if current_sma <= 0 or current_atr <= 0:
        HEDGE_CLOSE_ENABLED = True
        _prev_hedge_state = True
        return
    deviation = abs(mid_price - current_sma)
    atr_pips = current_atr * PIP
    trend_strength = round(deviation / atr_pips, 2) if atr_pips > 0 else 0.0
    if TREND_FILTER_ENABLED:
        strong = trend_strength > TREND_STRENGTH_THRESHOLD
        if TREND_HEDGE_DISABLE:
            HEDGE_CLOSE_ENABLED = not strong
        else:
            HEDGE_CLOSE_ENABLED = strong

def get_params():
    return {
        "atr": round(current_atr, 1),
        "spacing": current_spacing,
        "tp": current_tp,
        "min_spacing": MIN_SPACING,
        "max_spacing": MAX_SPACING,
        "atr_divisor": ATR_DIVISOR,
        "tp_multiplier": TP_MULTIPLIER,
        "base_lot": BASE_LOT,
        "base_spread": BASE_SPREAD,
        "dynamic_spread": bool(DYNAMIC_SPREAD),
        "mr_enabled": bool(MR_ENABLED),
        "mr_lookback": MR_LOOKBACK,
        "mr_threshold": MR_THRESHOLD,
        "current_sma": round(current_sma, 2),
        "current_sma_atr": round((current_sma - 0) / (current_atr * PIP), 1) if current_atr > 0 else 0,
        "trend_filter": bool(TREND_FILTER_ENABLED),
        "trend_strength": trend_strength,
        "micro_atr_window": micro_atr_window,
        "hedge_close_enabled": bool(HEDGE_CLOSE_ENABLED),
    }



def monthly_pnl():
    from collections import defaultdict
    months = defaultdict(float)
    for t in closed_trades:
        et = t.get("entry_time", "")
        if len(et) >= 7:
            months[et[:7]] += t.get("pnl", 0)
    return {k: round(v, 2) for k, v in sorted(months.items())}

def get_safety_status():
    upnl = sum(t.pnl for t in trades)
    eq = balance + upnl
    peak = max(equity_peak, eq)
    dd = (peak - eq) / peak * 100 if peak else 0
    halted = dd >= DD_STOP_THRESHOLD
    halved = dd >= DD_HALVE_THRESHOLD
    return {
        "drawdown": round(dd, 2),
        "halted": halted,
        "daily_loss_hit": False,
        "dd_halved": halved,
    }

def account_summary():
    global equity_peak
    upnl = sum(t.pnl for t in trades)
    eq = balance + upnl
    if eq > equity_peak:
        equity_peak = eq
    peak = max(equity_peak, eq)
    dd = (peak - eq) / peak * 100 if peak else 0
    total_pnl = eq - start_balance
    win_pnl = round(sum(h.get("pnl", 0) for h in hit_log if h.get("pnl", 0) > 0), 2)
    loss_pnl = round(sum(h.get("pnl", 0) for h in hit_log if h.get("pnl", 0) < 0), 2)
    realized_pnl = round(win_pnl + loss_pnl, 2)
    return {
        "balance": round(balance, 2),
        "equity": round(eq, 2),
        "upnl": round(upnl, 2),
        "open_orders": len(orders),
        "open_trades": len(trades),
        "drawdown": round(dd, 2),
        "pnl_today": round(eq - daily_start_balance, 2),
        "monthly_pnl": round(eq - month_start_balance, 2),
        "total_pnl": round(total_pnl, 2),
        "win_pnl": win_pnl,
        "loss_pnl": loss_pnl,
        "realized_pnl": realized_pnl,
        "wins": sum(1 for h in hit_log if h.get("pnl", 0) > 0),
        "losses": sum(1 for h in hit_log if h.get("pnl", 0) < 0),
        "return_pct": round((balance - start_balance) / start_balance * 100, 2),
        "daily_trades": daily_trade_count,
        "total_trades": total_trades,
        "recent_closed": closed_trades[-20:],
        "lot": round(lot_size, 4),
        "hard_mode": HARD_MODE,
        "hard_spacing_pips": HARD_SPACING_PIPS,
        "profit_target_pct": PROFIT_TARGET_PCT,
        "hard_profit_target": hard_profit_target,
        "cumulative_pnl": round(cumulative_pnl, 2),
        "micro_atr_window": micro_atr_window,
    }

def _replenish_order(side, price, level_idx):
    tp = round(price + current_tp * PIP if side == "buy" else price - current_tp * PIP, 2)
    orders.append(Order(side, price, tp, level_idx))

def _fmt_dur(s, now=None):
    if not s:
        return "--"
    n = now or time.time()
    if hasattr(n, "strftime"):
        s = s.timestamp() if hasattr(s, "timestamp") else s
        n = n.timestamp()
    elif hasattr(s, "timestamp"):
        s = s.timestamp()
    d = abs(int(n - s))
    if d < 60:
        return f"{d}s"
    if d < 3600:
        return f"{d//60}m{d%60}s"
    if d < 86400:
        return f"{d//3600}h{(d%3600)//60}m"
    return f"{d//86400}d{(d%86400)//3600}h"

def open_positions(bid, ask, now_t=None):
    result = []
    if hasattr(now_t, "strftime"):
        now_t = now_t.timestamp()
    for t in trades:
        age = now_t - t.entry_time
        age_days = age / 86400
        pnl = (bid - t.price) / PIP * PIP_VALUE * lot_size if t.side == "buy" else (t.price - ask) / PIP * PIP_VALUE * lot_size
        t.pnl = round(pnl, 2)
        result.append({
            "side": t.side,
            "entry": round(t.price, 2),
            "tp": round(t.tp, 2),
            "tp_range": round(abs(t.tp - t.price) / PIP),
            "pnl": round(pnl, 2),
            "dur": _fmt_dur(t.entry_time, now_t),
            "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)),
            "close_pct": round(t.close_pct * 100),
            "age_days": round(age_days, 1),
            "deadline_extended": age_days > EXPIRY_DAYS and age_days < HARD_STOP_DAYS and t.close_pct == 0,
        })
    return result

def place_orders(mid):
    global orders
    orders.clear()
    if HARD_MODE:
        step = HARD_SPACING_PIPS * PIP
        p = round(mid / step) * step if step else mid
        tp = round(step * TP_MULTIPLIER) if TP_MULTIPLIER else step
        for i in range(-20, 21):
            level = round(p + i * step, 2)
            buy_tp = round(level + tp * PIP, 2)
            sell_tp = round(level - tp * PIP, 2)
            orders.append(Order("buy", level, buy_tp, i))
            orders.append(Order("sell", level, sell_tp, i))
    else:
        step = current_spacing * PIP
        p = round(mid / step) * step if step else mid
        for i in range(-200, 201):
            level = round(p + i * step, 2)
            buy_tp = round(level + current_tp * PIP, 2)
            sell_tp = round(level - current_tp * PIP, 2)
            orders.append(Order("buy", level, buy_tp, i))
            orders.append(Order("sell", level, sell_tp, i))

def tick_prices(bid, ask, now_t=None):
    global balance, total_trades, daily_trade_count, hit_log, lot_size, _prev_hedge_state, cumulative_pnl
    if now_t is None:
        now_ts = time.time()
    elif isinstance(now_t, (int, float)):
        now_ts = now_t
    elif hasattr(now_t, "timestamp"):
        now_ts = now_t.timestamp()
    else:
        now_ts = time.time()
    mid_price = round((bid + ask) / 2, 2)
    update_trend_filter(mid_price)
    if TREND_FILTER_ENABLED and HEDGE_CLOSE_ENABLED and not _prev_hedge_state:
        by_level = {}
        for tr in list(trades):
            by_level.setdefault(tr.level_idx, []).append(tr)
        for level, pair in by_level.items():
            if len(pair) < 2:
                continue
            a, b = pair[0], pair[1]
            h = b if a.side == 'buy' and b.side == 'sell' else a  # pick the wrong-side one
            pnl = (h.price - bid) / PIP * PIP_VALUE * lot_size if h.side == 'sell' else (ask - h.price) / PIP * PIP_VALUE * lot_size
            balance += pnl
            hit_log.append({'t': time.strftime('%H:%M:%S', time.localtime(now_ts)), 'side': 'CLEANUP-' + h.side.upper(), 'entry': round(h.price, 2), 'exit': round(bid if h.side == 'sell' else ask, 2), 'price': round(bid if h.side == 'sell' else ask, 2), 'pnl': round(pnl, 2), 'dur': _fmt_dur(h.entry_time, now_ts), 'entry_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(h.entry_time)), 'exit_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(now_ts))})
            _remove_safe(trades, h)
            _replenish_order(h.side, h.price, h.level_idx)
    _prev_hedge_state = HEDGE_CLOSE_ENABLED
    to_fill = []
    for o in orders[:]:
        if o.side == "buy":
            if abs(ask - o.price) < PIP / 2:
                if MR_ENABLED and current_sma > 0 and mid_price > current_sma + MR_THRESHOLD * current_atr * PIP:
                    pass
                else:
                    to_fill.append(o)
        elif o.side == "sell":
            if abs(bid - o.price) < PIP / 2:
                if MR_ENABLED and current_sma > 0 and mid_price < current_sma - MR_THRESHOLD * current_atr * PIP:
                    pass
                else:
                    to_fill.append(o)
    for o in to_fill:
        if o not in orders:
            continue
        if len(trades) >= MAX_POSITIONS:
            break
        trades.append(Trade(o.id, o.side, o.price, o.tp, o.level_idx, entry_time=now_ts))
        _remove_safe(orders, o)
        total_trades += 1
        daily_trade_count += 1
        hedge = next((x for x in orders if x.level_idx == o.level_idx and x.side != o.side), None)
        if hedge and len(trades) < MAX_POSITIONS:
            trades.append(Trade(hedge.id, hedge.side, hedge.price, hedge.tp, hedge.level_idx, entry_time=now_ts))
            _remove_safe(orders, hedge)
            total_trades += 1
            daily_trade_count += 1
    if HARD_MODE:
        for t in trades[:]:
            hit_tp = (t.side == "buy" and bid >= t.tp) or (t.side == "sell" and ask <= t.tp)
            if hit_tp:
                pnl = (t.tp - t.price) / PIP * PIP_VALUE * lot_size * (1 if t.side == "buy" else -1)
                balance += pnl; cumulative_pnl += pnl
                trades.remove(t); closed_trades.append(t)
                t.close_time = now_ts; t.pnl = pnl
                hit_log.append({"t": now_ts.strftime("%H:%M"), "side": f"TP-{t.side.upper()}", "pnl": round(pnl, 2), "price": round(t.tp, 2)})
        upnl = sum((bid - t.price) / PIP * PIP_VALUE * lot_size if t.side == "buy" else (t.price - ask) / PIP * PIP_VALUE * lot_size for t in trades)
        total = cumulative_pnl + upnl
        if total >= hard_profit_target and len(trades) > 0:
            close_all_trades(bid, ask, now_ts, "PROFIT-TARGET")
            return
        if not trades: return
    for t in trades[:]:
        age = now_ts - t.entry_time
        age_days = age / 86400
        # ---- ATR stop-out ----
        if micro_atr > 0:
            atr_dist = micro_atr * PIP * ATR_STOP_MULTIPLIER
            if t.side == "buy":
                if bid < t.price - atr_dist:
                    force_close_trade(t, bid, ask, now_ts, "ATR-STOP")
                    continue
            else:
                if ask > t.price + atr_dist:
                    force_close_trade(t, bid, ask, now_ts, "ATR-STOP")
                    continue
        # ---- Time-stop: close if >80% of expiry_bars passed without TP hit ----
        if trade_age.get(t.id, 0) >= int(expiry_bars * TIME_STOP_FRAC):
            if t.side == "buy":
                tp_progress = (bid - t.price) / (t.tp - t.price) if t.tp != t.price else 0
            else:
                tp_progress = (t.price - ask) / (t.price - t.tp) if t.price != t.tp else 0
            if tp_progress < 0.5:
                force_close_trade(t, bid, ask, now_ts, "TIMESTOP")
                continue
        # ---- Normal TP hit ----        # ---- Normal TP hit ----
        if t.side == "buy":
            pnl = (bid - t.price) / PIP * PIP_VALUE * lot_size
            t.pnl = round(pnl, 2)
            if bid >= t.tp:
                gross = (t.tp - t.price) / PIP * PIP_VALUE * lot_size
                balance += gross
                hit_log.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-BUY", "entry": round(t.price, 2), "exit": round(t.tp, 2), "price": round(t.tp, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                closed_trades.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-BUY", "entry": round(t.price, 2), "exit": round(t.tp, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                _remove_safe(trades, t)
                _replenish_order(t.side, t.price, t.level_idx)
                if HEDGE_CLOSE_ENABLED:
                    for h in trades[:]:
                        if h.side == 'sell' and h.level_idx == t.level_idx:
                            loss = 0
                            balance += loss
                            hit_log.append({'t': time.strftime('%H:%M:%S', time.localtime(now_ts)), 'side': 'HEDGE-SELL', 'entry': round(h.price, 2), 'exit': round(h.price, 2), 'price': round(h.price, 2), 'pnl': round(loss, 2), 'dur': _fmt_dur(h.entry_time, now_ts), 'entry_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(h.entry_time)), 'exit_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(now_ts))})
                            closed_trades.append({'t': time.strftime('%H:%M:%S', time.localtime(now_ts)), 'side': 'HEDGE-SELL', 'entry': round(h.price, 2), 'exit': round(h.price, 2), 'pnl': round(loss, 2), 'dur': _fmt_dur(h.entry_time, now_ts), 'entry_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(h.entry_time)), 'exit_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(now_ts))})
                            _remove_safe(trades, h)
                            _replenish_order(h.side, h.price, h.level_idx)
        else:
            pnl = (t.price - ask) / PIP * PIP_VALUE * lot_size
            t.pnl = round(pnl, 2)
            if ask <= t.tp:
                gross = (t.price - t.tp) / PIP * PIP_VALUE * lot_size
                balance += gross
                hit_log.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-SELL", "entry": round(t.price, 2), "exit": round(t.tp, 2), "price": round(t.tp, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                closed_trades.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-SELL", "entry": round(t.price, 2), "exit": round(t.tp, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                _remove_safe(trades, t)
                _replenish_order(t.side, t.price, t.level_idx)
                if HEDGE_CLOSE_ENABLED:
                    for h in trades[:]:
                        if h.side == 'buy' and h.level_idx == t.level_idx:
                            loss = 0
                            balance += loss
                            hit_log.append({'t': time.strftime('%H:%M:%S', time.localtime(now_ts)), 'side': 'HEDGE-BUY', 'entry': round(h.price, 2), 'exit': round(h.price, 2), 'price': round(h.price, 2), 'pnl': round(loss, 2), 'dur': _fmt_dur(h.entry_time, now_ts), 'entry_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(h.entry_time)), 'exit_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(now_ts))})
                            closed_trades.append({'t': time.strftime('%H:%M:%S', time.localtime(now_ts)), 'side': 'HEDGE-BUY', 'entry': round(h.price, 2), 'exit': round(h.price, 2), 'pnl': round(loss, 2), 'dur': _fmt_dur(h.entry_time, now_ts), 'entry_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(h.entry_time)), 'exit_time': time.strftime('%Y-%m-%d %H:%M', time.localtime(now_ts))})
                            _remove_safe(trades, h)
                            _replenish_order(h.side, h.price, h.level_idx)
    safety = get_safety_status()
    if safety["halted"]:
        global trading_halted
        trading_halted = True

def _remove_safe(lst, item):
    if item in lst:
        lst.remove(item)

def _walk_bar(o, h, l, c, pip_step=1):
    segments = []
    up = h - o
    down = o - l
    if up >= down:
        if abs(h - o) > 0.001:
            segments.append((o, h))
        if abs(l - h) > 0.001:
            segments.append((h, l))
    else:
        if abs(l - o) > 0.001:
            segments.append((o, l))
        if abs(h - l) > 0.001:
            segments.append((l, h))
    if abs(c - segments[-1][1] if segments else o) > 0.001:
        segments.append((segments[-1][1] if segments else o, c))
    bar_ticks = []
    for start, end in segments:
        n = max(1, int(abs(end - start) / (pip_step * PIP)) + 1)
        step = (end - start) / n if n else 0
        for i in range(n):
            bar_ticks.append(round(start + step * i, 2))
    if not bar_ticks:
        bar_ticks = [round(o, 2)]
    return bar_ticks


def reset(state=None):
    global balance, start_balance, equity_peak, trades, orders, hit_log, closed_trades
    global current_atr, current_spacing, current_tp, _atr_raw
    global micro_atr, _micro_atr_raw, trade_age, atr_source, expiry_bars
    global price_history, mr_price_history, current_sma, lot_size, trading_halted
    global daily_trade_count, total_trades, month_start_balance, daily_start_balance
    global HARD_MODE, hard_profit_target, cumulative_pnl, micro_atr_window, _micro_atr_bar_buffer
    balance = 1000000.0
    start_balance = 1000000.0
    daily_start_balance = balance
    month_start_balance = balance
    equity_peak = balance
    trades = []
    orders = []
    hit_log = []
    closed_trades = []
    current_atr = 5.0
    _atr_raw = 5.0
    current_spacing = 1000
    current_tp = 500
    micro_atr = 5.0
    _micro_atr_raw = 5.0
    trade_age = {}
    atr_source = "micro"

    expiry_bars = 1440
    price_history.clear()
    mr_price_history.clear()
    current_sma = 0.0
    lot_size = BASE_LOT
    trading_halted = False
    daily_trade_count = 0
    total_trades = 0
    HARD_MODE = False
    hard_profit_target = 0.0
    cumulative_pnl = 0.0
    micro_atr_window = "1m"
    _micro_atr_bar_buffer = []

def feed_micro_bar(high, low, sim_tf_seconds=60):
    global _micro_atr_bar_buffer
    if sim_tf_seconds <= 0:
        sim_tf_seconds = 60
    _micro_atr_bar_buffer.append((high, low))
    tf_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1D": 86400}
    window_secs = tf_seconds.get(micro_atr_window, 60)
    bars_needed = max(1, window_secs // sim_tf_seconds)
    if len(_micro_atr_bar_buffer) >= bars_needed:
        agg_high = max(h for h, l in _micro_atr_bar_buffer)
        agg_low = min(l for h, l in _micro_atr_bar_buffer)
        bar_range = max(agg_high - agg_low, 0.1)
        update_micro_atr(bar_range=bar_range)
        apply_atr_spacing()
        _micro_atr_bar_buffer = []

def set_micro_atr_window(window):
    global micro_atr_window, _micro_atr_bar_buffer
    if window in ("1m", "5m", "15m", "1h", "4h", "1D"):
        micro_atr_window = window
        _micro_atr_bar_buffer = []
