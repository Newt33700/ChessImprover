/**
 * Tests unitaires — CognitiveDashboard (EPIC 19, US 19.1/19.2)
 */

const CognitiveDashboard = require("../js/cognitive_dashboard.js");

afterEach(() => {
  delete global.ApiClient;
});

// ── formatSeconds ────────────────────────────────────────────────────

describe("formatSeconds", () => {
  test("null renvoie un tiret", () => {
    expect(CognitiveDashboard.formatSeconds(null)).toBe("—");
  });

  test("moins d'une minute", () => {
    expect(CognitiveDashboard.formatSeconds(45)).toBe("45s");
  });

  test("minutes exactes", () => {
    expect(CognitiveDashboard.formatSeconds(120)).toBe("2m");
  });

  test("minutes et secondes", () => {
    expect(CognitiveDashboard.formatSeconds(125)).toBe("2m 5s");
  });

  test("arrondit les décimales", () => {
    expect(CognitiveDashboard.formatSeconds(59.6)).toBe("1m");
  });
});

// ── buildPhaseChartData ──────────────────────────────────────────────

describe("buildPhaseChartData", () => {
  test("ordonne les 3 phases avec labels français", () => {
    const data = CognitiveDashboard.buildPhaseChartData({
      by_phase: {
        opening: { avg_seconds: 40, share_pct: 80 },
        middlegame: { avg_seconds: 10, share_pct: 15 },
        endgame: { avg_seconds: 5, share_pct: 5 },
      },
    });
    expect(data.labels).toEqual(["Ouverture", "Milieu de jeu", "Finale"]);
    expect(data.avgSeconds).toEqual([40, 10, 5]);
    expect(data.sharePct).toEqual([80, 15, 5]);
  });

  test("phase absente -> null/0 par défaut", () => {
    const data = CognitiveDashboard.buildPhaseChartData({ by_phase: {} });
    expect(data.avgSeconds).toEqual([null, null, null]);
    expect(data.sharePct).toEqual([0, 0, 0]);
  });

  test("time_allocation undefined ne lève pas d'exception", () => {
    const data = CognitiveDashboard.buildPhaseChartData(undefined);
    expect(data.labels.length).toBe(3);
  });
});

// ── buildInsightMessages ─────────────────────────────────────────────

describe("buildInsightMessages", () => {
  function report(overrides = {}) {
    return {
      time_allocation: {
        sample_size: 10,
        by_phase: {
          opening: { avg_seconds: 10, share_pct: 33 },
          middlegame: { avg_seconds: 10, share_pct: 33 },
          endgame: { avg_seconds: 10, share_pct: 34 },
        },
        by_pressure: {
          under_pressure: { avg_seconds: 20 },
          equality: { avg_seconds: 20 },
        },
        ...overrides.time_allocation,
      },
      decision_fluidity: {
        top3: { avg_seconds: 5, count: 3 },
        weak: { avg_seconds: 6, count: 1 },
        decision_fatigue: false,
        ...overrides.decision_fluidity,
      },
    };
  }

  test("aucune donnée -> message d'invitation à analyser des parties", () => {
    const messages = CognitiveDashboard.buildInsightMessages({
      time_allocation: { sample_size: 0 },
      decision_fluidity: {},
    });
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatch(/Analysez/);
  });

  test("phase dominante (>= 60%) génère un insight ciblé", () => {
    const messages = CognitiveDashboard.buildInsightMessages(
      report({
        time_allocation: {
          sample_size: 10,
          by_phase: {
            opening: { avg_seconds: 40, share_pct: 80 },
            middlegame: { avg_seconds: 5, share_pct: 10 },
            endgame: { avg_seconds: 5, share_pct: 10 },
          },
          by_pressure: { under_pressure: { avg_seconds: null }, equality: { avg_seconds: null } },
        },
      })
    );
    expect(messages.some((m) => m.includes("80%") && m.includes("ouverture"))).toBe(true);
  });

  test("temps sous pression > équilibre génère un insight", () => {
    const messages = CognitiveDashboard.buildInsightMessages(
      report({
        time_allocation: {
          sample_size: 10,
          by_phase: { opening: { avg_seconds: 1, share_pct: 33 }, middlegame: { avg_seconds: 1, share_pct: 33 }, endgame: { avg_seconds: 1, share_pct: 34 } },
          by_pressure: { under_pressure: { avg_seconds: 90 }, equality: { avg_seconds: 10 } },
        },
      })
    );
    expect(messages.some((m) => m.includes("Sous pression"))).toBe(true);
  });

  test("decision_fatigue=true génère l'alerte de fatigue décisionnelle", () => {
    const messages = CognitiveDashboard.buildInsightMessages(
      report({ decision_fluidity: { top3: { avg_seconds: 5, count: 2 }, weak: { avg_seconds: 180, count: 1 }, decision_fatigue: true } })
    );
    expect(messages.some((m) => m.includes("Fatigue décisionnelle"))).toBe(true);
  });

  test("bonne fluidité (pas de fatigue, top3 joués) -> message positif", () => {
    const messages = CognitiveDashboard.buildInsightMessages(report());
    expect(messages.some((m) => m.includes("Bonne fluidité"))).toBe(true);
  });
});

