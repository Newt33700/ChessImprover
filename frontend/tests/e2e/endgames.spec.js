/**
 * E2E — Entraîneur de Finales Essentielles (EPIC 10).
 */
const { test, expect } = require("@playwright/test");
const { setupPage, signupFreshUser } = require("./helpers");

const QUEEN_MATE_SOLUTIONS = {
  "8/8/8/8/8/8/8/k1KQ4 w - - 0 1": "Qa4#",
  "7k/8/5K2/8/8/8/8/6Q1 w - - 0 1": "Qg7#",
  "k7/8/K7/8/8/8/8/Q7 w - - 0 1": "Qh8#",
};

test.beforeEach(async ({ page }) => {
  await setupPage(page, { solutions: QUEEN_MATE_SOLUTIONS });
});

test("mat trouvé (Roi+Dame) : Elo monte, feedback positif", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_endgames");

  await page.click("#card-endgame-trainer button");
  await page.click('.tactics-theme-btn[data-theme="queen_mate"]');
  await page.waitForSelector("#endgame-board", { state: "attached" });

  await page.evaluate(() => window.app._onEndgameDrop("a1", "a4"));

  await expect(page.locator("#endgame-board")).toHaveClass(/tactics-board--success/);
  await expect(page.locator("#endgame-feedback")).toHaveText("Bravo, mat trouvé !");
  await expect(page.locator("#endgame-elo-badge")).toHaveText("Elo 1015");
});

test("coup incorrect : halo rouge, solution révélée", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_endgames");

  await page.click("#card-endgame-trainer button");
  await page.click('.tactics-theme-btn[data-theme="queen_mate"]');
  await page.waitForSelector("#endgame-board", { state: "attached" });

  await page.evaluate(() => { window.__FORCE_MOVE_SAN = "Zz9"; });
  await page.evaluate(() => window.app._onEndgameDrop("a1", "a2"));

  await expect(page.locator("#endgame-board")).toHaveClass(/tactics-board--error/);
  await expect(page.locator("#endgame-feedback")).toContainText("Coup incorrect. Solution");
});

test("le menu de catégories filtre bien (Roi+Tour)", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_endgames");

  await page.click("#card-endgame-trainer button");
  await page.click('.tactics-theme-btn[data-theme="rook_mate"]');
  await page.waitForSelector("#endgame-board", { state: "attached" });

  await expect(page.locator("#endgame-problem-body")).toContainText("rook mate");
});
