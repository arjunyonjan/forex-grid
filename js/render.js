// render.js — the entire "framework": 1 function
window.render = (fn, root) => { root.innerHTML = fn(); };
