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

// ── isEmpty (état vide) ───────────────────────────────────────────

test("isEmpty: hasData===false → vrai, sinon faux", () => {
  expect(AS.isEmpty({ hasData: false })).toBe(true);
  expect(AS.isEmpty({ hasData: true })).toBe(false);
  expect(AS.isEmpty(AS.MOCK_SUMMARY)).toBe(false); // mock = données présentes
  expect(AS.isEmpty(null)).toBe(false);
});

// ── catégories détaillées (US 4.2) ────────────────────────────────

describe("categoryDetailHtml", () => {
  test("catalogues complets", () => {
    expect(AS.TACTIC_THEMES).toHaveLength(6);
    expect(AS.ENDGAME_LESSONS).toHaveLength(4);
  });

  test("tactics : rating + thèmes + bouton Résoudre + retour", () => {
    const html = AS.categoryDetailHtml("tactics", AS.MOCK_SUMMARY);
    expect(html).toContain("data-detail-back");
    expect(html).toContain("Mat en 2");
    expect(html).toContain("Résoudre");
    expect(html).toContain(String(AS.MOCK_SUMMARY.tactics.rating));
  });

  test("endgames : tuiles conversion/résilience + leçons + Étudier", () => {
    const html = AS.categoryDetailHtml("endgames", AS.MOCK_SUMMARY);
    expect(html).toContain("CONVERSION");
    expect(html).toContain("Finales de Tours");
    expect(html).toContain("Étudier");
  });

  test("openings : empty-state sans données, lignes avec topOpenings", () => {
    expect(AS.categoryDetailHtml("openings", {})).toContain("empty-state");
    const withTops = { topOpenings: [{ name: "Sicilienne", elo: 1500 }] };
    const html = AS.categoryDetailHtml("openings", withTops);
    expect(html).toContain("Sicilienne");
    expect(html).toContain("1500");
  });

  test("strategy : placeholder", () => {
    expect(AS.categoryDetailHtml("strategy", {})).toContain("empty-state");
  });
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

// ── formatShortDate (US 5.1) ───────────────────────────────────────

describe("formatShortDate", () => {
  test("formate une date ISO en JJ/MM", () => {
    expect(AS.formatShortDate("2026-07-01T00:00:00Z")).toBe("01/07");
  });

  test("chaîne vide/absente → chaîne vide", () => {
    expect(AS.formatShortDate("")).toBe("");
    expect(AS.formatShortDate(null)).toBe("");
    expect(AS.formatShortDate(undefined)).toBe("");
  });

  test("date invalide → 10 premiers caractères", () => {
    expect(AS.formatShortDate("not-a-date")).toBe("not-a-date");
  });
});

// ── buildProgressDatasets (US 5.1) ─────────────────────────────────

describe("buildProgressDatasets", () => {
  test("historique vide → labels et séries vides", () => {
    const { labels, series } = AS.buildProgressDatasets([]);
    expect(labels).toEqual([]);
    expect(series).toEqual({ openings: [], tactics: [], strategy: [], endgames: [] });
  });

  test("aligne labels et séries dans l'ordre chronologique fourni", () => {
    const history = [
      { date: "2026-06-01T00:00:00Z", openings: 2400, tactics: 2100, strategy: 2200, endgames: 1900 },
      { date: "2026-06-08T00:00:00Z", openings: 2550, tactics: 2300, strategy: 2350, endgames: 2050 },
    ];
    const { labels, series } = AS.buildProgressDatasets(history);
    expect(labels).toEqual(["01/06", "08/06"]);
    expect(series.openings).toEqual([2400, 2550]);
    expect(series.tactics).toEqual([2100, 2300]);
    expect(series.strategy).toEqual([2200, 2350]);
    expect(series.endgames).toEqual([1900, 2050]);
  });

  test("MOCK_HISTORY se transforme sans erreur (5 points)", () => {
    const { labels, series } = AS.buildProgressDatasets(AS.MOCK_HISTORY);
    expect(labels).toHaveLength(5);
    expect(series.openings).toHaveLength(5);
  });
});

// ── toggleProgressSeries (US 5.1) ──────────────────────────────────

describe("toggleProgressSeries", () => {
  function fakeChart() {
    return { setDatasetVisibility: jest.fn(), update: jest.fn() };
  }

  test("bascule la visibilité du bon index de dataset", () => {
    const chart = fakeChart();
    AS.toggleProgressSeries(chart, "tactics", false);
    const tacticsIndex = AS.CATEGORIES.findIndex((c) => c.key === "tactics");
    expect(chart.setDatasetVisibility).toHaveBeenCalledWith(tacticsIndex, false);
    expect(chart.update).toHaveBeenCalledTimes(1);
  });

  test("no-op si le chart est null", () => {
    expect(() => AS.toggleProgressSeries(null, "openings", true)).not.toThrow();
  });

  test("no-op si la clé de catégorie est inconnue", () => {
    const chart = fakeChart();
    AS.toggleProgressSeries(chart, "inconnue", true);
    expect(chart.setDatasetVisibility).not.toHaveBeenCalled();
    expect(chart.update).not.toHaveBeenCalled();
  });
});

// ── fetchHistory (fallback, US 5.1) ────────────────────────────────

describe("fetchHistory", () => {
  afterEach(() => { delete global.fetch; });

  test("renvoie l'historique backend quand la requête réussit", async () => {
    const history = [{ date: "2026-07-01T00:00:00Z", openings: 2000, tactics: 2000, strategy: 2000, endgames: 2000 }];
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ history }) });
    const out = await AS.fetchHistory("blitz", 30, "http://api.test");
    expect(out).toBe(history);
    expect(global.fetch).toHaveBeenCalledWith("http://api.test/api/v1/stats/history?cadence=blitz&days=30");
  });

  test("retombe sur MOCK_HISTORY si HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    const out = await AS.fetchHistory("blitz", 30, "http://api.test");
    expect(out).toBe(AS.MOCK_HISTORY);
  });

  test("retombe sur MOCK_HISTORY si le réseau échoue", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network"));
    const out = await AS.fetchHistory("blitz", 30, "http://api.test");
    expect(out).toBe(AS.MOCK_HISTORY);
  });

  test("retombe sur MOCK_HISTORY si le backend renvoie un historique absent", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    const out = await AS.fetchHistory("blitz", 30, "http://api.test");
    expect(out).toBe(AS.MOCK_HISTORY);
  });
});
