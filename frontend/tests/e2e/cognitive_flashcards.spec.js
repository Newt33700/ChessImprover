/**
 * E2E — Dashboard de Performance Cognitive (EPIC 19) & Cimetière des Erreurs (EPIC 20).
 */
const { test, expect } = require("@playwright/test");
const { setupPage, signupFreshUser, injectSolutions } = require("./helpers");

// 1.e4 d6 2.Nf3 e5 3.Nxe5, horloges annotées (base 600s) — même gaffe vérifiée
// que error_profile.spec.js, avec horodatage pour activer le calcul du temps
// de réflexion (EPIC 19) et des evals moteur pour activer cpl/fen/best_move_san
// (nécessaires à la génération de flashcards, EPIC 20).
const BLUNDER_PGN =
  '[Event "x"][Result "*"]\n\n' +
  "1. e4 {[%clk 0:10:00]} d6 {[%clk 0:10:00]} " +
  "2. Nf3 {[%clk 0:09:40]} e5 {[%clk 0:09:50]} " +
  "3. Nxe5 {[%clk 0:09:00]} *";

// Position avant Nxe5 (3e coup blanc) — meilleur coup fictif d4, distinct du
// coup joué (Nxe5), avec un écart >= 200cp (seuil de gaffe).
const BLUNDER_FEN = "rnbqkbnr/ppp2ppp/3p4/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3";
const BEST_SOLUTION_SAN = "d4";

async function submitAndWaitCompleted(page, pgn, evals) {
  return page.evaluate(
    async ({ pgnText, evalsObj }) => {
      const accepted = await window.ApiClient.analyzeGame(pgnText, { evals: evalsObj });
      const gameId = accepted.accepted[0].game_id;
      for (let i = 0; i < 30; i++) {
        const { game } = await window.ApiClient.getGame(gameId);
        if (game.status !== "processing") return game.status;
        await new Promise((r) => setTimeout(r, 200));
      }
      return "timeout";
    },
    { pgnText: pgn, evalsObj: evals }
  );
}

test.beforeEach(async ({ page }) => {
  await setupPage(page);
  await injectSolutions(page, { [BLUNDER_FEN]: BEST_SOLUTION_SAN });
});

test("une gaffe analysée alimente le Dashboard Cognitif et génère une flashcard", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_cognitive");

  const status = await submitAndWaitCompleted(page, BLUNDER_PGN, {
    [BLUNDER_FEN]: [["d2d4", 300], ["f3e5", -50]],
  });
  expect(status).toBe("completed");

  // Dashboard Cognitif (EPIC 19)
  await page.click("#btn-advstats");
  await expect(page.locator("#cog-dashboard-container .cog-insight").first()).toBeVisible();

  // Cimetière des Erreurs (EPIC 20, US 20.1) : une flashcard auto-générée.
  await expect(page.locator("#flashcards-summary .tac-rating")).toHaveText("1");
  await expect(page.locator('#flashcards-summary .tac-stat strong')).toHaveText("1");
});

test("Rappel Actif : coup correct révèle le succès et avance le calendrier SM-2", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_flashcards_ok");

  await submitAndWaitCompleted(page, BLUNDER_PGN, {
    [BLUNDER_FEN]: [["d2d4", 300], ["f3e5", -50]],
  });

  await page.click("#card-flashcards button");
  await page.waitForSelector("#flashcards-board", { state: "attached" });

  await page.evaluate(() => window.app._onFlashcardDrop("d2", "d4"));

  await expect(page.locator("#flashcards-board")).toHaveClass(/tactics-board--success/);
  await expect(page.locator("#flashcards-feedback")).toContainText("Bravo");
});

test("Rappel Actif : coup incorrect révèle la solution", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_flashcards_ko");

  await submitAndWaitCompleted(page, BLUNDER_PGN, {
    [BLUNDER_FEN]: [["d2d4", 300], ["f3e5", -50]],
  });

  await page.click("#card-flashcards button");
  await page.waitForSelector("#flashcards-board", { state: "attached" });

  await page.evaluate(() => { window.__FORCE_MOVE_SAN = "Nc3"; });
  await page.evaluate(() => window.app._onFlashcardDrop("b1", "c3"));

  await expect(page.locator("#flashcards-board")).toHaveClass(/tactics-board--error/);
  await expect(page.locator("#flashcards-feedback")).toContainText("Solution : d4");
});

test("sans gaffe, le Cimetière reste vide", async ({ page }) => {
  await page.goto("/index.html");
  await signupFreshUser(page, "e2e_flashcards_clean");

  const cleanPgn = '[Event "x"][Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0';
  await submitAndWaitCompleted(page, cleanPgn, {});

  await page.click("#btn-advstats");
  await expect(page.locator("#flashcards-summary .tac-rating")).toHaveText("0");
});
