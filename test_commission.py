import sys, json
sys.path.insert(0, "/root/forex-grid")
import broker as b

kf = json.load(open("/root/forex-grid/gcf_5m.json"))
kf = [d for d in kf if "2026-01-02" <= d["date"] <= "2026-01-31"][:3000]

def run(label, spread, comm):
    b.reset()
    b.MIN_SPACING = 2500
    b.current_spacing = 2500
    b.current_tp = 2500
    b.BASE_SPREAD = spread
    b.COMMISSION = comm
    b.DYNAMIC_SPREAD = False
    b.EXPIRY_BARS = 48
    b.place_orders(kf[0]["open"])
    for idx, bar in enumerate(kf):
        o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
        if o == h == l == c:
            continue
        sp = spread
        ts = __import__("time").mktime(__import__("time").strptime(bar["date"], "%Y-%m-%d %H:%M"))
        for mid_p in b._walk_bar(o, h, l, c, pip_step=1000):
            b.tick_prices(mid_p - sp/200, mid_p + sp/200, ts)
        b.update_trade_ages(kf[idx]["close"] - sp/200, kf[idx]["close"] + sp/200, ts)
    tot_comm = len(b.hit_log) * comm
    tp_sum = sum(h["pnl"] for h in b.hit_log if "TP-" in h.get("side",""))
    hedge_sum = sum(h["pnl"] for h in b.hit_log if "HEDGE" in h.get("side",""))
    expiry_sum = sum(h["pnl"] for h in b.hit_log if "EXPIRY" in h.get("side",""))
    gross = sum(h["pnl"] for h in b.hit_log)
    net = round(b.balance - 1000000, 2)
    return {"label":label,"trades":len(b.hit_log),"tp":round(tp_sum,2),"hedge":round(hedge_sum,2),"expiry":round(expiry_sum,2),"gross":round(gross,2),"comm":round(tot_comm,2),"net":net,"bal":round(b.balance,2)}

print("===== COMMISSION EROSION — Jan 2026 (5m, 3K bars) =====")
r = run("Spread=0  Comm=0.0", 0, 0.0)
print("Base:     trades="+str(r["trades"])+" tp=$"+str(r["tp"])+" hedge=$"+str(r["hedge"])+" gross=$"+str(r["gross"])+" net=$"+str(r["net"]))
r = run("Spread=20 Comm=0.0", 20, 0.0)
print("Spre20:   trades="+str(r["trades"])+" tp=$"+str(r["tp"])+" hedge=$"+str(r["hedge"])+" gross=$"+str(r["gross"])+" net=$"+str(r["net"]))
r = run("Spread=20 Comm=0.1", 20, 0.1)
print("Spr20c01: trades="+str(r["trades"])+" tp=$"+str(r["tp"])+" hedge=$"+str(r["hedge"])+" comm=$"+str(r["comm"])+" net=$"+str(r["net"]))
r = run("Spread=20 Comm=0.5", 20, 0.5)
print("Spr20c05: trades="+str(r["trades"])+" tp=$"+str(r["tp"])+" hedge=$"+str(r["hedge"])+" comm=$"+str(r["comm"])+" net=$"+str(r["net"]))
r = run("Spread=20 Comm=1.0", 20, 1.0)
print("Spr20c10: trades="+str(r["trades"])+" tp=$"+str(r["tp"])+" hedge=$"+str(r["hedge"])+" comm=$"+str(r["comm"])+" net=$"+str(r["net"]))
print("===== DONE =====")
