"""Losing conditions sim runner with SSE polling."""
import subprocess, json, time, sys

RUNNING = True

def sse_poll():
    """Quick SSE poll returning parsed messages."""
    try:
        r = subprocess.run(["curl", "-s", "-m", "3", "http://127.0.0.1:3004/stream-micro"],
            capture_output=True, timeout=5)
        msgs = []
        for line in r.stdout.decode().split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                try: msgs.append(json.loads(line[5:]))
                except: pass
        return msgs
    except:
        return []

def run(label, params, max_wait=8):
    global RUNNING
    print(f"\n--- {label} ---")
    sys.stdout.flush()
    data = json.dumps(params).encode()
    subprocess.run(["curl", "-s", "-m", "10", "-X", "POST", "http://127.0.0.1:3004/micro-start",
        "-H", "Content-Type: application/json", "-d", json.dumps(params)],
        capture_output=True, timeout=15)
    
    for i in range(max_wait):
        time.sleep(1)
        msgs = sse_poll()
        for m in msgs:
            if m.get("type") == "done":
                print(f"  [{i+1}s] DONE  R={m.get('return','?')}%  T={m.get('trades','?')}  WR={m.get('win_rate','?')}%  Bal=${m.get('balance',0):,.0f}  DD={m.get('dd','?')}")
                sys.stdout.flush()
                return m
        tick = [m for m in msgs if m.get("type") == "tick"]
        info = f"bar={tick[-1].get('bar','?')}/{tick[-1].get('total','?')}" if tick else "waiting..."
        print(f"  [{i+1}s] {info}")
        sys.stdout.flush()
    
    print(f"  [TIMEOUT {max_wait}s]")
    sys.stdout.flush()
    return None

print("=" * 50)
print("LOSING CONDITIONS SIMS")
print("=" * 50)

run("Jul28 0.0001", {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.0001,"speed":10000}, 5)
run("Jul28 0.001",  {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.001,"speed":10000}, 5)
run("Jul28 0.01",   {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.01,"speed":10000}, 5)
run("Jul28 0.1",    {"start":"2026-07-28","end":"2026-07-28","tf":"1m","lot":0.1,"speed":10000}, 5)
run("Ukraine 0.01", {"start":"2022-02-20","end":"2022-03-10","tf":"5m","lot":0.01,"speed":10000}, 15)
run("Crash22 0.01", {"start":"2022-06-01","end":"2022-08-31","tf":"5m","lot":0.01,"speed":10000}, 20)
run("SVB 0.01",     {"start":"2023-03-01","end":"2023-03-15","tf":"5m","lot":0.01,"speed":10000}, 15)

print("\n" + "=" * 50)
print("ALL DONE")
print("=" * 50)
