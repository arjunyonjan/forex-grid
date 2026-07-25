c = open("/root/forex-grid/main.py").read()
# Narrow to Feb-Mar 2022 (invasion peak volatility)
c = c.replace(
    'keyframes = [k for k in keyframes if k["date"][:10] >= "2022-01-01" and k["date"][:10] <= "2022-06-30"]',
    'keyframes = [k for k in keyframes if k["date"][:10] >= "2022-02-01" and k["date"][:10] <= "2022-03-31"]'
)
# Set speed=1000 for ~60s total run
c = c.replace("speed_multiplier = 100", "speed_multiplier = 1000")
open("/root/forex-grid/main.py", "w").write(c)
print("patch3 applied: Feb-Mar 2022, speed=1000")
