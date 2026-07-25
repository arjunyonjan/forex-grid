with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

# Add tab CSS
old_tab_css = 'details{font-size:11px}\ndetails summary{cursor:pointer;color:var(--fg2);padding:2px 0}\ndetails summary:hover{color:var(--fg)}\ndetails[open] summary{margin-bottom:3px}'
new_tab_css = '''/* Tabs */
.tab-bar{display:flex;gap:2px;margin-bottom:4px;overflow-x:auto}
.tab-btn{padding:5px 10px;border-radius:5px 5px 0 0;border:1px solid var(--bd);border-bottom:none;background:var(--bg);color:var(--fg2);cursor:pointer;font:inherit;font-size:11px;white-space:nowrap}
.tab-btn:hover{color:var(--fg);background:var(--hl)}
.tab-btn.active{background:var(--bg2);color:var(--fg);font-weight:600}
.tab-panel{display:none}
.tab-panel.active{display:block}'''

content = content.replace(old_tab_css, old_tab_css + '\n' + new_tab_css)
print("Tab CSS added")

# Find the bottom panels section - from "Grid + Positions" to end of safety net
old_bottom_start = '  <!-- Grid + Positions side by side -->'
old_bottom_end = '</div>\n</div>\n</div>'  # end of safety net card

# Actually let me find a more reliable marker - the safety net closing
safety_end_marker = '          </div>\n        </div>\n      </div>\n    </details>\n  </div>'

new_bottom = '''  <!-- Tabbed panels -->
  <div class="card" style="padding:6px">
    <div class="tab-bar">
      <button class="tab-btn active" onclick="switchTab('levels',this)">Levels</button>
      <button class="tab-btn" onclick="switchTab('trades',this)">Trades</button>
      <button class="tab-btn" onclick="switchTab('activity',this)">Activity</button>
      <button class="tab-btn" onclick="switchTab('info',this)">Info</button>
    </div>
    <div id="tab-levels" class="tab-panel active">
      <div style="display:flex;gap:4px;margin-bottom:4px">
        <span style="font-size:10px;color:var(--fg2)">Price Levels</span>
        <span style="font-size:10px;color:var(--fg2)" id="gridCount"></span>
        <span style="margin-left:auto;font-size:9px;padding:1px 4px;border-radius:4px;background:var(--hl)" id="gridParams"></span>
      </div>
      <div class="grid-list" id="gridLvls"></div>
    </div>
    <div id="tab-trades" class="tab-panel">
      <div style="display:flex;gap:4px;margin-bottom:4px">
        <span style="font-size:10px;color:var(--fg2)">Open Trades</span>
        <span style="font-size:10px;color:var(--fg2)" id="posCount"></span>
      </div>
      <div class="pos-list" id="posList" style="margin-bottom:6px"></div>
      <details style="font-size:11px">
        <summary style="font-size:10px;color:var(--fg2)">Closed Trades (last 20)</summary>
        <div class="hit-list" id="closedList"></div>
      </details>
    </div>
    <div id="tab-activity" class="tab-panel">
      <div class="hit-list" id="hitLog"></div>
    </div>
    <div id="tab-info" class="tab-panel" style="font-size:11px;color:var(--fg2);line-height:1.5">
      <p style="margin-bottom:4px"><strong>Three guards protect your account:</strong></p>
      <div style="margin:4px 0;padding:6px;background:var(--hl);border-radius:4px;border-left:3px solid var(--grn)">
        <strong style="color:var(--grn);font-size:10px">1. Position Size</strong>
        <div style="font-size:10px">Each trade uses <strong id="lotExplain">0.01 lots</strong> = <strong id="unitExplain">100 units</strong>. A $1 move = <strong id="pipExplain">$0.10</strong>. No single trade can hurt you.</div>
      </div>
      <div style="margin:4px 0;padding:6px;background:var(--hl);border-radius:4px;border-left:3px solid var(--yel)">
        <strong style="color:var(--yel);font-size:10px">2. Drawdown Limit</strong>
        <div style="font-size:10px">At 5% DD &rarr; halve lot. At 10% DD &rarr; halt. Sim max DD ~0.8%.</div>
      </div>
      <div style="margin:4px 0;padding:6px;background:var(--hl);border-radius:4px;border-left:3px solid var(--cyn)">
        <strong style="color:var(--cyn);font-size:10px">3. Daily Loss Limit</strong>
        <div style="font-size:10px">Lose $100 (1%) in a day &rarr; bot stops until next day. Prevents tilt.</div>
      </div>
    </div>
  </div>'''

# Find and replace the old bottom panels
start_idx = content.find(old_bottom_start)
end_idx = content.find('</div>\n  </div>\n</div>\n</body>')
if end_idx == -1:
    end_idx = content.rfind(safety_end_marker)

if start_idx != -1 and end_idx != -1:
    end_idx = end_idx + len(safety_end_marker) + 1
    before = content[:start_idx]
    after = content[end_idx:]
    content = before + new_bottom + after
    print("Bottom panels replaced with tabs")
else:
    print(f"Markers not found: start={start_idx}, end={end_idx}")

# Add switchTab function
old_script_end = '</script>\n</body>'
new_script = '''function switchTab(name,btn){
  document.querySelectorAll('.tab-panel').forEach(function(p){p.classList.remove('active')});
  document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active')});
  document.getElementById('tab-'+name).classList.add('active');
  btn.classList.add('active');
}
</script>
</body>'''

content = content.replace(old_script_end, new_script)
print("Tab switch JS added")

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("DONE")
