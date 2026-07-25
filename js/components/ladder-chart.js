GridBot.LadderChart = (grid, mid, gs) => {
  if (!grid || !grid.length) return "";
  const levels = grid.map(lvl => {
    const dist = lvl - mid;
    let sym = "&#x25BC;", cl = "text-emerald-400/70", label = "buy";
    if (lvl === Math.round(mid * 100) / 100) { sym = "&#x25CF;"; cl = "text-amber-400"; label = "mid"; }
    else if (dist > 0) { sym = "&#x25B2;"; cl = "text-rose-400/70"; label = "sell"; }
    const dim = Math.abs(dist) < gs * 1.2 / 100 && label !== "mid";
    const pipDist = label !== "mid"
      ? `<span class="font-mono text-[10px]" style="color:var(--fg3)">${dist>0?"+":""}${GridBot.fmt(dist*100,0)}<span class="opacity-50">pip</span></span>`
      : "";
    return `
    <div class="grid-level" style="opacity:${dim?0.4:1};border-color:${label==="mid"?"var(--hl2)":"transparent"};background:${label==="mid"?"var(--hl)":"transparent"}">
      <span class="${cl}" style="font-size:10px">${sym}</span>
      <span class="font-mono w-16 text-right" style="color:var(--fg)">${GridBot.fmt(lvl,2)}</span>
      <span class="text-[10px] flex-1" style="color:var(--fg2)">${label}</span>
      ${pipDist}
    </div>`;
  }).join("");
  return `<div class="space-y-px mb-3">${levels}</div>`;
};
