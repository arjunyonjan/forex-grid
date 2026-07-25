with open('/root/forex-grid/index.html','r') as f:
    content = f.read()
insert = '''  // Net P&L
  var totalPnl=d.total_pnl||0,retPct=d.return_pct||0;
  var pnlColor=totalPnl>=0?"var(--grn)":"var(--red)";
  $("netPnlVal").textContent=(totalPnl>=0?"+":"")+totalPnl.toFixed(2);
  $("netPnlVal").style.color=pnlColor;
  $("pnlSub").textContent="Return: "+(retPct>=0?"+":"")+retPct.toFixed(2)+"%";
'''
marker = '  $("actSub").textContent="Open: "+(d.open_trades||0)+" | Total: "+(d.total_trades||0);'
content = content.replace(marker, marker + '\n' + insert)
with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print('net P&L JS added')
