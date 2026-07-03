/**
 * Tests unitaires – ChessDB (IndexedDB wrapper) – US 0
 */

const ChessDB = require("../js/db.js");

beforeEach(() => {
  ChessDB._reset();
});

// ── Ouverture ──────────────────────────────────────────────────────

test("open() retourne une DB valide avec les 3 object stores", async () => {
  const db = await ChessDB.open();
  expect(db).toBeTruthy();
  expect(db.objectStoreNames.contains("games")).toBe(true);
  expect(db.objectStoreNames.contains("srs_cards")).toBe(true);
  expect(db.objectStoreNames.contains("openings_cache")).toBe(true);
});

// ── Games ──────────────────────────────────────────────────────────

test("saveGame() puis getAllGames() retourne la partie", async () => {
  const game = { game_id: "g1", pgn: "[Event\"\"]", accuracy: 72.5, date: "2026-01-01T00:00:00.000Z" };
  await ChessDB.saveGame(game);
  const all = await ChessDB.getAllGames();
  expect(all.length).toBe(1);
  expect(all[0].game_id).toBe("g1");
  expect(all[0].accuracy).toBe(72.5);
});

test("saveGame() ajoute la date si absente", async () => {
  const game = { game_id: "g2", pgn: "" };
  await ChessDB.saveGame(game);
  const all = await ChessDB.getAllGames();
  expect(all[0].date).toBeTruthy();
});

test("getAllGames() trie par date décroissante", async () => {
  await ChessDB.saveGame({ game_id: "old", date: "2025-01-01T00:00:00.000Z" });
  await ChessDB.saveGame({ game_id: "new", date: "2026-06-01T00:00:00.000Z" });
  const all = await ChessDB.getAllGames();
  expect(all[0].game_id).toBe("new");
  expect(all[1].game_id).toBe("old");
});

test("saveGame() met à jour une partie existante (upsert)", async () => {
  await ChessDB.saveGame({ game_id: "g3", accuracy: 50 });
  await ChessDB.saveGame({ game_id: "g3", accuracy: 80 });
  const all = await ChessDB.getAllGames();
  expect(all.length).toBe(1);
  expect(all[0].accuracy).toBe(80);
});

// ── SRS Cards ─────────────────────────────────────────────────────

test("saveCard() puis getAllCards() retourne la carte", async () => {
  const card = { id: "c1", fen: "startpos", ef: 2.5, interval: 1, reps: 0, due: "2026-06-29" };
  await ChessDB.saveCard(card);
  const all = await ChessDB.getAllCards();
  expect(all.length).toBe(1);
  expect(all[0].id).toBe("c1");
});

test("getDueCards() ne retourne que les cartes dues aujourd'hui ou avant", async () => {
  const today    = new Date().toISOString().split("T")[0];
  const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
  await ChessDB.saveCard({ id: "past",   due: "2020-01-01" });
  await ChessDB.saveCard({ id: "today",  due: today });
  await ChessDB.saveCard({ id: "future", due: tomorrow });
  const due = await ChessDB.getDueCards();
  const ids = due.map((c) => c.id);
  expect(ids).toContain("past");
  expect(ids).toContain("today");
  expect(ids).not.toContain("future");
});

test("getDueCards() trie par date croissante", async () => {
  await ChessDB.saveCard({ id: "b", due: "2020-06-01" });
  await ChessDB.saveCard({ id: "a", due: "2020-01-01" });
  const due = await ChessDB.getDueCards();
  expect(due[0].id).toBe("a");
});

// ── Openings Cache ────────────────────────────────────────────────

test("saveOpening() puis getOpening() retourne l'entrée", async () => {
  await ChessDB.saveOpening("rnbqkbnr w KQkq -", { name: "Sicilienne", moves: 5 });
  const entry = await ChessDB.getOpening("rnbqkbnr w KQkq -");
  expect(entry).toBeTruthy();
  expect(entry.name).toBe("Sicilienne");
  expect(entry.moves).toBe(5);
});

