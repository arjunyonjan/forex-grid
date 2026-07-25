import json, urllib.request, sys
from datetime import datetime

URL = "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?range=1mo&interval=1h"
headers = {"User-Agent": "Mozilla/5.0"}
req = urllib.request.Request(URL, headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())
ts = data["chart"]["result"][0]["timestamp"]
q = data["chart"]["result"][0]["indicators"]["quote"][0]
kf = []
for i, t in enumerate(ts):
    o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
    if o and h and l and c:
        kf.append({"date": datetime.utcfromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
                    "open": round(o,2), "high": round(h,2),
                    "low": round(l,2), "close": round(c,2)})
print(f"Total hourly bars: {len(kf)}")
print(f"Date range: {kf[0]['date']} to {kf[-1]['date']}")
print(f"First: {kf[0]}")
print(f"Last:  {kf[-1]}")
with open('/root/forex-grid/gcf_hourly.json','w') as f:
    json.dump(kf, f)
print("Saved to /root/forex-grid/gcf_hourly.json")
