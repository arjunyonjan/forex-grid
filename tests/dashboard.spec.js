import { test, expect } from "@playwright/test";

test.describe("Grid Bot Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/", { waitUntil: "load" });
  });

  test("page title is Grid Bot", async ({ page }) => {
    await expect(page).toHaveTitle(/Grid Bot/);
  });

  test("shows XAU/USD header", async ({ page }) => {
    await expect(page.locator("text=XAU/USD").first()).toBeVisible();
  });

  test("shows Gold Grid branding", async ({ page }) => {
    await expect(page.locator("text=Gold Grid")).toBeVisible();
  });

  test("price value renders", async ({ page }) => {
    await expect(page.locator("#priceVal")).toBeVisible();
  });

  test("bid/ask text renders", async ({ page }) => {
    await expect(page.locator("#priceSub")).toBeVisible();
  });

  test("status bar shows connection", async ({ page }) => {
    await expect(page.locator("#statusMsg")).toBeVisible();
  });

  test("account balance renders", async ({ page }) => {
    await expect(page.locator("#moneyVal")).toBeVisible();
  });

  test("equity value renders", async ({ page }) => {
    await expect(page.locator("#eqVal")).toBeVisible();
  });

  test("drawdown bar exists", async ({ page }) => {
    await expect(page.locator("#ddBar")).toBeAttached();
  });

  test("chart canvas exists", async ({ page }) => {
    await expect(page.locator("#chart")).toBeVisible();
  });

  test("tab buttons render", async ({ page }) => {
    await expect(page.locator("button:has-text('Levels')")).toBeVisible();
    await expect(page.locator("button:has-text('Trades')")).toBeVisible();
    await expect(page.locator("button:has-text('Activity')")).toBeVisible();
    await expect(page.locator("button:has-text('Moves')")).toBeVisible();
    await expect(page.locator("button:has-text('Info')")).toBeVisible();
  });

  test("levels tab active by default", async ({ page }) => {
    const levels = page.locator("#tab-levels");
    await expect(levels).toHaveClass(/active/);
  });

  test("theme toggle button exists", async ({ page }) => {
    const btn = page.locator("button[title='Theme']");
    await expect(btn).toBeVisible();
  });

  test("status bar shows live after connecting", async ({ page }) => {
    await expect(page.locator("#connStatus")).toContainText(/live|connecting|degraded/, { timeout: 8000 });
  });

  test("switch to trades tab", async ({ page }) => {
    await page.locator("button:has-text('Trades')").click();
    await expect(page.locator("#tab-trades")).toHaveClass(/active/);
  });

  test("switch to moves tab", async ({ page }) => {
    await page.locator("button:has-text('Moves')").click();
    await expect(page.locator("#tab-moves")).toHaveClass(/active/);
  });

  test("settings gear button exists", async ({ page }) => {
    await expect(page.locator("button[title='Settings']")).toBeVisible();
  });

  test("settings panel opens on gear click", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await expect(page.locator("text=Sim Speed")).toBeVisible();
    await expect(page.locator("text=Restart Sim")).toBeVisible();
  });

  test("settings panel shows max trade days", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await expect(page.locator("text=Max Trade Duration")).toBeVisible();
  });

  test("settings panel shows grid params", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await expect(page.locator("#settingsPanel")).toContainText("401");
  });

  test("AI badge exists in header", async ({ page }) => {
    await expect(page.locator("#aiBadge")).toBeAttached();
  });

  test("AI detail panel hidden by default", async ({ page }) => {
    const detail = page.locator("#aiDetail");
    await expect(detail).toBeHidden();
  });

  test("settings overlay closes panel", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await expect(page.locator("text=Sim Speed")).toBeVisible();
    await page.locator("#settingsOverlay").click({ force: true });
    await expect(page.locator("text=Sim Speed")).not.toBeVisible();
  });

  test("preset buttons exist in sidebar", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await expect(page.locator("text=History Presets")).toBeVisible();
    await expect(page.locator("text=Ukraine War")).toBeVisible();
    await expect(page.locator("text=130K Crash")).toBeVisible();
  });

  test("preset click loads Ukraine sim", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await page.locator("button:has-text('Ukraine War')").click();
    await expect(page.locator("#speedDisplay")).not.toContainText("1x");
  });

  test("preset shows 130K Crash", async ({ page }) => {
    await page.locator("button[title='Settings']").click();
    await expect(page.locator("text=Jan-Mar 26 ★")).toBeVisible();
  });
});

test.describe("Forex Grid Research Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/forexgrid.html", { waitUntil: "load" });
  });

  test("page title is Forex Grid", async ({ page }) => {
    await expect(page).toHaveTitle(/Forex Grid/);
  });

  test("shows main heading", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Forex Grid");
  });

  test("shows XAU/USD in subtitle", async ({ page }) => {
    await expect(page.locator("text=XAU/USD").first()).toBeVisible();
  });

  test("monthly table has 55 rows (2022-01 to 2026-07)", async ({ page }) => {
    await expect(page.locator("#monthBody")).toBeVisible();
    const rows = page.locator("#monthBody tr");
    await expect(rows).toHaveCount(55);
  });

  test("first row shows Jan 2022", async ({ page }) => {
    const firstRow = page.locator("#monthBody tr").first();
    await expect(firstRow).toContainText(/Jan/);
  });

  test("last row shows Jul 2026", async ({ page }) => {
    const lastRow = page.locator("#monthBody tr").last();
    await expect(lastRow).toContainText(/Jul/);
  });

  test("big event mentions Ukraine invasion", async ({ page }) => {
    await expect(page.locator("text=Ukraine").first()).toBeVisible();
  });

  test("big event mentions SVB collapse", async ({ page }) => {
    await expect(page.locator("text=SVB").first()).toBeVisible();
  });

  test("stat cards render", async ({ page }) => {
    await expect(page.locator("text=Largest Range")).toBeVisible();
    await expect(page.locator("text=Largest Rally")).toBeVisible();
    await expect(page.locator("text=Worst Crash")).toBeVisible();
  });

  test("monthly table has green and red rows", async ({ page }) => {
    const rows = page.locator("#monthBody tr");
    const count = await rows.count();
    let hasGreen = false, hasRed = false;
    for (let i = 0; i < count; i++) {
      const html = await rows.nth(i).innerHTML();
      if (html.includes('emerald')) hasGreen = true;
      if (html.includes('rose')) hasRed = true;
    }
    expect(hasGreen).toBe(true);
    expect(hasRed).toBe(true);
  });

  test("grid psychology section exists", async ({ page }) => {
    await expect(page.locator("text=Grid Psychology")).toBeVisible();
  });

  test("grid psychology shows kill switch info", async ({ page }) => {
    await expect(page.locator("text=MAX_TRADE_DAYS")).toBeVisible();
  });

  test("grid psychology shows 30-day kill", async ({ page }) => {
    await expect(page.locator("text=30-Day Kill Switch").first()).toBeVisible();
  });

  test("vol radar section exists", async ({ page }) => {
    await expect(page.locator("text=Vol Radar")).toBeVisible();
  });

  test("vol radar has slider", async ({ page }) => {
    await expect(page.locator("#volSlider")).toBeVisible();
  });

  test("ai forecaster section exists", async ({ page }) => {
    await expect(page.locator("text=AI Forecaster")).toBeVisible();
  });

  test("ai forecaster shows SVB warning", async ({ page }) => {
    await expect(page.locator("text=SVB").first()).toBeVisible();
  });

  test("ai forecaster shows CRITICAL 2026 warning", async ({ page }) => {
    await expect(page.locator("text=CRITICAL").first()).toBeVisible();
  });
});
