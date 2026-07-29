import sys, json, time, math
sys.path.insert(0, "/root/forex-grid")
import broker as b

def run_gap_test(lbl, start_price, gap_pips, d):
    b.reset(start_price)
    b.MIN_SPACING = 2500
    b.current_spacing = 2500
    b.place_orders(start_price)
    ob = len(b.orders)
    jump = gap_pips * 0.01
    new_price = start_price + jump if d == "up" else start_price - jump
    spread = 20
    b.tick_prices(new_price - spread/2, new_price + spread/2, None)
    trades = len([t for t in b.trades if t.entry_time is not None])
    wins = sum(1 for h in b.hit_log if h["pnl"] > 0)
    losses = sum(1 for h in b.hit_log if h["pnl"] < 0)
    tot = round(sum(h["pnl"] for h in b.hit_log), 2)
    hl = round(sum(h["pnl"] for h in b.hit_log if "HEDGE" in h.get("side","") and h["pnl"] < 0), 2)
    return {"lbl":lbl,"start":start_price,"new":new_price,"gp":gap_pips,"ob":ob,"trades":trades,"w":wins,"l":losses,"tot":tot,"hl":abs(hl),"bal":round(b.balance,2)}

results = []
results.append(run_gap_test("Gap 2500p 1x spc", 5000.0, 2500, "up"))
results.append(run_gap_test("Gap 5000p 2x spc", 5000.0, 5000, "up"))
results.append(run_gap_test("Gap 8680p 3.5x Jun14", 4238.8, 8680, "up"))
results.append(run_gap_test("Gap 5000p DOWN", 5000.0, 5000, "down"))
results.append(run_gap_test("Gap 1000p lt1x spc", 5000.0, 1000, "up"))

print("===== GAP OPEN STRESS TEST =====")
for r in results:
    print(f"{r['lbl']}:")
    print(f"  {r['start']}->{r['new']} ({r['gp']}p)  orders_before={r['ob']} trades={r['trades']} w/l={r['w']}/{r['l']}")
    print(f"  tot_pnl=${r['tot']} hedge_loss=${r['hl']} bal=${r['bal']}")
print()
print("Worst hedge loss: $" + str(max(r['hl'] for r in results)))
print("Max trades opened: " + str(max(r['trades'] for r in results)))
print("Total PnL range: $" + str(min(r['tot'] for r in results)) + " to $" + str(max(r['tot'] for r in results)))
print("===== DONE =====")
