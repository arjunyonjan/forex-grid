"""Two-sided grid broker — buy AND sell pending at every level simultaneously."""

import time
import random
import math
import os
import csv
from collections import deque

TRADE_LOG = "/root/forex-grid/trades.csv"
closed_trades = []

def _write_trade_log(side, entry, exit_p, pnl, gross, costs, reason, dur=None):
    file_exists = os.path.isfile(TRADE_LOG)
    with open(TRADE_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["time", "side", "entry", "exit", "pnl", "gross", "costs", "reason"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), side, entry, exit_p,
                    round(pnl, 2), round(gross, 2), round(costs, 2), reason])
    closed_trades.append({"t": time.strftime("%H:%M:%S"), "side": side,
                          "entry": entry, "exit": exit_p,
                          "pnl": round(pnl, 2), "reason": reason, "dur": dur})
    if len(closed_trades) > 50:
        closed_trades[:] = closed_trades[-50:]

API_KEY = "DUMMY_KEY"
ACCOUNT_ID = "101-001-12345678-001"
BASE = "https://api-fxpractice.oanda.com/v3"

LOT = 0.001
PIP_VALUE = 10.0
COMMISSION = 0.0
MAX_POSITIONS = 500
PIP = 0.01

ATR_WINDOW = 3600
MIN_SPACING = 60
MAX_SPACING = 600
ATR_DIVISOR = 0.7
TP_MULTIPLIER = 2
SL_MULTIPLIER = 2.5

DD_HALVE_THRESHOLD = 5.0
DD_STOP_THRESHOLD = 10.0
BASE_LOT = 0.001
MAX_BIAS = 20
MAX_TRADE_DAYS = 30

orders = []
trades = []
balance = 1000000.0
start_balance = 1000000.0
daily_start_balance = balance
month_start_balance = balance
last_day = time.localtime().tm_yday
last_month = time.localtime().tm_mon
equity_peak = balance
daily_trade_count = 0
total_trades = 0
hit_log = []

price_history = deque(maxlen=ATR_WINDOW)
current_atr = 5.0
_atr_raw = 5.0
current_spacing = 200
current_tp = 200
current_sl = 500
lot_size = BASE_LOT
trading_halted = False
safety_dd_halved = False
safety_dd_stopped = False
total_wins_cumulative = 0
total_losses_cumulative = 0
cumulative_win_pnl = 0.0
cumulative_loss_pnl = 0.0


class Order:
    def __init__(self, side, price, tp, level_idx):
        self.id = f"ord-{len(orders)+len(trades)+1}"
        self.side = side
        self.price = price
        self.tp = tp
        self.level_idx = level_idx
        self.created = time.time()
        self.filled = None
        self.pnl = 0
        self.cost = 0


def update_atr(mid):
    global current_atr, current_spacing, current_tp, current_sl, price_history, _atr_raw
    price_history.append(mid)
    n = len(price_history)
    if n < 3:
        return
    pm = price_history[-1]
    pp = price_history[-2]
    tick_pips = abs(pm - pp) / PIP
    window = min(n, 60)
    alpha = 2.0 / (window + 1)
    if n == 3:
        ema = tick_pips
    else:
        ema = _atr_raw + alpha * (tick_pips - _atr_raw)
    if ema < 0.01 or math.isnan(ema) or math.isinf(ema):
        ema = 0.01
    _atr_raw = ema
    current_atr = _atr_raw * math.sqrt(ATR_WINDOW)
    spacing = max(MIN_SPACING, min(MAX_SPACING, round(current_atr / ATR_DIVISOR)))
    if spacing != current_spacing:
        current_spacing = spacing
        current_tp = max(spacing + 1, round(spacing * TP_MULTIPLIER))
        current_sl = round(spacing * SL_MULTIPLIER)


def get_params():
    return {
        "atr": round(current_atr, 1),
        "spacing": current_spacing,
        "tp": current_tp,
        "sl": current_sl,
    }


