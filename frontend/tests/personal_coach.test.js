/**
 * Tests unitaires – PersonalCoach (US 6)
 * Teste tous les embranchements de l'arbre de décision.
 */

const PC = require("../js/personal_coach.js");

// ── Helpers de fixtures ───────────────────────────────────────────

function makeGame(opts = {}) {
  const {
    username = "alice",
    result   = "win",
    accuracy = 75,
    opening  = "Italienne",
    blunders = 0,
    moves    = [],
  } = opts;
  return {
    pgn:           `[Opening "${opening}"]`,
    white:         { username, result: result === "win" ? "win" : result === "draw" ? "agreed" : "checkmated" },
    black:         { username: "bob",  result: result === "win" ? "checkmated" : result === "draw" ? "agreed" : "win" },
    accuracy,
    blunders_count: blunders,
    moves,
  };
}

function manyGames(n, opts) {
  return Array.from({ length: n }, (_, i) => makeGame({ ...opts, accuracy: 75 + (i % 5) }));
}

// ── computeMetrics ────────────────────────────────────────────────

test("computeMetrics retourne null si pas de parties", () => {
  expect(PC.computeMetrics([], "alice")).toBeNull();
  expect(PC.computeMetrics(null, "alice")).toBeNull();
});

test("computeMetrics calcule blunderRate global", () => {
  const moves = [
    { color: "w", classification: "blunder" },
    { color: "w", classification: "good" },
    { color: "b", classification: "good" },
  ];
  const games = [makeGame({ blunders: 1, moves })];
  const m = PC.computeMetrics(games, "alice");
  expect(m.blunderRate).toBeGreaterThan(0);
});

test("computeMetrics calcule accuracy moyenne", () => {
  const games = [
    makeGame({ accuracy: 60 }),
    makeGame({ accuracy: 80 }),
  ];
  const m = PC.computeMetrics(games, "alice");
  expect(m.avgAccuracy).toBeCloseTo(70, 0);
});

test("computeMetrics détecte pire ouverture avec >= 5 parties", () => {
  const lossGames  = Array.from({ length: 5 }, () => makeGame({ result: "loss",  opening: "Caro-Kann" }));
  const winGames   = Array.from({ length: 5 }, () => makeGame({ result: "win",   opening: "Italienne" }));
  const m = PC.computeMetrics([...lossGames, ...winGames], "alice");
  expect(m.worstOpening).toBe("Caro-Kann");
  expect(m.worstWinRate).toBe(0);
});

test("computeMetrics ignore ouvertures avec < 5 parties", () => {
  const games = Array.from({ length: 3 }, () => makeGame({ result: "loss", opening: "Rare" }));
  const m = PC.computeMetrics(games, "alice");
  // Rare a seulement 3 parties → ignorée
  expect(m.worstOpening).toBeNull();
});

test("computeMetrics totalGames = nombre de parties analysées (max 30)", () => {
  const games = manyGames(40, {});
  const m = PC.computeMetrics(games, "alice");
  expect(m.totalGames).toBe(30);
});

// ── diagnose ──────────────────────────────────────────────────────

test("diagnose retourne un message par défaut si metrics null", () => {
  const advices = PC.diagnose(null);
  expect(advices).toHaveLength(1);
  expect(advices[0].action).toBeNull();
});

test("diagnose Règle 1 : earlyBlunderRate > 20% → réviser ouvertures", () => {
  const m = { earlyBlunderRate: 25, blunderRate: 3, avgAccuracy: 72, worstOpening: null, worstWinRate: null, avgEndgameAcc: null, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule1 = advices.find((a) => a.target === "tab-openings" && a.message.includes("précoces"));
  expect(rule1).toBeTruthy();
  expect(rule1.priority).toBe(10);
});

test("diagnose Règle 2 : worstOpening avec winRate < 30% sur 5+ parties", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 72, worstOpening: "Caro-Kann", worstWinRate: 20, avgEndgameAcc: null, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule2 = advices.find((a) => a.message.includes("Caro-Kann"));
  expect(rule2).toBeTruthy();
  expect(rule2.priority).toBe(9);
});

