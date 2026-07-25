import json, urllib.request, sys
from datetime import datetime

URL = "https://query1.finance.yahoo.com/v8/finance/chart/%3DXAUUSD?range=1mo&interval=1d"
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
        kf.append({"date": datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"),
                    "open": round(o,2), "high": round(h,2),
                    "low": round(l,2), "close": round(c,2)})
print(json.dumps({"keyframes": kf, "count": len(kf)}, indent=2))
