/**
 * E2E — Coach Tactique (EPIC 8, US 8.1-8.4).
 * Échiquier jouable indépendant, validation serveur, badge Elo + Série.
 */
const { test, expect } = require("@playwright/test");
const { setupPage, signupFreshUser } = require("./helpers");

// FEN → solution pour les positions `mate_in_1` du seed (db_client.py),
// nécessaire pour piloter le stub `Chess.move()` en local (E2E_STUB_CDN=1).
const MATE_IN_1_SOLUTIONS = {
  "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1": "Ra8#",
  "7k/6pp/8/8/8/8/8/R6K w - - 0 1": "Ra8#",
  "k7/8/1K6/8/8/8/8/7R w - - 0 1": "Rh8#",
  "6k1/4Rppp/8/8/8/8/6PP/6K1 w - - 0 1": "Re8#",
  "k1K5/8/8/8/8/8/8/6R1 w - - 0 1": "Ra1#",
};

test.beforeEach(async ({ page }) => {
  await setupPage(page, { solutions: MATE_IN_1_SOLUTIONS });
});

test("résout un problème mate_in_1 : Elo monte, série passe à 1", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_tactics");

  await page.click("#card-tactics button");
  await page.click('.tactics-theme-btn[data-theme="mate_in_1"]');
  await page.waitForSelector("#tactics-board", { state: "attached" });

  const streakBefore = await page.locator("#tactics-streak-badge").textContent();
  expect(streakBefore.trim()).toBe("🔥 0");

  await page.evaluate(() => window.app._onTacticsDrop("a1", "a8"));

  await expect(page.locator("#tactics-board")).toHaveClass(/tactics-board--success/);
  await expect(page.locator("#tactics-feedback")).toHaveText("Bravo, coup correct !");
  await expect(page.locator("#tactics-elo-badge")).toHaveText("Elo 1015");
  await expect(page.locator("#tactics-streak-badge")).toHaveText("🔥 1");
});

test("coup incorrect : halo rouge, flèche solution, Elo baisse", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_tactics");

  await page.click("#card-tactics button");
  await page.click('.tactics-theme-btn[data-theme="mate_in_1"]');
  await page.waitForSelector("#tactics-board", { state: "attached" });

  await page.evaluate(() => { window.__FORCE_MOVE_SAN = "Zz9"; });
  await page.evaluate(() => window.app._onTacticsDrop("a1", "a2"));

  await expect(page.locator("#tactics-board")).toHaveClass(/tactics-board--error/);
  await expect(page.locator("#tactics-elo-badge")).toHaveText("Elo 985");
  // EPIC 32 : plus de SAN en texte — la solution est fléchée sur l'échiquier.
  await expect(page.locator("#tactics-feedback")).toContainText("la flèche verte montre le coup attendu");
});

test("après résolution, un bouton « Problème suivant » permet d'enchaîner (EPIC 32)", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_tactics");

  await page.click("#card-tactics button");
  await page.click('.tactics-theme-btn[data-theme="mate_in_1"]');
  await page.waitForSelector("#tactics-board", { state: "attached" });
  // `_showTactics()` charge un problème "Aléatoire" avant même ce clic sur
  // le thème (cf. app.js:_showTactics) : attendre que le badge Elo reflète
  // bien LE PROBLÈME mate_in_1 (800, cf. seed) avant de jouer, pour ne pas
  // droper sur un échiquier encore en cours de remplacement par cette
  // requête concurrente plus ancienne.
  await expect(page.locator("#tactics-elo-badge")).toHaveText("Elo 800");

  await page.evaluate(() => window.app._onTacticsDrop("a1", "a8"));
  await expect(page.locator("#tactics-board")).toHaveClass(/tactics-board--success/);

  // Plus d'enchaînement automatique (EPIC 32) : un bouton explicite attend
  // que l'utilisateur soit prêt avant de charger le problème suivant.
  const nextBtn = page.locator(".next-problem-btn");
  await expect(nextBtn).toBeVisible();
  await nextBtn.click();

  await expect(async () => {
    const cls = await page.locator("#tactics-board").getAttribute("class");
    expect(cls).toBe("tactics-board");
  }).toPass({ timeout: 3000 });
});