def get_safety_status():
    upnl = sum(t.pnl for t in trades)
    eq = balance + upnl
    peak = max(equity_peak, eq)
    dd = (peak - eq) / peak * 100 if peak else 0
    safety_dd_halved = dd >= DD_HALVE_THRESHOLD
    safety_dd_stopped = dd >= DD_STOP_THRESHOLD
    if safety_dd_stopped:
        trading_halted = True; lot_size = BASE_LOT
    else:
        trading_halted = False
        if dd >= 7.5: lot_size = BASE_LOT * 0.25
        elif dd >= 5: lot_size = BASE_LOT * 0.5
        elif dd >= 3: lot_size = BASE_LOT * 0.75
        else: lot_size = BASE_LOT
    return {
        "lot": round(lot_size, 4),
        "halted": trading_halted,
        "dd_halved": safety_dd_halved,
        "dd_stopped": safety_dd_stopped,
        "dd_scale": "%.0f%%" % ((1 - lot_size / BASE_LOT) * 100) if lot_size < BASE_LOT else "full",
    }


def account_summary():
    global last_day, last_month, daily_start_balance, month_start_balance, balance, daily_trade_count, equity_peak
    upnl = sum(t.pnl for t in trades)
    eq = balance + upnl
    if eq > equity_peak:
        equity_peak = eq
    dd = (equity_peak - eq) / equity_peak * 100 if equity_peak else 0
    total_pnl = eq - start_balance
    rv = dict(
        balance=round(balance, 2), equity=round(eq, 2), upnl=round(upnl, 2),
        margin=0, margin_used=0, open_orders=len(orders), open_trades=len(trades),
        equity_peak=round(equity_peak, 2), drawdown=round(dd, 2),
        pnl_today=round(eq - daily_start_balance, 2),
        monthly_pnl=round(eq - month_start_balance, 2),
        total_pnl=round(total_pnl, 2), win_pnl=round(cumulative_win_pnl,2),
        wins=total_wins_cumulative,
        losses=total_losses_cumulative,
        loss_pnl=round(cumulative_loss_pnl,2), return_pct=round(total_pnl / start_balance * 100, 2),
        daily_trades=daily_trade_count, total_trades=total_trades,
        recent_closed=closed_trades[-20:],
    )
    rv.update(get_params())
    rv.update(get_safety_status())
    return rv
