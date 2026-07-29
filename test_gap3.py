import sys
sys.path.insert(0, "/root/forex-grid")
import broker as b

def swc(pips, d, spread=20, comm=0.1):
    b.reset(5000.0)
    b.MIN_SPACING = 2500
    b.current_spacing = 2500
    b.BASE_SPREAD = spread
    b.COMMISSION = comm
    b.DYNAMIC_SPREAD = False
    b.place_orders(5000.0)
    sign = 1 if d == "up" else -1
    total = pips * 0.01 * sign
    pos = 5000.0
    while (pos - 5000.0) * sign < total - 0.001:
        pos += 1 * 0.01 * sign
        b.tick_prices(pos - spread/200, pos + spread/200, None)
    w = sum(1 for h in b.hit_log if h["pnl"] > 0)
    l = sum(1 for h in b.hit_log if h["pnl"] < 0)
    tot = round(sum(h["pnl"] for h in b.hit_log), 2)
    hl = sum(h["pnl"] for h in b.hit_log if "HEDGE" in h.get("side","") and h["pnl"] < 0)
    tp = sum(h["pnl"] for h in b.hit_log if "TP-" in h.get("side","") and h["pnl"] > 0)
    return {"w":w,"l":l,"tot":tot,"hl":round(abs(hl),2),"tp":round(tp,2),"trades":len(b.hit_log),"bal":round(b.balance,2)}

print("===== GAP WITH REALISTIC COSTS =====")
print("Spread=20p Comm=0.1/trade MinSpacing=2500")
r = swc(2500, "up")
print("2500p up:  t="+str(r["trades"])+" w/l="+str(r["w"])+"/"+str(r["l"])+" tp=$"+str(r["tp"])+" hl=$"+str(r["hl"])+" net=$"+str(r["tot"])+" bal=$"+str(r["bal"]))
r = swc(5000, "up")
print("5000p up:  t="+str(r["trades"])+" w/l="+str(r["w"])+"/"+str(r["l"])+" tp=$"+str(r["tp"])+" hl=$"+str(r["hl"])+" net=$"+str(r["tot"])+" bal=$"+str(r["bal"]))
r = swc(7500, "up")
print("7500p up:  t="+str(r["trades"])+" w/l="+str(r["w"])+"/"+str(r["l"])+" tp=$"+str(r["tp"])+" hl=$"+str(r["hl"])+" net=$"+str(r["tot"])+" bal=$"+str(r["bal"]))
r = swc(2500, "down")
print("2500p dn:  t="+str(r["trades"])+" w/l="+str(r["w"])+"/"+str(r["l"])+" tp=$"+str(r["tp"])+" hl=$"+str(r["hl"])+" net=$"+str(r["tot"])+" bal=$"+str(r["bal"]))
r = swc(8680, "up")
print("8680p up:  t="+str(r["trades"])+" w/l="+str(r["w"])+"/"+str(r["l"])+" tp=$"+str(r["tp"])+" hl=$"+str(r["hl"])+" net=$"+str(r["tot"])+" bal=$"+str(r["bal"]))
print("===== DONE =====")
