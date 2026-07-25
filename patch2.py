c = open("/root/forex-grid/main.py").read()

# Fix sim_start strptime to handle datetime strings with time component
c = c.replace(
    'datetime.strptime(kf[0]["date"], "%Y-%m-%d")',
    'datetime.strptime(kf[0]["date"][:10], "%Y-%m-%d")'
)

# Change from last-7-day cutoff to 2022 war period
old_cut = """keyframes = load_keyframes()
if keyframes:
    last_date = datetime.strptime(keyframes[-1]["date"][:10], "%Y-%m-%d")
    cutoff = (last_date - timedelta(days=7)).strftime("%Y-%m-%d")
    keyframes = [k for k in keyframes if k["date"][:10] >= cutoff]"""

new_cut = """keyframes = load_keyframes()
if keyframes:
    # 2022 Russia-Ukraine war: Jan-Jun 2022 (high vol in XAU/USD)
    keyframes = [k for k in keyframes if k["date"][:10] >= "2022-01-01" and k["date"][:10] <= "2022-06-30"]"""

c = c.replace(old_cut, new_cut, 1)
open("/root/forex-grid/main.py", "w").write(c)
print("patch2 applied: strptime fix + 2022 war period")