def _fmt_dur(s, now=None):
    if not s: return "--"
    n = now or time.time()
    if hasattr(n, "strftime"): s = s.timestamp() if hasattr(s, "timestamp") else s; n = n.timestamp()
    elif hasattr(s, "timestamp"): s = s.timestamp()
    d = int(n - s)
    if d < 60: return "%ds" % d
    if d < 3600: return "%dm%ds" % (d//60, d%60)
    if d < 86400: return "%dh%dm" % (d//3600, (d%3600)//60)
    return "%dd%dh" % (d//86400, (d%86400)//3600)


def open_positions(bid, ask, now=None):
    mid = (bid + ask) / 2
    result = []
    for t in trades:
        pips = (mid - t.price) / 0.01 if t.side == "buy" else (t.price - mid) / 0.01
        result.append({
            "id": t.id,
            "side": t.side,
            "entry": round(t.price, 2),
            "tp": round(t.tp, 2),
            "pips": round(pips, 1),
            "pnl": round(t.pnl, 2),
            "cost": t.cost,
            "dur": _fmt_dur(t.filled, now),
        })
    return result


def place_order(side, price, tp, level_idx):
    o = Order(side, price, tp, level_idx)
    orders.append(o)
    return {"order_id": o.id, "status": "pending"}


def cancel_order(oid):
    global orders
    orders = [o for o in orders if o.id != oid]


def tick_prices(bid, ask, grid, now=None):
    global orders, trades, balance, daily_trade_count, total_trades, total_wins_cumulative, total_losses_cumulative, cumulative_win_pnl, cumulative_loss_pnl
    mid = (bid + ask) / 2

    new_orders = []
    for o in orders:
        if o.side == "buy" and ask <= o.price:
            o.cost = COMMISSION
            o.filled = now or time.time()
            o.pnl = -o.cost
            trades.append(o)
            daily_trade_count += 1
            total_trades += 1
            hit_log.append({"t": time.strftime("%H:%M:%S"), "side": "BUY",
                            "price": o.price, "cost": o.cost})
            gs = current_spacing * PIP
            hed = Order("sell", o.price, round(o.price - gs, 2), o.level_idx)
            hed.cost = COMMISSION; hed.filled = now or time.time(); hed.pnl = -hed.cost
            trades.append(hed)
            daily_trade_count += 1
            total_trades += 1
        elif o.side == "sell" and bid >= o.price:
            o.cost = COMMISSION
            o.filled = now or time.time()
            o.pnl = -o.cost
            trades.append(o)
            daily_trade_count += 1
            total_trades += 1
            hit_log.append({"t": time.strftime("%H:%M:%S"), "side": "SELL",
                            "price": o.price, "cost": o.cost})
            gs = current_spacing * PIP
            hed = Order("buy", o.price, round(o.price + gs, 2), o.level_idx)
            hed.cost = COMMISSION; hed.filled = now or time.time(); hed.pnl = -hed.cost
            trades.append(hed)
            daily_trade_count += 1
            total_trades += 1
        else:
            new_orders.append(o)
    orders = new_orders

    remaining = []
    for t in trades:
        if t.filled:
            t_now = now or time.time()
            if hasattr(t_now, "strftime"):
                t_sec = t.filled.timestamp() if hasattr(t.filled, "timestamp") else t.filled
                n_sec = t_now.timestamp()
            else:
                t_sec = t.filled.timestamp() if hasattr(t.filled, "timestamp") else t.filled
                n_sec = t_now
            dur = n_sec - t_sec
            if dur > MAX_TRADE_DAYS * 86400:
                gross = (mid - t.price) / 0.01 * PIP_VALUE * lot_size if t.side == "buy" else (t.price - mid) / 0.01 * PIP_VALUE * lot_size
                exit_cost = round(abs(ask - bid) + COMMISSION, 2)
                pnl = gross - exit_cost - abs(t.cost)
                balance += pnl
                total_losses_cumulative += 1
                cumulative_loss_pnl += pnl
                _write_trade_log(t.side.upper(), t.price, round(mid, 2), pnl, gross, exit_cost + abs(t.cost), "TIMEOUT", _fmt_dur(t.filled, now))
                hit_log.append({"t": time.strftime("%H:%M:%S"), "side": "TIMEOUT", "price": round(mid, 2), "pnl": round(pnl, 2), "dur": _fmt_dur(t.filled, now)})
                continue
        if t.side == "buy" and mid >= t.tp:
            gross = (t.tp - t.price) / 0.01 * PIP_VALUE * lot_size
            exit_cost = round(abs(ask - bid) + COMMISSION, 2)
            pnl = gross - exit_cost - abs(t.cost)
            balance += pnl
            total_wins_cumulative += 1
            cumulative_win_pnl += pnl
            _write_trade_log("BUY", t.price, t.tp, pnl, gross,
                             exit_cost + abs(t.cost), "TP", _fmt_dur(t.filled))
            hit_log.append({"t": time.strftime("%H:%M:%S"), "side": "TP-BUY",
                            "dur": _fmt_dur(t.filled),
                            "price": t.tp, "pnl": round(pnl, 2),
                            "gross": round(gross, 2),
                            "costs": round(exit_cost + abs(t.cost), 2)})
        elif t.side == "sell" and mid <= t.tp:
            gross = (t.price - t.tp) / 0.01 * PIP_VALUE * lot_size
            exit_cost = round(abs(ask - bid) + COMMISSION, 2)
            pnl = gross - exit_cost - abs(t.cost)
            balance += pnl
            total_wins_cumulative += 1
            cumulative_win_pnl += pnl
            _write_trade_log("SELL", t.price, t.tp, pnl, gross,
                             exit_cost + abs(t.cost), "TP", _fmt_dur(t.filled))
            hit_log.append({"t": time.strftime("%H:%M:%S"), "side": "TP-SELL",
                            "dur": _fmt_dur(t.filled),
                            "price": t.tp, "pnl": round(pnl, 2),
                            "gross": round(gross, 2),
                            "costs": round(exit_cost + abs(t.cost), 2)})
        else:
            mid = (bid + ask) / 2
            if t.side == "buy":
                t.pnl = (mid - t.price) / 0.01 * PIP_VALUE * lot_size - abs(t.cost)
            else:
                t.pnl = (t.price - mid) / 0.01 * PIP_VALUE * lot_size - abs(t.cost)
            remaining.append(t)

    trades = remaining
    if len(hit_log) > 200:
        hit_log[:] = hit_log[-200:]


def grid_hits(grid, mid, gs=None):
    global orders
    if gs is None:
        gs = current_spacing * PIP
    if trading_halted:
        return

    step = gs or (current_spacing * PIP)
    existing = set()
    for o in orders:
        k = round(o.price / step) if step else 0
        existing.add((k, o.side))
    for t in trades:
        k = round(t.price / step) if step else 0
        existing.add((k, t.side))

    to_place = []
    for lvl in grid:
        if abs(lvl - mid) < gs * 0.4:
            continue
        lk = round(lvl / step) if step else 0
        if mid > lvl and (lk, "buy") not in existing:
            tp = round(lvl + gs * TP_MULTIPLIER, 2)
            to_place.append(("buy", lvl, tp, lk))
        if mid < lvl and (lk, "sell") not in existing:
            tp = round(lvl - gs * TP_MULTIPLIER, 2)
            to_place.append(("sell", lvl, tp, lk))

    sell_count = sum(1 for t in trades if t.side == "sell")
    buy_count = sum(1 for t in trades if t.side == "buy")
    bias = sell_count - buy_count
    if bias >= MAX_BIAS:
        to_place = [x for x in to_place if x[0] != "sell"]
    elif bias <= -MAX_BIAS:
        to_place = [x for x in to_place if x[0] != "buy"]

    active = len(orders) + len(trades)
    slots = MAX_POSITIONS - active
    if slots <= 0:
        return

    to_place.sort(key=lambda x: abs(x[1] - mid))
    to_place = to_place[:slots]

    for side, lvl, tp, idx in to_place:
        place_order(side, lvl, tp, idx)


def simulate(hours=24, start_price=4050.0, spacing=200, init_bal=10000.0):
    import copy
    saved = copy.deepcopy({
        "orders": orders, "trades": trades, "balance": balance,
        "start_balance": start_balance, "daily_start_balance": daily_start_balance,
        "month_start_balance": month_start_balance, "equity_peak": equity_peak,
        "daily_trade_count": daily_trade_count, "total_trades": total_trades,
        "hit_log": hit_log, "price_history": list(price_history),
        "current_atr": current_atr, "current_spacing": current_spacing,
        "current_tp": current_tp, "current_sl": current_sl,
        "lot_size": lot_size, "trading_halted": trading_halted,
    })

    orders.clear()
    trades.clear()
    hit_log.clear()
    price_history.clear()
    balance = 10000.0
    equity_peak = balance
    daily_trade_count = 0
    total_trades = 0
    current_atr = 5.0
    current_spacing = spacing
    current_tp = 100
    current_sl = round(current_spacing * SL_MULTIPLIER)
    lot_size = BASE_LOT
    balance = init_bal
    trading_halted = False

    mid = start_price
    spread = 0.0
    vol = 0.15
    dt = 1.0 / (365.25 * 86400)

    mid_p = start_price
    peak_eq = balance
    max_dd = 0

    step = current_spacing * PIP
    p = round(mid_p / step) * step
    grid = [round(p + i * step, 2) for i in range(-15, 16)]
    grid_hits(grid, mid_p, gs=step)

    tick_count = hours * 3600
    for _ in range(tick_count):
        epsilon = random.gauss(0, 1)
        ret = -0.5 * vol * vol * dt + vol * epsilon * dt ** 0.5
        mid_p *= math.exp(ret)
        bid = mid_p - spread / 2
        ask = mid_p + spread / 2
        update_atr(mid_p)
        step = current_spacing * PIP
        p = round(mid_p / step) * step
        grid = [round(p + i * step, 2) for i in range(-15, 16)]
        tick_prices(bid, ask, grid)
        grid_hits(grid, mid_p, gs=step)
        eq = balance + sum(t.pnl for t in trades)
        if eq > peak_eq:
            peak_eq = eq
        dd = (peak_eq - eq) / peak_eq * 100 if peak_eq else 0
        if dd > max_dd:
            max_dd = dd
        if eq <= 0:
            break

    end_eq = balance + sum(t.pnl for t in trades)
    monthly_equiv = (end_eq - 10000) / 10000 * 100 * (30 * 24 / max(hours, 1))
    result = {
        "start_balance": 10000.0,
        "end_balance": round(balance, 2),
        "end_equity": round(end_eq, 2),
        "total_trades": total_trades,
        "wins": total_wins_cumulative,
        "losses": total_losses_cumulative,
        "max_dd": round(max_dd, 2),
        "monthly_equiv": round(monthly_equiv, 2),
        "hours": hours,
        "avg_atr": round(current_atr, 1),
        "avg_spacing": current_spacing,
    }

    orders.clear()
    trades.clear()
    hit_log.clear()
    price_history.clear()
    balance = saved["balance"]
    equity_peak = saved["equity_peak"]
    daily_trade_count = saved["daily_trade_count"]
    total_trades = saved["total_trades"]
    hit_log.extend(saved["hit_log"])
    price_history.extend(saved["price_history"])
    current_atr = saved["current_atr"]
    current_spacing = saved["current_spacing"]
    current_tp = saved["current_tp"]
    current_sl = saved["current_sl"]
    lot_size = saved["lot_size"]
    trading_halted = saved["trading_halted"]
    total_wins_cumulative = saved["total_wins_cumulative"]
    total_losses_cumulative = saved["total_losses_cumulative"]
    cumulative_win_pnl = saved["cumulative_win_pnl"]
    cumulative_loss_pnl = saved["cumulative_loss_pnl"]

    return result


def simulate_from_keyframes(keyframes, init_bal=10000.0, spacing=100, tick_scale=1440):
    """Simulate grid bot over real OHLC daily keyframes."""
    import copy
    global orders, trades, hit_log, closed_trades, price_history
    global current_atr, current_spacing, current_tp, current_sl
    global lot_size, trading_halted, equity_peak, balance, daily_trade_count, total_trades

    saved = copy.deepcopy({
        "orders": orders, "trades": trades,
        "balance": balance, "start_balance": start_balance,
        "daily_start_balance": daily_start_balance,
        "month_start_balance": month_start_balance,
        "equity_peak": equity_peak,
        "daily_trade_count": daily_trade_count,
        "total_trades": total_trades,
        "hit_log": hit_log, "price_history": list(price_history),
        "current_atr": current_atr, "current_spacing": current_spacing,
        "current_tp": current_tp, "current_sl": current_sl,
        "lot_size": lot_size, "trading_halted": trading_halted,
        "closed_trades": list(closed_trades),
        "total_wins_cumulative": total_wins_cumulative,
        "total_losses_cumulative": total_losses_cumulative,
        "cumulative_win_pnl": cumulative_win_pnl,
        "cumulative_loss_pnl": cumulative_loss_pnl,
    })

    orders.clear()
    trades.clear()
    hit_log.clear()
    closed_trades.clear()
    price_history.clear()
    bal = float(init_bal)
    init_bal = bal
    total_wins_cumulative = 0
    total_losses_cumulative = 0
    cumulative_win_pnl = 0.0
    cumulative_loss_pnl = 0.0
    equity_peak = bal
    daily_trade_count = 0
    total_trades = 0
    current_atr = 5.0
    current_spacing = spacing
    current_tp = 100
    current_sl = round(current_spacing * SL_MULTIPLIER)
    lot_size = BASE_LOT
    balance = init_bal
    trading_halted = False

    spread = 0.0
    peak_eq = bal
    max_dd = 0
    total_ticks = 0

    if not keyframes:
        return {"error": "No keyframes provided"}

    mid_p = keyframes[0]["open"]
    step = current_spacing * PIP
    p = round(mid_p / step) * step
    grid = [round(p + i * step, 2) for i in range(-15, 16)]
    grid_hits(grid, mid_p, gs=step)

    for day_idx, day in enumerate(keyframes):
        o = day["open"]
        h = day["high"]
        l = day["low"]
        c = day["close"]
        daily_range = max(h - l, 1.0)
        sqrt_t = math.sqrt(float(tick_scale))
        phi = 0.3
        per_tick_vol = daily_range / sqrt_t * math.sqrt(1 - phi * phi)
        noise_prev = 0.0
        for tick in range(tick_scale):
            t = (tick + 1) / float(tick_scale)
            bridge = o + (c - o) * t
            noise = phi * noise_prev + random.gauss(0, per_tick_vol)
            noise_prev = noise
            mid_p = bridge + noise
            mid_p = max(l, min(h, mid_p))

            bid = mid_p - spread / 2
            ask = mid_p + spread / 2
            step = current_spacing * PIP
            p = round(mid_p / step) * step
            grid = [round(p + i * step, 2) for i in range(-15, 16)]
            tick_prices(bid, ask, grid)
            grid_hits(grid, mid_p, gs=step)
            total_ticks += 1

            bal = balance
            eq = bal + sum(t.pnl for t in trades)
            if eq > peak_eq:
                peak_eq = eq
            dd = (peak_eq - eq) / peak_eq * 100 if peak_eq else 0
            if dd > max_dd:
                max_dd = dd
            _st = get_safety_status()
            trading_halted = _st['halted']
            lot_size = _st['lot']
            if eq <= 0:
                break

    end_eq = bal + sum(t.pnl for t in trades)
    total_pnl = end_eq - init_bal
    wins = total_wins_cumulative
    losses = total_losses_cumulative
    tp_hits = [h for h in hit_log if h.get("side", "").startswith("TP")]
    avg_tp_pnl = round(cumulative_win_pnl / max(wins, 1), 2)
    exit_costs = [h.get("costs", 0) for h in tp_hits if "costs" in h]
    avg_exit_cost = round(sum(exit_costs) / len(exit_costs), 2) if exit_costs else 0

    result = {
        "start_balance": round(init_bal, 2),
        "end_balance": round(balance, 2),
        "end_equity": round(balance + sum(t.pnl for t in trades), 2),
        "total_pnl": round(balance + sum(t.pnl for t in trades) - init_bal, 2),
        "return_pct": round((balance + sum(t.pnl for t in trades) - init_bal) / init_bal * 100, 2),
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "avg_tp_pnl": avg_tp_pnl,
        "avg_exit_cost": avg_exit_cost,
        "max_dd": round(max_dd, 2),
        "days": len(keyframes),
        "ticks": total_ticks,
        "avg_atr": round(current_atr, 1),
        "avg_spacing": current_spacing,
    }

    orders.clear()
    trades.clear()
    hit_log.clear()
    closed_trades.clear()
    price_history.clear()
    balance = saved["balance"]
    bal = saved["balance"]
    equity_peak = saved["equity_peak"]
    daily_trade_count = saved["daily_trade_count"]
    total_trades = saved["total_trades"]
    hit_log.extend(saved["hit_log"])
    closed_trades.extend(saved.get("closed_trades", []))
    price_history.extend(saved["price_history"])
    current_atr = saved["current_atr"]
    total_wins_cumulative = saved["total_wins_cumulative"]
    total_losses_cumulative = saved["total_losses_cumulative"]
    cumulative_win_pnl = saved["cumulative_win_pnl"]
    cumulative_loss_pnl = saved["cumulative_loss_pnl"]
    current_spacing = saved["current_spacing"]
    current_tp = saved["current_tp"]
    current_sl = saved["current_sl"]
    lot_size = saved["lot_size"]
    trading_halted = saved["trading_halted"]

    return result

def _check_guardrails(bal, peak, init_bal):
    """Inline guardrail check for sim loops. Returns (halted, new_lot)."""
    eq = bal + sum(t.pnl for t in trades)
    dd = (peak - eq) / peak * 100 if peak else 0
    if dd >= DD_STOP_THRESHOLD:
        return True, BASE_LOT
    if dd >= DD_HALVE_THRESHOLD:
        return False, BASE_LOT / 2
    return False, BASE_LOT
