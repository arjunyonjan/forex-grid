import time
from collections import deque

PIP = 0.01
PIP_VALUE = 10.0
BASE_LOT = 0.01
LOT = 0.01
COMMISSION = 0.0
BASE_SPREAD = 0
DYNAMIC_SPREAD = True
ATR_WINDOW = 14
MIN_SPACING = 1000
MAX_SPACING = 10000
ATR_DIVISOR = 2.0
TP_MULTIPLIER = 0.5
MR_ENABLED = True
MR_LOOKBACK = 20
MR_THRESHOLD = 0.3
MR_ENABLED = True
MR_LOOKBACK = 20
MR_THRESHOLD = 0.3

DD_HALVE_THRESHOLD = 5.0
DD_STOP_THRESHOLD = 10.0
MAX_POSITIONS = 500

EXPIRY_DAYS = 15
HARD_STOP_DAYS = 20
EXPIRY_SECS = EXPIRY_DAYS * 86400
HARD_STOP_SECS = HARD_STOP_DAYS * 86400
CLOSE_FRAC_PER_DAY = 0.25
TP_GRACE_FRAC = 0.5

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

class Order:
    def __init__(self, side, price, tp, level_idx):
        self.id = f"ord-{len(orders)+len(trades)+1}"
        self.side = side
        self.price = price
        self.tp = tp
        self.level_idx = level_idx
        self.created = time.time()

class Trade:
    def __init__(self, oid, side, entry, tp, level_idx, entry_time=None):
        self.id = f"trd-{len(trades)+1}"
        self.side = side
        self.price = entry
        self.tp = tp
        self.level_idx = level_idx
        self.entry_time = entry_time or time.time()
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

def update_sma(mid_price):
    global current_sma
    mr_price_history.append(mid_price)
    if len(mr_price_history) >= MR_LOOKBACK:
        current_sma = sum(mr_price_history) / len(mr_price_history)
    else:
        current_sma = 0.0

def update_sma(mid_price):
    global current_sma
    mr_price_history.append(mid_price)
    if len(mr_price_history) >= MR_LOOKBACK:
        current_sma = sum(mr_price_history) / len(mr_price_history)
    else:
        current_sma = 0.0

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
        "mr_enabled": bool(MR_ENABLED),
        "mr_lookback": MR_LOOKBACK,
        "mr_threshold": MR_THRESHOLD,
        "current_sma": round(current_sma, 2),
    }

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
        "return_pct": round(total_pnl / start_balance * 100, 2),
        "daily_trades": daily_trade_count,
        "total_trades": total_trades,
        "recent_closed": closed_trades[-20:],
        "lot": round(lot_size, 4),
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
    d = int(n - s)
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
    step = current_spacing * PIP
    p = round(mid / step) * step if step else mid
    for i in range(-200, 201):
        level = round(p + i * step, 2)
        buy_tp = round(level + current_tp * PIP, 2)
        sell_tp = round(level - current_tp * PIP, 2)
        orders.append(Order("buy", level, buy_tp, i))
        orders.append(Order("sell", level, sell_tp, i))

