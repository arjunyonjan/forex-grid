import json, time, random, asyncio, math
from datetime import datetime, timedelta
from pathlib import Path
from broker import account_summary, open_positions, tick_prices, place_orders, update_atr, get_params, current_spacing, PIP, BASE_SPREAD, DYNAMIC_SPREAD, ATR_WINDOW, _walk_bar, MIN_SPACING, MAX_SPACING, ATR_DIVISOR, TP_MULTIPLIER, MR_ENABLED, MR_LOOKBACK, MR_THRESHOLD, update_sma, current_sma, MR_ENABLED, MR_LOOKBACK, MR_THRESHOLD, update_sma, current_sma, monthly_pnl, trend_strength, HEDGE_CLOSE_ENABLED, TREND_FILTER_ENABLED
from collections import deque
from aiohttp import web

PIP_VALUE = 10.0
QUEUE_MAXSIZE = 60
BASE_PRICE = 4110.0
spread = BASE_SPREAD
speed_multiplier = 100
current_preset_label = "Full Timeline"
last_broadcast = 0.0

def load_keyframes():
    sources = []
    basedir = Path(__file__).parent
    for fname, res in [("gcf_1m.json", 60), ("gcf_5m.json", 300), ("gcf_15m.json", 900), ("gcf_1h.json", 3600), ("gcf_daily.json", 86400), ("gcf_ukraine_hourly.json", 3600)]:
        p = basedir / fname
        if p.exists():
            data = json.loads(p.read_text())
            for d in data:
                d["res"] = res
            sources.extend(data)
    sources.sort(key=lambda x: (x["date"], x["res"]))
    return sources

keyframes = [d for d in load_keyframes() if d.get("res") == 900 and not (d["open"] == d["high"] == d["low"] == d["close"])]

_daily_raw = json.loads((Path(__file__).parent / "gcf_daily.json").read_text()) if (Path(__file__).parent / "gcf_daily.json").exists() else []
_daily_bars = [d for d in _daily_raw if not (d["open"] == d["high"] == d["low"] == d["close"])]
if keyframes and _daily_bars:
    s, e = keyframes[0]["date"][:10], keyframes[-1]["date"][:10]
    dr = [d for d in _daily_bars if s <= d["date"][:10] <= e]
    if dr:
        atr_r = 0.0
        for d in dr:
            rp = max(d["high"] - d["low"], 0.1)
            atr_r = atr_r + (2/15)*(rp - atr_r) if atr_r > 0 else rp
        update_atr(bar_range=atr_r)

daily_moves = []
if keyframes:
    days = {}
    for d in keyframes:
        date = d["date"][:10]
        if date not in days:
            days[date] = {"date": date, "o": d["open"], "h": d["high"], "l": d["low"], "c": d["close"]}
        else:
            days[date]["h"] = max(days[date]["h"], d["high"])
            days[date]["l"] = min(days[date]["l"], d["low"])
            days[date]["c"] = d["close"]
    for day in days.values():
        r = round((day["h"] - day["l"]) / 0.01)
        t = round((day["c"] - day["o"]) / 0.01)
        daily_moves.append({"date": day["date"], "o": day["o"], "h": day["h"], "l": day["l"], "c": day["c"], "range": r, "trend": t, "dir": "DOWN" if day["c"] < day["o"] else "UP"})
    daily_moves.sort(key=lambda x: x["range"], reverse=True)

monthly_moves = []
all_kf = load_keyframes()
all_2022 = [d for d in all_kf if d["date"][:4] == "2022"]
if all_2022:
    months = {}
    for d in all_2022:
        m = d["date"][:7]
        if m not in months:
            months[m] = {"date": m, "o": d["open"], "h": d["high"], "l": d["low"], "c": d["close"]}
        else:
            months[m]["h"] = max(months[m]["h"], d["high"])
            months[m]["l"] = min(months[m]["l"], d["low"])
            months[m]["c"] = d["close"]
    for m in sorted(months):
        day = months[m]
        r = round((day["h"] - day["l"]) / 0.01)
        t = round((day["c"] - day["o"]) / 0.01)
        monthly_moves.append({"date": m, "o": day["o"], "h": day["h"], "l": day["l"], "c": day["c"], "range": r, "trend": t, "dir": "DOWN" if day["c"] < day["o"] else "UP"})

clients = set()

async def broadcast(msg):
    dead = []
    for q in list(clients):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            try:
                while not q.empty():
                    q.get_nowait()
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        except Exception:
            dead.append(q)
    for q in dead:
        clients.discard(q)

async def stream_handler(request):
    q = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    clients.add(q)
    resp = web.StreamResponse()
    resp.content_type = "text/event-stream"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    await resp.prepare(request)
    init_msg = {"type": "init", "daily_moves": daily_moves, "monthly_moves": monthly_moves, "preset_label": current_preset_label}
    init_data = "data: " + json.dumps(init_msg) + "\n\n"
    await resp.write(init_data.encode())
    try:
        while True:
            msg = await q.get()
            data = "data: " + json.dumps(msg) + "\n\n"
            await resp.write(data.encode())
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        clients.discard(q)
    return resp

async def set_speed(request):
    global speed_multiplier
    try:
        body = await request.json()
        speed_multiplier = max(1, min(1000000, int(body.get("speed", 1000))))
        return web.json_response({"speed": speed_multiplier})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def restart_sim(request):
    global _loop_active, current_preset_label
    current_preset_label = "Default"
    _loop_active = False
    await asyncio.sleep(0.5)
    import broker as _b
    _b.orders.clear()
    _b.trades.clear()
    _b.hit_log.clear()
    _b.closed_trades.clear()
    _b.price_history.clear()
    _b.balance = 1000000.0
    _b.start_balance = 1000000.0
    _b.equity_peak = 1000000.0
    _b.daily_trade_count = 0
    _b.total_trades = 0
    _b.current_atr = 5.0
    _b._atr_raw = 5.0
    _b.current_spacing = 1500
    _b.current_tp = 1500
    _b.lot_size = _b.BASE_LOT
    _b.trading_halted = False
    _loop_active = True
    asyncio.ensure_future(tick_loop())
    return web.json_response({"status": "restarted"})

