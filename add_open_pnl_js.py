with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

insert = '\n  // Open P&L (unrealized)\n  var upnl=d.upnl||0,openTrades=d.open_trades||0;\n  var upnlColor=upnl>=0?"var(--grn)":"var(--red)";\n  $("openPnlVal").textContent=(upnl>=0?"+":"")+upnl.toFixed(2);\n  $("openPnlVal").style.color=upnlColor;\n  $("openSub").textContent=openTrades+" open trades";'

marker = '\n  // Win/Loss breakdown'

if marker in content:
    content = content.replace(marker, insert + marker)
    print("Open P&L JS added")
else:
    print("Marker not found")

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("Done")
