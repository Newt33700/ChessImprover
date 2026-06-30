/**
 * Tests unitaires – AdvancedStats (EPIC 4, US 4.1 / 4.2)
 * Couvre la logique pure (couleurs, deltas, deep-dive, gauge, fallback API).
 */

const AS = require("../js/advanced_stats.js");

// ── cellClass ─────────────────────────────────────────────────────

test("cellClass: égal → neutral", () => {
  expect(AS.cellClass(1500, 1500)).toBe("neutral");
});

test("cellClass: supérieur léger → pos", () => {
  expect(AS.cellClass(1550, 1500)).toBe("pos");
});

test("cellClass: supérieur fort (≥150) → pos-strong", () => {
  expect(AS.cellClass(1700, 1500)).toBe("pos-strong");
  expect(AS.cellClass(1650, 1500)).toBe("pos-strong"); // exactement +150
});

test("cellClass: inférieur léger → neg", () => {
  expect(AS.cellClass(1450, 1500)).toBe("neg");
});

test("cellClass: inférieur fort (≥150) → neg-strong", () => {
  expect(AS.cellClass(1300, 1500)).toBe("neg-strong");
  expect(AS.cellClass(1350, 1500)).toBe("neg-strong"); // exactement -150
});

// ── phaseDelta / formatDelta ──────────────────────────────────────

test("phaseDelta calcule l'écart signé", () => {
  expect(AS.phaseDelta(1400, 1250)).toBe(150);
  expect(AS.phaseDelta(1200, 1250)).toBe(-50);
});

test("formatDelta préfixe le signe", () => {
  expect(AS.formatDelta(150)).toBe("+150");
  expect(AS.formatDelta(-50)).toBe("-50");
  expect(AS.formatDelta(0)).toBe("0");
});

// ── deepDiveFor (calé sur la maquette mobile Blitz) ───────────────

test("deepDiveFor(blitz) reproduit les deltas de la maquette", () => {
  const dd = AS.deepDiveFor(AS.MOCK_SUMMARY, "blitz");
  expect(dd.estimated).toBe(1250);
  const byKey = Object.fromEntries(dd.phases.map((p) => [p.key, p.delta]));
  expect(byKey.openings).toBe(150);
  expect(byKey.tactics).toBe(-150);
  expect(byKey.strategy).toBe(30);
  expect(byKey.endgames).toBe(-50);
});

test("deepDiveFor renvoie les 4 catégories ordonnées", () => {
  const dd = AS.deepDiveFor(AS.MOCK_SUMMARY, "bullet");
  expect(dd.phases.map((p) => p.key)).toEqual([
    "openings", "tactics", "strategy", "endgames",
  ]);
});

// ── gaugeAngle ────────────────────────────────────────────────────

test("gaugeAngle: min → -90, max → +90, milieu → 0", () => {
  expect(AS.gaugeAngle(AS.GAUGE_MIN)).toBe(-90);
  expect(AS.gaugeAngle(AS.GAUGE_MAX)).toBe(90);
  expect(AS.gaugeAngle((AS.GAUGE_MIN + AS.GAUGE_MAX) / 2)).toBe(0);
});

test("gaugeAngle borne les valeurs hors plage", () => {
  expect(AS.gaugeAngle(-1000)).toBe(-90);
  expect(AS.gaugeAngle(9999)).toBe(90);
});

test("gaugeAngle: plage dégénérée → 0", () => {
  expect(AS.gaugeAngle(1500, 1500, 1500)).toBe(0);
});

// ── matrixRows ────────────────────────────────────────────────────

test("matrixRows produit 3 lignes avec 4 cellules classées", () => {
  const rows = AS.matrixRows(AS.MOCK_SUMMARY);
  expect(rows.map((r) => r.cadence)).toEqual(["bullet", "blitz", "rapid"]);
  rows.forEach((r) => {
    expect(r.cells).toHaveLength(4);
    r.cells.forEach((c) => expect(typeof c.cls).toBe("string"));
  });
});

test("matrixRows: blitz/endgames (1200 < 1250) est négatif", () => {
  const blitz = AS.matrixRows(AS.MOCK_SUMMARY).find((r) => r.cadence === "blitz");
  const endgames = blitz.cells.find((c) => c.key === "endgames");
  expect(endgames.cls).toBe("neg");
});

// ── fetchSummary (fallback) ───────────────────────────────────────

describe("fetchSummary", () => {
  afterEach(() => { delete global.fetch; });

  test("renvoie le JSON backend quand la requête réussit", async () => {
    const payload = { period: "7d", rows: {} };
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => payload });
    const out = await AS.fetchSummary("7d", "http://api.test");
    expect(out).toBe(payload);
    expect(global.fetch).toHaveBeenCalledWith("http://api.test/api/v1/stats/summary?period=7d");
  });

  test("retombe sur MOCK_SUMMARY si HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    const out = await AS.fetchSummary("30d", "http://api.test");
    expect(out).toBe(AS.MOCK_SUMMARY);
  });

  test("retombe sur MOCK_SUMMARY si le réseau échoue", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network"));
    const out = await AS.fetchSummary("30d", "http://api.test");
    expect(out).toBe(AS.MOCK_SUMMARY);
  });
});
