import json, urllib.request
with open("/root/forex-grid/gcf_15m.json") as f:
    kf = json.load(f)
data = json.dumps({"keyframes": kf, "spacing": 100, "tick_scale": 15}).encode()
req = urllib.request.Request("http://127.0.0.1:3001/sim-keyframes", data=data,
    headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=300) as resp:
    d = json.loads(resp.read())
print(f"15m@100p: ret={d.get('return_pct',0):+.2f}%  DD={d.get('max_dd',0):.1f}%  trades={d.get('total_trades',0)}  ticks={d.get('ticks',0)}  bars={d.get('days',0)}")
