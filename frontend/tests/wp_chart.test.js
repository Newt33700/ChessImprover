/**
 * Tests unitaires – WPChart (Win Probability Chart)
 * Teste la formule de conversion centipions → probabilité, et la construction du dataset.
 */

const fs   = require("fs");
const path = require("path");

// Charger wp_chart.js en mode module CommonJS
function loadWPChart() {
  const code = fs.readFileSync(
    path.resolve(__dirname, "../js/wp_chart.js"),
    "utf8"
  );
  const adapted = code.replace("window.WPChart = WPChart;", "module.exports = WPChart;");
  const m = { exports: {} };
  // eslint-disable-next-line no-new-func
  new Function("module", "exports", adapted)(m, m.exports);
  return m.exports;
}

const WPChart = loadWPChart();

// ── cpToWP ────────────────────────────────────────────────────────

test("cpToWP(0) = 50% (égalité parfaite)", () => {
  expect(WPChart.cpToWP(0)).toBeCloseTo(50, 5);
});

test("cpToWP(+250) ≈ 71.5% (avantage blanc)", () => {
  expect(WPChart.cpToWP(250)).toBeCloseTo(71.5, 0);
});

test("cpToWP(-250) ≈ 28.5% (avantage noir)", () => {
  expect(WPChart.cpToWP(-250)).toBeCloseTo(28.5, 0);
});

test("cpToWP(+1000) est proche de 100%", () => {
  expect(WPChart.cpToWP(1000)).toBeGreaterThan(97);
  expect(WPChart.cpToWP(1000)).toBeLessThanOrEqual(100);
});

test("cpToWP(-1000) est proche de 0%", () => {
  expect(WPChart.cpToWP(-1000)).toBeLessThan(3);
  expect(WPChart.cpToWP(-1000)).toBeGreaterThanOrEqual(0);
});

test("cpToWP est symmétrique : cpToWP(x) + cpToWP(-x) = 100", () => {
  expect(WPChart.cpToWP(300) + WPChart.cpToWP(-300)).toBeCloseTo(100, 4);
  expect(WPChart.cpToWP(100) + WPChart.cpToWP(-100)).toBeCloseTo(100, 4);
});

// ── evalToWP ──────────────────────────────────────────────────────

test("evalToWP(10000) = 100 (mat en faveur des Blancs)", () => {
  expect(WPChart.evalToWP(10000)).toBe(100);
});

test("evalToWP(-10000) = 0 (mat en faveur des Noirs)", () => {
  expect(WPChart.evalToWP(-10000)).toBe(0);
});

test("evalToWP(0) = 50", () => {
  expect(WPChart.evalToWP(0)).toBe(50);
});

test("evalToWP retourne un nombre à 2 décimales max", () => {
  const wp = WPChart.evalToWP(123);
  expect(wp).toBe(parseFloat(wp.toFixed(2)));
});

test("evalToWP(250) ≈ 71.5%", () => {
  expect(WPChart.evalToWP(250)).toBeCloseTo(71.5, 0);
});

// ── buildDataset ──────────────────────────────────────────────────

test("buildDataset avec 0 coups retourne point initial uniquement", () => {
  const { labels, data } = WPChart.buildDataset([]);
  expect(labels).toHaveLength(1);
  expect(labels[0]).toBe("Début");
  expect(data[0]).toBe(50);
});

test("buildDataset crée un label par coup + 'Début'", () => {
  const moves = [
    { san: "e4", color: "w", evalCp: 20 },
    { san: "e5", color: "b", evalCp: -10 },
    { san: "Nf3", color: "w", evalCp: 30 },
  ];
  const { labels, data } = WPChart.buildDataset(moves);
  expect(labels).toHaveLength(4); // Début + 3 coups
  expect(labels[0]).toBe("Début");
  expect(labels[1]).toContain("e4");
  expect(labels[2]).toContain("e5");
});

test("buildDataset retourne null pour les coups sans evalCp", () => {
  const moves = [{ san: "d4", color: "w" }];
  const { data } = WPChart.buildDataset(moves);
  expect(data[1]).toBeNull();
});

test("buildDataset applique evalToWP sur evalCp", () => {
  const moves = [{ san: "e4", color: "w", evalCp: 0 }];
  const { data } = WPChart.buildDataset(moves);
  expect(data[1]).toBe(50);
});

test("buildDataset numérote les coups correctement", () => {
  const moves = [
    { san: "e4",  color: "w", evalCp: 10 },
    { san: "c5",  color: "b", evalCp: -10 },
    { san: "Nf3", color: "w", evalCp: 20 },
    { san: "d6",  color: "b", evalCp: -20 },
  ];
  const { labels } = WPChart.buildDataset(moves);
  // Coup 1 blanc → "1.B e4", coup 1 noir → "1.N c5"
  expect(labels[1]).toMatch(/1\.B/);
  expect(labels[2]).toMatch(/1\.N/);
  expect(labels[3]).toMatch(/2\.B/);
  expect(labels[4]).toMatch(/2\.N/);
});
