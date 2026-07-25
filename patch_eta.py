c = open("/root/forex-grid/main.py").read()
# Add year to sim_time
c = c.replace('"%b %d %H:%M:%S NST"', '"%Y %b %d %H:%M:%S"')
# Remove eta_seconds from broadcast msg
c = c.replace(', "eta_seconds": max(0, int((total_ticks - tick_count) / speed_multiplier))', '')
open("/root/forex-grid/main.py", "w").write(c)
print("fixed: year in sim_time, eta removed")
