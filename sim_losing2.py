"""Hour-long losing condition sims: test why grid produces 0 trades + edge cases."""
import subprocess, json, time, sys

SSE_URL = "http://127.0.0.1:3004/stream-micro"
START_URL = "http://127.0.0.1:3004/micro-start"

def sse():
    try:
        r = subprocess.run(["curl","-s","-m","3",SSE_URL], capture_output=True, timeout=5)
        msgs = []
        for line in r.stdout.decode().split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                try: msgs.append(json.loads(line[5:]))
                except: pass
        return msgs
    except: return []

def start(params):
    subprocess.run(["curl","-s","-m","10","-X","POST",START_URL,
        "-H","Content-Type: application/json","-d",json.dumps(params)],
        capture_output=True, timeout=15)

def run(label, params, max_wait=10):
    print(f"\n--- {label} ---", flush=True)
    start(params)
    for i in range(max_wait):
        time.sleep(1)
        msgs = sse()
        for m in msgs:
            if m.get("type") == "done":
                print(f"  DONE [{i+1}s] R={m.get('return')}% T={m.get('trades')} WR={m.get('win_rate')}% Bal=${m.get('balance',0):,.0f} DD={m.get('dd')}", flush=True)
                return m.get('trades',0)
        tick = [m for m in msgs if m.get("type") == "tick"]
        info = f"bar={tick[-1].get('bar','?')}/{tick[-1].get('total','?')}" if tick else "no SSE"
        print(f"  [{i+1}s] {info}", flush=True)
    print(f"  TIMEOUT", flush=True)
    return None

print("="*60, flush=True)
print("ROUND 1: Grid params — why 0 trades?", flush=True)
print("="*60, flush=True)

# Test different grid spacings and pip_steps
run("Jul28 pip_step=10", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.001,"speed":10000}, 5)
run("Jul28 pip_step=50", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.001,"speed":10000}, 5)
run("Ukraine pip_step=10", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.001,"speed":10000}, 15)
run("Crash22 pip_step=10", {"start":"2022-06-01","end":"2022-08-31","tf":"5m","lot":0.001,"speed":10000}, 20)

print("\n"+"="*60, flush=True)
print("ROUND 2: ATR & spacing variations", flush=True)
print("="*60, flush=True)

run("Jul28 min_spc=500", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000}, 5)
run("Jul28 min_spc=100", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000}, 5)
run("Ukraine min_spc=500", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.01,"speed":10000}, 15)
run("Ukraine macro ATR", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.01,"speed":10000,"atr_source":"macro"}, 15)

print("\n"+"="*60, flush=True)
print("ROUND 3: Hard mode + high lot", flush=True)
print("="*60, flush=True)

run("Jul28 hardmode", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.1,"speed":10000,"hard_mode":True}, 5)
run("Ukraine hardmode", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.1,"speed":10000,"hard_mode":True}, 15)
run("Crash22 hardmode", {"start":"2022-06-01","end":"2022-08-31","tf":"5m","lot":0.1,"speed":10000,"hard_mode":True}, 20)

print("\n"+"="*60, flush=True)
print("ROUND 4: 1m data for volatile periods", flush=True)
print("="*60, flush=True)

run("Ukraine 1m data", {"start":"2022-02-24","end":"2022-02-28","tf":"1m","lot":0.01,"speed":10000}, 15)
run("SVB 1m data", {"start":"2023-03-08","end":"2023-03-15","tf":"1m","lot":0.01,"speed":10000}, 15)

print("\n"+"="*60, flush=True)
print("ROUND 5: Extreme params", flush=True)
print("="*60, flush=True)

run("Jul28 lot=1.0", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":1.0,"speed":10000}, 5)
run("Ukraine lot=1.0", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":1.0,"speed":10000}, 15)

print("\n"+"="*60, flush=True)
print("ROUND 6: Long expiry + larger range", flush=True)
print("="*60, flush=True)

run("Jul28 expiry=24h", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000,"expiry":24}, 5)
run("Ukraine expiry=24h", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.01,"speed":10000,"expiry":24}, 15)
run("Crash22 expiry=24h", {"start":"2022-06-01","end":"2022-08-31","tf":"5m","lot":0.01,"speed":10000,"expiry":24}, 20)

print("\n"+"="*60, flush=True)
print("ROUND 7: Micro gaps + sweeps (single bar)", flush=True)
print("="*60, flush=True)

# Single big bars that should trigger fills
run("Jul28 atr_window=15m", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000,"atr_window":"15m"}, 5)
run("Jul28 atr_window=1h", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000,"atr_window":"1h"}, 5)
run("Jul28 atr_window=4h", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000,"atr_window":"4h"}, 5)

print("\n"+"="*60, flush=True)
print("ROUND 8: 2026 full year crash", flush=True)
print("="*60, flush=True)

run("Crash2026 5m", {"start":"2026-01-01","end":"2026-03-31","tf":"5m","lot":0.01,"speed":10000}, 20)
run("Crash2026 1m", {"start":"2026-01-15","end":"2026-01-25","tf":"1m","lot":0.01,"speed":10000}, 15)
run("July2026 rally", {"start":"2026-07-01","end":"2026-07-28","tf":"5m","lot":0.01,"speed":10000}, 20)

print("\n"+"="*60, flush=True)
print("ROUND 9: Risk param stress", flush=True)
print("="*60, flush=True)

run("Jul28 profit_target=1%", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.1,"speed":10000,"profit_target":1.0}, 5)
run("Ukraine profit_target=1%", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.1,"speed":10000,"profit_target":1.0}, 15)

print("\n"+"="*60, flush=True)
print("ROUND 10: Slow speed observation", flush=True)
print("="*60, flush=True)

run("Jul28 speed=10 obs", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.1,"speed":10}, 60)
run("Jul28 speed=50 obs", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.1,"speed":50}, 30)

print("\n"+"="*60, flush=True)
print("ALL ROUNDS COMPLETE", flush=True)
print("="*60, flush=True)
