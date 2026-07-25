import broker
kf = [{"open": 4000, "high": 4100, "low": 3900, "close": 4000}]
r = broker.simulate_from_keyframes(kf, 10000, 500)
print("Avg TP PnL:", r["avg_tp_pnl"])
print("Trades:", r["total_trades"], "Wins:", r["wins"])
print("Return:", r["return_pct"], "%")
print("Expected for 500p: gross=$5.00 - spread=$0.30 = $4.70 net")