test("diagnose Règle 2 ne se déclenche pas si winRate >= 30%", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 72, worstOpening: "Italienne", worstWinRate: 35, avgEndgameAcc: null, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule2 = advices.find((a) => a.message.includes("Italienne"));
  expect(rule2).toBeFalsy();
});

test("diagnose Règle 3 : blunderRate > 5% → puzzles SRS", () => {
  const m = { earlyBlunderRate: 10, blunderRate: 8, avgAccuracy: 65, worstOpening: null, worstWinRate: null, avgEndgameAcc: null, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule3 = advices.find((a) => a.target === "exercise" && a.message.includes("gaffes global"));
  expect(rule3).toBeTruthy();
  expect(rule3.priority).toBe(8);
});

test("diagnose Règle 4 : avgEndgameAcc < 60% → finale fragile", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 72, worstOpening: null, worstWinRate: null, avgEndgameAcc: 45, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule4 = advices.find((a) => a.target === "tab-endgame");
  expect(rule4).toBeTruthy();
  expect(rule4.priority).toBe(7);
});

test("diagnose Règle 4 ne se déclenche pas si avgEndgameAcc null", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 72, worstOpening: null, worstWinRate: null, avgEndgameAcc: null, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule4 = advices.find((a) => a.target === "tab-endgame");
  expect(rule4).toBeFalsy();
});

test("diagnose Règle 5 : accuracy 75-85% → conseil milieu de partie", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 80, worstOpening: null, worstWinRate: null, avgEndgameAcc: null, totalGames: 10 };
  const advices = PC.diagnose(m);
  const rule5 = advices.find((a) => a.target === "review");
  expect(rule5).toBeTruthy();
  expect(rule5.priority).toBe(5);
});

test("diagnose Règle 6 : < 5 parties → demander plus de données", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 72, worstOpening: null, worstWinRate: null, avgEndgameAcc: null, totalGames: 3 };
  const advices = PC.diagnose(m);
  const rule6 = advices.find((a) => a.priority === 1);
  expect(rule6).toBeTruthy();
});

test("diagnose trie par priorité décroissante", () => {
  const m = { earlyBlunderRate: 25, blunderRate: 8, avgAccuracy: 60, worstOpening: "Caro-Kann", worstWinRate: 20, avgEndgameAcc: 45, totalGames: 15 };
  const advices = PC.diagnose(m);
  for (let i = 1; i < advices.length; i++) {
    expect(advices[i].priority).toBeLessThanOrEqual(advices[i - 1].priority);
  }
});

test("diagnose fallback si aucune règle critère ne se déclenche", () => {
  const m = { earlyBlunderRate: 5, blunderRate: 3, avgAccuracy: 90, worstOpening: null, worstWinRate: null, avgEndgameAcc: null, totalGames: 20 };
  const advices = PC.diagnose(m);
  expect(advices.length).toBeGreaterThan(0);
  // Doit contenir au moins un message de continuation
  expect(advices.some((a) => a.message.includes("solide") || a.message.includes("Continue"))).toBe(true);
});

// ── renderHTML ────────────────────────────────────────────────────

test("renderHTML génère un div.coach-card par advice", () => {
  const advices = [
    { priority: 10, message: "Teste l'arbre", action: "Cliquer", target: "exercise" },
    { priority: 5,  message: "Second conseil", action: null, target: null },
  ];
  const html = PC.renderHTML(advices);
  expect(html.match(/coach-card/g)).toHaveLength(2);
});

test("renderHTML inclut le bouton d'action si défini", () => {
  const advices = [{ priority: 8, message: "msg", action: "Agir", target: "exercise" }];
  const html = PC.renderHTML(advices);
  expect(html).toContain("coach-action-btn");
  expect(html).toContain("Agir");
});

test("renderHTML n'inclut pas de bouton si action null", () => {
  const advices = [{ priority: 1, message: "msg", action: null, target: null }];
  const html = PC.renderHTML(advices);
  expect(html).not.toContain("coach-action-btn");
});
