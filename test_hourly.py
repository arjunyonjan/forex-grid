import json, subprocess, sys

with open("/root/forex-grid/gcf_hourly.json") as f:
    kf = json.load(f)

URL = "http://127.0.0.1:3001/sim-keyframes"
data = {"keyframes": kf, "spacing": 100, "tick_scale": 60}
r = subprocess.run(["curl", "-s", "-m", "120", "-X", "POST", URL,
    "-H", "Content-Type: application/json",
    "-d", json.dumps(data)], capture_output=True, text=True, timeout=120)
try:
    d = json.loads(r.stdout)
    print(json.dumps(d, indent=2))
except:
    print("STDOUT:", r.stdout[:500])
    print("STDERR:", r.stderr[:500])
