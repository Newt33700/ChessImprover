/**
 * Tests unitaires – SRS SM-2 algorithm (US 4)
 * Teste l'algorithme d'espacement SM-2 directement depuis app.js
 */

const fs   = require("fs");
const path = require("path");

// Extraire uniquement le module SRS depuis app.js
function loadSRS() {
  const code = fs.readFileSync(
    path.resolve(__dirname, "../js/app.js"),
    "utf8"
  );

  // Extraire le bloc SRS
  const srsStart = code.indexOf("const SRS = {");
  const srsEnd   = code.indexOf("\n};", srsStart) + 3;
  const srsCode  = code.slice(srsStart, srsEnd);

  // Fournir les dépendances minimales
  global.localStorage = {
    _store: {},
    getItem(k) { return this._store[k] ?? null; },
    setItem(k, v) { this._store[k] = v; },
  };

  const storeCode = `
    const Store = {
      get(k, fb=null){ try{const r=localStorage.getItem(k);return r!==null?JSON.parse(r):fb;}catch{return fb;} },
      set(k,v){ try{localStorage.setItem(k,JSON.stringify(v));}catch{} },
    };
    const STORAGE_KEYS = { SRS_CARDS: "ci_srs_cards" };
  `;

  const full = storeCode + srsCode + "\nmodule.exports = SRS;";
  const m = { exports: {} };
  // eslint-disable-next-line no-new-func
  new Function("module", "exports", full)(m, m.exports);
  return m.exports;
}

let SRS;

beforeEach(() => {
  global.localStorage = {
    _store: {},
    getItem(k) { return this._store[k] ?? null; },
    setItem(k, v) { this._store[k] = v; },
  };
  // Stub window pour éviter l'erreur ReferenceError dans saveCard
  global.window = { ChessDB: null };
  SRS = loadSRS();
});

// ── createCard ────────────────────────────────────────────────────

test("createCard crée une carte avec les valeurs SM-2 initiales", () => {
  const card = SRS.createCard("c1", "rnbqkbnr/... w", ["e2e4", "e7e5"]);
  expect(card.id).toBe("c1");
  expect(card.fen).toBe("rnbqkbnr/... w");
  expect(card.solution).toEqual(["e2e4", "e7e5"]);
  expect(card.ef).toBe(2.5);
  expect(card.interval).toBe(1);
  expect(card.reps).toBe(0);
  expect(card.due).toBeTruthy();
});

test("createCard due = aujourd'hui", () => {
  const today = new Date().toISOString().split("T")[0];
  const card  = SRS.createCard("c2", "pos", []);
  expect(card.due).toBe(today);
});

// ── review SM-2 ───────────────────────────────────────────────────

test("review quality=5 → reps=1, interval=1", () => {
  const card = SRS.createCard("c3", "pos", []);
  const next = SRS.review(card, 5);
  expect(next.reps).toBe(1);
  expect(next.interval).toBe(1);
});

test("review quality=5 deux fois → interval=6", () => {
  const c1 = SRS.review(SRS.createCard("c4", "pos", []), 5);
  const c2 = SRS.review(c1, 5);
  expect(c2.reps).toBe(2);
  expect(c2.interval).toBe(6);
});

test("review quality=5 trois fois → interval = round(c2.interval * c3.ef)", () => {
  const c1 = SRS.review(SRS.createCard("c5", "pos", []), 5);
  const c2 = SRS.review(c1, 5);
  const c3 = SRS.review(c2, 5);
  expect(c3.reps).toBe(3);
  // interval = round(c2.interval * newEf) où newEf est l'EF mis à jour = c3.ef
  expect(c3.interval).toBe(Math.round(c2.interval * c3.ef));
});

test("review quality<3 → reset reps=0, interval=1, due=aujourd'hui", () => {
  const c1 = SRS.review(SRS.createCard("c6", "pos", []), 5);
  const c2 = SRS.review(c1, 5);
  const reset = SRS.review(c2, 1);
  const today = new Date().toISOString().split("T")[0];
  expect(reset.reps).toBe(0);
  expect(reset.interval).toBe(1);
  expect(reset.due).toBe(today);
});

test("review quality=5 augmente EF", () => {
  const card = SRS.createCard("c7", "pos", []);
  const next = SRS.review(card, 5);
  expect(next.ef).toBeGreaterThan(card.ef);
});

test("review quality=3 laisse EF stable ou légèrement réduit", () => {
  const card = SRS.createCard("c8", "pos", []);
  const next = SRS.review(card, 3);
  expect(next.ef).toBeLessThanOrEqual(card.ef);
  expect(next.ef).toBeGreaterThanOrEqual(1.3);
});

test("review EF ne descend jamais sous EF_MIN = 1.3", () => {
  let card = SRS.createCard("c9", "pos", []);
  for (let i = 0; i < 10; i++) card = SRS.review(card, 3);
  expect(card.ef).toBeGreaterThanOrEqual(1.3);
});

test("review quality=5 due = dans interval jours (±1 tolérance)", () => {
  const c1 = SRS.review(SRS.createCard("c10", "pos", []), 5);
  const c2 = SRS.review(c1, 5);  // interval=6
  const today    = new Date();
  const dueDate  = new Date(c2.due);
  const diffDays = Math.round((dueDate - today) / 86400000);
  // ±1 jour de tolérance pour les comparaisons de minuit
  expect(Math.abs(diffDays - c2.interval)).toBeLessThanOrEqual(1);
});

// ── getDue ────────────────────────────────────────────────────────

test("getDue retourne les cartes dont due <= aujourd'hui", () => {
  const today    = new Date().toISOString().split("T")[0];
  const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
  const cards    = [
    { id: "a", due: "2020-01-01" },
    { id: "b", due: today },
    { id: "c", due: tomorrow },
  ];
  const due = SRS.getDue(cards);
  expect(due.map((c) => c.id)).toContain("a");
  expect(due.map((c) => c.id)).toContain("b");
  expect(due.map((c) => c.id)).not.toContain("c");
});

test("getDue trie par date croissante", () => {
  const cards = [
    { id: "late",  due: "2021-06-01" },
    { id: "early", due: "2020-01-01" },
  ];
  const due = SRS.getDue(cards);
  expect(due[0].id).toBe("early");
});

// ── saveCard ──────────────────────────────────────────────────────

test("saveCard persiste et récupère la carte", () => {
  const card = SRS.createCard("s1", "pos", ["e2e4"]);
  SRS.saveCard(card);
  const cards = SRS.load();
  expect(cards.find((c) => c.id === "s1")).toBeTruthy();
});

test("saveCard met à jour une carte existante", () => {
  SRS.saveCard(SRS.createCard("s2", "pos", []));
  const updated = { ...SRS.createCard("s2", "pos", []), interval: 10 };
  SRS.saveCard(updated);
  const found = SRS.load().find((c) => c.id === "s2");
  expect(found.interval).toBe(10);
});
