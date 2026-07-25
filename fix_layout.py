with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

new_big_row = '  <div class=big-row>\n    <div class=card big-card>\n      <div class=big-label>XAU/USD</div>\n      <div class=big-val id=priceVal style=font-size:24px>--</div>\n      <div class=big-sub id=priceSub>Bid / Ask</div>\n    </div>\n    <div class=card big-card>\n      <div class=big-label>Balance</div>\n      <div class=big-val id=moneyVal>--</div>\n      <div class=big-sub id=moneySub>Today: --</div>\n    </div>\n    <div class=card big-card>\n      <div class=big-label>Risk</div>\n      <div class=big-val id=riskVal>0%</div>\n      <div class=dd-bar-wrap><div class=dd-bar-fill id=ddBar style=width:0%></div></div>\n      <div class=big-sub id=riskSub>--% drawdown</div>\n    </div>\n    <div class=card big-card>\n      <div class=big-label>Market State (ATR)</div>\n      <div class=big-val id=atrVal>--</div>\n      <div class=big-sub id=atrSub>--</div>\n    </div>\n    <div class=card style="flex:1;min-width:220px;padding:8px">\n      <div style="display:flex;gap:8px;height:100%">\n        <div style="flex:1;display:flex;flex-direction:column;gap:4px">\n          <div style="flex:1;display:flex;flex-direction:column;justify-content:center;text-align:center;padding:4px">\n            <div style="font-size:10px;color:var(--fg2)">Net P&amp;L</div>\n            <div id=netPnlVal style="font-size:20px;font-weight:700">--</div>\n            <div id=pnlSub style="font-size:10px;color:var(--fg2)">--</div>\n          </div>\n          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">\n            <div style="font-size:9px;color:var(--fg2)">Open P&amp;L</div>\n            <div id=openPnlVal style="font-size:16px;font-weight:700;color:var(--cyn)">--</div>\n            <div id=openSub style="font-size:9px;color:var(--fg2)">-- trades</div>\n          </div>\n        </div>\n        <div style="width:1px;background:var(--bd)"></div>\n        <div style="flex:1;display:flex;flex-direction:column;gap:4px">\n          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">\n            <div style="font-size:9px;color:var(--fg2)">Profit</div>\n            <div id=winPnlVal style="font-size:16px;font-weight:700;color:var(--grn)">--</div>\n            <div id=winSub style="font-size:9px;color:var(--fg2)">--</div>\n          </div>\n          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">\n            <div style="font-size:9px;color:var(--fg2)">Loss</div>\n            <div id=lossPnlVal style="font-size:16px;font-weight:700;color:var(--red)">--</div>\n            <div id=lossSub style="font-size:9px;color:var(--fg2)">--</div>\n          </div>\n        </div>\n      </div>\n    </div>\n  </div>\n\n  <!-- Chart -->'

old_big_row_start = '  <div class=big-row>'
old_big_row_end = '  <!-- Chart -->'

start_idx = content.find(old_big_row_start)
end_idx = content.find(old_big_row_end)
if start_idx != -1 and end_idx != -1:
    before = content[:start_idx]
    after = content[end_idx:]
    content = before + new_big_row + after
    print("Big-row replaced")
else:
    print("Could not find markers")

import re
content = re.sub(r'\s*// Activity[\s\S]*?actSub\.textContent[^\n]*\n', '', content)
content = re.sub(r'\s*\$\(\\"actVal\\"\)[^\n]*\n', '', content)

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("Done")
