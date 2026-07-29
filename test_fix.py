import sys, json, importlib, importlib.util

kf = json.load(open("/root/forex-grid/gcf_5m.json"))
kf = [d for d in kf if "2026-01-02" <= d["date"] <= "2026-01-31"][:3000]

def run_with(mod):
    mod.reset()
    mod.MIN_SPACING = 2500
    mod.current_spacing = 2500
    mod.current_tp = 2500
    mod.BASE_SPREAD = 0
    mod.COMMISSION = 0
    mod.DYNAMIC_SPREAD = False
    mod.EXPIRY_BARS = 48
    mod.place_orders(kf[0]["open"])
    for idx, bar in enumerate(kf):
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        if o == h == l == c:
            continue
        ts = __import__("time").mktime(__import__("time").strptime(bar["date"], "%Y-%m-%d %H:%M"))
        for mid_p in mod._walk_bar(o, h, l, c, pip_step=1000):
            mod.update_sma(mid_p)
            mod.tick_prices(mid_p, mid_p, ts)
        mod.update_trade_ages(kf[idx]["close"], kf[idx]["close"], ts)
    tp = sum(h["pnl"] for h in mod.hit_log if h["pnl"] > 0 and "TP-" in h.get("side",""))
    hl = sum(h["pnl"] for h in mod.hit_log if h["pnl"] < 0 and "HEDGE" in h.get("side",""))
    cleanup = sum(h["pnl"] for h in mod.hit_log if "CLEANUP" in h.get("side",""))
    expiry = sum(h["pnl"] for h in mod.hit_log if "EXPIRY" in h.get("side",""))
    profit = sum(h["pnl"] for h in mod.hit_log if "PROFIT" in h.get("side",""))
    gross = sum(h["pnl"] for h in mod.hit_log)
    net = round(mod.balance - 1000000, 2)
    return {"trades":len(mod.hit_log),"tp":round(tp,2),"hl":round(hl,2),"cleanup":round(cleanup,2),"expiry":round(expiry,2),"profit":round(profit,2),"gross":round(gross,2),"net":net}

sys.path.insert(0, "/root/forex-grid")
import broker as b_orig
spec = importlib.util.spec_from_file_location("b_fixed", "/root/forex-grid/broker_fixed.py")
b_fixed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b_fixed)

print("===== CLEANUP FIX (with update_sma) =====")
ro = run_with(b_orig)
rf = run_with(b_fixed)
print(f"CURRENT: tr={ro['trades']} tp=${ro['tp']} hl=${ro['hl']} cln=${ro['cleanup']} exp=${ro['expiry']} net=${ro['net']}")
print(f"FIX:     tr={rf['trades']} tp=${rf['tp']} hl=${rf['hl']} cln=${rf['cleanup']} exp=${rf['expiry']} net=${rf['net']}")
print(f"DIFF: ${rf['net']-ro['net']:+.2f}")
cleanup_trig = abs(ro['cleanup'])+abs(rf['cleanup'])
print(f"CLEANUP fired? orig={ro['cleanup']!=0} fix={rf['cleanup']!=0}")
print("===== DONE =====")
