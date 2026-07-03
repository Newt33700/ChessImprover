/**
 * IndexedDB wrapper – Chess Improver
 * Tables : games | srs_cards | openings_cache
 * Migre silencieusement depuis localStorage au premier chargement.
 */

const DB_NAME    = "ChessImprover";
const DB_VERSION = 1;

const ChessDB = (() => {
  let _db = null;

  function open() {
    if (_db) return Promise.resolve(_db);
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);

      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains("games")) {
          const gs = db.createObjectStore("games", { keyPath: "game_id" });
          gs.createIndex("date", "date", { unique: false });
        }
        if (!db.objectStoreNames.contains("srs_cards")) {
          const sc = db.createObjectStore("srs_cards", { keyPath: "id" });
          sc.createIndex("due", "due", { unique: false });
        }
        if (!db.objectStoreNames.contains("openings_cache")) {
          db.createObjectStore("openings_cache", { keyPath: "epd" });
        }
      };

      req.onsuccess = (e) => { _db = e.target.result; resolve(_db); };
      req.onerror   = (e) => reject(e.target.error);
    });
  }

  function tx(store, mode = "readonly") {
    return open().then((db) => db.transaction(store, mode).objectStore(store));
  }

  function wrap(req) {
    return new Promise((res, rej) => {
      req.onsuccess = (e) => res(e.target.result);
      req.onerror   = (e) => rej(e.target.error);
    });
  }

  // ── Generic CRUD ────────────────────────────────────────────────

  async function put(store, record) {
    return wrap((await tx(store, "readwrite")).put(record));
  }

  async function get(store, key) {
    return wrap((await tx(store)).get(key));
  }

  async function getAll(store) {
    return wrap((await tx(store)).getAll());
  }

  async function remove(store, key) {
    return wrap((await tx(store, "readwrite")).delete(key));
  }

  // ── Games ────────────────────────────────────────────────────────

  async function saveGame(game) {
    if (!game.date) game.date = new Date().toISOString();
    return put("games", game);
  }

  async function getAllGames() {
    const games = await getAll("games");
    return games.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  }

  // ── SRS Cards ────────────────────────────────────────────────────

  async function saveCard(card) {
    return put("srs_cards", card);
  }

  async function getAllCards() {
    return getAll("srs_cards");
  }

  async function getDueCards() {
    const today = new Date().toISOString().split("T")[0];
    const cards = await getAllCards();
    return cards
      .filter((c) => !c.due || c.due <= today)
      .sort((a, b) => (a.due || "").localeCompare(b.due || ""));
  }

  // ── Openings Cache ────────────────────────────────────────────────

  async function saveOpening(epd, data) {
    return put("openings_cache", { epd, ...data });
  }

  async function getOpening(epd) {
    return get("openings_cache", epd);
  }

  // ── Livre d'ouvertures complet (EPIC 25, US 25.2 — gap §10.2 fermé) ──
  // Le Set d'EPD (~28k positions) était reparsé depuis les 5 TSV à chaque
  // refresh (~5 requêtes réseau + ~2s de chess.js). Il est désormais mis en
  // cache dans `openings_cache` sous une clé réservée, avec un TTL de 7 jours.

  const OPENING_BOOK_KEY = "__opening_book__";
  const OPENING_BOOK_TTL_MS = 7 * 24 * 3600 * 1000;

  /** Vrai si l'entrée de cache du livre est encore fraîche (TTL 7 jours). */
  function isOpeningBookFresh(entry, now = Date.now()) {
    return !!(entry
      && Array.isArray(entry.epds)
      && entry.epds.length > 0
      && typeof entry.savedAt === "number"
      && now - entry.savedAt < OPENING_BOOK_TTL_MS);
  }

  /** Liste d'EPD du livre en cache, ou `null` si absente/périmée/corrompue. */
  async function getOpeningBook() {
    try {
      const entry = await get("openings_cache", OPENING_BOOK_KEY);
      return isOpeningBookFresh(entry) ? entry.epds : null;
    } catch {
      return null;
    }
  }

  /** Persiste la liste d'EPD du livre (horodatée pour le TTL). Best-effort. */
  async function saveOpeningBook(epds) {
    if (!Array.isArray(epds) || !epds.length) return null;
    try {
      return await put("openings_cache", {
        epd: OPENING_BOOK_KEY,
        epds,
        savedAt: Date.now(),
      });
    } catch {
      return null;
    }
  }

  // ── Migration from localStorage ──────────────────────────────────

  async function migrateFromLocalStorage() {
    const migrated = localStorage.getItem("ci_idb_migrated");
    if (migrated) return;

    try {
      const KEYS = {
        GAMES:     "ci_games",
        SRS_CARDS: "ci_srs_cards",
      };

      const rawGames = localStorage.getItem(KEYS.GAMES);
      if (rawGames) {
        const games = JSON.parse(rawGames);
        if (Array.isArray(games)) {
          for (const g of games) {
            if (!g.game_id) g.game_id = `migrated_${Date.now()}_${Math.random()}`;
            if (!g.date)    g.date    = new Date().toISOString();
            await saveGame(g);
          }
        }
      }

      const rawCards = localStorage.getItem(KEYS.SRS_CARDS);
      if (rawCards) {
        const cards = JSON.parse(rawCards);
        if (Array.isArray(cards)) {
          for (const c of cards) {
            if (!c.id) c.id = `migrated_card_${Date.now()}_${Math.random()}`;
            await saveCard(c);
          }
        }
      }

      localStorage.setItem("ci_idb_migrated", "1");
    } catch (err) {
      console.warn("[ChessDB] migration partielle:", err);
    }
  }

  function _reset() { _db = null; }

  return {
    open,
    saveGame,
    getAllGames,
    saveCard,
    getAllCards,
    getDueCards,
    saveOpening,
    getOpening,
    getOpeningBook,
    saveOpeningBook,
    isOpeningBookFresh,
    OPENING_BOOK_TTL_MS,
    migrateFromLocalStorage,
    // exposed for tests
    _put: put,
    _get: get,
    _getAll: getAll,
    _remove: remove,
    _reset,
  };
})();

if (typeof window !== "undefined") window.ChessDB = ChessDB;
if (typeof module !== "undefined" && module.exports != null) module.exports = ChessDB;