test("getOpening() retourne undefined pour une clé inconnue", async () => {
  const entry = await ChessDB.getOpening("inconnu");
  expect(entry).toBeUndefined();
});

// ── Migration ─────────────────────────────────────────────────────

test("migrateFromLocalStorage() migre les parties et les cartes", async () => {
  global.localStorage._store = {
    ci_games: JSON.stringify([
      { game_id: "ls_game_1", accuracy: 65, pgn: "" },
    ]),
    ci_srs_cards: JSON.stringify([
      { id: "ls_card_1", due: "2026-01-01", ef: 2.5, interval: 1, reps: 0 },
    ]),
  };

  await ChessDB.migrateFromLocalStorage();

  const games = await ChessDB.getAllGames();
  expect(games.some((g) => g.game_id === "ls_game_1")).toBe(true);

  const cards = await ChessDB.getAllCards();
  expect(cards.some((c) => c.id === "ls_card_1")).toBe(true);
});

test("migrateFromLocalStorage() ne migre pas deux fois", async () => {
  global.localStorage._store = {
    ci_games: JSON.stringify([{ game_id: "dup", accuracy: 70, pgn: "" }]),
    ci_idb_migrated: "1",
  };

  await ChessDB.migrateFromLocalStorage();
  const games = await ChessDB.getAllGames();
  expect(games.length).toBe(0);
});

// ── Livre d'ouvertures complet (EPIC 25, US 25.2) ──────────────────

describe("Opening book cache (TTL 7 jours)", () => {
  beforeEach(() => ChessDB._reset());

  test("getOpeningBook renvoie null si aucun cache", async () => {
    await ChessDB.open();
    expect(await ChessDB.getOpeningBook()).toBeNull();
  });

  test("saveOpeningBook puis getOpeningBook restitue les EPD", async () => {
    await ChessDB.open();
    await ChessDB.saveOpeningBook(["epd1", "epd2"]);
    expect(await ChessDB.getOpeningBook()).toEqual(["epd1", "epd2"]);
  });

  test("saveOpeningBook ignore les listes vides/invalides", async () => {
    await ChessDB.open();
    expect(await ChessDB.saveOpeningBook([])).toBeNull();
    expect(await ChessDB.saveOpeningBook(null)).toBeNull();
    expect(await ChessDB.getOpeningBook()).toBeNull();
  });

  test("une entrée périmée (TTL dépassé) est considérée absente", async () => {
    await ChessDB.open();
    await ChessDB._put("openings_cache", {
      epd: "__opening_book__",
      epds: ["vieux"],
      savedAt: Date.now() - ChessDB.OPENING_BOOK_TTL_MS - 1000,
    });
    expect(await ChessDB.getOpeningBook()).toBeNull();
  });

  test("isOpeningBookFresh : cas limites", () => {
    const now = 1000000;
    const fresh = { epds: ["x"], savedAt: now - 1 };
    const stale = { epds: ["x"], savedAt: now - ChessDB.OPENING_BOOK_TTL_MS - 1 };
    expect(ChessDB.isOpeningBookFresh(fresh, now)).toBe(true);
    expect(ChessDB.isOpeningBookFresh(stale, now)).toBe(false);
    expect(ChessDB.isOpeningBookFresh(null, now)).toBe(false);
    expect(ChessDB.isOpeningBookFresh({ epds: [], savedAt: now }, now)).toBe(false);
    expect(ChessDB.isOpeningBookFresh({ epds: ["x"] }, now)).toBe(false);
    expect(ChessDB.isOpeningBookFresh({ epds: "pas-un-tableau", savedAt: now }, now)).toBe(false);
  });

  test("le cache du livre ne pollue pas les entrées ECO individuelles", async () => {
    await ChessDB.open();
    await ChessDB.saveOpening("epd-individuelle", { name: "Sicilienne" });
    await ChessDB.saveOpeningBook(["a", "b"]);
    const single = await ChessDB.getOpening("epd-individuelle");
    expect(single.name).toBe("Sicilienne");
    expect(await ChessDB.getOpeningBook()).toEqual(["a", "b"]);
  });
});
