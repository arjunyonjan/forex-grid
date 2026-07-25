window.GridBot.drawChart = (canvas, history, isDark) => {
  if (!canvas || history.length < 2) return;
  const r = canvas.parentElement.getBoundingClientRect();
  canvas.width = r.width - 4;
  canvas.height = 240;
  const ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
  const pad = { t: 28, b: 18, l: 62, r: 18 };
  const pw = w - pad.l - pad.r, ph = h - pad.t - pad.b;
  ctx.clearRect(0, 0, w, h);
  let lo = Infinity, hi = -Infinity;
  for (const v of history) { if (v < lo) lo = v; if (v > hi) hi = v; }
  const rng = hi - lo || 1;
  lo -= rng * 0.12; hi += rng * 0.12;
  const scale = ph / (hi - lo);
  ctx.save();
  ctx.beginPath(); ctx.rect(pad.l, 0, pw, h); ctx.clip();
  ctx.strokeStyle = isDark ? "#1a1a2e" : "#e2e8f0"; ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) {
    const y = pad.t + ph * i / 4;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    const price = hi - (hi - lo) * i / 4;
    ctx.fillStyle = isDark ? "#504e70" : "#94a3b8";
    ctx.font = "10px ui-monospace,monospace"; ctx.textAlign = "right";
    ctx.fillText(GridBot.fmt(price, 2), pad.l - 6, y + 4);
  }
  ctx.beginPath();
  ctx.strokeStyle = isDark ? "#a78bfa" : "#7c3aed"; ctx.lineWidth = 2.5; ctx.lineJoin = "round";
  for (let i = 0; i < history.length; i++) {
    const x = pad.l + (i / (history.length - 1)) * pw;
    const y = pad.t + (hi - history[i]) * scale;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.lineTo(pad.l + pw, pad.t + ph); ctx.lineTo(pad.l, pad.t + ph); ctx.closePath();
  const g = ctx.createLinearGradient(0, pad.t, 0, pad.t + ph);
  g.addColorStop(0, isDark ? "rgba(167,139,250,0.15)" : "rgba(124,58,237,0.10)");
  g.addColorStop(1, "rgba(167,139,250,0)"); ctx.fillStyle = g; ctx.fill();
  ctx.restore();
  const lx = pad.l + pw, ly = pad.t + (hi - history[history.length - 1]) * scale + 2;
  ctx.fillStyle = isDark ? "#c4b5fd" : "#7c3aed";
  ctx.font = "bold 10px ui-monospace,monospace"; ctx.textAlign = "left";
  ctx.fillText(GridBot.fmt(history[history.length - 1], 2), lx + 6, Math.max(16, Math.min(h - 6, ly)));
  ctx.beginPath();
  ctx.arc(lx, Math.max(pad.t, Math.min(pad.t + ph, ly - 2)), 4, 0, Math.PI * 2);
  ctx.fillStyle = isDark ? "#c4b5fd" : "#7c3aed"; ctx.fill();
};
