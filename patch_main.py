with open("/root/forex-grid/main.py") as f:
    lines = f.readlines()

out = []
for i, line in enumerate(lines):
    out.append(line)
    # Move dt calc right before tick_prices in keyframe loop
    if "update_atr(mid_p)" in line:
        out.append("            dt = sim_start + timedelta(seconds=day_idx * 900 + tick)\n")
    # Remove standalone dt lines that are now redundant
    if line.strip().startswith("dt = sim_start") and "tick" in line:
        continue

with open("/root/forex-grid/main.py", "w") as f:
    f.writelines(out)
print("patched")
