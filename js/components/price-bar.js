GridBot.PriceBar = (d) => `
<div class="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs sm:text-sm mb-3" style="color:var(--fg2)">
  <div class="flex items-center gap-1.5"><span class="text-gray-500">Bid</span><span class="text-emerald-400 font-semibold">${GridBot.fmt(d.bid,2)}</span></div>
  <div class="flex items-center gap-1.5"><span class="text-gray-500">Ask</span><span class="text-rose-400 font-semibold">${GridBot.fmt(d.ask,2)}</span></div>
  <div class="flex items-center gap-1.5"><span class="text-gray-500">Sprd</span><span class="text-gray-300">${GridBot.fmt(d.spread,2)}</span></div>
  <div class="flex items-center gap-1.5"><span class="text-gray-500">Mid</span><span class="text-violet-400 font-semibold">${GridBot.fmt(d.mid,2)}</span></div>
  <span class="text-gray-600/40">|</span>
  <div class="flex items-center gap-2">
    <span class="text-gray-500">O</span><span class="text-gray-300 font-medium">${d.orders||0}</span>
    <span class="text-gray-500">T</span><span class="text-gray-300 font-medium">${d.trades||0}</span>
  </div>
  <span class="text-gray-600/40">|</span>
  <div class="flex items-center gap-1.5"><span class="text-gray-500">Bal</span><span class="text-emerald-400 font-semibold">$${GridBot.fmt(d.balance,0)}</span></div>
  <div class="flex items-center gap-1.5"><span class="text-gray-500">Eq</span><span class="text-sky-400 font-semibold">$${GridBot.fmt(d.equity,0)}</span></div>
</div>`;
