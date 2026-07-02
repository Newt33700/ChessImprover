/**
 * Utilitaires partagés par les tests E2E Playwright (fixtures/config).
 *
 * Le stub CDN (`fixtures/stub_chess.js`) est actif par défaut, partout
 * (local ET CI) : ces tests exercent le vrai backend (API, base in-memory,
 * validation serveur) et le vrai code applicatif (`app.js`, `api_client.js`)
 * bout-en-bout, mais remplacent délibérément `chess.js`/`chessboard.js` —
 * les tests pilotent les handlers de coup directement
 * (`window.app._onTacticsDrop(...)`) avec des cases fixes, ce qui exige que
 * `Chess.move()` renvoie toujours le SAN attendu plutôt que de valider une
 * vraie position (voir le stub). Tester le rendu réel de ces librairies
 * tierces n'est pas l'objectif ; `E2E_STUB_CDN=0` reste possible pour un
 * test manuel avec les vraies librairies, mais nécessite d'adapter les
 * scénarios (cases from/to réellement légales).
 */

const fs = require("fs");
const path = require("path");

const STUB_CHESS = fs.readFileSync(path.join(__dirname, "fixtures", "stub_chess.js"), "utf8");
const SHOULD_STUB_CDN = process.env.E2E_STUB_CDN !== "0";
const API_BASE = process.env.E2E_API_BASE || "http://localhost:8006";

async function installCdnStubsIfNeeded(page) {
  if (!SHOULD_STUB_CDN) return;
  await page.route("**://cdnjs.cloudflare.com/**", (route) => {
    if (route.request().url().endsWith(".css")) {
      return route.fulfill({ status: 200, contentType: "text/css", body: "" });
    }
    return route.fulfill({ status: 200, contentType: "application/javascript", body: STUB_CHESS });
  });
  await page.route("**://cdn.jsdelivr.net/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/javascript", body: "" })
  );
  await page.route("**://fonts.googleapis.com/**", (route) =>
    route.fulfill({ status: 200, contentType: "text/css", body: "" })
  );
  await page.route("**raw.githubusercontent.com/**", (route) =>
    route.fulfill({ status: 200, contentType: "text/plain", body: "" })
  );
}

/** Redirige `js/config.js` + le fallback `Auth` vers le backend E2E local. */
async function configureApiBase(page, apiBase = API_BASE) {
  await page.route("**/js/config.js", (route) =>
    route.fulfill({ status: 200, contentType: "application/javascript", body: `window.API_BASE = '${apiBase}';` })
  );
  await page.addInitScript({ content: `window.CI_API_URL = '${apiBase}';` });
}

/** Injecte une table FEN → solution pour piloter le stub `Chess.move()`. */
async function injectSolutions(page, solutions) {
  await page.addInitScript({ content: `window.__TACTICS_SOLUTIONS = ${JSON.stringify(solutions)};` });
}

/** Prépare la page (stubs CDN + API base) — à appeler avant `page.goto`. */
async function setupPage(page, { solutions } = {}) {
  await installCdnStubsIfNeeded(page);
  await configureApiBase(page);
  if (solutions) await injectSolutions(page, solutions);
}

/** Crée un compte frais et ferme la modale d'authentification. */
async function signupFreshUser(page, prefix) {
  const rand = Math.floor(Math.random() * 1e6);
  const email = `${prefix}_${rand}@e2e.test`;
  const username = `${prefix}_${rand}`;
  await page.waitForSelector("#btn-open-auth", { timeout: 15000 });
  await page.click("#btn-open-auth");
  await page.click('.auth-tab[data-form="signup-form"]');
  await page.fill("#signup-email", email);
  await page.fill("#signup-username", username);
  await page.fill("#signup-password", "pass123");
  await page.click("#signup-form button[type=submit]");
  await page.waitForSelector("#auth-modal[hidden]", { state: "attached", timeout: 10000 });
  return { email, username };
}

module.exports = {
  SHOULD_STUB_CDN,
  API_BASE,
  installCdnStubsIfNeeded,
  configureApiBase,
  injectSolutions,
  setupPage,
  signupFreshUser,
};
