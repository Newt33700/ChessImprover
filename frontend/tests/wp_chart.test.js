/**
 * Tests unitaires – WPChart (Win Probability Chart) – US 1
 */

const WPChart = require("../js/wp_chart.js");

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

test("cpToWP est symétrique : cpToWP(x) + cpToWP(-x) = 100", () => {
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
  const { labels } = WPChart.buildDataset(moves);
  expect(labels).toHaveLength(4);
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
  expect(labels[1]).toMatch(/1\.B/);
  expect(labels[2]).toMatch(/1\.N/);
  expect(labels[3]).toMatch(/2\.B/);
  expect(labels[4]).toMatch(/2\.N/);
});

// ── render / updateMove / highlightMove / destroy ─────────────────

test("render crée un graphique Chart.js", () => {
  const moves = [{ san: "e4", color: "w", evalCp: 20 }];
  WPChart.render("test-canvas", moves);
  expect(global.Chart).toHaveBeenCalledTimes(1);
});

test("render ne plante pas si canvas absent", () => {
  global.document.getElementById.mockReturnValueOnce(null);
  expect(() => WPChart.render("missing-canvas", [])).not.toThrow();
  expect(global.Chart).not.toHaveBeenCalled();
});

test("render avec onPointClick ne plante pas sur le click", () => {
  const onPoint = jest.fn();
  WPChart.render("test-canvas", [{ san: "e4", color: "w", evalCp: 10 }], onPoint);
  expect(global.Chart).toHaveBeenCalledTimes(1);
});

test("updateMove met à jour les données après render", () => {
  WPChart.render("test-canvas", [{ san: "e4", color: "w", evalCp: 0 }]);
  expect(() => WPChart.updateMove(0, 100)).not.toThrow();
});

test("updateMove ne plante pas si pas de graphique", () => {
  WPChart.destroy(); // assure qu'il n'y a pas de chart
  expect(() => WPChart.updateMove(0, 100)).not.toThrow();
});

test("highlightMove met en évidence un point", () => {
  WPChart.render("test-canvas", [{ san: "e4", color: "w", evalCp: 0 }]);
  expect(() => WPChart.highlightMove(0)).not.toThrow();
});

test("highlightMove ne plante pas sans graphique", () => {
  WPChart.destroy();
  expect(() => WPChart.highlightMove(0)).not.toThrow();
});

test("destroy supprime l'instance du graphique", () => {
  WPChart.render("test-canvas", []);
  WPChart.destroy();
  // après destroy, updateMove ne plante pas (graphique null)
  expect(() => WPChart.updateMove(0, 50)).not.toThrow();
});
