with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

# CSS update
old_css_line = '.big-row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:4px;margin-bottom:4px}'
new_css_line = '.big-row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:4px;margin-bottom:4px}'
if old_css_line in content:
    content = content.replace(old_css_line, new_css_line)
    print("CSS updated to 4 columns")
else:
    print("CSS line not found, trying alt...")
    old_css2 = '.big-row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:4px;margin-bottom:4px}'
    if old_css2 in content:
        content = content.replace(old_css2, new_css_line)
        print("CSS updated (alt)")

# Remove media query entries for 5 cols
content = content.replace(
    '@media(max-width:700px){.big-row{grid-template-columns:1fr 1fr 1fr}.big-card{min-height:48px}.big-val{font-size:14px}}',
    '@media(max-width:700px){.big-row{grid-template-columns:1fr 1fr}.big-card{min-height:48px}.big-val{font-size:14px}}'
)
content = content.replace(
    '@media(max-width:480px){.big-row{grid-template-columns:1fr 1fr}.big-card{min-height:42px}.big-val{font-size:13px}.c{padding:4px}}',
    '@media(max-width:480px){.big-row{grid-template-columns:1fr 1fr}.big-card{min-height:38px}.big-val{font-size:12px}.c{padding:3px}}'
)
print("Media queries updated")

# Split: close big-row after ATR card, put group panel in its own row
old_group = '''    <div class=card style="flex:1;min-width:220px;padding:8px">
      <div style="display:flex;gap:8px;height:100%">
        <div style="flex:1;display:flex;flex-direction:column;gap:4px">
          <div style="flex:1;display:flex;flex-direction:column;justify-content:center;text-align:center;padding:4px">
            <div style="font-size:10px;color:var(--fg2)">Net P&amp;L</div>
            <div id=netPnlVal style="font-size:20px;font-weight:700">--</div>
            <div id=pnlSub style="font-size:10px;color:var(--fg2)">--</div>
          </div>
          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2)">Open P&amp;L</div>
            <div id=openPnlVal style="font-size:16px;font-weight:700;color:var(--cyn)">--</div>
            <div id=openSub style="font-size:9px;color:var(--fg2)">-- trades</div>
          </div>
        </div>
        <div style="width:1px;background:var(--bd)"></div>
        <div style="flex:1;display:flex;flex-direction:column;gap:4px">
          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2)">Profit</div>
            <div id=winPnlVal style="font-size:16px;font-weight:700;color:var(--grn)">--</div>
            <div id=winSub style="font-size:9px;color:var(--fg2)">--</div>
          </div>
          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2)">Loss</div>
            <div id=lossPnlVal style="font-size:16px;font-weight:700;color:var(--red)">--</div>
            <div id=lossSub style="font-size:9px;color:var(--fg2)">--</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Chart -->'''

new_group = '''  </div>

  <!-- Stats panel -->
  <div class=card style="padding:6px;margin-bottom:4px">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px">
      <div style="text-align:center;padding:2px">
        <div style="font-size:9px;color:var(--fg2)">Net P&amp;L</div>
        <div id=netPnlVal style="font-size:15px;font-weight:700">--</div>
        <div id=pnlSub style="font-size:9px;color:var(--fg2)">--</div>
      </div>
      <div style="text-align:center;padding:2px">
        <div style="font-size:9px;color:var(--fg2)">Open P&amp;L</div>
        <div id=openPnlVal style="font-size:15px;font-weight:700;color:var(--cyn)">--</div>
        <div id=openSub style="font-size:9px;color:var(--fg2)">-- trades</div>
      </div>
      <div style="text-align:center;padding:2px">
        <div style="font-size:9px;color:var(--fg2)">Profit</div>
        <div id=winPnlVal style="font-size:15px;font-weight:700;color:var(--grn)">--</div>
        <div id=winSub style="font-size:9px;color:var(--fg2)">-- wins</div>
      </div>
      <div style="text-align:center;padding:2px">
        <div style="font-size:9px;color:var(--fg2)">Loss</div>
        <div id=lossPnlVal style="font-size:15px;font-weight:700;color:var(--red)">--</div>
        <div id=lossSub style="font-size:9px;color:var(--fg2)">-- losses</div>
      </div>
    </div>
  </div>

  <!-- Chart -->'''

if old_group in content:
    content = content.replace(old_group, new_group)
    print("Group panel restructured")
else:
    print("Group panel pattern not found")

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("ALL DONE")
