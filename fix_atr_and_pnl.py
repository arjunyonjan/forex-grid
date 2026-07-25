with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

# 1. Fix ATR thresholds
old_thresh = '''  if(atr<1){emote="DEAD";color="#666";advice="No movement"}
  else if(atr<3){emote="CALM";color="var(--grn)";advice="Full lot, tight grid"}
  else if(atr<6){emote="ACTIVE";color="var(--yel)";advice="Normal conditions"}
  else if(atr<10){emote="VOLATILE";color="var(--orng)";advice="Widen spacing"}
  else if(atr<15){emote="CHAOTIC";color="var(--red)";advice="Halve lot, wide grid"}
  else{emote="CRISIS";color="#a00";advice="Halt recommended"}'''

new_thresh = '''  if(atr<100){emote="DEAD";color="#666";advice="No movement"}
  else if(atr<300){emote="CALM";color="var(--grn)";advice="Full lot, tight grid"}
  else if(atr<600){emote="ACTIVE";color="var(--yel)";advice="Normal conditions"}
  else if(atr<1000){emote="VOLATILE";color="var(--orng)";advice="Widen spacing"}
  else if(atr<2000){emote="CHAOTIC";color="var(--red)";advice="Halve lot, wide grid"}
  else{emote="CRISIS";color="#a00";advice="Halt recommended"}'''

if old_thresh in content:
    content = content.replace(old_thresh, new_thresh)
    print("ATR thresholds updated")
else:
    print("Warning: ATR thresholds pattern not found - trying alternate...")
    # Might have different whitespace
    import re
    content = re.sub(
        r'if\(atr<1\).*?CRISIS.*?recommended"\}',
        new_thresh.replace('\n', '\\n'),
        content
    )

# 2. Replace single Net P&L big-card with group panel (Net P&L + Profit Only + Loss Only)
old_card = '''    <div class=card big-card>
      <div class=big-label>Net P&amp;L</div>
      <div class=big-val id=netPnlVal>--</div>
      <div class=big-sub id=pnlSub>--</div>
    </div>'''

new_group = '''    <div class=card style="flex:1;min-width:220px;padding:8px">
      <div style="display:flex;gap:8px;height:100%">
        <div style="flex:1;display:flex;flex-direction:column;justify-content:center;text-align:center;padding:4px">
          <div style="font-size:10px;color:var(--fg2);text-transform:uppercase;margin-bottom:2px">Net P&amp;L</div>
          <div id=netPnlVal style="font-size:20px;font-weight:700">--</div>
          <div id=pnlSub style="font-size:10px;color:var(--fg2)">--</div>
        </div>
        <div style="width:1px;background:var(--bd)"></div>
        <div style="flex:1;display:flex;flex-direction:column;gap:4px">
          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2);text-transform:uppercase">Profit</div>
            <div id=winPnlVal style="font-size:16px;font-weight:700;color:var(--grn)">--</div>
            <div id=winSub style="font-size:9px;color:var(--fg2)">--</div>
          </div>
          <div style="flex:1;text-align:center;background:var(--hl);border-radius:6px;padding:4px;display:flex;flex-direction:column;justify-content:center">
            <div style="font-size:9px;color:var(--fg2);text-transform:uppercase">Loss</div>
            <div id=lossPnlVal style="font-size:16px;font-weight:700;color:var(--red)">--</div>
            <div id=lossSub style="font-size:9px;color:var(--fg2)">--</div>
          </div>
        </div>
      </div>
    </div>'''

if old_card in content:
    content = content.replace(old_card, new_group)
    print("Net P&L card replaced with group panel")
else:
    print("Warning: Net P&L card pattern not found")

# 3. Add win/loss JS after Net P&L JS
old_pnl_js = '''  // Net P&L
  var totalPnl=d.total_pnl||0,retPct=d.return_pct||0;
  var pnlColor=totalPnl>=0?"var(--grn)":"var(--red)";
  $("netPnlVal").textContent=(totalPnl>=0?"+":"")+totalPnl.toFixed(2);
  $("netPnlVal").style.color=pnlColor;
  $("pnlSub").textContent="Return: "+(retPct>=0?"+":"")+retPct.toFixed(2)+"%";'''

new_pnl_js = '''  // Net P&L
  var totalPnl=d.total_pnl||0,retPct=d.return_pct||0;
  var pnlColor=totalPnl>=0?"var(--grn)":"var(--red)";
  $("netPnlVal").textContent=(totalPnl>=0?"+":"")+totalPnl.toFixed(2);
  $("netPnlVal").style.color=pnlColor;
  $("pnlSub").textContent="Return: "+(retPct>=0?"+":"")+retPct.toFixed(2)+"%";

  // Win/Loss breakdown
  var winPnl=d.win_pnl||0,lossPnl=d.loss_pnl||0;
  var wins=d.wins||0,losses=d.losses||0;
  $("winPnlVal").textContent="+"+winPnl.toFixed(2);
  $("winPnlVal").style.color="var(--grn)";
  $("winSub").textContent=wins+" wins";
  $("lossPnlVal").textContent=lossPnl.toFixed(2);
  $("lossPnlVal").style.color="var(--red)";
  $("lossSub").textContent=losses+" losses";'''

if old_pnl_js in content:
    content = content.replace(old_pnl_js, new_pnl_js)
    print("Win/Loss JS added")
else:
    print("Warning: Net P&L JS not found")

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("ALL DONE")
