content = open("/root/forex-grid/main.py").read()

# Replace KF_PATH block with multi-resolution loader
old_kf = '''TICK_SCALE = 600

KF_PATH = Path(__file__).parent / "gcf_daily.json"
keyframes = json.loads(KF_PATH.read_text()) if KF_PATH.exists() else []
if len(keyframes) > 7: keyframes = keyframes[-7:]'''

new_kf = '''KF_PATH = Path(__file__).parent / "gcf_daily.json"

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
    last_date = datetime.strptime(keyframes[-1]["date"][:10], "%Y-%m-%d")
    cutoff = (last_date - timedelta(days=7)).strftime("%Y-%m-%d")
    keyframes = [k for k in keyframes if k["date"][:10] >= cutoff]'''

content = content.replace(old_kf, new_kf, 1)

# Remove old TICK_SCALE refs in tick_loop and replace with per-keyframe ticks_per
old_tick = '''    for day_idx in range(total_kf):
        day = kf[day_idx]
        o, h, l, c = day["open"], day["high"], day["low"], day["close"]
        daily_range = max(h - l, 1.0)
        sqrt_t = math.sqrt(float(TICK_SCALE))
        per_tick_vol = daily_range / sqrt_t * math.sqrt(1 - phi * phi) * 0.5

        for tick in range(TICK_SCALE):
            t = (tick + 1) / TICK_SCALE
            bridge = o + (c - o) * t
            noise = phi * noise_prev + random.gauss(0, per_tick_vol)
            noise_prev = noise
            mid_p = max(l, min(h, bridge + noise))

            bid = mid_p - spread / 2
            ask = mid_p + spread / 2
            update_atr(mid_p)
            dt = sim_start + timedelta(seconds=day_idx * 86400 + int(tick * 86400 / TICK_SCALE))
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
                "elapsed_seconds": int((dt - sim_start).total_seconds()), "eta_seconds": max(0, int((total_kf * TICK_SCALE - tick_count) / speed_multiplier)), "sim_time": dt.strftime("%b %d %H:%M:%S NST"),
                **acct,
            }
            now_m = time.time()
            if now_m - last_broadcast > 0.016:
                last_broadcast = now_m
                asyncio.ensure_future(broadcast(msg))
            await asyncio.sleep(1 / speed_multiplier)'''

new_tick = '''    total_secs = 0
    for day_idx in range(total_kf):
        day = kf[day_idx]
        o, h, l, c = day["open"], day["high"], day["low"], day["close"]
        res = day.get("res", 86400)
        ticks_per = max(1, int(res / 60))
        daily_range = max(h - l, 1.0)
        sqrt_t = math.sqrt(float(ticks_per))
        per_tick_vol = daily_range / sqrt_t * math.sqrt(1 - phi * phi) * 0.5

        for tick in range(ticks_per):
            t = (tick + 1) / ticks_per
            bridge = o + (c - o) * t
            noise = phi * noise_prev + random.gauss(0, per_tick_vol)
            noise_prev = noise
            mid_p = max(l, min(h, bridge + noise))

            bid = mid_p - spread / 2
            ask = mid_p + spread / 2
            update_atr(mid_p)
            dt = sim_start + timedelta(seconds=total_secs + int(tick * res / ticks_per))
            grid = build_grid(mid_p)
            tick_prices(bid, ask, grid, dt)
            grid_hits(grid, mid_p)

            tick_count += 1
            acct = account_summary()
            pos = open_positions(bid, ask, dt)

            total_ticks = sum(max(1, int(kf[i].get("res",86400)/60)) for i in range(total_kf))
            msg = {
                "bid": round(bid, 2), "ask": round(ask, 2), "mid": round(mid_p, 2),
                "spread": round(spread, 2), "grid": grid,
                "positions": pos,
                "hit_log": list(__import__("broker").hit_log[-20:]),
                "speed": speed_multiplier, "tick": tick_count,
                "elapsed_seconds": int((dt - sim_start).total_seconds()), "eta_seconds": max(0, int((total_ticks - tick_count) / speed_multiplier)), "sim_time": dt.strftime("%b %d %H:%M:%S NST"),
                **acct,
            }
            now_m = time.time()
            if now_m - last_broadcast > 0.016:
                last_broadcast = now_m
                asyncio.ensure_future(broadcast(msg))
            await asyncio.sleep(1 / speed_multiplier)
        total_secs += res'''

content = content.replace(old_tick, new_tick, 1)

# Remove any remaining TICK_SCALE constant line
content = content.replace("TICK_SCALE = 600\n", "")

# Set speed to 100
content = content.replace("speed_multiplier = 10000", "speed_multiplier = 100")

# Update halt message
content = content.replace('print(f"HALT: 7-day daily sim complete")', 'print(f"HALT: multi-resolution sim complete — {total_kf} keyframes, {tick_count} ticks")')

open("/root/forex-grid/main.py", "w").write(content)
print("STEP 4/4 — main.py patched successfully")
