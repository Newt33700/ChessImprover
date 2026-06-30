/**
 * Tests unitaires – StatsDashboard (US 5)
 */

const SD = require("../js/stats_dashboard.js");

// ── estimateEloLogistic ───────────────────────────────────────────

test("estimateEloLogistic(50%, 1000) = 1000 (égalité parfaite)", () => {
  expect(SD.estimateEloLogistic(50, 1000)).toBe(1000);
});

test("estimateEloLogistic(99.9%, 2800) est capé à 2800", () => {
  expect(SD.estimateEloLogistic(99.9, 2800)).toBe(2800);
});

test("estimateEloLogistic(100%, 1000) > 2000 (valeur logistique haute)", () => {
  // log10(0.999/0.001)*400 ≈ 1199, donc ≈ 2200 avec opp=1000
  expect(SD.estimateEloLogistic(100, 1000)).toBeGreaterThan(2000);
});

test("estimateEloLogistic(0%, 1000) = 400 (cap bas)", () => {
  expect(SD.estimateEloLogistic(0, 1000)).toBe(400);
});

test("estimateEloLogistic plus de précision → plus d'Elo", () => {
  const e1 = SD.estimateEloLogistic(60, 1000);
  const e2 = SD.estimateEloLogistic(80, 1000);
  const e3 = SD.estimateEloLogistic(95, 1000);
  expect(e2).toBeGreaterThan(e1);
  expect(e3).toBeGreaterThan(e2);
});

test("estimateEloLogistic(75%, 1500) > estimateEloLogistic(75%, 1000)", () => {
  expect(SD.estimateEloLogistic(75, 1500)).toBeGreaterThan(SD.estimateEloLogistic(75, 1000));
});

test("estimateEloLogistic retourne un entier", () => {
  const elo = SD.estimateEloLogistic(72, 1200);
  expect(elo).toBe(Math.round(elo));
});

// ── movingAverage ─────────────────────────────────────────────────

test("movingAverage window=1 retourne les valeurs inchangées", () => {
  expect(SD.movingAverage([10, 20, 30], 1)).toEqual([10, 20, 30]);
});

test("movingAverage window=3 lisse correctement", () => {
  const result = SD.movingAverage([10, 20, 30, 40, 50], 3);
  expect(result[0]).toBe(10);    // seul point
  expect(result[1]).toBe(15);    // (10+20)/2
  expect(result[2]).toBe(20);    // (10+20+30)/3
  expect(result[3]).toBe(30);    // (20+30+40)/3
  expect(result[4]).toBe(40);    // (30+40+50)/3
});

test("movingAverage ignore les null", () => {
  const result = SD.movingAverage([10, null, 30], 3);
  expect(result[1]).toBe(10);   // seul non-null dans window
  expect(result[2]).toBe(20);   // (10+30)/2
});

test("movingAverage retourne null si tous null dans window", () => {
  const result = SD.movingAverage([null, null, null], 3);
  result.forEach((v) => expect(v).toBeNull());
});

test("movingAverage window=5 (défaut) sur 3 points", () => {
  const result = SD.movingAverage([60, 70, 80]);
  expect(result[0]).toBe(60);
  expect(result[1]).toBe(65);
  expect(result[2]).toBe(70);
});

// ── filterByDays ──────────────────────────────────────────────────

test("filterByDays retourne uniquement les parties dans la fenêtre", () => {
  const now   = new Date();
  const old   = new Date(now - 100 * 86400000).toISOString();
  const recent= new Date(now -   5 * 86400000).toISOString();
  const games = [{ date: old, accuracy: 60 }, { date: recent, accuracy: 80 }];
  const result = SD.filterByDays(games, 7);
  expect(result).toHaveLength(1);
  expect(result[0].accuracy).toBe(80);
});

test("filterByDays trie par date croissante", () => {
  const now  = new Date();
  const d1   = new Date(now - 20 * 86400000).toISOString();
  const d2   = new Date(now -  5 * 86400000).toISOString();
  const games = [{ date: d2, accuracy: 80 }, { date: d1, accuracy: 60 }];
  const result = SD.filterByDays(games, 30);
  expect(result[0].accuracy).toBe(60);
  expect(result[1].accuracy).toBe(80);
});

test("filterByDays retourne vide si aucune partie dans la fenêtre", () => {
  const old = new Date(Date.now() - 100 * 86400000).toISOString();
  expect(SD.filterByDays([{ date: old }], 7)).toHaveLength(0);
});

// ── buildChartData ────────────────────────────────────────────────

test("buildChartData construit labels, eloData, accData", () => {
  const now = new Date();
  const games = [
    { date: new Date(now - 2 * 86400000).toISOString(), accuracy: 70, opponent_elo: 1000 },
    { date: new Date(now - 1 * 86400000).toISOString(), accuracy: 75, opponent_elo: 1000 },
  ];
  const data = SD.buildChartData(games, 7);
  expect(data.labels).toHaveLength(2);
  expect(data.eloData).toHaveLength(2);
  expect(data.accData).toHaveLength(2);
  data.eloData.forEach((v) => expect(v).not.toBeNull());
  data.accData.forEach((v) => expect(v).not.toBeNull());
});

test("buildChartData retourne null pour accuracy manquante", () => {
  const now = new Date();
  const games = [{ date: new Date(now - 1 * 86400000).toISOString(), accuracy: null }];
  const data  = SD.buildChartData(games, 7);
  expect(data.rawAcc[0]).toBeNull();
});

// ── wpFromCp ──────────────────────────────────────────────────────

test("wpFromCp(0) = 50", () => {
  expect(SD.wpFromCp(0)).toBeCloseTo(50, 5);
});

test("wpFromCp clamp : résultat identique pour cp=20000 et cp=10000", () => {
  expect(SD.wpFromCp(20000)).toBeCloseTo(SD.wpFromCp(10000), 5);
});

// ── render (renderCharts via render) ─────────────────────────────

test("render avec localStorage vide retourne données vides", async () => {
  const data = await SD.render(7, "elo-canvas", "acc-canvas");
  expect(data.labels).toHaveLength(0);
});

test("render avec parties en localStorage crée les graphiques", async () => {
  localStorage.setItem("ci_games", JSON.stringify([
    { date: new Date(Date.now() - 86400000).toISOString(), accuracy: 75, opponent_elo: 1000 },
  ]));
  const data = await SD.render(30, "elo-canvas", "acc-canvas");
  expect(data.labels).toHaveLength(1);
  expect(global.Chart).toHaveBeenCalled();
});
