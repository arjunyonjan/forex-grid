import json, subprocess, sys
URL = "http://127.0.0.1:3001/sim-keyframes"
KF = [{"open":4110,"high":4203,"low":4091,"close":4001},{"open":4001,"high":4045,"low":3963,"close":4028},{"open":4028,"high":4098,"low":3983,"close":4089},{"open":4089,"high":4098,"low":3983,"close":4018},{"open":4018,"high":4094,"low":4001,"close":4008},{"open":4008,"high":4065,"low":3944,"close":4031},{"open":4031,"high":4116,"low":3960,"close":4124},{"open":4124,"high":4144,"low":4030,"close":4176},{"open":4176,"high":4196,"low":4121,"close":4165},{"open":4165,"high":4203,"low":4128,"close":4107},{"open":4107,"high":4183,"low":4092,"close":4078},{"open":4078,"high":4134,"low":4022,"close":4122},{"open":4122,"high":4136,"low":4072,"close":4121},{"open":4121,"high":4123,"low":3986,"close":4002},{"open":4002,"high":4101,"low":3984,"close":4056},{"open":4056,"high":4081,"low":4017,"close":4062},{"open":4062,"high":4070,"low":3969,"close":3973},{"open":3973,"high":4024,"low":3960,"close":4018},{"open":4018,"high":4041,"low":3983,"close":4006},{"open":4006,"high":4087,"low":3999,"close":4078},{"open":4078,"high":4166,"low":4075,"close":4133},{"open":4133,"high":4141,"low":4040,"close":4056}]

for sp in [100, 200, 500, 1000]:
    returns, dds, ratios = [], [], []
    for _ in range(3):
        data = {"keyframes": KF, "spacing": sp}
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
        except: pass
    if returns:
        avg_r = round(sum(returns)/len(returns), 2)
        avg_dd = round(sum(dds)/len(dds), 2)
        avg_ratio = round(sum(ratios)/len(ratios), 1)
        print(f"{sp:5}p: avg_ret={avg_r:+.2f}%  avg_DD={avg_dd:.1f}%  avg_ratio={avg_ratio}:1")
