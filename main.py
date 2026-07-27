import json, time, random, asyncio, math
from datetime import datetime, timedelta
from pathlib import Path
from broker import account_summary, open_positions, tick_prices, place_orders, update_atr, get_params, current_spacing, PIP, BASE_SPREAD, DYNAMIC_SPREAD, ATR_WINDOW, _walk_bar, MIN_SPACING, MAX_SPACING, ATR_DIVISOR, TP_MULTIPLIER
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
    for fname, res in [("gcf_1m.json", 60), ("gcf_5m.json", 300), ("gcf_15m.json", 900), ("gcf_1h.json", 3600), ("gcf_daily.json", 86400)]:
        p = basedir / fname
        if p.exists():
            data = json.loads(p.read_text())
            for d in data:
                d["res"] = res
            sources.extend(data)
    sources.sort(key=lambda x: (x["date"], x["res"]))
    seen = set()
    merged = []
    for d in sources:
        k = d["date"]
        if k not in seen:
            seen.add(k)
            merged.append(d)
    return merged

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
    "last7d": {"start": "2026-07-19", "end": "2026-07-24", "speed": 100, "label": "Last 7 Days"},
    "5m": {"start": "2026-06-24", "end": "2026-07-24", "speed": 50, "label": "1 Month (5m Data)", "res": 300},
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
    return web.json_response({
        account: _b.account_summary(),
        open_trades: [{
            id: t.id, side: t.side, entry: t.entry, size: t.size,
            pnl: t.pnl, sl: t.sl, tp: t.tp, age_days: t.age_days,
            close_pct: getattr(t, close_pct, 0),
            days_since_open: getattr(t, days_since_open, 0),
        } for t in _b.trades],
        hit_log: list(_b.hit_log),
        closed_trades: list(_b.closed_trades),
        preset: current_preset_label,
        params: _b.get_params(),
    })

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
    asyncio.ensure_future(broadcast({"type": "done", "sim_time": dt.strftime("%Y %b %d %H:%M:%S"), "tick": tick_count, "balance": acct.get("balance"), "equity": acct.get("equity"), "total_pnl": acct.get("total_pnl"), "total_trades": acct.get("total_trades"), "wins": acct.get("wins"), "losses": acct.get("losses"), "max_dd": acct.get("drawdown")}))
    _loop_active = False

async def on_startup(app):
    global _loop_active
    _loop_active = True
    asyncio.ensure_future(tick_loop())

def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_get("/stream", stream_handler)
    app.router.add_post("/speed", set_speed)
    app.router.add_post("/restart", restart_sim)
    app.router.add_post("/preset", set_preset)
    app.router.add_get("/results", results_handler)
    app.router.add_get("/", index)
    app.router.add_get("/{path:.*}", static_handler)
    web.run_app(app, host="127.0.0.1", port=3001)

if __name__ == "__main__":
    main()
