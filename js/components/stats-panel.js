GridBot.StatsPanel = (d) => `
<div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-3">
  <div class="card"><div class="text-[10px] tracking-wider font-medium" style="color:var(--fg2)">BALANCE</div>
    <div class="text-emerald-400 font-bold text-lg sm:text-xl mt-0.5">$${GridBot.fmt(d.balance,0)}</div></div>
  <div class="card"><div class="text-[10px] tracking-wider font-medium" style="color:var(--fg2)">EQUITY</div>
    <div class="text-sky-400 font-bold text-lg sm:text-xl mt-0.5">$${GridBot.fmt(d.equity,0)}</div></div>
  <div class="card"><div class="text-[10px] tracking-wider font-medium" style="color:var(--fg2)">DRAWDOWN</div>
    <div class="${d.drawdown>5?"text-rose-400":"text-amber-400"} font-bold text-lg sm:text-xl mt-0.5">${GridBot.fmt(d.drawdown,1)}%</div></div>
  <div class="card"><div class="text-[10px] tracking-wider font-medium" style="color:var(--fg2)">P&amp;L TODAY</div>
    <div class="${GridBot.pnlCl(d.pnl_today)} font-bold text-lg sm:text-xl mt-0.5">${d.pnl_today>=0?"+":""}$${GridBot.fmt(d.pnl_today,0)}</div></div>
</div>`;