// ── renderHTML / render ──────────────────────────────────────────────

describe("renderHTML", () => {
  test("un <li> par message d'insight", () => {
    const html = CognitiveDashboard.renderHTML({
      time_allocation: { sample_size: 0 },
      decision_fluidity: {},
    });
    expect(html).toContain("<li class=\"cog-insight\">");
    expect(html).toContain("Analysez");
  });
});

describe("fetchReport", () => {
  test("utilise ApiClient si configuré", async () => {
    global.ApiClient = {
      isConfigured: () => true,
      getCognitiveLoad: jest.fn().mockResolvedValue({ time_allocation: { sample_size: 5 }, decision_fluidity: {} }),
    };
    const report = await CognitiveDashboard.fetchReport();
    expect(report.time_allocation.sample_size).toBe(5);
  });

  test("replie sur EMPTY_REPORT si ApiClient échoue", async () => {
    global.ApiClient = {
      isConfigured: () => true,
      getCognitiveLoad: jest.fn().mockRejectedValue(new Error("HTTP 401")),
    };
    const report = await CognitiveDashboard.fetchReport();
    expect(report).toEqual(CognitiveDashboard.EMPTY_REPORT);
  });

  test("replie sur EMPTY_REPORT sans ApiClient configuré", async () => {
    global.ApiClient = { isConfigured: () => false };
    const report = await CognitiveDashboard.fetchReport();
    expect(report).toEqual(CognitiveDashboard.EMPTY_REPORT);
  });
});

describe("render", () => {
  function makeElement() {
    return {
      _html: "",
      get innerHTML() { return this._html; },
      set innerHTML(v) { this._html = v; },
      getContext: () => ({}),
    };
  }

  test("remplit le container avec les insights", async () => {
    global.ApiClient = {
      isConfigured: () => true,
      getCognitiveLoad: jest.fn().mockResolvedValue({
        time_allocation: { sample_size: 0 },
        decision_fluidity: {},
      }),
    };
    const containerEl = makeElement();
    document.getElementById.mockReturnValueOnce(containerEl).mockReturnValueOnce(null);
    await CognitiveDashboard.render("cog-container", "missing-canvas");
    expect(containerEl.innerHTML).toContain("cog-insight");
  });

  test("container introuvable ne lève pas d'exception", async () => {
    global.ApiClient = { isConfigured: () => false };
    document.getElementById.mockReturnValueOnce(null).mockReturnValueOnce(null);
    await expect(CognitiveDashboard.render("does-not-exist")).resolves.toBeDefined();
  });
});
