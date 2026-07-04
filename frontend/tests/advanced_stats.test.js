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

  test("tactics : rating + thèmes + bouton Résoudre + retour + gauge", () => {
    const html = AS.categoryDetailHtml("tactics", AS.MOCK_SUMMARY);
    expect(html).toContain("data-detail-back");
    expect(html).toContain("Mat en 2");
    expect(html).toContain("Résoudre");
    expect(html).toContain(String(AS.MOCK_SUMMARY.tactics.rating));
    expect(html).toContain("tac-gauge");
    expect(html).toContain("69%"); // 68.5 arrondi
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

// ── tacticSuccessGaugeHtml (US 4.2) ────────────────────────────────

describe("tacticSuccessGaugeHtml", () => {
  test("affiche le pourcentage arrondi", () => {
    expect(AS.tacticSuccessGaugeHtml(72.3)).toContain("72%");
  });

  test("0% : offset = circonférence complète (aucun remplissage)", () => {
    const html = AS.tacticSuccessGaugeHtml(0);
    const r = 42;
    const c = 2 * Math.PI * r;
    expect(html).toContain(`stroke-dashoffset="${c.toFixed(2)}"`);
    expect(html).toContain("0%");
  });

  test("100% : offset = 0 (anneau plein)", () => {
    const html = AS.tacticSuccessGaugeHtml(100);
    expect(html).toContain('stroke-dashoffset="0.00"');
    expect(html).toContain("100%");
  });

  test("valeurs hors bornes clampées [0, 100]", () => {
    expect(AS.tacticSuccessGaugeHtml(-20)).toContain("0%");
    expect(AS.tacticSuccessGaugeHtml(150)).toContain("100%");
  });

  test("undefined/null → 0% (pas de NaN)", () => {
    expect(AS.tacticSuccessGaugeHtml(undefined)).toContain("0%");
    expect(AS.tacticSuccessGaugeHtml(null)).toContain("0%");
    expect(AS.tacticSuccessGaugeHtml(undefined)).not.toContain("NaN");
  });

  test("libellé du taux de réussite présent", () => {
    expect(AS.tacticSuccessGaugeHtml(50)).toContain("Taux de réussite tactique");
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

// ── Courbe d'Elo Chess.com (EPIC 24) ───────────────────────────────

describe("buildEloCurveData (EPIC 24)", () => {
  test("transforme les points en labels courts + valeurs", () => {
    const points = [
      { date: "2026-06-28", rating: 1100 },
      { date: "2026-07-01", rating: 1150 },
    ];
    expect(AS.buildEloCurveData(points)).toEqual({
      labels: ["28/06", "01/07"],
      data: [1100, 1150],
    });
  });

  test("entrées vides ou invalides → structures vides", () => {
    expect(AS.buildEloCurveData([])).toEqual({ labels: [], data: [] });
    expect(AS.buildEloCurveData(null)).toEqual({ labels: [], data: [] });
    expect(AS.buildEloCurveData(undefined)).toEqual({ labels: [], data: [] });
  });
});

describe("buildEloCurvePoints (repli navigateur — mêmes règles que le backend)", () => {
  // `now` figé pour des fenêtres déterministes : 10/07/2026 12:00 UTC.
  const NOW = new Date("2026-07-10T12:00:00Z");
  const T = (iso) => Math.floor(new Date(iso).getTime() / 1000);
  const game = (over = {}) => ({
    time_class: "blitz",
    end_time: T("2026-07-08T10:00:00Z"),
    white: { username: "Alice", rating: 1200 },
    black: { username: "bob", rating: 1100 },
    ...over,
  });

  test("un point par jour joué, rating du bon côté", () => {
    const points = AS.buildEloCurvePoints([game()], "alice", "blitz", 30, NOW);
    expect(points).toEqual([{ date: "2026-07-08", rating: 1200 }]);
  });

  test("pseudo insensible à la casse, côté noir aussi", () => {
    const points = AS.buildEloCurvePoints([game()], "BOB", "blitz", 30, NOW);
    expect(points).toEqual([{ date: "2026-07-08", rating: 1100 }]);
  });

  test("filtre par cadence", () => {
    expect(AS.buildEloCurvePoints([game({ time_class: "rapid" })], "alice", "blitz", 30, NOW)).toEqual([]);
  });

  test("hors fenêtre temporelle → exclu", () => {
    const old = game({ end_time: T("2026-05-01T10:00:00Z") });
    expect(AS.buildEloCurvePoints([old], "alice", "blitz", 30, NOW)).toEqual([]);
  });

  test("la DERNIÈRE partie du jour donne le rating du jour", () => {
    const morning = game({ end_time: T("2026-07-08T08:00:00Z"), white: { username: "alice", rating: 1180 } });
    const evening = game({ end_time: T("2026-07-08T20:00:00Z"), white: { username: "alice", rating: 1230 } });
    const points = AS.buildEloCurvePoints([evening, morning], "alice", "blitz", 30, NOW);
    expect(points).toEqual([{ date: "2026-07-08", rating: 1230 }]);
  });

  test("points triés chronologiquement sur plusieurs jours", () => {
    const d1 = game({ end_time: T("2026-07-05T10:00:00Z"), white: { username: "alice", rating: 1150 } });
    const d2 = game({ end_time: T("2026-07-08T10:00:00Z"), white: { username: "alice", rating: 1210 } });
    const points = AS.buildEloCurvePoints([d2, d1], "alice", "blitz", 30, NOW);
    expect(points.map((p) => p.date)).toEqual(["2026-07-05", "2026-07-08"]);
  });

  test("entrées inexploitables ignorées sans planter", () => {
    const bad = [
      null,
      game({ end_time: "not-a-number" }),
      game({ white: { username: "alice" } }),          // rating absent
      game({ white: { username: "someone-else" }, black: { username: "other" } }),
    ];
    expect(AS.buildEloCurvePoints(bad, "alice", "blitz", 30, NOW)).toEqual([]);
    expect(AS.buildEloCurvePoints(null, "alice", "blitz", 30, NOW)).toEqual([]);
  });
});

describe("fetchEloCurve (EPIC 24)", () => {
  afterEach(() => { delete global.fetch; });

  test("renvoie la courbe backend quand la requête réussit", async () => {
    const curve = { cadence: "blitz", days: 30, points: [{ date: "2026-07-01", rating: 1200 }] };
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => curve });
    const out = await AS.fetchEloCurve("blitz", 30, "http://api.test");
    expect(out).toEqual(curve);
    expect(global.fetch).toHaveBeenCalledWith("http://api.test/api/v1/stats/elo-curve?cadence=blitz&days=30");
  });

  test("renvoie null si HTTP non-ok (422 pseudo non lié, 502 Chess.com down)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 422 });
    expect(await AS.fetchEloCurve("blitz", 7, "http://api.test")).toBeNull();
  });

  test("renvoie null si le réseau échoue — jamais de données simulées", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network"));
    expect(await AS.fetchEloCurve("rapid", 90, "http://api.test")).toBeNull();
  });
});

describe("renderEloCurve (EPIC 24)", () => {
  test("null sans canvas", () => {
    expect(AS.renderEloCurve(null, [])).toBeNull();
  });

  test("construit un Chart line avec les points fournis", () => {
    const canvas = { getContext: () => ({}) };
    const points = [{ date: "2026-07-01", rating: 1200 }];
    AS.renderEloCurve(canvas, points);
    const cfg = global.Chart.mock.calls[global.Chart.mock.calls.length - 1][1];
    expect(cfg.type).toBe("line");
    expect(cfg.data.datasets[0].data).toEqual([1200]);
    expect(cfg.data.labels).toEqual(["01/07"]);
  });
});