PRESETS = {
    "ukraine": {"start": "2022-01-01", "end": "2022-06-30", "speed": 100, "label": "Ukraine War"},
    "crash2022": {"start": "2022-06-01", "end": "2022-11-30", "speed": 100, "label": "2022 Crash"},
    "svb": {"start": "2023-02-01", "end": "2023-05-31", "speed": 100, "label": "SVB Crisis"},
    "oct2023": {"start": "2023-09-01", "end": "2023-11-30", "speed": 100, "label": "Oct 2023 War"},
    "rally2024": {"start": "2024-03-01", "end": "2024-06-30", "speed": 100, "label": "Gold Rally 24"},
    "election2024": {"start": "2024-09-01", "end": "2024-12-31", "speed": 100, "label": "US Election 24"},
    "tariff2025": {"start": "2025-03-01", "end": "2025-06-30", "speed": 100, "label": "Tariff War 25"},
    "crash2026": {"start": "2026-01-01", "end": "2026-03-31", "speed": 10, "label": "130K Crash"},
    "full2022": {"start": "2022-01-01", "end": "2022-12-31", "speed": 1000, "label": "Normal 2022"},
    "all": {"start": "2022-01-01", "end": "2026-07-31", "speed": 1000, "label": "Full Timeline"},
    "july2026": {"start": "2026-07-01", "end": "2026-07-31", "speed": 100, "label": "July 2026"},
    "jan2026": {"start": "2026-01-02", "end": "2026-01-31", "speed": 100, "label": "Jan 2026"},
    "last7d": {"start": "2026-07-19", "end": "2026-07-24", "speed": 100, "label": "Last 7 Days"},
    "5m": {"start": "2026-06-24", "end": "2026-07-24", "speed": 50, "label": "1 Month (5m Data)", "res": 300},
    "jul28": {"start": "2026-07-28", "end": "2026-07-28", "speed": 10, "label": "July 28 (1m)"},
}

_loop_active = False

async def set_preset(request):
    global keyframes, daily_moves, monthly_moves, speed_multiplier, _loop_active, current_preset_label
    try:
        body = await request.json()
        name = body.get("name", "")
        p = PRESETS.get(name)
        if not p:
            return web.json_response({"error": f"Unknown preset: {name}"}, status=400)
        _loop_active = False
        await asyncio.sleep(0.5)
        import broker as _b
        _b.orders.clear()
        _b.trades.clear()
        _b.hit_log.clear()
        _b.closed_trades.clear()
        _b.price_history.clear()
        _b.balance = 1000000.0
        _b.start_balance = 1000000.0
        _b.equity_peak = 1000000.0
        _b.daily_trade_count = 0
        _b.total_trades = 0
        _b.current_atr = 5.0
        _b._atr_raw = 5.0
        _b.current_spacing = 1500
        _b.current_tp = 1500
        _b.current_sl = 1875
        _b.trading_halted = False
        all_kf = load_keyframes()
        res_filter = p.get("res") if "res" in p else None
        kf_pool = [k for k in all_kf if k.get("res") == res_filter] if res_filter else all_kf
        keyframes = [k for k in kf_pool if p["start"] <= k["date"][:10] <= p["end"] and not (k["open"] == k["high"] == k["low"] == k["close"])]
        daily_moves = []
        if keyframes:
            days = {}
            for d in keyframes:
                date = d["date"][:10]
                if date not in days:
                    days[date] = {"date": date, "o": d["open"], "h": d["high"], "l": d["low"], "c": d["close"]}
                else:
                    days[date]["h"] = max(days[date]["h"], d["high"])
                    days[date]["l"] = min(days[date]["l"], d["low"])
                    days[date]["c"] = d["close"]
            for day in days.values():
                r = round((day["h"] - day["l"]) / 0.01)
                t = round((day["c"] - day["o"]) / 0.01)
                daily_moves.append({"date": day["date"], "o": day["o"], "h": day["h"], "l": day["l"], "c": day["c"], "range": r, "trend": t, "dir": "DOWN" if day["c"] < day["o"] else "UP"})
            daily_moves.sort(key=lambda x: x["range"], reverse=True)
        speed_multiplier = p["speed"]
        current_preset_label = p["label"]
        _loop_active = True
        asyncio.ensure_future(tick_loop())
        return web.json_response({"status": "switched", "days": len(keyframes), "speed": p["speed"], "label": p["label"]})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def toggle_trend_filter(request):
    import broker as _b
    try:
        body = await request.json()
        _b.TREND_FILTER_ENABLED = body.get("enabled", not _b.TREND_FILTER_ENABLED)
        _b.TREND_HEDGE_DISABLE = body.get("disable_on_trend", _b.TREND_HEDGE_DISABLE)
        return web.json_response({"trend_filter": _b.TREND_FILTER_ENABLED, "disable_on_trend": _b.TREND_HEDGE_DISABLE})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def simulate_handler(request):
    hours = int(request.query.get("hours", 24))
    result = await asyncio.to_thread(simulate, hours, BASE_PRICE)
    return web.json_response(result)

async def sim_keyframes_handler(request):
    try:
        body = await request.json()
        kf = body.get("keyframes", [])
        sp = body.get("spacing", 100)
        result = await asyncio.to_thread(simulate_from_keyframes, kf, 1000000.0, sp, body.get("tick_scale", 480))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

async def results_handler(request):
    import broker as _b
    now_t = time.time()
    with open("/dev/null", "w") as _:
        pos = _b.open_positions(0, 0, now_t)
    return web.json_response({
        "account": _b.account_summary(),
        "open_trades": pos,
        "hit_log": list(_b.hit_log),
        "closed_trades": list(_b.closed_trades),
        "preset": current_preset_label,
        "params": _b.get_params(),
    })

def _parse_bar_date(date_str):
    s = date_str[:16]
    if len(s) == 10:
        s += " 00:00"
    return __import__("datetime").datetime.strptime(s, "%Y-%m-%d %H:%M")

