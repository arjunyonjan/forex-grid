import broker, json
kf = [{"open": 4000, "high": 4100, "low": 3900, "close": 4000}]
r = broker.simulate_from_keyframes(kf, 10000, 1000)
# Inspect hit_log before it gets cleared
# The function saves/restores state, so hit_log is empty after the call
# We need to patch temporarily
# Let's just check the result carefully
print(json.dumps(r, indent=2))

# Now let's add a custom test
import copy
saved_hit_log = copy.deepcopy(broker.hit_log)
broker.current_spacing = 1000
# Print first-order TP calc
gs = 1000 * 0.01
print(f"gs={gs}, TP_MULTIPLIER={broker.TP_MULTIPLIER}, LOT={broker.LOT}, PIP_VALUE={broker.PIP_VALUE}")
print(f"Expected gross per TP: (gs * TP_MULTIPLIER) / 0.01 * PIP_VALUE * LOT")
print(f"  = {gs} / 0.01 * {broker.PIP_VALUE} * {broker.LOT}")
print(f"  = ${gs / 0.01 * broker.PIP_VALUE * broker.LOT:.2f}")
print(f"Expected net: ${gs / 0.01 * broker.PIP_VALUE * broker.LOT - 0.30:.2f}")
broker.hit_log = saved_hit_log
