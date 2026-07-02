/**
 * E2E — Entraîneur d'Ouvertures (EPIC 9, répertoire + SRS).
 */
const { test, expect } = require("@playwright/test");
const { setupPage, signupFreshUser } = require("./helpers");

test.beforeEach(async ({ page }) => {
  await setupPage(page);
});

test("ajoute une ligne, la révise sans erreur, calendrier SM-2 avancé à J+1", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_openings");

  await page.click("#card-openings-trainer button");
  await page.waitForTimeout(300);

  await page.fill("#ot-name", "Ruy Lopez");
  await page.fill("#ot-moves", "e4 e5 Nf3 Nc6 Bb5");
  await page.click("#ot-add-form button[type=submit]");
  await expect(page.locator("#ot-add-feedback")).toHaveText("Ligne ajoutée au répertoire !");

  await page.waitForSelector("#ot-board", { state: "attached" });

  // Rejoue la ligne coup par coup (un seul `_onOtDrop` en vol à la fois),
  // en respectant le rythme asynchrone réel de l'enchaînement des coups.
  for (let tick = 0; tick < 20; tick++) {
    const done = await page.evaluate(() => {
      const app = window.app;
      if (!app._otLine || app._otFinished) return true;
      if (app._otMoveIndex >= app._otLine.moves.length) return true;
      if (app._otChess.turn() === app._otPlayerColor) {
        window.__FORCE_MOVE_SAN = app._otLine.moves[app._otMoveIndex];
        app._onOtDrop("a1", "a2");
      }
      return false;
    });
    if (done) break;
    await page.waitForTimeout(500);
  }

  await expect(page.locator("#ot-review-body")).toContainText("Aucune ligne à réviser aujourd'hui", {
    timeout: 3000,
  });

  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  await expect(page.locator("#ot-lines-list")).toContainText(tomorrow);
  await expect(page.locator("#ot-lines-list")).toContainText("Ruy Lopez");
});

test("une ligne avec une séquence illégale est rejetée", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_openings");

  await page.click("#card-openings-trainer button");
  await page.waitForTimeout(300);

  await page.fill("#ot-name", "Ligne invalide");
  await page.fill("#ot-moves", "e4 e5 Bxh7");
  await page.click("#ot-add-form button[type=submit]");

  await expect(page.locator("#ot-add-feedback")).toContainText("invalide");
});
