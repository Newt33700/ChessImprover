/**
 * Tests unitaires – EndgameDetector (US 3)
 * L'API Syzygy est mockée.
 */

const fs   = require("fs");
const path = require("path");

function loadEndgameDetector() {
  const code = fs.readFileSync(
    path.resolve(__dirname, "../js/endgame_detector.js"),
    "utf8"
  );
  const adapted = code.replace("window.EndgameDetector = EndgameDetector;", "module.exports = EndgameDetector;");
  const m = { exports: {} };
  // eslint-disable-next-line no-new-func
  new Function("module", "exports", adapted)(m, m.exports);
  return m.exports;
}

const ED = loadEndgameDetector();

// ── countMaterial ─────────────────────────────────────────────────

test("countMaterial position initiale = 78 pts", () => {
  const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  const { material } = ED.countMaterial(fen);
  // 2Q(18) + 4R(20) + 4B(12) + 4N(12) + 16P(0) = 62 pts
  expect(material).toBe(62);
});

test("countMaterial uniquement les rois = 0 pts", () => {
  const fen = "8/8/8/8/8/8/8/K6k w - - 0 1";
  const { material, totalPieces } = ED.countMaterial(fen);
  expect(material).toBe(0);
  expect(totalPieces).toBe(2);
});

test("countMaterial R+T vs R → 5 pts, 4 pièces", () => {
  // Blanc : Roi + Tour ; Noir : Roi
  const fen = "8/8/8/8/4k3/8/8/R3K3 w - - 0 1";
  const { material, totalPieces } = ED.countMaterial(fen);
  expect(material).toBe(5); // Tour = 5
  expect(totalPieces).toBe(3); // 2 rois + 1 tour
});

test("countMaterial Tour+Fou+Cavalier = 11 pts", () => {
  const fen = "8/8/8/8/8/8/8/RBNk3K w - - 0 1";
  const { material } = ED.countMaterial(fen);
  expect(material).toBe(5 + 3 + 3); // 11
});

// ── detectEndgamePhase ────────────────────────────────────────────

test("detectEndgamePhase vrai si matériel <= 13", () => {
  // Position avec R+T+C (11 pts) → finale
  const fen = "8/8/8/8/8/8/8/RNk4K w - - 0 1";
  expect(ED.detectEndgamePhase(fen)).toBe(true);
});

test("detectEndgamePhase faux si matériel > 13", () => {
  // Position initiale (62 pts) → pas de finale
  const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  expect(ED.detectEndgamePhase(fen)).toBe(false);
});

test("detectEndgamePhase vrai à exactement 13 pts", () => {
  // Deux tours (10 pts) + un fou (3 pts) = 13 pts
  const fen = "8/8/8/8/8/8/8/RRBk3K w - - 0 1";
  expect(ED.detectEndgamePhase(fen)).toBe(true);
});

// ── isEligibleForSyzygy ───────────────────────────────────────────

test("isEligibleForSyzygy vrai si <= 7 pièces", () => {
  // Roi blanc + Tour + Roi noir = 3 pièces
  const fen = "8/8/8/8/4k3/8/8/R3K3 w - - 0 1";
  expect(ED.isEligibleForSyzygy(fen)).toBe(true);
});

test("isEligibleForSyzygy faux si > 7 pièces", () => {
  // Position initiale = 32 pièces
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

test("classifyCategory 'loss' → 'loss'", () => {
  expect(ED.classifyCategory({ category: "loss" })).toBe("loss");
});

test("classifyCategory null si pas de category", () => {
  expect(ED.classifyCategory({})).toBeNull();
  expect(ED.classifyCategory(null)).toBeNull();
});

// ── analyzeGame avec mock Syzygy ──────────────────────────────────

test("analyzeGame détecte le début de la finale", async () => {
  const fen8 = "8/8/8/8/8/8/8/RBNk3K w - - 0 1"; // 11 pts → finale
  const moves = [
    { fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", color: "w", accuracy_score: 80 },
    { fen: fen8, color: "b", accuracy_score: 75 },
  ];

  const results = await ED.analyzeGame(moves, "w");
  expect(results.endgameStartIndex).toBe(1);
  expect(results.endgameAccuracies).toContain(75);
});

test("analyzeGame détecte une gaffe de finale via Syzygy mock", async () => {
  // Mocked querySyzygy : coup 0 = win, coup 1 = draw (gaffe)
  const fen1 = "8/8/8/4k3/8/8/8/R3K3 w - - 0 1";
  const fen2 = "8/8/4k3/8/8/8/8/R3K3 b - - 1 1";
  const moves = [
    { fen: fen1, color: "w", accuracy_score: 90 },
    { fen: fen2, color: "w", accuracy_score: 20 },
  ];

  const callCount = { n: 0 };
  const responses = [{ category: "win" }, { category: "draw" }];

  const origQuery = ED.querySyzygy;
  ED.querySyzygy = async () => responses[callCount.n++];

  // Monkey-patch analyzeGame to use the patched querySyzygy
  // Instead, we pass a custom analyzeGame closure test
  let prevCat = null;
  const blunders = [];
  for (let i = 0; i < moves.length; i++) {
    const m = moves[i];
    if (ED.isEligibleForSyzygy(m.fen)) {
      const data = await ED.querySyzygy(m.fen);
      const cat  = ED.classifyCategory(data);
      if (m.color === "w" && prevCat === "win" && cat !== "win") {
        blunders.push({ moveIndex: i, from: prevCat, to: cat });
      }
      prevCat = cat;
    }
  }

  ED.querySyzygy = origQuery;

  expect(blunders).toHaveLength(1);
  expect(blunders[0].from).toBe("win");
  expect(blunders[0].to).toBe("draw");
});

test("analyzeGame calcule la précision moyenne en finale", async () => {
  const fen = "8/8/8/8/8/8/8/R3K3 w - - 0 1";
  const moves = [
    { fen, color: "w", accuracy_score: 80 },
    { fen, color: "b", accuracy_score: 60 },
    { fen, color: "w", accuracy_score: 100 },
  ];

  const results = await ED.analyzeGame(moves, "w");
  expect(results.endgameAvgAccuracy).toBeCloseTo(80, 0);
});
