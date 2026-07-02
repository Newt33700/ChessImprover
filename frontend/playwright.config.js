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
