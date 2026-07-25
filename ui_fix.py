with open('/root/forex-grid/index.html','r') as f:
    content = f.read()

# New CSS
new_css = '''*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#f1f5f9;--bg2:#fff;--bd:#e2e8f0;--fg:#334155;--fg2:#64748b;--hl:#f8fafc;--hl2:#cbd5e1;--grn:#16a34a;--red:#dc2626;--yel:#ca8a04;--cyn:#0891b2;--orng:#ea580c}
.dark{--bg:#0a0a0f;--bg2:#111120;--bd:#1e1e3a;--fg:#c0c0d0;--fg2:#606080;--hl:#181830;--hl2:#303050;--grn:#22c55e;--red:#ef4444;--yel:#eab308;--cyn:#06b6d4;--orng:#f97316}
body{background:var(--bg);color:var(--fg);font:13px/1.4 ui-monospace,sans-serif;min-height:100dvh}
.c{max-width:900px;margin:0 auto;padding:8px}
.flex{display:flex;gap:6px;align-items:center}
.g1{gap:3px}.g2{gap:6px}
.mb1{margin-bottom:4px}.mt1{margin-top:4px}
.card{background:var(--bg2);border:1px solid var(--bd);border-radius:8px;padding:8px}
canvas{width:100%;height:160px;border-radius:4px;background:var(--hl)}
.btn{padding:3px 8px;border-radius:5px;border:1px solid var(--bd);background:var(--bg2);color:var(--fg);cursor:pointer;font:inherit;font-size:11px;line-height:1.4}
.btn:hover{background:var(--hl);border-color:var(--hl2)}
.grn{color:var(--grn)}.red{color:var(--red)}.yel{color:var(--yel)}.cyn{color:var(--cyn)}
.bg-grn{background:var(--grn)}.bg-red{background:var(--red)}.bg-yel{background:var(--yel)}
.tag{display:inline-block;padding:2px 6px;border-radius:8px;font-size:10px;font-weight:600}

/* Status bar */
#statusBar{display:flex;align-items:center;gap:6px;padding:4px 10px;border-radius:6px;font-weight:600;font-size:12px;transition:.3s}
#statusBar.ok{border:1px solid var(--grn);color:var(--grn)}
#statusBar.warn{border:1px solid var(--yel);color:var(--yel)}
#statusBar.bad{border:1px solid var(--red);color:var(--red)}
#statusDot{width:6px;height:6px;border-radius:50%;display:inline-block}
#statusBar.ok #statusDot{background:var(--grn)}
#statusBar.warn #statusDot{background:var(--yel)}
#statusBar.bad #statusDot{background:var(--red)}

/* Big number rows */
.big-row{display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:4px;margin-bottom:4px}
.big-card{text-align:center;padding:6px 4px;display:flex;flex-direction:column;justify-content:center;min-height:56px}
.big-val{font-size:16px;font-weight:700;letter-spacing:-.3px}
.big-label{font-size:8px;color:var(--fg2);text-transform:uppercase}
.big-sub{font-size:9px;color:var(--fg2)}

/* DD bar */
.dd-bar-wrap{height:4px;background:var(--hl);border-radius:2px;overflow:hidden;margin:3px 0}
.dd-bar-fill{height:100%;border-radius:2px;transition:width .5s,background .3s}

/* Grid levels */
.grid-lvl{display:flex;align-items:center;gap:4px;padding:1px 4px;border-radius:3px;border:1px solid transparent;font-size:10px}
.grid-lvl:hover{background:var(--hl);border-color:var(--hl2)}
.grid-list{display:flex;flex-direction:column;gap:1px;max-height:240px;overflow-y:auto}

/* Positions */
.pos-row{display:flex;align-items:center;gap:8px;padding:3px 6px;border-radius:5px;border:1px solid var(--bd);font-size:11px}
.pos-row:hover{background:var(--hl)}
.pos-list{display:flex;flex-direction:column;gap:3px}

/* Hit log */
.hit-row{display:flex;gap:8px;padding:1px 0;font-size:10px;color:var(--fg2)}
.hit-row:hover{color:var(--fg)}
.hit-list{max-height:150px;overflow-y:auto}

/* Toggle */
details{font-size:11px}
details summary{cursor:pointer;color:var(--fg2);padding:2px 0}
details summary:hover{color:var(--fg)}
details[open] summary{margin-bottom:3px}

@media(max-width:700px){.big-row{grid-template-columns:1fr 1fr 1fr}.big-card{min-height:48px}.big-val{font-size:14px}}
@media(max-width:480px){.big-row{grid-template-columns:1fr 1fr}.big-card{min-height:42px}.big-val{font-size:13px}.c{padding:4px}}'''

old_css_start = '*{margin:0;padding:0;box-sizing:border-box}'
old_css_end = '</style>'

idx1 = content.find(old_css_start)
idx2 = content.find(old_css_end, idx1)
if idx1 != -1 and idx2 != -1:
    content = content[:idx1] + new_css + content[idx2:]
    print("CSS replaced")
else:
    print("CSS markers not found")

# Replace header
old_header = '''  <div class="flex g2 mb1">
    <span style="font-size:16px;font-weight:700">Gold Grid</span>
    <span style="width:8px;height:8px;border-radius:50%;background:var(--fg2);display:inline-block" id="topDot"></span>
    <span style="font-size:11px;color:var(--fg2);margin-left:auto" id="connStatus">connecting</span>
    <span style="font-size:10px;color:var(--fg2);margin-right:8px" id="simTime">Jun 23 00:00:00 NST</span>
    </select>
    <button class="btn" onclick="document.body.classList.toggle('dark')">&#9790;</button>
  </div>'''

new_header = '''  <div class="flex g1" style="margin-bottom:3px">
    <span style="font-size:14px;font-weight:700">Gold Grid</span>
    <span style="width:6px;height:6px;border-radius:50%;background:var(--fg2);display:inline-block" id="topDot"></span>
    <span style="font-size:10px;color:var(--fg2)" id="connStatus">connecting</span>
    <span style="margin-left:auto;font-size:10px;color:var(--fg2)" id="simTime">Jun 23 00:00:00 NST</span>
    <button class="btn" onclick="toggleFS()" title="Fullscreen">&#9974;</button>
    <button class="btn" onclick="document.body.classList.toggle('dark')">&#9790;</button>
  </div>'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("Header replaced")
else:
    print("Header not found")

# Replace status bar
old_status = '''  <!-- Status banner -->
  <div id="statusBar" class="mb1">
    <span id="statusDot"></span>
    <span id="statusMsg">Loading market data...</span>
  </div>'''

new_status = '''  <div id="statusBar" class="mb1">
    <span id="statusDot"></span>
    <span id="statusMsg" style="font-size:11px">Loading market data...</span>
  </div>'''

if old_status in content:
    content = content.replace(old_status, new_status)
    print("Status bar replaced")
else:
    print("Status bar not found")

# Add fullscreen JS
old_fs_marker = '    <button class="btn" onclick="document.body.classList.toggle(\'dark\')">&#9790;</button>\n  </div>'

# Add toggleFS function before first function call or at end of script
# Find the onMsg function and add before it
old_onmsg = '\nfunction onMsg(d){'
new_fs_js = '\nfunction toggleFS(){if(!document.fullscreenElement){document.documentElement.requestFullscreen()}else{document.exitFullscreen()}}\nfunction onMsg(d){'

if old_onmsg in content:
    content = content.replace(old_onmsg, new_fs_js)
    print("Fullscreen JS added")
else:
    print("onMsg not found")

with open('/root/forex-grid/index.html','w') as f:
    f.write(content)
print("ALL DONE")
