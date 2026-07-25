GridBot.HitLog = (hits) => {
  if (!hits || !hits.length) return "";
  const rows = hits.slice().reverse().map(x => `
    <div class="row px-2 py-1 flex gap-3" style="background:var(--bg)">
      <span style="color:var(--fg3)" class="font-mono w-14 shrink-0">${x.t}</span>
      <span class="${x.pnl?GridBot.pnlCl(x.pnl):"text-gray-500"} font-medium w-16 shrink-0">${x.side}</span>
      ${x.price?`<span class="font-mono w-14 shrink-0" style="color:var(--fg)">${GridBot.fmt(x.price,2)}</span>`:""}
      ${x.cost?`<span class="font-mono" style="color:var(--fg3)">-$${GridBot.fmt(x.cost,2)}</span>`:""}
      ${x.pnl?`<span class="${GridBot.pnlCl(x.pnl)} font-bold font-mono">${x.pnl>=0?"+":""}$${GridBot.fmt(x.pnl,2)}</span>`:""}
    </div>`).join("");
  return `
<div class="text-[10px] tracking-wider font-medium mb-1.5" style="color:var(--fg2)">RECENT HITS</div>
<div class="max-h-24 overflow-y-auto space-y-0.5 text-[11px]">${rows}</div>`;
};
