/**
 * E2E — Mode Tactical Sprint (EPIC 12, US 11.1/11.2).
 *
 * Elo tactique par défaut (1000) correspond exactement à un seul problème du
 * seed (`hanging_piece`, difficulty_elo 1000, FEN ci-dessous) — la sélection
 * adaptative renvoie donc toujours ce même problème tant que l'Elo n'est pas
 * modifié (le mode Sprint ne touche jamais `tactical_elo`), ce qui rend le
 * scénario déterministe sans avoir à couvrir tout le seed.
 */
const { test, expect } = require("@playwright/test");
const { setupPage, signupFreshUser } = require("./helpers");

const SPRINT_SOLUTIONS = {
  "4k3/8/8/8/4n3/8/4Q3/4K3 w - - 0 1": "Qxe4+",
};

test.beforeEach(async ({ page }) => {
  await setupPage(page, { solutions: SPRINT_SOLUTIONS });
});

test("démarre un sprint et résout un problème avec succès", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_sprint");

  await page.click("#card-sprint button");
  await page.click("#btn-sprint-start");
  await page.waitForSelector("#sprint-board", { state: "attached" });
  await expect(page.locator("#sprint-timer-badge")).toHaveText("60s");

  await page.evaluate(() => window.app._onSprintDrop("e2", "e4"));

  await expect(page.locator("#sprint-solved-count")).toHaveText("1 résolu(s)");
});

test("le sprint se termine et affiche le score final", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_sprint_end");

  await page.click("#card-sprint button");
  await page.click("#btn-sprint-start");
  await page.waitForSelector("#sprint-board", { state: "attached" });

  await page.evaluate(() => window.app._onSprintDrop("e2", "e4"));
  await expect(page.locator("#sprint-solved-count")).toHaveText("1 résolu(s)");

  // Simule l'expiration du chrono (60s réelles non nécessaires en test).
  await page.evaluate(() => window.app._endSprint());

  await expect(page.locator("#sprint-body")).toContainText("Sprint terminé");
  await expect(page.locator("#sprint-body")).toContainText("1 problème(s) résolu(s), score 10");
  await expect(page.locator("#btn-sprint-start")).toHaveText("Rejouer (60s)");
});

test("le bandeau Ghost affiche le meilleur score une fois activé", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_sprint_ghost");

  // Sprint 1 : terminé avec un score, alimente le mode Ghost (public, US 11.2).
  await page.click("#card-sprint button");
  await page.click("#btn-sprint-start");
  await page.waitForSelector("#sprint-board", { state: "attached" });
  await page.evaluate(() => window.app._onSprintDrop("e2", "e4"));
  await expect(page.locator("#sprint-solved-count")).toHaveText("1 résolu(s)");
  await page.evaluate(() => window.app._endSprint());
  await expect(page.locator("#sprint-body")).toContainText("Sprint terminé");

  // Sprint 2 : le Ghost du sprint 1 doit être disponible dès le démarrage.
  await page.click("#btn-sprint-start");
  await page.waitForSelector("#sprint-board", { state: "attached" });
  await page.waitForFunction(() => window.app._ghostData?.available === true);
  await page.check("#sprint-ghost-toggle");

  await expect(page.locator("#sprint-ghost-overlay")).toBeVisible();
  await expect(page.locator("#sprint-ghost-overlay")).toContainText("Meilleur score : 10");
});
