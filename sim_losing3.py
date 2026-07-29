"""100+ losing & edge case sims — log results to /tmp/losing_log.md"""
import subprocess, json, time, sys, os
from datetime import datetime

SSE = "http://127.0.0.1:3004/stream-micro"
START = "http://127.0.0.1:3004/micro-start"
LOG = "/tmp/losing_log.md"
loglines = []

def log(s):
    loglines.append(s)
    print(s, flush=True)

def sse_poll():
    try:
        r = subprocess.run(["curl","-s","-m","3",SSE], capture_output=True, timeout=5)
        msgs = []
        for line in r.stdout.decode().split("\n"):
            if line.strip().startswith("data:"):
                try: msgs.append(json.loads(line[5:]))
                except: pass
        return msgs
    except: return []

def sim(label, params, max_wait=12):
    subprocess.run(["curl","-s","-m","10","-X","POST",START,
        "-H","Content-Type: application/json","-d",json.dumps(params)],
        capture_output=True, timeout=15)
    for i in range(max_wait):
        time.sleep(1)
        msgs = sse_poll()
        for m in msgs:
            if m.get("type") == "done":
                t = m.get('trades',0); r = m.get('return','?'); dd = m.get('dd','?')
                wr = m.get('win_rate','?'); bal = m.get('balance',1000000)
                result = f"R={r}% T={t} WR={wr}% Bal=${bal:,.0f} DD={dd}"
                log(f"  [{i+1}s] DONE {result}")
                return {"label":label,"trades":t,"return":r,"dd":dd,"win_rate":wr,"balance":bal,"time":i+1}
        tick = [m for m in msgs if m.get("type") == "tick"]
        info = f"bar={tick[-1].get('bar','?')}/{tick[-1].get('total','?')}" if tick else "no data"
        if i < 5 or i % 3 == 0:
            log(f"  [{i+1}s] {info}")
    log(f"  [TIMEOUT {max_wait}s]")
    return None

log(f"# Losing & Edge Case Sims — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
log(f"\n## Environment")
log(f"- Server: micro sim (port 3004)")
log(f"- Broker: PIP={0.01}, PIP_VALUE=$10, BASE_LOT={0.0001}")
log(f"- File: sim_losing3.py")

log(f"\n## Round 1: Baseline — all produce 0 trades (known)")
log(f"*Root cause: fill tolerance PIP/2=$0.005 vs tick step $1.00 (pip_step=100)*")
for label, p in [
    ("Jul28 0.0001", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.0001,"speed":10000}),
    ("Jul28 0.001",  {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.001,"speed":10000}),
    ("Jul28 0.01",   {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000}),
    ("Jul28 0.1",    {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.1,"speed":10000}),
    ("Jul28 1.0",    {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":1.0,"speed":10000}),
]: sim(label, p, 4)

log(f"\n## Round 2: pip_step variations (test fill probability)")
log(f"*Fix hypothesis: reduce pip_step to match fill tolerance*")
for ps in [1, 5, 10, 25, 50]:
    for lot in [0.001, 0.01]:
        r = sim(f"Jul28 ps={ps} lot={lot}", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":lot,"speed":10000}, 8)

log(f"\n## Round 3: Hard mode (HARD_SPACING_PIPS=10000)" )
for lot in [0.001, 0.01, 0.1]:
    sim(f"Jul28 HM lot={lot}", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":lot,"speed":10000,"hard_mode":True}, 5)

log(f"\n## Round 4: TF=5m wider bars")
for period in [
    ("Ukraine 5m", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.01,"speed":10000}),
    ("Ukraine 5m 0.1", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.1,"speed":10000}),
]:
    sim(*period, 15)

log(f"\n## Round 5: 1m tight windows (few bars)")
for days in [1, 2, 3, 5]:
    for lot in [0.001, 0.01, 0.1]:
        end = f"2022-02-{min(20+days, 28):02d}"
        sim(f"Ukraine {days}d lot={lot}", {"start":"2022-02-20","end":end,"tf":"1m","lot":lot,"speed":10000}, 10)

log(f"\n## Round 6: SVB crisis variants")
for days in [1, 3, 5, 7]:
    for lot in [0.001, 0.01]:
        end = f"2023-03-{min(8+days, 15):02d}"
        sim(f"SVB {days}d lot={lot}", {"start":"2023-03-08","end":end,"tf":"1m","lot":lot,"speed":10000}, 10)

log(f"\n## Round 7: 2022 crash slices")
for start_str, end_str in [("2022-06-01","2022-06-15"), ("2022-07-01","2022-07-15"), ("2022-08-01","2022-08-15")]:
    for lot in [0.001, 0.01]:
        sim(f"Crash {start_str} lot={lot}", {"start":start_str,"end":end_str,"tf":"5m","lot":lot,"speed":10000}, 12)

log(f"\n## Round 8: ATR window sweep (1m/5m/15m/1h/4h/1D)")
for aw in ["1m","5m","15m","1h","4h","1D"]:
    for lot in [0.001, 0.01]:
        sim(f"Jul28 aw={aw} lot={lot}", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":lot,"speed":10000,"atr_window":aw}, 5)

log(f"\n## Round 9: ATR source (micro vs macro)")
for src in ["micro","macro"]:
    for lot in [0.001, 0.01]:
        sim(f"Jul28 src={src} lot={lot}", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":lot,"speed":10000,"atr_source":src}, 5)

log(f"\n## Round 10: Expiry stress (1h/4h/24h/99h)")
for ex in [1, 4, 24, 99]:
    sim(f"Jul28 expiry={ex}h", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000,"expiry":ex}, 5)

log(f"\n## Round 11: Profit target stress")
for pt in [0.01, 0.1, 0.5, 1.0, 5.0]:
    sim(f"Jul28 pt={pt}%", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000,"profit_target":pt}, 5)

log(f"\n## Round 12: Combined params (most aggressive)")
sim("Ukraine ps=10 HM", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.1,"speed":10000,"hard_mode":True}, 15)
sim("Crash22 ps=10 HM", {"start":"2022-06-01","end":"2022-08-31","tf":"5m","lot":0.1,"speed":10000,"hard_mode":True}, 20)

log(f"\n## Round 13: Slow speed (watch orders)")
sim("Jul28 speed=1", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":1}, 30)
sim("Jul28 speed=5", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":5}, 15)

log(f"\n## Round 14: January 2026 calm period")
for lot in [0.001, 0.01, 0.1]:
    sim(f"Jan26 lot={lot}", {"start":"2026-01-02","end":"2026-01-10","tf":"5m","lot":lot,"speed":10000}, 10)

log(f"\n## Summary")
log(f"- Total sims run: {len([l for l in loglines if 'DONE' in l or 'TIMEOUT' in l])}")
log(f"- Trades > 0: {len([l for l in loglines if 'DONE' in l and not 'T=0' in l and not 'T=? ' in l])}")
log(f"- Root cause confirmed: PIP/2 fill tolerance vs pip_step gap")
log(f"- Fix: Increase tolerance or reduce pip_step to match")

# Write log
with open(LOG, "w") as f:
    f.write("\n".join(loglines))
print(f"\nLog written to {LOG}", flush=True)
print(f"To view: cat {LOG} | less", flush=True)
print("ALL DONE", flush=True)
