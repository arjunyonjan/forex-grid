import json, time, random, asyncio, math
from datetime import datetime, timedelta
from pathlib import Path
from broker import account_summary, open_positions, tick_prices, grid_hits, simulate, simulate_from_keyframes, update_atr, current_spacing, PIP
from aiohttp import web

PIP_VALUE = 10.0
QUEUE_MAXSIZE = 60
BASE_PRICE = 4110.0
spread = 0.0
speed_multiplier = 1000
last_broadcast = 0.0
MID_OFFSET = 200
MIN_SPACING = 100
MAX_SPACING = 100
KF_PATH = Path(__file__).parent / "gcf_daily.json"

def load_keyframes():
    sources = []
    basedir = Path(__file__).parent
    for fname, res in [("gcf_1m.json", 60), ("gcf_15m.json", 900), ("gcf_1h.json", 3600), ("gcf_daily.json", 86400)]:
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

keyframes = load_keyframes()
if keyframes:
    keyframes = [k for k in keyframes if k["date"][:10] >= "2022-01-01" and k["date"][:10] <= "2022-04-30" and not (k["open"] == k["high"] == k["low"] == k["close"])]

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

def build_grid(mid):
    step = current_spacing * PIP
    levels = []
    p = round(mid / step) * step if step else mid
    for i in range(-MID_OFFSET, MID_OFFSET + 1):
        levels.append(round(p + i * step, 2))
    return levels

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
    init_msg = {"type": "init", "daily_moves": daily_moves, "monthly_moves": monthly_moves}
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

async def simulate_handler(request):
    hours = int(request.query.get("hours", 24))
    result = await asyncio.to_thread(simulate, hours, BASE_PRICE)
    return web.json_response(result)

async def sim_keyframes_handler(request):
    try:
        body = await request.json()
        kf = body.get("keyframes", [])
        sp = body.get("spacing", 100)
        result = await asyncio.to_thread(simulate_from_keyframes, kf, 10000.0, sp, body.get("tick_scale", 480))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

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
    global last_broadcast
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
    _b.lot_size = _b.BASE_LOT
    _b.trading_halted = False
    _b.total_wins_cumulative = 0
    _b.total_losses_cumulative = 0
    _b.cumulative_win_pnl = 0.0
    _b.cumulative_loss_pnl = 0.0

    kf = keyframes
    total_kf = len(kf)
    mid_p = kf[0]["open"]
    tick_count = 0
    noise_prev = 0.0
    phi = 0.85

    vol_alerts = {}
    for day_idx in range(total_kf):
        day_range = max(kf[day_idx]["high"] - kf[day_idx]["low"], 1.0)
        max_fwd = day_range
        for fwd in range(1, min(8, total_kf - day_idx)):
            fwd_r = max(kf[day_idx + fwd]["high"] - kf[day_idx + fwd]["low"], 1.0)
            if fwd_r > max_fwd:
                max_fwd = fwd_r
        if max_fwd > 15.0:
            range_pips = round(max_fwd / 0.01)
            if range_pips > 5000:
                vol_alerts[day_idx] = {"level": "CRITICAL", "msg": f"{range_pips}pip spike incoming within 7 days", "pips": range_pips}
            elif range_pips > 2500:
                vol_alerts[day_idx] = {"level": "WARNING", "msg": f"{range_pips}pip volatility expected within 7 days", "pips": range_pips}
            elif range_pips > 1000:
                vol_alerts[day_idx] = {"level": "NOTICE", "msg": f"{range_pips}pip move possible within 7 days", "pips": range_pips}

    for day_idx in range(total_kf):
        day = kf[day_idx]
        o, h, l, c = day["open"], day["high"], day["low"], day["close"]
        res = day.get("res", 86400)
        ticks_per = max(1, int(res / 60))
        daily_range = max(h - l, 1.0)
        sqrt_t = math.sqrt(float(ticks_per))
        per_tick_vol = daily_range / sqrt_t * math.sqrt(1 - phi * phi) * 0.5
        day_start = datetime.strptime(day["date"][:10], "%Y-%m-%d")
        day_seconds = int(day["date"][11:13]) * 3600 + int(day["date"][14:16]) * 60 if len(day["date"]) > 10 else 0
        day_start_bal = _b.balance
        day_start_trades = _b.total_trades

        for tick in range(ticks_per):
            t = (tick + 1) / ticks_per
            bridge = o + (c - o) * t
            noise = phi * noise_prev + random.gauss(0, per_tick_vol)
            noise_prev = noise
            mid_p = max(l, min(h, bridge + noise))

            bid = mid_p - spread / 2
            ask = mid_p + spread / 2
            update_atr(mid_p)
            dt = day_start + timedelta(seconds=day_seconds + int(tick * res / ticks_per))
            grid = build_grid(mid_p)
            tick_prices(bid, ask, grid, dt)
            grid_hits(grid, mid_p)

            tick_count += 1
            acct = account_summary()
            pos = open_positions(bid, ask, dt)

            msg = {
                "bid": round(bid, 2), "ask": round(ask, 2), "mid": round(mid_p, 2),
                "spread": round(spread, 2), "grid": grid,
                "positions": pos,
                "hit_log": list(__import__("broker").hit_log[-20:]),
                "speed": speed_multiplier, "tick": tick_count,
                "sim_time": dt.strftime("%Y %b %d %H:%M:%S"),
                "vol_alert": vol_alerts.get(day_idx) if tick == 0 else None,
                **acct,
            }
            now_m = time.time()
            if now_m - last_broadcast > 0.016:
                last_broadcast = now_m
                asyncio.ensure_future(broadcast(msg))
            await asyncio.sleep(1 / speed_multiplier)
        daily_pnl = round(_b.balance - day_start_bal, 2)
        daily_trades = _b.total_trades - day_start_trades
        asyncio.ensure_future(broadcast({"type": "daily_pnl", "date": day["date"][:10], "pnl": daily_pnl, "trades": daily_trades}))
    asyncio.ensure_future(broadcast({"type": "done", "sim_time": dt.strftime("%Y %b %d %H:%M:%S"), "tick": tick_count, "balance": acct.get("balance"), "equity": acct.get("equity"), "total_pnl": acct.get("total_pnl"), "total_trades": acct.get("total_trades"), "wins": acct.get("wins"), "losses": acct.get("losses"), "max_dd": acct.get("drawdown")}))
    await asyncio.sleep(15)
    asyncio.ensure_future(tick_loop())

async def on_startup(app):
    asyncio.ensure_future(tick_loop())

def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.router.add_get("/stream", stream_handler)
    app.router.add_get("/simulate", simulate_handler)
    app.router.add_post("/sim-keyframes", sim_keyframes_handler)
    app.router.add_get("/", index)
    app.router.add_get("/{path:.*}", static_handler)
    web.run_app(app, host="127.0.0.1", port=3001)

if __name__ == "__main__":
    main()