def run_headless(preset_name):
    import json, time, sys
    from pathlib import Path
    import broker as _b
    p = PRESETS.get(preset_name)
    if not p:
        return {"error": f"Unknown preset: {preset_name}"}
    all_kf = load_keyframes()
    res_filter = p.get("res")
    kf_pool = [k for k in all_kf if k.get("res") == res_filter] if res_filter else all_kf
    kf = [k for k in kf_pool if p["start"] <= k["date"][:10] <= p["end"] and not (k["open"] == k["high"] == k["low"] == k["close"])]
    if not kf:
        return {"error": f"No data for {preset_name} ({p['start']} to {p['end']})"}
    _b.TREND_FILTER_ENABLED = True
    _b.TREND_HEDGE_DISABLE = False
    _b.HEDGE_CLOSE_ENABLED = True
    _b.balance = _b.start_balance = _b.equity_peak = 1000000.0
    _b.orders.clear(); _b.trades.clear(); _b.hit_log.clear(); _b.closed_trades.clear()
    _b.mr_price_history.clear(); _b.current_sma = 0.0
    _b.current_atr = _b._atr_raw = 5.0; _b.current_spacing = 1500
    _b.current_tp = round(_b.current_spacing * _b.TP_MULTIPLIER)
    _b.daily_trade_count = 0; _b.total_trades = 0; _b.lot_size = _b.BASE_LOT
    _b.place_orders(kf[0]["open"])
    for idx, bar in enumerate(kf):
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        _b.update_atr(bar_range=max(h - l, 0.1))
        spread = max(20, min(150, _b.current_atr * 0.1)) if _b.DYNAMIC_SPREAD else _b.BASE_SPREAD
        ts = _parse_bar_date(bar["date"])
        for mid_p in _b._walk_bar(o, h, l, c, pip_step=100):
            _b.update_sma(mid_p)
            _b.tick_prices(mid_p - spread/2, mid_p + spread/2, ts)
            if len(_chart_micro) < 1000 and (len(_chart_micro) == 0 or round(mid_p,2) != _chart_micro[-1].get("p",0)):
                _chart_micro.append({"p": round(mid_p,2), "a": round(_b.micro_atr, 1)})
    acct = _b.account_summary()
    wins = sum(1 for h in _b.hit_log if h.get("pnl",0) > 0)
    losses = sum(1 for h in _b.hit_log if h.get("pnl",0) < 0)
    won = round(sum(h["pnl"] for h in _b.hit_log if h["pnl"] > 0), 2)
    lost = round(sum(h["pnl"] for h in _b.hit_log if h["pnl"] < 0), 2)
    tp_hits = sum(1 for h in _b.hit_log if "TP-" in h.get("side",""))
    hedge = sum(1 for h in _b.hit_log if "HEDGE" in h.get("side",""))
    cleanup = sum(1 for h in _b.hit_log if "CLEANUP" in h.get("side",""))
    return {
        "preset": preset_name, "label": p["label"],
        "start": p["start"], "end": p["end"],
        "bars": len(kf),
        "start_balance": 1000000.0,
        "end_balance": _b.balance,
        "end_equity": acct.get("equity"),
        "total_pnl": round(_b.balance - 1000000, 2),
        "return_pct": acct["return_pct"],
        "max_dd": acct["drawdown"],
        "total_trades": acct["total_trades"],
        "wins": wins, "losses": losses,
        "win_pnl": won, "loss_pnl": lost,
        "pf": round(abs(won/lost), 2) if lost else 999,
        "tp_hits": tp_hits, "hedge_closes": hedge, "cleanups": cleanup,
        "final_atr": _b.current_atr, "final_spacing": _b.current_spacing,
    }

_report_cache = {}

async def report_handler(request):
    preset_name = request.match_info.get("preset", "")
    if preset_name in _report_cache:
        return web.json_response(_report_cache[preset_name])
    result = await asyncio.to_thread(run_headless, preset_name)
    if "error" not in result:
        _report_cache[preset_name] = result
    return web.json_response(result)

