// Configuration Playwright pour les tests E2E (frontend/tests/e2e/).
// Démarre automatiquement le backend (uvicorn, port 8006) et le frontend
// statique (http.server, port 8080) — `npx playwright test` suffit.

const fs = require("fs");

const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium";
const launchOptions = fs.existsSync(SANDBOX_CHROMIUM) ? { executablePath: SANDBOX_CHROMIUM } : {};

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: "./tests/e2e",
  testMatch: "**/*.spec.js",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:8080",
    launchOptions,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8006",
      cwd: "../backend",
      port: 8006,
      reuseExistingServer: true,
      timeout: 30_000,
      // Le backend refuse de démarrer avec le JWT_SECRET par défaut hors debug
      // (fail-fast, audit 07/2026) — on fournit un secret de test explicite.
      // DISABLE_LICHESS_PUZZLES : le Coach Tactique (EPIC 34) interroge l'API
      // Puzzle Lichess en priorité ; en CI (réseau sortant autorisé), un vrai
      // puzzle Lichess écraserait le seed local déterministe que ces tests
      // stubbent (FEN fixes), les rendant flaky. Forcer le seed local ici.
      env: {
        ...process.env,
        JWT_SECRET: process.env.JWT_SECRET || "e2e-test-secret",
        DISABLE_LICHESS_PUZZLES: "1",
      },
    },
    {
      command: "python3 -m http.server 8080",
      cwd: ".",
      port: 8080,
      reuseExistingServer: true,
      timeout: 15_000,
    },
  ],
};
