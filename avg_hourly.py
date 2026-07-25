import json, subprocess, sys

with open("/root/forex-grid/gcf_hourly.json") as f:
    KF = json.load(f)

URL = "http://127.0.0.1:3001/sim-keyframes"
for sp in [100, 200, 500, 1000]:
    returns, dds, ratios = [], [], []
    for _ in range(3):
        data = {"keyframes": KF, "spacing": sp, "tick_scale": 60}
        r = subprocess.run(["curl", "-s", "-m", "300", "-X", "POST", URL,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(data)], capture_output=True, text=True, timeout=300)
        try:
            d = json.loads(r.stdout)
            ret = d.get("return_pct", 0)
            dd = d.get("max_dd", 0)
            pnl = d.get("total_pnl", 0)
            ratio = round(abs(pnl) / max(dd / 100 * 10000, 0.01), 1) if dd != 0 else 0
            returns.append(ret); dds.append(dd); ratios.append(ratio)
        except Exception as e:
            print(f"  Error: {e}")
    if returns:
        avg_r = round(sum(returns)/len(returns), 2)
        avg_dd = round(sum(dds)/len(dds), 2)
        avg_ratio = round(sum(ratios)/len(ratios), 1)
        print(f"{sp:5}p: avg_ret={avg_r:+.2f}%  avg_DD={avg_dd:.1f}%  avg_ratio={avg_ratio}:1  (n={len(returns)})")
