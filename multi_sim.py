import json, subprocess, sys
URL = "http://127.0.0.1:3001/sim-keyframes"
KF = [
    {"open":4127.1,"high":4135.2,"low":4118.5,"close":4129.9},
    {"open":4104.4,"high":4104.7,"low":3963.3,"close":3990.3},
    {"open":3988.4,"high":4030.5,"low":3986.7,"close":4030.5},
    {"open":4078.7,"high":4078.7,"low":4078.7,"close":4078.7},
    {"open":4057.5,"high":4070.0,"low":4003.2,"close":4022.3},
    {"open":4002.6,"high":4049.7,"low":3962.5,"close":4022.9},
    {"open":4013.1,"high":4100.0,"low":3963.0,"close":4068.3},
    {"open":4067.5,"high":4140.1,"low":4062.0,"close":4112.7},
    {"open":4175.4,"high":4199.7,"low":4134.2,"close":4155.1},
    {"open":4126.5,"high":4167.2,"low":4107.2,"close":4145.3},
    {"open":4116.3,"high":4120.3,"low":4053.0,"close":4070.9},
    {"open":4066.4,"high":4130.6,"low":4064.2,"close":4130.6},
    {"open":4122.3,"high":4125.8,"low":4090.6,"close":4104.1},
    {"open":4081.0,"high":4081.0,"low":3985.9,"close":3997.0},
    {"open":3995.7,"high":4091.2,"low":3986.5,"close":4061.1},
    {"open":4049.1,"high":4070.1,"low":4019.4,"close":4044.0},
    {"open":4030.5,"high":4030.5,"low":3972.6,"close":3985.6},
    {"open":3975.5,"high":4017.2,"low":3964.2,"close":4012.7},
    {"open":4003.4,"high":4018.9,"low":4002.7,"close":4010.3},
    {"open":4002.1,"high":4071.1,"low":3999.7,"close":4071.1},
    {"open":4096.2,"high":4152.1,"low":4096.2,"close":4146.9},
    {"open":4126.0,"high":4144.0,"low":4042.5,"close":4052.3}
]

for sp in [100, 200, 500, 1000]:
    data = {"keyframes": KF, "spacing": sp}
    r = subprocess.run(["curl", "-s", "-m", "300", "-X", "POST", URL,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)], capture_output=True, text=True, timeout=300)
    try:
        d = json.loads(r.stdout)
        ret = d.get("return_pct", 0)
        dd = d.get("max_dd", 0)
        wins = d.get("wins", 0)
        tp = d.get("avg_tp_pnl", 0)
        trades = d.get("total_trades", 0)
        return_pnl = d.get("total_pnl", 0)
        ratio = round(abs(return_pnl) / max(abs(dd / 100 * 10000), 0.01), 1)
        print(f"{sp:5}p: return={ret:+.2f}%  DD={dd:.1f}%  ratio={ratio:.1f}:1  wins={wins}  trades={trades}  TP=${tp}")
    except Exception as e:
        print(f"{sp:5}p: ERROR {e}")
