with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

# 1. Remove the standalone Trades big-card
old_trades_card = '''    <div class=card big-card>
      <div class=big-label>Trades</div>
      <div class=big-val id=actVal>0</div>
      <div class=big-sub id=actSub>Total: 0</div>
    </div>
'''

if old_trades_card in content:
    content = content.replace(old_trades_card, '')
    print("Standalone Trades card removed")
else:
    print("Warning: Trades card not found")

# 2. Add "Open Trades" as 3rd item in right column of group panel
old_col_end = '''          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2);text-transform:uppercase">Loss</div>
            <div id=lossPnlVal style="font-size:16px;font-weight:700;color:var(--red)">--</div>
            <div id=lossSub style="font-size:9px;color:var(--fg2)">--</div>
          </div>
        </div>'''

new_col_end = '''          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2);text-transform:uppercase">Loss</div>
            <div id=lossPnlVal style="font-size:16px;font-weight:700;color:var(--red)">--</div>
            <div id=lossSub style="font-size:9px;color:var(--fg2)">--</div>
          </div>
          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2);text-transform:uppercase">Open</div>
            <div id=actVal style="font-size:16px;font-weight:700">0</div>
            <div id=actSub style="font-size:9px;color:var(--fg2)">Total: 0</div>
          </div>
        </div>'''

if old_col_end in content:
    content = content.replace(old_col_end, new_col_end)
    print("Open Trades added to group panel")
else:
    print("Warning: Group panel column end not found")

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("DONE")