def tick_prices(bid, ask, now_t=None):
    global balance, total_trades, daily_trade_count, hit_log, lot_size
    if now_t is None:
        now_ts = time.time()
    elif isinstance(now_t, (int, float)):
        now_ts = now_t
    elif hasattr(now_t, "timestamp"):
        now_ts = now_t.timestamp()
    else:
        now_ts = time.time()
    mid_price = round((bid + ask) / 2, 2)
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
        orders.remove(o)
        total_trades += 1
        daily_trade_count += 1
        hedge = next((x for x in orders if x.level_idx == o.level_idx and x.side != o.side), None)
        if hedge and len(trades) < MAX_POSITIONS:
            trades.append(Trade(hedge.id, hedge.side, hedge.price, hedge.tp, hedge.level_idx, entry_time=now_ts))
            orders.remove(hedge)
            total_trades += 1
            daily_trade_count += 1
    for t in trades[:]:
        age = now_ts - t.entry_time
        age_days = age / 86400
        # ---- Deadline logic ----
        if age_days > EXPIRY_DAYS:
            if t.side == "buy":
                tp_progress = (bid - t.price) / (t.tp - t.price) if t.tp != t.price else 0
            else:
                tp_progress = (t.price - ask) / (t.price - t.tp) if t.price != t.tp else 0
            near_tp = tp_progress >= TP_GRACE_FRAC
            if near_tp and age_days < HARD_STOP_DAYS:
                pass
            else:
                days_past = int(age_days - EXPIRY_DAYS)
                target_close = min(days_past * CLOSE_FRAC_PER_DAY, 1.0)
                to_close = target_close - t.close_pct
                if to_close > 0:
                    if t.side == "buy":
                        partial = (bid - t.price) / PIP * PIP_VALUE * lot_size * to_close
                    else:
                        partial = (t.price - ask) / PIP * PIP_VALUE * lot_size * to_close
                    balance += partial
                    t.close_pct += to_close
                    pct_str = f"{round(t.close_pct * 100)}%"
                    hit_log.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "PARTIAL", "entry": round(t.price, 2), "exit": round(bid if t.side == "buy" else ask, 2), "price": round(bid if t.side == "buy" else ask, 2), "pnl": round(partial, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts)), "close_pct": pct_str})
            if t.close_pct >= 1.0 or age_days >= HARD_STOP_DAYS:
                remaining = 1.0 - t.close_pct
                if remaining > 0:
                    if t.side == "buy":
                        gross = (bid - t.price) / PIP * PIP_VALUE * lot_size * remaining
                    else:
                        gross = (t.price - ask) / PIP * PIP_VALUE * lot_size * remaining
                    balance += gross
                    close_side = "HARDSTOP" if age_days >= HARD_STOP_DAYS else "EXPCLOSE"
                    hit_log.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": close_side + "-" + t.side.upper(), "entry": round(t.price, 2), "exit": round(bid if t.side == "buy" else ask, 2), "price": round(bid if t.side == "buy" else ask, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                    closed_trades.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": close_side + "-" + t.side.upper(), "entry": round(t.price, 2), "exit": round(bid if t.side == "buy" else ask, 2), "pnl": round(gross, 2), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                trades.remove(t)
                _replenish_order(t.side, t.price, t.level_idx)
                continue
        # ---- Normal TP hit ----
        if t.side == "buy":
            pnl = (bid - t.price) / PIP * PIP_VALUE * lot_size
            t.pnl = round(pnl, 2)
            if bid >= t.tp:
                gross = (t.tp - t.price) / PIP * PIP_VALUE * lot_size
                balance += gross
                hit_log.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-BUY", "entry": round(t.price, 2), "exit": round(t.tp, 2), "price": round(t.tp, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                closed_trades.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-BUY", "entry": round(t.price, 2), "exit": round(t.tp, 2), "pnl": round(gross, 2), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                trades.remove(t)
                _replenish_order(t.side, t.price, t.level_idx)
        else:
            pnl = (t.price - ask) / PIP * PIP_VALUE * lot_size
            t.pnl = round(pnl, 2)
            if ask <= t.tp:
                gross = (t.price - t.tp) / PIP * PIP_VALUE * lot_size
                balance += gross
                hit_log.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-SELL", "entry": round(t.price, 2), "exit": round(t.tp, 2), "price": round(t.tp, 2), "pnl": round(gross, 2), "dur": _fmt_dur(t.entry_time, now_ts), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                closed_trades.append({"t": time.strftime("%H:%M:%S", time.localtime(now_ts)), "side": "TP-SELL", "entry": round(t.price, 2), "exit": round(t.tp, 2), "pnl": round(gross, 2), "entry_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(t.entry_time)), "exit_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ts))})
                trades.remove(t)
                _replenish_order(t.side, t.price, t.level_idx)
    safety = get_safety_status()
    if safety["halted"]:
        global trading_halted
        trading_halted = True

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
