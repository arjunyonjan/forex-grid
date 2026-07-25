import json, sys
sys.path.insert(0, '/root/forex-grid')
import broker

full_kf = [
    {'open':4127.1,'high':4135.2,'low':4118.5,'close':4129.9},
    {'open':4104.4,'high':4104.7,'low':3963.3,'close':3990.3},
    {'open':3988.4,'high':4030.5,'low':3986.7,'close':4030.5},
    {'open':4078.7,'high':4078.7,'low':4078.7,'close':4078.7},
    {'open':4057.5,'high':4070.0,'low':4003.2,'close':4022.3},
    {'open':4002.6,'high':4049.7,'low':3962.5,'close':4022.9},
    {'open':4013.1,'high':4100.0,'low':3963.0,'close':4068.3},
    {'open':4067.5,'high':4140.1,'low':4062.0,'close':4112.7},
    {'open':4175.4,'high':4199.7,'low':4134.2,'close':4155.1},
    {'open':4126.5,'high':4167.2,'low':4107.2,'close':4145.3},
    {'open':4116.3,'high':4120.3,'low':4053.0,'close':4070.9},
    {'open':4066.4,'high':4130.6,'low':4064.2,'close':4130.6},
    {'open':4122.3,'high':4125.8,'low':4090.6,'close':4104.1},
    {'open':4081.0,'high':4081.0,'low':3985.9,'close':3997.0},
    {'open':3995.7,'high':4091.2,'low':3986.5,'close':4061.1},
    {'open':4049.1,'high':4070.1,'low':4019.4,'close':4044.0},
    {'open':4030.5,'high':4030.5,'low':3972.6,'close':3985.6},
    {'open':3975.5,'high':4017.2,'low':3964.2,'close':4012.7},
    {'open':4003.4,'high':4018.9,'low':4002.7,'close':4010.3},
    {'open':4002.1,'high':4071.1,'low':3999.7,'close':4071.1},
    {'open':4096.2,'high':4152.1,'low':4096.2,'close':4146.9},
    {'open':4126.0,'high':4144.0,'low':4042.5,'close':4052.3},
]

broker.orders.clear()
broker.trades.clear()
broker.hit_log.clear()
broker.balance = 10000.0
broker.start_balance = 10000.0
broker.daily_start_balance = 10000.0
broker.month_start_balance = 10000.0
broker.equity_peak = 10000.0
broker.daily_trade_count = 0
broker.total_trades = 0
broker.current_atr = 5.0
broker.current_spacing = 100
broker.current_tp = 100
broker.current_sl = 250
broker.lot_size = 0.001
broker.trading_halted = False

# Monkey-patch to add debug before clearing
orig_fn = broker.simulate_from_keyframes
def debug_fn(*args, **kwargs):
    global _last_hitlog
    # Save hit_log ref before calling
    result = orig_fn(*args, **kwargs)
    # hit_log was cleared inside, but result has the data
    return result

res = debug_fn(full_kf, init_bal=10000.0, spacing=100)
# Recompute from result to check consistency
avg_pnl = res["avg_tp_pnl"]
wins = res["wins"]
total_pnl = res["total_pnl"]
closed_pnl = res["end_balance"] - res["start_balance"]
floating_pnl = res["end_equity"] - res["end_balance"]
print("=== PnL DEBUG ===")
print(f"TP hits (wins)      : {wins}")
print(f"Avg TP PnL per hit  : ${avg_pnl}")
print(f"Expected from TP hits: ${wins * avg_pnl:.2f}")
print(f"Closed PnL (balance): ${closed_pnl:.2f}")
print(f"Floating PnL (open) : ${floating_pnl:.2f}")
print(f"Total PnL (equity)  : ${total_pnl:.2f}")
print(f"Ratio (closed/expect): {closed_pnl/(wins*avg_pnl) if wins*avg_pnl else 0:.1f}x")
print(f"Total trades opened : {res['total_trades']}")
print(json.dumps(res, indent=2))
