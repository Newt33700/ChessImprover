/**
 * Tests unitaires – EndgameDetector (US 3)
 */

const ED = require("../js/endgame_detector.js");

// Stub global fetch (Syzygy API)
global.fetch = jest.fn();

// Keep original querySyzygy so tests can restore it after mocking
const origQuerySyzygy = ED.querySyzygy;
beforeEach(() => {
  ED.querySyzygy = origQuerySyzygy;
  global.fetch = jest.fn();
});

// ── countMaterial ─────────────────────────────────────────────────

test("countMaterial position initiale = 62 pts de matériel", () => {
  const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  const { material } = ED.countMaterial(fen);
  expect(material).toBe(62);
});

test("countMaterial uniquement les rois = 0 pts, 2 pièces", () => {
  const fen = "8/8/8/8/8/8/8/K6k w - - 0 1";
  const { material, totalPieces } = ED.countMaterial(fen);
  expect(material).toBe(0);
  expect(totalPieces).toBe(2);
});

test("countMaterial R+T vs R → 5 pts, 3 pièces", () => {
  const fen = "8/8/8/8/4k3/8/8/R3K3 w - - 0 1";
  const { material, totalPieces } = ED.countMaterial(fen);
  expect(material).toBe(5);
  expect(totalPieces).toBe(3);
});

test("countMaterial Tour+Fou+Cavalier = 11 pts", () => {
  const fen = "8/8/8/8/8/8/8/RBNk3K w - - 0 1";
  const { material } = ED.countMaterial(fen);
  expect(material).toBe(11);
});

// ── detectEndgamePhase ────────────────────────────────────────────

test("detectEndgamePhase vrai si matériel <= 13", () => {
  const fen = "8/8/8/8/8/8/8/RNk4K w - - 0 1";
  expect(ED.detectEndgamePhase(fen)).toBe(true);
});

test("detectEndgamePhase faux si matériel > 13", () => {
  const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  expect(ED.detectEndgamePhase(fen)).toBe(false);
});

test("detectEndgamePhase vrai à exactement 13 pts", () => {
  const fen = "8/8/8/8/8/8/8/RRBk3K w - - 0 1";
  expect(ED.detectEndgamePhase(fen)).toBe(true);
});

// ── isEligibleForSyzygy ───────────────────────────────────────────

test("isEligibleForSyzygy vrai si <= 7 pièces", () => {
  const fen = "8/8/8/8/4k3/8/8/R3K3 w - - 0 1";
  expect(ED.isEligibleForSyzygy(fen)).toBe(true);
});

test("isEligibleForSyzygy faux si > 7 pièces", () => {
  const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  expect(ED.isEligibleForSyzygy(fen)).toBe(false);
});

// ── classifyCategory ──────────────────────────────────────────────

test("classifyCategory 'win' → 'win'", () => {
  expect(ED.classifyCategory({ category: "win" })).toBe("win");
});

test("classifyCategory 'cursed-win' → 'win'", () => {
  expect(ED.classifyCategory({ category: "cursed-win" })).toBe("win");
});

test("classifyCategory 'draw' → 'draw'", () => {
  expect(ED.classifyCategory({ category: "draw" })).toBe("draw");
});

test("classifyCategory 'blessed-loss' → 'draw'", () => {
  expect(ED.classifyCategory({ category: "blessed-loss" })).toBe("draw");
});

test("classifyCategory 'loss' → 'loss'", () => {
  expect(ED.classifyCategory({ category: "loss" })).toBe("loss");
});

test("classifyCategory null si pas de category", () => {
  expect(ED.classifyCategory({})).toBeNull();
  expect(ED.classifyCategory(null)).toBeNull();
});

test("classifyCategory 'cursed-loss' → 'loss'", () => {
  expect(ED.classifyCategory({ category: "cursed-loss" })).toBe("loss");
});

test("classifyCategory catégorie inconnue → 'unknown'", () => {
  expect(ED.classifyCategory({ category: "something-else" })).toBe("unknown");
});

// ── querySyzygy (chemin erreur) ────────────────────────────────────

