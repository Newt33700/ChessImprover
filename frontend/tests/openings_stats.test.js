/**
 * Tests unitaires – OpeningsStats (US 2)
 */

const OS = require("../js/openings_stats.js");

function makeGame(opening, white, black, result) {
  const pgn = `[White "${white}"][Black "${black}"][Opening "${opening}"][Result "*"]`;
  return {
    pgn,
    white: { username: white, result: result === "w" ? "win" : result === "d" ? "agreed" : "checkmated" },
    black: { username: black, result: result === "b" ? "win" : result === "d" ? "agreed" : "checkmated" },
  };
}

// ── getResult ─────────────────────────────────────────────────────

test("getResult retourne 'win' quand le joueur gagne", () => {
  const g = makeGame("Sicilienne", "alice", "bob", "w");
  expect(OS.getResult(g, "alice")).toBe("win");
});

test("getResult retourne 'loss' quand le joueur perd", () => {
  const g = makeGame("Sicilienne", "alice", "bob", "w");
  expect(OS.getResult(g, "bob")).toBe("loss");
});

test("getResult retourne 'draw' sur partie nulle", () => {
  const g = {
    pgn: `[White "alice"][Black "bob"]`,
    white: { username: "alice", result: "agreed" },
    black: { username: "bob",   result: "agreed" },
  };
  expect(OS.getResult(g, "alice")).toBe("draw");
  expect(OS.getResult(g, "bob")).toBe("draw");
});

test("getResult retourne null si username absent", () => {
  const g = makeGame("Italienne", "alice", "bob", "w");
  expect(OS.getResult(g, "")).toBeNull();
});

// ── extractOpeningName ────────────────────────────────────────────

test("extractOpeningName lit le header PGN Opening", () => {
  const g = { pgn: `[Opening "Défense Sicilienne"]` };
  expect(OS.extractOpeningName(g)).toBe("Défense Sicilienne");
});

test("extractOpeningName lit le header ECO si Opening absent", () => {
  const g = { pgn: `[ECO "B20"]` };
  expect(OS.extractOpeningName(g)).toBe("B20");
});

test("extractOpeningName lit game.opening si pas de PGN header", () => {
  const g = { pgn: "", opening: "Ruy Lopez" };
  expect(OS.extractOpeningName(g)).toBe("Ruy Lopez");
});

test("extractOpeningName retourne 'Inconnue' si rien", () => {
  const g = { pgn: "" };
  expect(OS.extractOpeningName(g)).toBe("Inconnue");
});

// ── aggregate ─────────────────────────────────────────────────────

test("aggregate regroupe correctement les victoires/nuls/défaites", () => {
  const games = [
    makeGame("Sicilienne", "alice", "bob", "w"),
    makeGame("Sicilienne", "alice", "bob", "w"),
    makeGame("Sicilienne", "alice", "bob", "b"),
    makeGame("Sicilienne", "alice", "bob", "d"),
    makeGame("Sicilienne", "alice", "bob", "d"),
  ];
  const entries = OS.aggregate(games, "alice");
  expect(entries).toHaveLength(1);
  const e = entries[0];
  expect(e.wins).toBe(2);
  expect(e.losses).toBe(1);
  expect(e.draws).toBe(2);
  expect(e.total).toBe(5);
  expect(e.color).toBe("Blanc");
});

test("aggregate distingue Blanc et Noir pour la même ouverture", () => {
  const games = [
    makeGame("Italienne", "alice", "bob",   "w"),
    makeGame("Italienne", "carol", "alice", "b"),
  ];
  const entries = OS.aggregate(games, "alice");
  expect(entries).toHaveLength(2);
  const colors = entries.map((e) => e.color).sort();
  expect(colors).toEqual(["Blanc", "Noir"]);
});

test("aggregate trie par nombre de parties décroissant", () => {
  const games = [
    makeGame("Italienne",  "a", "b", "w"),
    makeGame("Sicilienne", "a", "b", "w"),
    makeGame("Sicilienne", "a", "b", "b"),
    makeGame("Sicilienne", "a", "b", "d"),
  ];
  const entries = OS.aggregate(games, "a");
  expect(entries[0].opening).toBe("Sicilienne");
  expect(entries[0].total).toBe(3);
});

test("aggregate ignore les parties sans username correspondant", () => {
  const games = [makeGame("Italienne", "x", "y", "w")];
  const entries = OS.aggregate(games, "alice");
  expect(entries).toHaveLength(0);
});

// ── computeRates ──────────────────────────────────────────────────

test("computeRates calcule les pourcentages corrects", () => {
  const e = { wins: 5, draws: 2, losses: 8, total: 15 };
  const { winPct, drawPct, lossPct } = OS.computeRates(e);
  expect(winPct).toBeCloseTo(33.3, 0);
  expect(drawPct).toBeCloseTo(13.3, 0);
  expect(lossPct).toBeCloseTo(53.3, 0);
});

test("computeRates retourne 0 si total = 0", () => {
  const { winPct, drawPct, lossPct } = OS.computeRates({ wins: 0, draws: 0, losses: 0, total: 0 });
  expect(winPct).toBe(0);
  expect(drawPct).toBe(0);
  expect(lossPct).toBe(0);
});

test("computeRates sum ≈ 100 pour 10/2/8", () => {
  const e = { wins: 10, draws: 2, losses: 8, total: 20 };
  const { winPct, drawPct, lossPct } = OS.computeRates(e);
  expect(winPct + drawPct + lossPct).toBeCloseTo(100, 0);
});

// ── renderTable (interne) ─────────────────────────────────────────

test("_renderTable retourne empty-state si aucune entrée", () => {
  const html = OS._renderTable([]);
  expect(html).toContain("empty-state");
});

test("_renderTable génère une ligne par entrée", () => {
  const entries = [
    { opening: "Sicilienne", color: "Blanc", wins: 5, draws: 2, losses: 3, total: 10 },
  ];
  const html = OS._renderTable(entries);
  expect(html).toContain("Sicilienne");
  expect(html).toContain("wdl-gauge");
  expect(html).toContain("Blanc");
});

// ── escapeHtml ────────────────────────────────────────────────────

test("_escapeHtml échappe les caractères HTML", () => {
  const escaped = OS._escapeHtml('<Test & "World">');
  expect(escaped).toContain("&lt;");
  expect(escaped).toContain("&amp;");
  expect(escaped).toContain("&quot;");
  expect(escaped).toContain("&gt;");
});

// ── render (point d'entrée public) ────────────────────────────────

test("render avec localStorage vide ne plante pas", async () => {
  await expect(OS.render("test-container")).resolves.toBeUndefined();
});

test("render avec parties en localStorage affiche le tableau", async () => {
  const games = [
    { pgn: '[Opening "Italienne"][White "alice"][Black "bob"]',
      white: { username: "alice", result: "win" },
      black: { username: "bob",   result: "checkmated" } },
  ];
  localStorage.setItem("ci_username", JSON.stringify("alice"));
  localStorage.setItem("ci_games", JSON.stringify(games));
  await expect(OS.render("test-container")).resolves.toBeUndefined();
});
