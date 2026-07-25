// GridBot utilities
window.GridBot = window.GridBot || {};
GridBot.fmt = (n, d = 0) => Number(n).toFixed(d);
GridBot.pnlCl = v => v >= 0 ? "text-emerald-400" : "text-rose-400";
GridBot.sideCl = s => s === "buy" ? "text-emerald-400" : "text-rose-400";
