GridBot.PositionsTable = (positions) => {
  if (!positions || !positions.length) return "";
  const rows = positions.map(t => `
    <div class="pos-row">
      <span class="${GridBot.sideCl(t.side)} font-semibold w-10 text-xs">${t.side.toUpperCase()}</span>
      <span style="color:var(--fg)" class="font-mono w-16 text-xs">${GridBot.fmt(t.entry,2)}</span>
      <span class="text-xs w-20" style="color:var(--fg2)">TP <span class="font-mono">${GridBot.fmt(t.tp,2)}</span></span>
      <span class="${t.pips>=0?"text-emerald-400":"text-rose-400"} font-mono w-16 text-xs">${t.pips>=0?"+":""}${GridBot.fmt(t.pips,0)}<span class="text-[9px] opacity-60">pip</span></span>
      <span class="${GridBot.pnlCl(t.pnl)} font-bold font-mono text-xs ml-auto">${t.pnl>=0?"+":""}$${GridBot.fmt(t.pnl,2)}</span>
    </div>`).join("");
  return `
<div class="mb-3">
  <div class="text-[10px] tracking-wider font-medium mb-1.5" style="color:var(--fg2)">OPEN POSITIONS</div>
  <div class="space-y-1.5">${rows}</div>
</div>`;
};