async def index(request):
    resp = web.FileResponse(Path(__file__).parent / "index.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp

async def static_handler(request):
    path = request.match_info["path"]
    file = Path(__file__).parent / path
    if file.is_file():
        resp = web.FileResponse(file)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return resp
    raise web.HTTPNotFound()

async def tick_loop():
    global last_broadcast, _loop_active
    if not _loop_active:
        _loop_active = True
    if not keyframes:
        return
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
    _b._atr_raw = 5.0
    _b.current_spacing = 1500
    _b.current_tp = 1500
    _b.current_sl = 1500
    _b.lot_size = _b.BASE_LOT

    kf = keyframes
    total_kf = len(kf)
    mid_p = kf[0]["open"]
    tick_count = 0
    noise_prev = 0.0
    phi = 0.85
    atr_short = __import__("collections").deque(maxlen=60)
    atr_long = __import__("collections").deque(maxlen=1440)
    prev_mid_for_atr = mid_p
    reactive_alert_day = -1

    vol_events = {
        "2022-01-03": "New Year, gold consolidates",
        "2022-01-04": "Fed tapering expectations",
        "2022-02-14": "\uD83C\uDDFA\uD83C\uDDE6 Ukraine invasion imminent — gold 1973 spike incoming",
        "2022-02-24": "\uD83C\uDDFA\uD83C\uDDE6 Russia invades Ukraine — gold 2072 peak",
        "2022-03-01": "Fed rate hikes begin",
        "2022-03-08": "Gold at 2072 war high",
        "2022-06-15": "Fed 75bp hike — gold crashes",
        "2022-09-28": "Gold 1620 — 2-year low, DXY 114",
        "2022-11-03": "Fed pivot hopes — gold 1778",
        "2023-03-10": "\uD83C\uDFE6 SVB collapse — banking crisis",
        "2023-05-04": "Gold 2072 new ATH — debt ceiling",
        "2023-10-07": "\uD83C\uDDF5\uD83C\uDDF8 Hamas attack — gold 2004",
        "2023-12-04": "Gold 2130 ATH — rate cut hopes",
        "2024-03-08": "Gold 2200 — central bank buying",
        "2024-04-19": "\uD83C\uDF0D Iran-Israel tensions — gold 2429",
        "2024-09-18": "Fed cuts 50bp — gold 2672",
        "2025-01-20": "\uD83C\uDDFA\uD83C\uDDF8 Trump tariff threats — gold 2838",
        "2025-04-02": "\uD83C\uDF0D Tariff war escalates — gold 3485",
        "2025-09-15": "BRICS+ summit — de-dollarization",
        "2025-10-15": "\uD83C\uDFDB\uFE0F US fiscal crisis — gold 4358",
        "2026-01-29": "Gold 5586 parabolic spike — reserve crisis",
        "2026-03-02": "\u26A1 Gold crash begins — 5405 to 4100",
        "2026-03-23": "Gold 4100 — liquidity crisis low",
    }
    vol_alerts = {}
    for day_idx in range(total_kf):
        day_range = max(kf[day_idx]["high"] - kf[day_idx]["low"], 1.0)
        max_fwd = day_range
        max_date = kf[day_idx]["date"][:10]
        for fwd in range(1, min(8, total_kf - day_idx)):
            fwd_r = max(kf[day_idx + fwd]["high"] - kf[day_idx + fwd]["low"], 1.0)
            if fwd_r > max_fwd:
                max_fwd = fwd_r
                max_date = kf[day_idx + fwd]["date"][:10]
        if max_fwd > 15.0:
            range_pips = round(max_fwd / 0.01)
            ev = vol_events.get(max_date, "")
            ev_prefix = ev + " — " if ev else ""
            if range_pips > 5000:
                vol_alerts[day_idx] = {"level": "CRITICAL", "msg": f"{ev_prefix}{range_pips}pip spike incoming within 7 days", "pips": range_pips, "event": ev}
            elif range_pips > 2500:
                vol_alerts[day_idx] = {"level": "WARNING", "msg": f"{ev_prefix}{range_pips}pip volatility expected within 7 days", "pips": range_pips, "event": ev}
            elif range_pips > 1000:
                vol_alerts[day_idx] = {"level": "NOTICE", "msg": f"{ev_prefix}{range_pips}pip move possible within 7 days", "pips": range_pips, "event": ev}

    _broker = __import__('broker')
    _broker.current_spacing = 1500
    _broker.current_tp = 1500
    if _daily_bars:
        s, e = kf[0]["date"][:10], kf[-1]["date"][:10]
        dr = [d for d in _daily_bars if s <= d["date"][:10] <= e]
        if dr:
            atr_r = 0.0
            for d in dr:
                rp = max(d["high"] - d["low"], 0.1)
                atr_r = atr_r + (2/15)*(rp - atr_r) if atr_r > 0 else rp
            _broker.current_atr = round(atr_r / _broker.PIP, 1)
            _broker._atr_raw = _broker.current_atr
            _broker.current_spacing = max(MIN_SPACING, min(MAX_SPACING, round(_broker.current_atr / ATR_DIVISOR)))
            _broker.current_tp = max(_broker.current_spacing + 1, round(_broker.current_spacing * TP_MULTIPLIER))
    place_orders(kf[0]["open"])

    for day_idx in range(total_kf):
        if not _loop_active:
            return
        day = kf[day_idx]
        o, h, l, c = day["open"], day["high"], day["low"], day["close"]
        res = day.get("res", 86400)
        day_start = datetime.strptime(day["date"][:10], "%Y-%m-%d")
        day_seconds = int(day["date"][11:13]) * 3600 + int(day["date"][14:16]) * 60 if len(day["date"]) > 10 else 0
        _b.daily_start_balance = _b.balance
        day_start_bal = _b.balance
        day_start_trades = _b.total_trades

        pip_step = 10
        bar_ticks = _walk_bar(o, h, l, c, pip_step)

        for tick_idx, mid_p in enumerate(bar_ticks):
            if not _loop_active:
                return
            pip_move = abs(mid_p - prev_mid_for_atr) / PIP
            prev_mid_for_atr = mid_p
            atr_short.append(pip_move)
            atr_long.append(pip_move)
            reactive_alert = None
            if len(atr_short) >= 60 and len(atr_long) >= 1440:
                short_avg = sum(atr_short) / len(atr_short)
                long_avg = sum(atr_long) / len(atr_long)
                ratio = short_avg / max(long_avg, 0.01)
                if ratio > 5.0 and day_idx != reactive_alert_day:
                    reactive_alert_day = day_idx
                    reactive_alert = {"level": "CRITICAL", "msg": f"Extreme volatility — ATR ratio {ratio:.1f}x, {short_avg:.0f}pip/tick", "pips": round(short_avg * 1440), "event": ""}
                elif ratio > 3.0 and day_idx != reactive_alert_day:
                    reactive_alert_day = day_idx
                    reactive_alert = {"level": "WARNING", "msg": f"Volatility spike — ATR ratio {ratio:.1f}x, {short_avg:.0f}pip/tick", "pips": round(short_avg * 1440), "event": ""}

            spread = max(20, min(150, _broker.current_atr * 0.1)) if DYNAMIC_SPREAD else BASE_SPREAD
            bid = mid_p - spread / 2
            ask = mid_p + spread / 2
            tick_ms = res / max(len(bar_ticks), 1) / 1000
            dt = day_start + __import__("datetime").timedelta(seconds=day_seconds + int(tick_idx * tick_ms))
            update_sma(mid_p)
            update_sma(mid_p)
            tick_prices(bid, ask, dt)

            tick_count += 1
            acct = account_summary()
            pos = open_positions(bid, ask, dt)

            vol_alert = vol_alerts.get(day_idx) if tick_idx == 0 else (reactive_alert if tick_idx % 10 == 0 else None)
            elapsed_seconds = int((dt - day_start).total_seconds()) + day_idx * int(res / 60) * 60
            msg = {
                "bid": round(bid, 2), "ask": round(ask, 2), "mid": round(mid_p, 2),
                "spread": round(spread, 2), "grid": list(set(o.price for o in __import__("broker").orders)),
                "positions": pos,
                "hit_log": list(__import__("broker").hit_log[-20:]),
                "speed": speed_multiplier, "tick": tick_count,
                "sim_time": dt.strftime("%Y %b %d %H:%M:%S"),
                "vol_alert": vol_alert,
                "elapsed_seconds": elapsed_seconds,
                "preset_label": current_preset_label,
                "monthly_pnl": monthly_pnl(),
                **get_params(),
                **acct,
            }
            now_m = time.time()
            if now_m - last_broadcast > 0.016:
                last_broadcast = now_m
                asyncio.ensure_future(broadcast(msg))
            await asyncio.sleep(1 / speed_multiplier)
        daily_pnl = round(_b.balance - day_start_bal, 2)
        daily_trades = _b.total_trades - day_start_trades
        bar_range_pips = max(h - l, 0.1) / PIP
        alpha = 2.0 / (ATR_WINDOW + 1)
        _b._atr_raw = _b._atr_raw + alpha * (bar_range_pips - _b._atr_raw) if _b._atr_raw >= 0.01 else bar_range_pips
        _b.current_atr = round(_b._atr_raw, 1)
        _b.current_spacing = max(MIN_SPACING, min(MAX_SPACING, round(_b.current_atr / ATR_DIVISOR)))
        _b.current_tp = max(_b.current_spacing + 1, round(_b.current_spacing * TP_MULTIPLIER))
        asyncio.ensure_future(broadcast({"type": "daily_pnl", "date": day["date"][:10], "pnl": daily_pnl, "trades": daily_trades}))
    wins_c = sum(1 for h in __import__("broker").hit_log if h.get("pnl",0) > 0)
    losses_c = sum(1 for h in __import__("broker").hit_log if h.get("pnl",0) < 0)
    won_c = round(sum(h["pnl"] for h in __import__("broker").hit_log if h["pnl"] > 0), 2)
    lost_c = round(sum(h["pnl"] for h in __import__("broker").hit_log if h["pnl"] < 0), 2)
    tp_c = sum(1 for h in __import__("broker").hit_log if "TP-" in h.get("side",""))
    hedge_c = sum(1 for h in __import__("broker").hit_log if "HEDGE" in h.get("side",""))
    cleanup_c = sum(1 for h in __import__("broker").hit_log if "CLEANUP" in h.get("side",""))
    asyncio.ensure_future(broadcast({"type": "done", "label": current_preset_label,
        "sim_time": dt.strftime("%Y %b %d %H:%M:%S"), "tick": tick_count,
        "balance": acct.get("balance"), "equity": acct.get("equity"),
        "total_pnl": acct.get("total_pnl"), "return_pct": acct.get("return_pct"),
        "total_trades": acct.get("total_trades"),
        "wins": wins_c, "losses": losses_c, "win_pnl": won_c, "loss_pnl": lost_c,
        "pf": round(abs(won_c/lost_c),2) if lost_c else 999,
        "tp_hits": tp_c, "hedge_closes": hedge_c, "cleanups": cleanup_c,
        "max_dd": acct.get("drawdown"),
    }))
    _loop_active = False



MICRO_SUBSCRIBERS = []
MICRO_EXPIRY = 1
MICRO_ATR_SOURCE = "micro"
MICRO_RUNNING = False
MICRO_ATR_WINDOW = "1m"
MICRO_HARD_MODE = False
MICRO_PROFIT_TARGET_PCT = 0.1
_last_done = None
_micro_run_id = 0
current_mid = 5000.0
_chart_micro = []

async def broadcast_micro(msg):
    for ws in MICRO_SUBSCRIBERS[:]:
        try:
            await ws.write(("data: " + json.dumps(msg) + "\n\n").encode())
        except Exception:
            if ws in MICRO_SUBSCRIBERS:
                MICRO_SUBSCRIBERS.remove(ws)

def load_micro_data(start_date, end_date, tf="1m"):
    import json, csv, concurrent.futures, threading, glob
    from pathlib import Path
    cache_dir = Path("/root/forex-grid")
    cache_file = cache_dir / f"micro_{tf}_{start_date}_{end_date}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    CSV_CUTOFF = "2026-01-30"
    keys = []
    bar_id_set = set()
    def dedup(bar):
        key = (bar["date"], bar["open"], bar["high"], bar["low"], bar["close"])
        if key in bar_id_set:
            return False
        bar_id_set.add(key)
        return True
    # 1. Try merged 2004-2026 cache first (best quality)
    merged_pattern = str(cache_dir / f"micro_{tf}_*.json")
    merged_found = False
    for mf_path in sorted(glob.glob(merged_pattern)):
        mf = Path(mf_path)
        if mf == cache_file:
            continue
        try:
            parts = mf.stem.split("_")
            mf_start, mf_end = parts[-2], parts[-1]
            if mf_start <= start_date:
                all_data = json.loads(mf.read_text())
                filtered = [d for d in all_data if start_date <= d["date"][:10] <= min(end_date, CSV_CUTOFF) and not (d["open"] == d["high"] == d["low"] == d["close"])]
                if filtered:
                    merged_found = True
                    for b in filtered:
                        if dedup(b):
                            keys.append(b)
        except: pass
    # 2. CSV files (pre-2026 data)
    if not merged_found:
        TF_CSV = {"1m":"XAU_1m_data.csv","5m":"XAU_5m_data.csv","15m":"XAU_15m_data.csv","30m":"XAU_30m_data.csv","1h":"XAU_1h_data.csv","4h":"XAU_4h_data.csv","1d":"XAU_1d_data.csv"}
        csv_file = cache_dir / TF_CSV.get(tf, "")
        if csv_file.exists():
            try:
                with open(csv_file) as fh:
                    reader = csv.reader(fh, delimiter=";")
                    next(reader, None)
                    for row in reader:
                        if len(row) < 5:
                            continue
                        dt = row[0].replace(".", "-")[:16]
                        d10 = dt[:10]
                        if d10 < start_date:
                            continue
                        if d10 > min(end_date, CSV_CUTOFF):
                            break
                        o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
                        if o == h == l == c:
                            continue
                        b = {"date": dt, "open": o, "high": h, "low": l, "close": c}
                        if dedup(b):
                            keys.append(b)
                        if len(keys) >= 50000:
                            break
            except Exception:
                pass
    # 3. gcf_5m.json for dates after CSV cutoff (covers gap Feb-Jul)
    if end_date > CSV_CUTOFF:
        p = Path("/root/forex-grid/gcf_5m.json")
        if p.exists():
            try:
                gcf_data = json.loads(p.read_text())
                for d in gcf_data:
                    d10 = d["date"][:10]
                    if d10 >= max(start_date, CSV_CUTOFF) and d10 <= end_date:
                        if not (d["open"] == d["high"] == d["low"] == d["close"]):
                            if dedup(d):
                                keys.append(d)
            except: pass
    # 4. yfinance for very recent (last 60 days)
    if end_date > CSV_CUTOFF:
        yf_start = max(start_date, CSV_CUTOFF)
        yf_int = "1m" if tf == "1m" else "5m"
        yf_keys = []
        done = threading.Event()
        def fetch_yf():
            nonlocal yf_keys
            try:
                import yfinance as yf
                g = yf.download("GC=F", interval=yf_int, start=yf_start, end=end_date, progress=False)
                if not g.empty:
                    for ts, row in g.iterrows():
                        d = row
                        yf_keys.append({"date": ts.strftime("%Y-%m-%d %H:%M"),
                            "open": float(d["Open"].iloc[0]) if hasattr(d["Open"], "iloc") else float(d["Open"]),
                            "high": float(d["High"].iloc[0]) if hasattr(d["High"], "iloc") else float(d["High"]),
                            "low": float(d["Low"].iloc[0]) if hasattr(d["Low"], "iloc") else float(d["Low"]),
                            "close": float(d["Close"].iloc[0]) if hasattr(d["Close"], "iloc") else float(d["Close"])})
            except: pass
            finally: done.set()
        t = threading.Thread(target=fetch_yf, daemon=True)
        t.start()
        done.wait(timeout=15)
        for b in yf_keys:
            if dedup(b):
                keys.append(b)
    if keys:
        keys.sort(key=lambda x: x["date"])
        cache_file.write_text(json.dumps(keys))
        return keys
    # 5. Last resort: raw gcf_5m.json with duplicates
    if tf == "5m":
        p = Path("/root/forex-grid/gcf_5m.json")
        if p.exists():
            data = json.loads(p.read_text())
            return [d for d in data if start_date <= d["date"][:10] <= end_date and not (d["open"] == d["high"] == d["low"] == d["close"])]
    return []

async def run_micro_sim(kf, expiry_hours=1, atr_source="micro", tf="1m", hard_mode=False, profit_target_pct=0.1):
    global MICRO_RUNNING, _last_done, _micro_run_id
    import broker as _b
    _micro_run_id += 1
    my_id = _micro_run_id
    MICRO_RUNNING = True
    _b.balance = _b.start_balance = _b.equity_peak = 1000000.0
    _b.orders.clear(); _b.trades.clear(); _b.hit_log.clear(); _b.closed_trades.clear()
    _b.mr_price_history.clear(); _b.current_sma = 0.0
    _b.current_atr = _b._atr_raw = 5.0
    _b.micro_atr = _b._micro_atr_raw = 5.0
    _b.current_spacing = 1500
    _b.current_tp = round(1500 * _b.TP_MULTIPLIER)
    bars_per_hour = 60 if tf == "1m" else 12
    _b.expiry_bars = expiry_hours * bars_per_hour
    _b.trade_age.clear()
    _b.atr_source = atr_source
    _b.daily_trade_count = 0; _b.total_trades = 0
    _b.lot_size = _b.lot_size if _b.lot_size is not None and _b.lot_size > 0 else _b.BASE_LOT
    _b._prev_hedge_state = True
    global speed_multiplier
    sim_tf_seconds = 60 if tf == "1m" else 300
    _b.micro_atr_window = MICRO_ATR_WINDOW
    _b._micro_atr_bar_buffer = []
    if hard_mode:
        _b.HARD_MODE = True
        _b.HARD_SPACING_PIPS = 10000
        _b.PROFIT_TARGET_PCT = profit_target_pct
        _b.hard_profit_target = 1000000.0 * profit_target_pct / 100.0
        _b.cumulative_pnl = 0.0
    _b.place_orders(kf[0]["open"])
    total = len(kf)
    atr_history = []
    for idx, bar in enumerate(kf):
        if not MICRO_RUNNING:
            break
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        if o == h == l == c:
            continue
        spread = max(20, min(150, _b.current_atr * 0.1)) if _b.DYNAMIC_SPREAD else _b.BASE_SPREAD
        ts = datetime.strptime(bar["date"], "%Y-%m-%d %H:%M")
        for mid_p in _b._walk_bar(o, h, l, c, pip_step=100):
            _b.update_sma(mid_p)
            _b.tick_prices(mid_p - spread/2, mid_p + spread/2, ts)
        _b.feed_micro_bar(high=h, low=l, sim_tf_seconds=sim_tf_seconds)
        _b.apply_atr_spacing()
        _b.update_trade_ages(mid_p - spread/2, mid_p + spread/2, ts, atr_val=_b.micro_atr)
        atr_history.append(round(_b.micro_atr, 1))
        if len(atr_history) > 500:
            atr_history = atr_history[-500:]
        if idx % 5 == 0:
            acct = _b.account_summary()
            pos = _b.open_positions(mid_p - spread/2, mid_p + spread/2, ts)
            ages = {t.id: _b.trade_age.get(t.id, 0) for t in _b.trades}
            gl = [round(o.price, 2) for o in _b.orders]
            msg = {"type": "tick", "bar": idx, "total": total,
                "bid": round(mid_p - spread/2, 2), "ask": round(mid_p + spread/2, 2),
                "mid": round(mid_p, 2), "ts": ts.strftime("%H:%M"), "balance": _b.balance, "equity": acct["equity"],
                "positions": pos, "hit_log": list(_b.hit_log[-30:]),
                "spacing": _b.current_spacing, "tp": _b.current_tp,
                "micro_atr": round(_b.micro_atr, 1), "macro_atr": round(_b.current_atr, 1),
                "atr_source": _b.atr_source,
                "trade_ages": ages, "expiry_bars": _b.expiry_bars,
                "grid_levels": gl, "atr_history": atr_history,
                "tf": tf,
                "hard_mode": _b.HARD_MODE,
                "hard_profit_target": _b.hard_profit_target,
                "cumulative_pnl": round(_b.cumulative_pnl, 2),
                "profit_target_pct": _b.PROFIT_TARGET_PCT,
                "micro_atr_window": _b.micro_atr_window,
                "closed_trades": list(_b.closed_trades[-50:])}
            await broadcast_micro(msg)
            sleep_s = max(0, 1.0 / speed_multiplier)
            await asyncio.sleep(sleep_s)
    acct = _b.account_summary()
    wins = sum(1 for h in _b.hit_log if h.get("pnl", 0) > 0)
    losses = sum(1 for h in _b.hit_log if h.get("pnl", 0) < 0)
    won = round(sum(h["pnl"] for h in _b.hit_log if h["pnl"] > 0), 2)
    lost = round(sum(h["pnl"] for h in _b.hit_log if h["pnl"] < 0), 2)
    _done_msg = {"type": "done", "balance": _b.balance,
        "return": round((_b.balance - 1000000) / 10000, 2),
        "dd": round(_b.equity_peak - min(_b.equity_peak, _b.balance), 2),
        "trades": _b.total_trades,
        "tick_count": idx + 1,
        "total_bars": total,
        "wins": wins, "losses": losses,
        "win_rate": round(wins / (wins + losses) * 100, 1) if (wins + losses) else 0,
        "won_amount": won, "lost_amount": lost,
        "micro_atr": round(_b.micro_atr, 1), "final_spacing": _b.current_spacing,
        "closed_trades": list(_b.closed_trades[-50:])}
    _done_msg["chart"] = _chart_micro[-500:]
    _last_done = _done_msg
    if my_id == _micro_run_id:
        await broadcast_micro(_done_msg)
        MICRO_RUNNING = False

async def stream_micro_handler(request):
    global MICRO_SUBSCRIBERS, _last_done
    ws = web.StreamResponse()
    ws.headers["Content-Type"] = "text/event-stream"
    ws.headers["Cache-Control"] = "no-cache"
    ws.headers["Connection"] = "keep-alive"
    await ws.prepare(request)
    MICRO_SUBSCRIBERS.append(ws)
    init_msg = {"type": "init", "expiry": MICRO_EXPIRY, "atr_source": MICRO_ATR_SOURCE,
        "micro_atr_window": MICRO_ATR_WINDOW}
    try:
        await ws.write(("data: " + json.dumps(init_msg) + "\n\n").encode())
        if _last_done is not None:
            await ws.write(("data: " + json.dumps(_last_done) + "\n\n").encode())
        while True:
            await asyncio.sleep(30)
            await ws.write(b":keepalive\n\n")
    except:
        pass
    if ws in MICRO_SUBSCRIBERS:
        MICRO_SUBSCRIBERS.remove(ws)
    return ws

async def micro_start_handler(request):
    global MICRO_EXPIRY, MICRO_ATR_SOURCE, MICRO_RUNNING, MICRO_ATR_WINDOW, speed_multiplier
    import broker as _b
    global _chart_micro, _last_done
    MICRO_RUNNING = False
    _chart_micro.clear()
    _last_done = None

    await asyncio.sleep(0.3)
    try:
        body = await request.json()
        preset_name = body.get("preset", "yesterday")
        MICRO_EXPIRY = int(body.get("expiry", 1))
        if MICRO_EXPIRY <= 0:
            MICRO_EXPIRY = 9999
        else:
            MICRO_EXPIRY = max(1, min(9999, MICRO_EXPIRY))
        MICRO_ATR_SOURCE = body.get("atr_source", "micro")
        MICRO_HARD_MODE = body.get("hard_mode", False)
        MICRO_PROFIT_TARGET_PCT = float(body.get("profit_target", 0.1))
        speed_multiplier = int(body.get("speed", 100))
        lot = float(body.get("lot", _b.BASE_LOT))
        _b.lot_size = lot
        aw = body.get("atr_window", "")
        if aw in ("1m", "5m", "15m"):
            _b.set_micro_atr_window(aw)
            MICRO_ATR_WINDOW = aw
    except Exception:
        body = None
        preset_name = "yesterday"
        MICRO_EXPIRY = 1
        MICRO_ATR_SOURCE = "micro"
        MICRO_HARD_MODE = False
        MICRO_PROFIT_TARGET_PCT = 0.1
    tf = body.get("tf", "1m") if isinstance(body, dict) else "1m"
    if isinstance(body, dict) and body.get("start") and body.get("end"):
        p = {"start": body["start"], "end": body["end"]}
    else:
        p = PRESETS.get(preset_name)
    if not p:
        return web.json_response({"error": "Unknown preset"}, status=400)
    kf = load_micro_data(p["start"], p["end"], tf)
    if not kf:
        return web.json_response({"error": f"No {tf} data"}, status=400)
    async def run_micro_sim_wrapped():
        try:
            await run_micro_sim(kf, MICRO_EXPIRY, MICRO_ATR_SOURCE, tf,
                hard_mode=MICRO_HARD_MODE, profit_target_pct=MICRO_PROFIT_TARGET_PCT)
        except Exception as e:
            import traceback; traceback.print_exc()
            await broadcast_micro({"type": "done", "error": str(e)})
    asyncio.ensure_future(run_micro_sim_wrapped())
    return web.json_response({"status": "started", "bars": len(kf), "expiry": MICRO_EXPIRY,
        "atr_source": MICRO_ATR_SOURCE, "micro_atr_window": MICRO_ATR_WINDOW,
        "tf": tf, "hard_mode": MICRO_HARD_MODE, "profit_target": MICRO_PROFIT_TARGET_PCT})

async def micro_atr_source_handler(request):
    global MICRO_ATR_SOURCE
    import broker as _b
    try:
        body = await request.json()
        source = body.get("source", "micro")
        if source not in ("micro", "macro"):
            return web.json_response({"error": "source must be micro or macro"}, status=400)
        _b.switch_atr_source(source)
        MICRO_ATR_SOURCE = source
        await broadcast_micro({"type": "atr_switch", "atr_source": source,
            "micro_atr": round(_b.micro_atr, 1), "macro_atr": round(_b.current_atr, 1),
            "spacing": _b.current_spacing})
        return web.json_response({"atr_source": source, "spacing": _b.current_spacing})
    except Exception:
        body = None
        return web.json_response({"error": "invalid body"}, status=400)

async def micro_speed_handler(request):
    global speed_multiplier
    try:
        body = await request.json()
        speed_multiplier = max(1, min(10000, int(body.get("speed", 100))))
    except:
        pass
    return web.json_response({"speed": speed_multiplier})

async def micro_atr_window_handler(request):
    global MICRO_ATR_WINDOW
    import broker as _b
    try:
        body = await request.json()
        window = body.get("window", "1m")
        if window in ("1m", "5m", "15m"):
            _b.set_micro_atr_window(window)
            _b._micro_atr_raw = 5.0
            _b.micro_atr = 5.0
            MICRO_ATR_WINDOW = window
            await broadcast_micro({"type": "atr_window", "micro_atr_window": window,
                "micro_atr": round(_b.micro_atr, 1), "spacing": _b.current_spacing})
            return web.json_response({"micro_atr_window": window})
        return web.json_response({"error": "invalid window"}, status=400)
    except Exception:
        body = None
        return web.json_response({"error": "invalid body"}, status=400)

async def micro_report_handler(request):
    preset_name = request.match_info.get("preset", "last7d")
    tf = request.query.get("tf", "1m")
    atr_source = request.query.get("atr", "micro")
    p = PRESETS.get(preset_name)
    if not p:
        return web.json_response({"error": "Unknown preset"}, status=400)
    kf = load_micro_data(p["start"], p["end"], tf)
    if not kf:
        return web.json_response({"error": "no data"}, status=400)
    import broker as _b
    _b.balance = _b.start_balance = _b.equity_peak = 1000000.0
    _b.orders.clear(); _b.trades.clear(); _b.hit_log.clear()
    _b.mr_price_history.clear(); _b.current_sma = 0.0
    _b.current_atr = _b._atr_raw = 5.0
    _b.micro_atr = _b._micro_atr_raw = 5.0
    _b.current_spacing = 1500
    _b.trade_age.clear()
    _b.daily_trade_count = 0; _b.total_trades = 0
    _b.lot_size = _b.BASE_LOT
    _b.atr_source = atr_source
    sim_tf_seconds = 60 if tf == "1m" else 300
    _b.micro_atr_window = MICRO_ATR_WINDOW
    _b._micro_atr_bar_buffer = []
    _b.place_orders(kf[0]["open"])
    total = len(kf)
    atr_history = []
    for idx, bar in enumerate(kf):
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        if o == h == l == c:
            continue
        spread = max(20, min(150, _b.current_atr * 0.1)) if _b.DYNAMIC_SPREAD else _b.BASE_SPREAD
        ts = datetime.strptime(bar["date"], "%Y-%m-%d %H:%M")
        for mid_p in _b._walk_bar(o, h, l, c, pip_step=100):
            _b.update_sma(mid_p)
            _b.tick_prices(mid_p - spread/2, mid_p + spread/2, ts)
        _b.feed_micro_bar(high=h, low=l, sim_tf_seconds=sim_tf_seconds)
        _b.apply_atr_spacing()
        _b.update_trade_ages(mid_p - spread/2, mid_p + spread/2, ts, atr_val=_b.micro_atr)
        atr_history.append(round(_b.micro_atr, 1))
        if len(atr_history) > 500:
            atr_history = atr_history[-500:]
    acct = _b.account_summary()
    wins = sum(1 for h in _b.hit_log if h.get("pnl", 0) > 0)
    losses = sum(1 for h in _b.hit_log if h.get("pnl", 0) < 0)
    return web.json_response({
        "balance": _b.balance, "return_pct": round((_b.balance - 1000000) / 10000, 2),
        "trades": _b.total_trades, "wins": wins, "losses": losses,
        "win_rate": round(wins / (wins + losses) * 100, 1) if (wins + losses) else 0,
        "final_micro_atr": round(_b.micro_atr, 1), "final_spacing": _b.current_spacing,
        "atr_history": atr_history, "bars": total,
    })

async def grid_micro_page(request):
    from pathlib import Path
    return web.FileResponse(Path(__file__).parent / "index-micro.html")
async def on_startup(app):
    global _loop_active
    _loop_active = True
    asyncio.ensure_future(tick_loop())

def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3001
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_get("/stream", stream_handler)
    app.router.add_post("/speed", set_speed)
    app.router.add_post("/restart", restart_sim)
    app.router.add_post("/preset", set_preset)
    app.router.add_get("/results", results_handler)
    app.router.add_post("/toggle_trend_filter", toggle_trend_filter)
    app.router.add_get("/report/{preset}", report_handler)
    app.router.add_get("/", index)
    
    app.router.add_get("/stream-micro", stream_micro_handler)
    app.router.add_post("/micro-start", micro_start_handler)
    app.router.add_post("/atr-source", micro_atr_source_handler)
    app.router.add_post("/micro-speed", micro_speed_handler)
    app.router.add_post("/micro-atr-window", micro_atr_window_handler)
    app.router.add_get("/report-micro/{preset}", micro_report_handler)
    app.router.add_get("/grid-micro", grid_micro_page)
    async def micro_close_trade_handler(request):
        import broker as _b
        try:
            body = await request.json()
            trade_id = body.get("trade_id", "")
            if not trade_id:
                return web.json_response({"error": "no trade_id"}, status=400)
            t = None
            for tr in _b.trades:
                if tr.id == trade_id:
                    t = tr
                    break
            if not t:
                return web.json_response({"error": "trade not found"}, status=404)
            ts = datetime.now()
            pnl = _b.close_trade(trade_id, current_mid, current_mid, ts, "MANUAL")
            return web.json_response({"status": "closed", "trade_id": trade_id, "pnl": pnl})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    app.router.add_post("/micro-close-trade", micro_close_trade_handler)
    app.router.add_get("/{path:.*}", static_handler)
    web.run_app(app, host="127.0.0.1", port=port)

if __name__ == "__main__":
    main()
