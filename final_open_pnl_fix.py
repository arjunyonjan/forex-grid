with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

old_block = '''  // Open P&L (unrealized)
  var upnlColor=upnl>=0?"var(--grn)":"var(--red)";
  // Open P&L (unrealized)
  var upnlColor=upnl>=0?"var(--grn)":"var(--red)";
  $("openPnlVal").textContent=(upnl>=0?"+":"")+upnl.toFixed(2);
  $("openPnlVal").style.color=upnlColor;
  $("openSub").textContent=openTrades+" open trades";'''

new_block = '''  // Open P&L (unrealized)
  var upnl=d.upnl||0,openTrades=d.open_trades||0;
  var upnlColor=upnl>=0?"var(--grn)":"var(--red)";
  $("openPnlVal").textContent=(upnl>=0?"+":"")+upnl.toFixed(2);
  $("openPnlVal").style.color=upnlColor;
  $("openSub").textContent=openTrades+" open trades";'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Open P&L JS fixed")
else:
    print("Pattern not found - checking alternatives...")
    import re
    # Find the broken block and replace the whole thing
    pattern = r'// Open P&L \(unrealized\)[\s\S]*?open trades";'
    matches = list(re.finditer(pattern, content))
    print(f"Found {len(matches)} matches")
    if matches:
        # Replace last occurrence (the complete one is likely the later one)
        for m in matches:
            print(f"  Match: {repr(m.group()[:60])}...")
        # Replace all occurrences
        content = re.sub(pattern, new_block, content)

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("Done")
