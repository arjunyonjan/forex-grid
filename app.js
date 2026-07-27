// App — SSE → innerHTML, data-onclick delegation, canvas draw
(function() {
  const root = document.getElementById("app");
  let data = { bid:0, ask:0, mid:0, spread:0, grid:[], hits:[], balance:10000, equity:10000,
    upnl:0, orders:0, trades:0, drawdown:0, pnl_today:0, daily_trades:0, hit_log:[], positions:[] };
  let isDark = localStorage.getItem("gridTheme") !== "light";
  let showHowModal = false;
  let simRunning = false;
  let simResults = null;
  let trendFilterOn = true;
  const history = [];

  function App() {
    const d = data;
    const gs = Math.round((d.grid[1] - d.grid[0]) * 100) || 20;
    return `
<div class="space-y-0.5">
  <div class="flex items-start justify-between mb-2">
    <div class="flex items-center gap-2">
      <span class="w-2 h-2 rounded-full bg-emerald-400/80 animate-pulse"></span>
      <span class="text-xs font-medium tracking-wide" style="color:var(--fg2)">XAU/USD \u00b7 LIVE</span>
      <span class="text-[10px] px-2 py-0.5 rounded-full font-mono" style="background:var(--hl);color:var(--fg2);border:1px solid var(--bd)">0.01 lot \u00b7 $0.10/pip</span>
    </div>
    <div class="flex items-center gap-2">
      <button class="btn text-[10px] px-2 py-1.5 leading-none" data-onclick="showHowItWorks" title="How it works">?</button>
      <button class="btn text-[10px] px-2 py-1.5 font-bold" data-onclick="runSim" ${simRunning?"disabled":""} title="Run 24H sim">${simRunning?"\u23f3":"24H"}</button>
      <button class="btn text-[10px] px-2 py-1.5 ${trendFilterOn?'':'opacity-50'}" data-onclick="toggleTrendFilter" title="Trend filter: ${trendFilterOn?'ON':'OFF'}">
        ${trendFilterOn?'\u{1F3AF} TREND':'<span style="opacity:0.4">\u{1F3AF} TREND</span>'}
      </button>
      <button class="btn text-xs px-3 py-1.5" data-onclick="toggleTheme">${isDark ? "\u2600\ufe0f" : "\U0001f319"}</button>
    </div>
  </div>
  ${GridBot.PriceBar(d)}
  ${GridBot.StatsPanel(d)}
  <div class="card mb-3 overflow-hidden p-0"><canvas id="price-canvas" class="w-full"></canvas></div>
  ${GridBot.PositionsTable(d.positions)}
  <div class="flex items-center gap-3 mb-1.5 text-[10px]" style="color:var(--fg2)">
    <span class="flex items-center gap-2"><span class="text-emerald-400/70">\u25bc</span><span class="font-medium">Buy</span></span>
    <span class="flex items-center gap-2"><span class="text-rose-400/70">\u25b2</span><span class="font-medium">Sell</span></span>
    <span class="flex items-center gap-2"><span class="text-amber-400 font-bold">\u25cf</span><span class="font-medium">Mid</span></span>
    <span class="ml-auto font-mono">${gs}<span class="opacity-50">pip</span> \u00b7 ${d.grid.length}<span class="opacity-50">lvls</span></span>
  </div>
  ${GridBot.LadderChart(d.grid, d.mid, gs)}
  ${GridBot.HitLog(d.hit_log)}
  ${simResults ? `
<div class="card mb-3 p-3" style="border-color:var(--hl2)">
  <div class="flex items-center justify-between mb-2">
    <div class="text-[10px] tracking-wider font-bold" style="color:var(--fg2)">${simResults.label||"24H SIMULATION"} RESULTS</div>
    <button class="text-[10px] px-2 py-0.5 rounded" style="color:var(--fg3);background:var(--hl)" data-onclick="closeSim">\u2715</button>
  </div>
  <div class="grid grid-cols-3 sm:grid-cols-6 gap-2">
    <div><div class="text-[9px]" style="color:var(--fg3)">P&L</div><div class="text-sm font-bold ${simResults.return_pct>=0?"text-emerald-400":"text-rose-400"}">${simResults.return_pct>=0?"+":""}${GridBot.fmt(simResults.return_pct,2)}%</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">BALANCE</div><div class="text-sm font-bold" style="color:var(--fg)">$${GridBot.fmt(simResults.total_pnl+1000000,0)}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">PF</div><div class="text-sm font-bold ${simResults.pf>=1?"text-emerald-400":"text-rose-400"}">${simResults.pf==999?"\u221e":simResults.pf}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">W/L</div><div class="text-sm font-bold" style="color:var(--fg)">${simResults.wins}/${simResults.losses}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">DD</div><div class="text-sm font-bold ${simResults.max_dd>5?"text-rose-400":"text-amber-400"}">${GridBot.fmt(simResults.max_dd,1)}%</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">TRADES</div><div class="text-sm font-bold" style="color:var(--fg)">${simResults.total_trades}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">TP</div><div class="text-sm font-bold" style="color:var(--fg)">${simResults.tp_hits||0}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">HEDGE</div><div class="text-sm font-bold text-amber-400">${simResults.hedge_closes||0}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">CLEANUP</div><div class="text-sm font-bold text-sky-400">${simResults.cleanups||0}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">+P&L</div><div class="text-sm font-bold text-emerald-400">$${GridBot.fmt(simResults.win_pnl,0)}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">-P&L</div><div class="text-sm font-bold text-rose-400">$${GridBot.fmt(simResults.loss_pnl,0)}</div></div>
    <div><div class="text-[9px]" style="color:var(--fg3)">NET</div><div class="text-sm font-bold ${(simResults.win_pnl+simResults.loss_pnl)>=0?"text-emerald-400":"text-rose-400"}">$${GridBot.fmt(simResults.win_pnl+simResults.loss_pnl,0)}</div></div>
  </div>
</div>` : ""}
  <div class="text-[10px] text-center mt-6" style="color:var(--fg3)">Grid Bot \u00b7 XAU/USD \u00b7 0.01 lot \u00b7 20 pip spacing</div>
  ${showHowModal ? `
<div id="how-modal-overlay" data-onclick="closeHowItWorks" style="position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:99;display:flex;align-items:center;justify-content:center;padding:1rem;">
  <div onclick="event.stopPropagation()" style="background:var(--bg2);border:1px solid var(--bd);border-radius:12px;max-width:480px;width:100%;padding:1.5rem;position:relative;max-height:80vh;overflow-y:auto;">
    <button data-onclick="closeHowItWorks" style="position:absolute;top:10px;right:12px;background:none;border:none;color:var(--fg3);font-size:18px;cursor:pointer;line-height:1;">\u2715</button>
    <div class="text-sm leading-relaxed space-y-3" style="color:var(--fg2)">
      <div class="font-bold text-base" style="color:var(--fg)">How the Grid Bot Works</div>
      <p>Think of the grid like a ladder. The bot places buy orders on lower rungs and sell orders on higher rungs. When price swings past a rung, the bot takes profit (or loss) and flips the order — so buys become sells and vice versa.</p>
      <p>The chart shows the recent price path. The ladder shows where orders sit. <span class="text-emerald-400/70">\u25bc Buy</span> rungs profit when price rises from them. <span class="text-rose-400/70">\u25b2 Sell</span> rungs profit when price drops from them. The <span class="text-amber-400">\u25cf midpoint</span> is where the ladder resets.</p>
      <p>This works well in ranging markets (price bouncing in a channel). In strong trends, the grid can get overwhelmed — hence the drawdown tracker.</p>
      <div class="mt-3 pt-3" style="border-top:1px solid var(--bd)">
        <div class="font-bold text-xs mb-1" style="color:var(--fg2)">API / Reports</div>
        <div class="text-[10px] space-y-1 font-mono" style="color:var(--fg3)">
          <div><span class="text-emerald-400">GET</span> <code style="color:var(--fg)">/report/&lt;preset&gt;</code> \u2014 run headless, get JSON result</div>
          <div><span style="color:var(--fg2)">Presets:</span> ukraine, crash2022, svb, oct2023, rally2024, election2024, tariff2025, crash2026, full2022, all, july2026, last7d, 5m</div>
          <div><span class="text-emerald-400">POST</span> <code style="color:var(--fg)">/preset</code> \u2014 <code>{"name":"ukraine"}</code> \u2014 run live in dashboard</div>
          <div><span class="text-amber-400">POST</span> <code style="color:var(--fg)">/toggle_trend_filter</code> \u2014 <code>{"enabled":true,"disable_on_trend":false}</code></div>
          <div><span class="text-amber-400">POST</span> <code style="color:var(--fg)">/speed</code> \u2014 <code>{"speed":100}</code></div>
          <div>Results auto-populate dashboard card when preset finishes.</div>
        </div>
      </div>
    </div>
  </div>
</div>` : ""}
</div>`;
  }

  function render() {
    root.innerHTML = App();
    GridBot.drawChart(document.getElementById("price-canvas"), history, isDark);
  }

  // SSE
  const es = new EventSource("/stream");
  es.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === "done") {
      simResults = msg;
      simRunning = false;
      render();
      return;
    }
    data = msg;
    if (data.trend_filter !== undefined) trendFilterOn = data.trend_filter;
    history.push(data.mid);
    if (history.length > 300) history.shift();
    render();
  };

  // Event delegation
  document.addEventListener("click", e => {
    const el = e.target.closest("[data-onclick]");
    if (!el) return;
    if (el.dataset.onclick === "toggleTheme") {
      isDark = !isDark;
      localStorage.setItem("gridTheme", isDark ? "dark" : "light");
      document.body.classList.toggle("light", !isDark);
      render();
    } else if (el.dataset.onclick === "showHowItWorks") {
      showHowModal = true;
      render();
    } else if (el.dataset.onclick === "closeHowItWorks") {
      showHowModal = false;
      render();
    } else if (el.dataset.onclick === "runSim") {
      simRunning = true;
      simResults = null;
      render();
      fetch("/simulate?hours=24").then(r=>r.json()).then(d=>{
        simResults = d;
        simRunning = false;
        render();
      }).catch(()=>{
        simRunning = false;
        render();
      });
    } else if (el.dataset.onclick === "closeSim") {
      simResults = null;
      render();
    } else if (el.dataset.onclick === "toggleTrendFilter") {
      trendFilterOn = !trendFilterOn;
      fetch("/toggle_trend_filter", {method:"POST",body:JSON.stringify({enabled:trendFilterOn}),headers:{"Content-Type":"application/json"}}).catch(()=>{});
      render();
    }
  });

  // Initial render
  document.body.classList.toggle("light", !isDark);
  render();
})();
