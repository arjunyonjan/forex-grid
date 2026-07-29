import sys, json, time, importlib, importlib.util

sys.path.insert(0, "/root/forex-grid")
spec_o = importlib.util.spec_from_file_location("b_orig", "/root/forex-grid/broker.py")
spec_f = importlib.util.spec_from_file_location("b_fixed", "/root/forex-grid/broker_fixed.py")
b_orig = importlib.util.module_from_spec(spec_o)
b_fixed = importlib.util.module_from_spec(spec_f)
spec_o.loader.exec_module(b_orig)
spec_f.loader.exec_module(b_fixed)

kf = json.load(open("/root/forex-grid/gcf_5m.json"))[:3000]

def run(mod):
    mod.reset()
    mod.MIN_SPACING=2500; mod.current_spacing=2500; mod.current_tp=2500
    mod.BASE_SPREAD=0; mod.COMMISSION=0; mod.DYNAMIC_SPREAD=False; mod.EXPIRY_BARS=48
    mod.place_orders(kf[0]["open"])
    for bar in kf:
        o,h,l,c = bar["open"],bar["high"],bar["low"],bar["close"]
        if o==h==l==c: continue
        ts=time.mktime(time.strptime(bar["date"],"%Y-%m-%d %H:%M"))
        for mid_p in mod._walk_bar(o,h,l,c,pip_step=1000):
            mod.update_sma(mid_p)
            mod.tick_prices(mid_p,mid_p,ts)
        mod.update_trade_ages(c,c,ts)
    tp = sum(h["pnl"] for h in mod.hit_log if h["pnl"]>0)
    hl = sum(h["pnl"] for h in mod.hit_log if h["pnl"]<0)
    net = round(mod.balance-1000000,2)
    return {"tr":len(mod.hit_log),"tp":round(tp,2),"hl":round(hl,2),"net":net}

print("CURRENT broker.py:")
ro = run(b_orig)
print(f"  TR={ro['tr']} TP=${ro['tp']} HL=${ro['hl']} NET=${ro['net']}")

print("FIXED broker_fixed.py:")
rf = run(b_fixed)
print(f"  TR={rf['tr']} TP=${rf['tp']} HL=${rf['hl']} NET=${rf['net']}")

diff = round(rf['net']-ro['net'],2)
print(f"DIFF: ${diff:+.2f}")
