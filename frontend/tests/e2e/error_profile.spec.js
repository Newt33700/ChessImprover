/**
 * E2E — Analyse Comportementale (EPIC 11, US 9.1/9.2).
 * Bandeau "Entraînement Personnalisé" + endpoint /tactics/custom.
 */
const { test, expect } = require("@playwright/test");
const { setupPage, signupFreshUser } = require("./helpers");

// 1.e4 d6 2.Nf3 e5 3.Nxe5 — gaffe blanche vérifiée (cf. backend
// test_analyzer.py). Le tag [Event] varie pour éviter la déduplication par
// hash de PGN (US 7.2) : chaque soumission doit déclencher une analyse.
const blunderPgn = (i) => `[Event "blunder-${i}"][Result "*"]\n\n1. e4 d6 2. Nf3 e5 3. Nxe5 *`;

/** Soumet une partie via l'API réelle et attend la fin de l'analyse (worker async). */
async function submitAndWaitCompleted(page, pgn) {
  return page.evaluate(async (pgnText) => {
    const accepted = await window.ApiClient.analyzeGame(pgnText);
    const gameId = accepted.accepted[0].game_id;
    for (let i = 0; i < 30; i++) {
      const { game } = await window.ApiClient.getGame(gameId);
      if (game.status !== "processing") return game.status;
      await new Promise((r) => setTimeout(r, 200));
    }
    return "timeout";
  }, pgn);
}

test.beforeEach(async ({ page }) => {
  await setupPage(page);
});

test("4 gaffes répétées déclenchent le bandeau Entraînement Personnalisé", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_errprofile");

  for (let i = 0; i < 4; i++) {
    const status = await submitAndWaitCompleted(page, blunderPgn(i));
    expect(status).toBe("completed");
  }

  await page.click("#card-tactics button");
  await expect(page.locator("#tactics-custom-training")).toBeVisible();
  await expect(page.locator("#tactics-custom-hint")).toContainText("pièce non protégée");
});

test("le bouton Entraînement Personnalisé charge un problème hanging_piece", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_errprofile_custom");

  for (let i = 0; i < 4; i++) {
    await submitAndWaitCompleted(page, blunderPgn(i));
  }

  await page.click("#card-tactics button");
  await expect(page.locator("#tactics-custom-training")).toBeVisible();
  await page.click("#btn-custom-training");

  await page.waitForSelector("#tactics-board", { state: "attached" });
  await expect(page.locator(".tactics-category-badge")).toHaveText("hanging piece");
});

test("sans erreur récurrente, le bandeau reste masqué", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_errprofile_clean");

  await page.click("#card-tactics button");
  await expect(page.locator("#tactics-custom-training")).toBeHidden();
});
