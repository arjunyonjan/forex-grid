import json, urllib.request, datetime

url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=7d"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
result = data["chart"]["result"][0]
timestamps = result["timestamp"]
quotes = result["indicators"]["quote"][0]

candles = []
for i, ts in enumerate(timestamps):
    o = quotes["open"][i]
    h = quotes["high"][i]
    l = quotes["low"][i]
    c = quotes["close"][i]
    if None in (o, h, l, c):
        continue
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    candles.append({
        "date": dt.strftime("%Y-%m-%d %H:%M"),
        "open": round(o, 1),
        "high": round(h, 1),
        "low": round(l, 1),
        "close": round(c, 1)
    })
print(f"Downloaded {len(candles)} 1m candles")
with open("/root/forex-grid/gcf_1m.json", "w") as f:
    json.dump(candles, f, indent=2)
print("Saved to /root/forex-grid/gcf_1m.json")