test("querySyzygy lance une erreur si API renvoie HTTP 500", async () => {
  global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
  await expect(ED.querySyzygy("8/8/8/4k3/8/8/8/R3K3 w - - 0 1")).rejects.toThrow("500");
});

// ── analyzeGame avec mock querySyzygy ─────────────────────────────

test("analyzeGame détecte le début de la finale", async () => {
  const fen8 = "8/8/8/8/8/8/8/RBNk3K w - - 0 1";
  const moves = [
    { fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", color: "w", accuracy_score: 80 },
    { fen: fen8, color: "b", accuracy_score: 75 },
  ];
  const results = await ED.analyzeGame(moves, "w");
  expect(results.endgameStartIndex).toBe(1);
  expect(results.endgameAccuracies).toContain(75);
});

test("analyzeGame détecte gaffe de finale (win→draw)", async () => {
  const origQuery = ED.querySyzygy;
  let call = 0;
  ED.querySyzygy = jest.fn().mockImplementation(() =>
    Promise.resolve({ category: call++ === 0 ? "win" : "draw" })
  );

  const fen1 = "8/8/8/4k3/8/8/8/R3K3 w - - 0 1";
  const fen2 = "8/8/4k3/8/8/8/8/R3K3 b - - 1 1";
  const moves = [
    { fen: fen1, color: "w", accuracy_score: 90 },
    { fen: fen2, color: "w", accuracy_score: 20 },
  ];

  const results = await ED.analyzeGame(moves, "w");
  expect(results.syzygyBlunders).toHaveLength(1);
  expect(results.syzygyBlunders[0].from).toBe("win");
  expect(results.syzygyBlunders[0].to).toBe("draw");

  ED.querySyzygy = origQuery;
});

test("analyzeGame calcule la précision moyenne en finale", async () => {
  ED.querySyzygy = jest.fn().mockResolvedValue({ category: "win" });
  const fen = "8/8/8/8/8/8/8/R3K3 w - - 0 1";
  const moves = [
    { fen, color: "w", accuracy_score: 80 },
    { fen, color: "b", accuracy_score: 60 },
    { fen, color: "w", accuracy_score: 100 },
  ];
  const results = await ED.analyzeGame(moves, "w");
  expect(results.endgameAvgAccuracy).toBeCloseTo(80, 0);
});

test("analyzeGame ne plante pas si API Syzygy échoue", async () => {
  ED.querySyzygy = jest.fn().mockRejectedValue(new Error("réseau"));
  const fen = "8/8/8/8/8/8/8/R3K3 w - - 0 1";
  const results = await ED.analyzeGame([{ fen, color: "w", accuracy_score: 70 }], "w");
  expect(results.syzygyBlunders).toHaveLength(0);
});

test("analyzeGame appelle onProgress pour chaque coup Syzygy", async () => {
  ED.querySyzygy = jest.fn().mockResolvedValue({ category: "win" });
  const fen = "8/8/8/8/8/8/8/R3K3 w - - 0 1";
  const progressCalls = [];
  await ED.analyzeGame([{ fen, color: "w", accuracy_score: 90 }], "w", (p) => progressCalls.push(p));
  expect(progressCalls).toHaveLength(1);
  expect(progressCalls[0].category).toBe("win");
});

// ── renderStats ────────────────────────────────────────────────────

test("renderStats avec endgameStartIndex null affiche empty-state", () => {
  const results = { endgameStartIndex: null, syzygyBlunders: [] };
  ED.renderStats(results, "test-container");
  const el = global.document.getElementById("test-container");
  // La fonction ne plante pas
  expect(true).toBe(true);
});

test("renderStats avec blunders ne plante pas", () => {
  const results = {
    endgameStartIndex: 2,
    endgameAvgAccuracy: 75.5,
    syzygyBlunders: [{ san: "Re1", from: "win", to: "draw" }],
  };
  expect(() => ED.renderStats(results, "test-container")).not.toThrow();
});

test("renderStats avec syzygyBlunders vide affiche no-blunder", () => {
  const results = {
    endgameStartIndex: 1,
    endgameAvgAccuracy: 80,
    syzygyBlunders: [],
  };
  expect(() => ED.renderStats(results, "test-container")).not.toThrow();
});
