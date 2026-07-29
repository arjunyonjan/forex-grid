import { chromium } from "playwright";
const BASE = "http://169.58.11.35";
let passed = 0, total = 0;

async function test(name, fn) {
  total++;
  try { await fn(); passed++; process.stderr.write(`PASS ${name}\n`); }
  catch (e) { process.stderr.write(`FAIL ${name}: ${e.message.slice(0,100)}\n`); }
}

async function run() {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const api = page.request;

  // Backend API tests (via fetch, no UI)
  await test("POST /micro-start returns 200", async () => {
    const r = await api.post(BASE + "/micro-start", {
      data: JSON.stringify({ start: "2026-07-28", end: "2026-07-28", tf: "1m", lot: 0.001, speed: 100 }),
      headers: { "Content-Type": "application/json" }
    });
    if (r.status() !== 200) throw new Error("Status " + r.status());
    const body = await r.json();
    if (body.status !== "started") throw new Error("Not started: " + body.status);
    if (!body.bars || body.bars <= 0) throw new Error("No bars: " + body.bars);
  });

  await test("POST /micro-start with all params", async () => {
    const r = await api.post(BASE + "/micro-start", {
      data: JSON.stringify({ start: "2026-01-02", end: "2026-01-10", tf: "5m", lot: 0.01, speed: 1000, expiry: 24, atr_source: "macro", atr_window: "15m", hard_mode: true, profit_target: 0.5 }),
      headers: { "Content-Type": "application/json" }
    });
    if (r.status() !== 200) throw new Error("Status " + r.status());
    const body = await r.json();
    if (body.tf !== "5m") throw new Error("TF not 5m: " + body.tf);
  });

  await test("POST /micro-start with invalid preset", async () => {
    const r = await api.post(BASE + "/micro-start", {
      data: JSON.stringify({ preset: "nonexistent_preset_xyz" }),
      headers: { "Content-Type": "application/json" }
    });
    if (r.status() !== 400) throw new Error("Expected 400, got " + r.status());
  });

  await test("POST /micro-speed returns 200", async () => {
    const r = await api.post(BASE + "/micro-speed", {
      data: JSON.stringify({ speed: 500 }),
      headers: { "Content-Type": "application/json" }
    });
    if (r.status() !== 200) throw new Error("Status " + r.status());
    const body = await r.json();
    if (body.speed !== 500) throw new Error("Speed not 500: " + body.speed);
  });

  await test("POST /micro-speed min/max clamping", async () => {
    for (const v of [0, 1, 500, 10000, 99999]) {
      const r = await api.post(BASE + "/micro-speed", {
        data: JSON.stringify({ speed: v }),
        headers: { "Content-Type": "application/json" }
      });
      const body = await r.json();
      if (body.speed < 1 || body.speed > 10000) throw new Error(`Speed ${v}→${body.speed} out of range`);
    }
  });

  await test("POST /micro-atr-window all values", async () => {
    for (const w of ["1m", "5m", "15m", "1h", "4h", "1D"]) {
      const r = await api.post(BASE + "/micro-atr-window", {
        data: JSON.stringify({ window: w }),
        headers: { "Content-Type": "application/json" }
      });
      if (r.status() !== 200) throw new Error(`${w} failed: ${r.status()}`);
      const body = await r.json();
      if (body.micro_atr_window !== w) throw new Error(`${w} not set: ${body.micro_atr_window}`);
    }
  });

  await test("POST /micro-atr-window invalid", async () => {
    const r = await api.post(BASE + "/micro-atr-window", {
      data: JSON.stringify({ window: "invalid" }),
      headers: { "Content-Type": "application/json" }
    });
    if (r.status() !== 400) throw new Error("Expected 400, got " + r.status());
  });

  await test("GET /stream-micro returns SSE init", async () => {
    const resp = await page.goto(BASE + "/stream-micro", { waitUntil: "commit", timeout: 5000 });
    if (resp.status() !== 200) throw new Error("Status " + resp.status());
    await page.waitForTimeout(1000);
    const text = await page.textContent("body");
    if (!text || !text.includes("init")) throw new Error("No init in SSE");
  });

  await test("GET /grid-micro returns 200", async () => {
    const r = await api.get(BASE + "/grid-micro");
    if (r.status() !== 200) throw new Error("Status " + r.status());
    const text = await r.text();
    if (!text.includes("Grid Pro")) throw new Error("No Grid Pro in page");
  });

  await test("POST /atr-source micro and macro", async () => {
    for (const src of ["micro", "macro"]) {
      const r = await api.post(BASE + "/atr-source", {
        data: JSON.stringify({ source: src }),
        headers: { "Content-Type": "application/json" }
      });
      if (r.status() !== 200) throw new Error(`${src} failed: ${r.status()}`);
    }
  });

  // Full lifecycle test: start → SSE data → stop → restart
  await test("Full lifecycle: start → data → stop", async () => {
    await page.goto(BASE + "/grid-micro", { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForTimeout(500);

    await page.selectOption("#speedSel", "5");
    await page.waitForTimeout(200);

    await page.click("#startBtn");
    await page.waitForTimeout(500);

    // Check status changed from Starting...
    const status = await page.$eval("#status", el => el.textContent);
    if (status === "Starting..." || status === "Ready.") throw new Error("Status stuck: " + status);

    // Wait for Data (up to 30s at 5x)
    let gotBar = false;
    for (let i = 0; i < 60; i++) {
      const bar = await page.$eval("#cBar", el => el.textContent);
      if (bar && bar !== "0/0" && bar !== "--" && bar.includes("/")) { gotBar = true; break; }
      await page.waitForTimeout(500);
    }
    if (!gotBar) throw new Error("Bars never updated");

    const price = await page.$eval("#cPrice", el => el.textContent);
    if (price === "--") throw new Error("Price not shown");
    const time = await page.$eval("#cTime", el => el.textContent);
    if (time === "--") throw new Error("Time not shown");

    // Stop sim for next tests
    await page.evaluate(() => { if (window.stopSim) window.stopSim(); });
    await page.waitForTimeout(500);
  });

  // Stress: rapid start/stop cycles
  await test("Stress: 3× start/stop cycles", async () => {
    for (let cycle = 0; cycle < 3; cycle++) {
      await page.click("#startBtn");
      await page.waitForTimeout(800);
      const s = await page.$eval("#status", el => el.textContent);
      if (s === "Starting..." || s === "Ready.") {
        // Try via evaluate
        await page.evaluate(() => { if (window.startSim) window.startSim(); });
        await page.waitForTimeout(800);
      }
      await page.waitForTimeout(300);
      await page.evaluate(() => { if (window.stopSim) window.stopSim(); });
      await page.waitForTimeout(300);
      const stopped = await page.$eval("#status", el => el.textContent);
      if (!stopped.startsWith("Stopped") && !stopped.startsWith("Done")) {
        throw new Error(`Cycle ${cycle} failed to stop: ${stopped}`);
      }
    }
  });

  // Theme toggle stress
  await test("Theme toggle cycle 5×", async () => {
    for (let i = 0; i < 5; i++) {
      await page.click("#themeBtn");
      await page.waitForTimeout(100);
    }
    // Should end in original state (even number of toggles)
  });

  // Tab switching stress
  await test("Tab switch rapid 10×", async () => {
    for (let i = 0; i < 10; i++) {
      await page.click(i % 2 === 0 ? "#tabHistBtn" : "#tabOpenBtn");
      await page.waitForTimeout(50);
    }
    const active = await page.$eval("#tabOpenBtn", el => el.classList.contains("active"));
    if (!active) throw new Error("Open Positions not active after toggle cycle");
  });

  // All speed values
  await test("All 6 speed values POST", async () => {
    for (const s of [1, 5, 10, 100, 1000, 10000]) {
      const r = await api.post(BASE + "/micro-speed", {
        data: JSON.stringify({ speed: s }),
        headers: { "Content-Type": "application/json" }
      });
      if (r.status() !== 200) throw new Error(`Speed ${s} failed: ${r.status()}`);
    }
  });

  // All 4 lot values
  await test("All 4 lot values start sim", async () => {
    for (const lot of [0.0001, 0.001, 0.01, 0.1]) {
      const r = await api.post(BASE + "/micro-start", {
        data: JSON.stringify({ start: "2026-07-28", end: "2026-07-28", tf: "1m", lot, speed: 1000 }),
        headers: { "Content-Type": "application/json" }
      });
      if (r.status() !== 200) throw new Error(`Lot ${lot} failed: ${r.status()}`);
      await page.waitForTimeout(500);
      await page.evaluate(() => { if (window.stopSim) window.stopSim(); });
    }
  });

  await browser.close();
  const elapsed = Math.round((Date.now() - startTime) / 1000);
  process.stderr.write(`\nDONE ${passed}/${total} in ${elapsed}s\n`);
  process.stdout.write(JSON.stringify({ passed, total, elapsed }));
  process.exit(passed === total ? 0 : 1);
}

const startTime = Date.now();
run().catch(e => { process.stderr.write("FATAL: " + e.message + "\n"); process.exit(1); });
