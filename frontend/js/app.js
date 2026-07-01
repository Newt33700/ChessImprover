/**
 * Chess Improver – Mode Standalone (déployable sans backend)
 * Toute la logique métier est portée en JS pur :
 *   - Parsing PGN via chess.js
 *   - Calcul Elo CAPS simplifié
 *   - Détection blunders géométrique
 *   - SM-2 SRS
 *   - XP / Streaks en LocalStorage
 *   - Sync Chess.com via API publique (CORS-friendly)
 */

// ═══════════════════════════════════════════════════════════════════
// Constantes
// ═══════════════════════════════════════════════════════════════════
const CHESS_COM_API = "https://api.chess.com/pub";

const STORAGE_KEYS = {
  XP: "ci_xp", LEVEL: "ci_level", STREAK: "ci_streak",
  LAST_ACTIVE: "ci_last_active", GAMES: "ci_games",
  SRS_CARDS: "ci_srs_cards", USERNAME: "ci_username",
};

const XP_PER_GAME     = 50;
const XP_PER_EXERCISE = 10;
const XP_PER_LEVEL    = (lvl) => lvl * 100;

// Calibré pour analyse depth-5 (moteur asm.js) : 100cp perte → ~74% précision
const DECAY = 0.003;

// ═══════════════════════════════════════════════════════════════════
// LocalStorage Store
// ═══════════════════════════════════════════════════════════════════
const Store = {
  get(k, fb = null) { try { const r = localStorage.getItem(k); return r !== null ? JSON.parse(r) : fb; } catch { return fb; } },
  set(k, v)         { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};

// ═══════════════════════════════════════════════════════════════════
// Logique Elo (portée depuis Python)
// ═══════════════════════════════════════════════════════════════════
const EloEngine = {
  movAccuracy(cpLoss) {
    return 100 * Math.exp(-DECAY * Math.abs(cpLoss));
  },

  gameAccuracy(scores) {
    if (!scores.length) return 0;
    return scores.reduce((a, b) => a + b, 0) / scores.length;
  },

  estimateElo(accuracy, opponentElo) {
    // Formule logistique : expectedScore → différence Elo → Elo estimé
    const es  = Math.max(0.001, Math.min(0.999, accuracy / 100));
    const adv = 400 * Math.log10(es / (1 - es));
    return Math.round(Math.max(400, Math.min(2800, opponentElo + adv)));
  },

  classify(score) {
    if (score >= 95) return "brilliant";
    if (score >= 85) return "excellent";
    if (score >= 70) return "good";
    if (score >= 50) return "inaccuracy";
    if (score >= 25) return "mistake";
    return "blunder";
  },
};

// ═══════════════════════════════════════════════════════════════════
// Analyse PGN côté client (chess.js)
// ═══════════════════════════════════════════════════════════════════
const PGNAnalyzer = {
  /**
   * Analyse géométrique d'une partie PGN.
   * Retourne { moves, blunders, opponentElo }
   */
  analyze(pgn) {
    const chess = new Chess();
    let blunders = 0;
    const moves = [];

    try {
      chess.load_pgn(pgn);
    } catch {
      return { moves: [], blunders: 0, opponentElo: 1000 };
    }

    // Extraire les headers
    const headers = chess.header();
    const whiteElo = parseInt(headers.WhiteElo) || 1000;
    const blackElo = parseInt(headers.BlackElo) || 1000;

    // Extraire les horloges [%clk H:MM:SS] présentes dans les commentaires PGN
    const CLK_RE = /\[%clk\s+(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)\]/g;
    const clocks = [];
    let clkM;
    while ((clkM = CLK_RE.exec(pgn)) !== null) {
      clocks.push(Math.round(parseInt(clkM[1]) * 3600 + parseInt(clkM[2]) * 60 + parseFloat(clkM[3])));
    }
    const tcMatch = pgn.match(/\[TimeControl\s+"(\d+)/);
    const initialTime = tcMatch ? parseInt(tcMatch[1]) : null;

    // Reconstruire coup par coup (sans évaluation moteur)
    const history = chess.history({ verbose: true });
    chess.reset();

    history.forEach((move, i) => {
      const clock = i < clocks.length ? clocks[i] : null;
      const prevSameColor = i >= 2 ? clocks[i - 2] : initialTime;
      const timeSpent = (prevSameColor != null && clock != null) ? Math.max(0, prevSameColor - clock) : null;
      chess.move(move);
      moves.push({
        san: move.san,
        from: move.from, to: move.to,
        color: move.color,
        accuracy_score: null,      // null = en attente Stockfish
        classification: "unknown",
        cpLoss: null,
        fen: chess.fen(),
        clock,
        timeSpent,
      });
    });

    return { moves, blunders: 0, opponentElo: blackElo };
  },

  /**
   * Détection des blunders réels depuis les évaluations Stockfish
   * (appelé depuis le callback du Web Worker)
   */
  updateWithStockfish(moves, topEvals, playedEvals) {
    return moves.map((m, i) => {
      if (topEvals[i] === undefined) return m;
      const cpLoss = Math.abs(topEvals[i] - (playedEvals[i] ?? topEvals[i]));
      const accuracy = EloEngine.movAccuracy(cpLoss);
      return { ...m, accuracy_score: parseFloat(accuracy.toFixed(1)), classification: EloEngine.classify(accuracy), cpLoss };
    });
  },
};

// ═══════════════════════════════════════════════════════════════════
// SRS SM-2 (JS pur)
// ═══════════════════════════════════════════════════════════════════
const SRS = {
  EF_MIN: 1.3,

  createCard(id, fen, solution) {
    return { id, fen, solution, ef: 2.5, interval: 1, reps: 0, due: new Date().toISOString().split("T")[0] };
  },

  review(card, quality) {
    const today = new Date().toISOString().split("T")[0];
    if (quality < 3) {
      return { ...card, reps: 0, interval: 1, due: today };
    }
    const delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02);
    const newEf = Math.max(this.EF_MIN, card.ef + delta);
    const newReps = card.reps + 1;
    let newInterval;
    if (newReps === 1) newInterval = 1;
    else if (newReps === 2) newInterval = 6;
    else newInterval = Math.max(1, Math.round(card.interval * newEf));

    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + newInterval);
    return { ...card, ef: parseFloat(newEf.toFixed(4)), reps: newReps, interval: newInterval, due: dueDate.toISOString().split("T")[0] };
  },

  getDue(cards) {
    const today = new Date().toISOString().split("T")[0];
    return cards.filter((c) => !c.due || c.due <= today).sort((a, b) => (a.due || "").localeCompare(b.due || ""));
  },

  load()        { return Store.get(STORAGE_KEYS.SRS_CARDS, []); },
  save(cards)   { Store.set(STORAGE_KEYS.SRS_CARDS, cards); },

  saveCard(card) {
    const cards = this.load();
    const idx = cards.findIndex((c) => c.id === card.id);
    if (idx >= 0) cards[idx] = card; else cards.push(card);
    this.save(cards);
    if (window.ChessDB) ChessDB.saveCard(card).catch(() => {});
  },
};

// ═══════════════════════════════════════════════════════════════════
// XP & Streaks
// ═══════════════════════════════════════════════════════════════════
const XPSystem = {
  get()           { return { xp: Store.get(STORAGE_KEYS.XP, 0), level: Store.get(STORAGE_KEYS.LEVEL, 1) }; },
  add(amount)     {
    let { xp, level } = this.get();
    xp += amount;
    while (xp >= XP_PER_LEVEL(level)) { xp -= XP_PER_LEVEL(level); level++; document.dispatchEvent(new CustomEvent("xp:levelup", { detail: { level } })); }
    Store.set(STORAGE_KEYS.XP, xp);
    Store.set(STORAGE_KEYS.LEVEL, level);
    return { xp, level };
  },
};

const StreakSystem = {
  today() { return new Date().toISOString().split("T")[0]; },
  daysDiff(a, b) { return Math.round(Math.abs(new Date(a) - new Date(b)) / 86400000); },
  get() { return Store.get(STORAGE_KEYS.STREAK, 0); },
  record() {
    const today = this.today();
    const last  = Store.get(STORAGE_KEYS.LAST_ACTIVE, null);
    let streak  = Store.get(STORAGE_KEYS.STREAK, 0);
    if (!last)              streak = 1;
    else if (last === today) return streak;
    else if (this.daysDiff(last, today) === 1) streak++;
    else streak = 1;
    Store.set(STORAGE_KEYS.STREAK, streak);
    Store.set(STORAGE_KEYS.LAST_ACTIVE, today);
    return streak;
  },
};

// ═══════════════════════════════════════════════════════════════════
// Chess.com API client (JS, CORS public)
// ═══════════════════════════════════════════════════════════════════
const ChessComClient = {
  async getRecentGames(username, limit = 15) {
    const now = new Date();
    const games = [];
    for (let delta = 0; delta < 3 && games.length < limit; delta++) {
      const d = new Date(now.getFullYear(), now.getMonth() - delta, 1);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      try {
        const res = await fetch(`${CHESS_COM_API}/player/${username}/games/${y}/${m}`, {
          headers: { "User-Agent": "ChessImprover/1.0" },
        });
        if (!res.ok) continue;
        const data = await res.json();
        games.push(...(data.games || []));
      } catch { /* réseau indisponible */ }
    }
    return games.slice(-limit).reverse();
  },

  async getStats(username) {
    try {
      const res = await fetch(`${CHESS_COM_API}/player/${username}/stats`);
      return res.ok ? res.json() : {};
    } catch { return {}; }
  },
};

// ═══════════════════════════════════════════════════════════════════
// Application principale
// ═══════════════════════════════════════════════════════════════════
class ChessImproverApp {
  constructor() {
    this.username    = Store.get(STORAGE_KEYS.USERNAME, "");
    this.boardMgr    = null;
    this.currentGame = null;
    this.recentGames = [];
    this.serverGames = []; // US 7.1 — parties déjà soumises/analysées côté serveur

    this._openingBookPromise = this._buildOpeningBook();
    this._initBoard();
    this._bindEvents();
    this._renderAll();

    if (this.username) {
      document.getElementById("username-input").value = this.username;
    }
  }

  // ─── Init ───────────────────────────────────────────────────────

  _initBoard() {
    this.boardMgr = new BoardManager(
      "board",
      (move, fen) => this._onPlayerMove(move, fen),
      (evalData)  => this._onEngineEval(evalData),
    );
    document.addEventListener("review:move",    (e) => this._onReviewMove(e.detail));
    document.addEventListener("exercise:result",(e) => this._onExerciseResult(e.detail));
    document.addEventListener("ghost:result",   (e) => this._onGhostResult(e.detail));
    document.addEventListener("move:accuracy",  (e) => this._onMoveAccuracy(e.detail));
    document.addEventListener("board:flip",     (e) => this._onBoardFlip(e.detail));
    document.addEventListener("xp:levelup",     (e) => this._toast(`🎉 Niveau ${e.detail.level} atteint !`, "success"));
  }

  _bindEvents() {
    document.getElementById("btn-connect")?.addEventListener("click",  () => this._connectUser());
    document.getElementById("username-input")?.addEventListener("keydown", (e) => { if (e.key === "Enter") this._connectUser(); });
    document.getElementById("btn-analyze")?.addEventListener("click",  () => this._analyzePGN());
    document.getElementById("btn-exercise")?.addEventListener("click", () => this._startExercise());
    document.getElementById("btn-prev")?.addEventListener("click",     () => this.boardMgr.prevMove());
    document.getElementById("btn-next")?.addEventListener("click",     () => this.boardMgr.nextMove());
    document.getElementById("btn-flip")?.addEventListener("click",     () => this.boardMgr.flipBoard());
    document.getElementById("games-list")?.addEventListener("click",   (e) => {
      const item = e.target.closest("[data-pgn]");
      if (item) { document.getElementById("pgn-input").value = item.dataset.pgn; this._openPgnModal(); }
    });
    document.getElementById("moves-list")?.addEventListener("click", (e) => {
      const item = e.target.closest("[data-move-index]");
      if (item) this.boardMgr.goToMove(parseInt(item.dataset.moveIndex, 10));
    });

    // PGN modal
    document.getElementById("btn-to-pgn")?.addEventListener("click",    () => this._openPgnModal());
    document.getElementById("btn-to-pgn-2")?.addEventListener("click",  () => this._openPgnModal());
    document.getElementById("btn-close-pgn")?.addEventListener("click", () => this._closePgnModal());
    document.getElementById("pgn-modal")?.addEventListener("click", (e) => {
      if (e.target === e.currentTarget) this._closePgnModal();
    });

    // Launch review from match card
    document.getElementById("btn-launch-review")?.addEventListener("click", () => {
      if (this.currentGame) this._enterReviewMode(this.currentGame);
    });

    // Auto-analyze button
    document.getElementById("btn-auto-analyze")?.addEventListener("click", () => this._showBilan());

    // Statistiques Avancées (EPIC 4) — cadence, période, deep-dive
    this._advCadence = "blitz";
    this._advPeriod = "30d";
    document.querySelectorAll("#adv-cadence-tabs .adv-cad-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#adv-cadence-tabs .adv-cad-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this._advCadence = btn.dataset.cad;
        if (window.AdvancedStats && this._advSummary) {
          AdvancedStats.renderDeepDive(document.getElementById("adv-deepdive"), this._advSummary, this._advCadence);
        }
        this._loadProgressChart();
      });
    });
    document.querySelectorAll("#adv-period .adv-period-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#adv-period .adv-period-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this._advPeriod = btn.dataset.period;
        this._loadAdvStats();
      });
    });
    // Deep-dive : clic sur une catégorie → vue détaillée (délégation, US 4.2)
    document.getElementById("adv-deepdive")?.addEventListener("click", (e) => {
      const item = e.target.closest(".dd-item");
      if (item) this._showCategoryDetail(item.dataset.cat);
    });
    document.getElementById("adv-detail")?.addEventListener("click", (e) => {
      if (e.target.closest("[data-detail-back]")) this._hideCategoryDetail();
    });
    // Toggles de séries du graphe de progression (US 5.1)
    document.getElementById("adv-progress-toggles")?.addEventListener("change", (e) => {
      const cb = e.target.closest("input[type=checkbox][data-key]");
      if (!cb || !this._progressChart) return;
      AdvancedStats.toggleProgressSeries(this._progressChart, cb.dataset.key, cb.checked);
    });

    // Legacy back buttons
    document.getElementById("btn-back-dashboard")?.addEventListener("click", () => this._goHome());

    // Tabs Dashboard (US 2, 5, 6)
    document.getElementById("btn-open-tabs")?.addEventListener("click", () => this._openTabs());
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => this._switchTab(btn.dataset.tab));
    });

    // Period selectors pour stats
    document.querySelectorAll(".period-btn2").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".period-btn2").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        if (window.StatsDashboard) StatsDashboard.render(parseInt(btn.dataset.days));
      });
    });

    // Auth modal — switch Login/Signup tabs
    document.querySelectorAll(".auth-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        // Scopé à #auth-modal : le profile-modal (US 6.3) réutilise aussi
        // la classe .auth-form et ne doit pas être affecté par ce toggle.
        document.querySelectorAll("#auth-modal .auth-form").forEach((f) => { f.hidden = true; });
        const target = document.getElementById(tab.dataset.form);
        if (target) target.hidden = false;
      });
    });

    // Fermer le modal auth en cliquant sur l'overlay
    document.getElementById("auth-modal")?.addEventListener("click", (e) => {
      if (e.target === e.currentTarget) this._closeAuthModal();
    });
  }

  // ─── Connexion Chess.com ────────────────────────────────────────

  async _connectUser(forceUsername) {
    const input = document.getElementById("username-input");
    const username = forceUsername || input?.value.trim();
    if (!username) return;
    this.username = username;
    Store.set(STORAGE_KEYS.USERNAME, username);
    this._setLoading(true, `Chargement des parties de ${username}…`);
    try {
      const games = await ChessComClient.getRecentGames(username, 20);
      this.recentGames = games;
      this._renderGamesList(games);
      this._renderReviewCard(games);
      this._toast(`${games.length} parties chargées ✓`, "success");
    } catch (err) {
      this._toast("Impossible de contacter Chess.com", "error");
    } finally {
      this._setLoading(false);
      this._renderAll();
    }
  }

  // ─── Analyse PGN ────────────────────────────────────────────────

  _analyzePGN() {
    const pgn = document.getElementById("pgn-input")?.value.trim();
    if (!pgn) { this._toast("Collez un PGN à analyser", "error"); return; }

    this._setLoading(true, "Analyse en cours…");
    setTimeout(() => {   // yielde le rendu avant le calcul
      try {
        const { moves, blunders, opponentElo } = PGNAnalyzer.analyze(pgn);
        if (!moves.length) { this._toast("PGN invalide ou vide", "error"); return; }

        const analysis = {
          game_id:            `manual_${Date.now()}`,
          pgn,
          accuracy:           null,   // calculé par Stockfish
          estimated_elo:      null,
          moves,
          blunders_count:     blunders,
          missed_forks_count: 0,
          time_panic_count:   0,
        };

        // Sauvegarde localStorage (compat) + IndexedDB
        const saved = Store.get(STORAGE_KEYS.GAMES, []);
        saved.unshift(analysis);
        Store.set(STORAGE_KEYS.GAMES, saved.slice(0, 100));
        if (window.ChessDB) {
          ChessDB.saveGame({ ...analysis, date: new Date().toISOString() }).catch(() => {});
        }
        this._syncToBackend(analysis);

        StreakSystem.record();
        const { xp, level } = XPSystem.add(XP_PER_GAME);
        this._renderXP(xp, level);

        this.currentGame = analysis;
        this._closePgnModal();
        this._enterReviewMode(analysis);
      } catch (err) {
        this._toast(`Erreur d'analyse : ${err.message}`, "error");
      } finally {
        this._setLoading(false);
      }
    }, 50);
  }

  // ─── Mode Review ────────────────────────────────────────────────

  _enterReviewMode(analysis) {
    this._hideBoardPanels();
    this.currentGame = analysis;

    // Détecter la couleur du joueur depuis les headers PGN
    this.playerColor = this._detectPlayerColor(analysis.pgn);

    this._showBoardActive();
    this._setModePill("Review");
    const prompt = document.getElementById("exercise-prompt");
    if (prompt) prompt.hidden = true;
    this._renderMovesList(analysis.moves);
    this._renderGameStats(analysis);
    this._renderReviewedButton();

    this.boardMgr.startReview(analysis.moves.map((m) => ({
      san: m.san, classification: m.classification, fen: m.fen, color: m.color,
    })));

    this._detectBookDepth(analysis.moves).then((depth) => {
      if (depth !== null) this.boardMgr.setBookDepth(depth);
    });

    // Orienter le board : joueur toujours en bas
    const shouldBeFlipped = this.playerColor === "b";
    if (shouldBeFlipped !== this.boardMgr.flipped) {
      this.boardMgr.flipBoard();   // émet board:flip → _onBoardFlip
    } else {
      this._updatePlayerBars(this.boardMgr.flipped);
    }

    // US 3 : analyse de finale asynchrone (ne bloque pas l'UI)
    this._runEndgameAnalysis(analysis);
  }

  _buildOpeningBook() {
    const base = "https://raw.githubusercontent.com/lichess-org/chess-openings/master/";
    const book = new Set();
    return Promise.all(["a", "b", "c", "d", "e"].map(async (f) => {
      try {
        const r = await fetch(`${base}${f}.tsv`);
        if (!r.ok) return;
        const text = await r.text();
        for (const line of text.split("\n").slice(1)) {
          const pgn = line.split("\t")[2]?.trim();
          if (!pgn) continue;
          const chess = new Chess();
          const tokens = pgn.split(/\s+/).filter((t) => t && !/^\d+\.?$/.test(t));
          for (const san of tokens) {
            if (!chess.move(san)) break;
            book.add(chess.fen().split(" ").slice(0, 4).join(" "));
          }
        }
      } catch { /* réseau indisponible, livre réduit */ }
    })).then(() => book);
  }

  async _detectBookDepth(moves) {
    const book = await this._openingBookPromise;
    if (!book?.size) return null;
    let depth = 0;
    for (const move of moves) {
      if (book.has(move.fen.split(" ").slice(0, 4).join(" "))) depth++;
      else break;
    }
    return depth;
  }

  _detectPlayerColor(pgn) {
    try {
      const chess = new Chess();
      chess.load_pgn(pgn || "");
      const h = chess.header();
      const user = (this.username || "").toLowerCase();
      if (!user) return "w";
      if ((h.White || "").toLowerCase() === user) return "w";
      if ((h.Black || "").toLowerCase() === user) return "b";
    } catch {}
    return "w";
  }

  _onBoardFlip({ flipped }) {
    this._updatePlayerBars(flipped);
    this._updateReviewClocks(this.boardMgr?.reviewIndex ?? -1);
  }

  _updatePlayerBars(flipped) {
    const pgn = this.currentGame?.pgn || "";
    let whiteName = "Blancs", blackName = "Noirs";
    try {
      const chess = new Chess();
      chess.load_pgn(pgn);
      const h = chess.header();
      whiteName = h.White || "Blancs";
      blackName = h.Black || "Noirs";
    } catch {}

    // Flipped = noir en bas ; sinon blanc en bas
    const bottomColor = flipped ? "b" : "w";
    const topColor    = flipped ? "w" : "b";
    const bottomName  = flipped ? blackName : whiteName;
    const topName     = flipped ? whiteName : blackName;

    const nameTop    = document.getElementById("name-top");
    const nameBottom = document.getElementById("name-bottom");
    const pieceTop   = document.getElementById("piece-top");
    const pieceBottom= document.getElementById("piece-bottom");

    if (nameTop)    nameTop.textContent    = topName;
    if (nameBottom) nameBottom.textContent = bottomName;
    if (pieceTop)   { pieceTop.className   = `player-piece-indicator ${topColor === "w" ? "white" : "black"}`; }
    if (pieceBottom){ pieceBottom.className= `player-piece-indicator ${bottomColor === "w" ? "white" : "black"}`; }
  }

  _showMoveBadge(san, cls, playerColor) {
    const badge = document.getElementById("move-badge");
    if (!badge) return;

    if (!san || !cls || cls === "unknown") {
      badge.classList.remove("visible");
      return;
    }

    // Destination square from SAN
    let dest;
    if (san === "O-O")     dest = playerColor === "w" ? "g1" : "g8";
    else if (san === "O-O-O") dest = playerColor === "w" ? "c1" : "c8";
    else {
      const clean = san.replace(/[+#]$/, "").replace(/=[QRBN]$/, "");
      dest = clean.slice(-2);
    }
    if (!/^[a-h][1-8]$/.test(dest)) { badge.classList.remove("visible"); return; }

    const fileIdx = dest.charCodeAt(0) - 97; // a=0 … h=7
    const rankIdx = parseInt(dest[1]) - 1;   // 1=0 … 8=7
    const flipped = this.boardMgr?.flipped || false;

    // Top-right corner of the destination square (as % of board-area)
    const left = (!flipped ? fileIdx + 1 : 8 - fileIdx) * 12.5;
    const top  = (!flipped ? 7 - rankIdx : rankIdx)     * 12.5;

    const icons = {
      book:       { bg: "#8b7355",              text: "B"  },
      brilliant:  { bg: "var(--col-brilliant)", text: "✦" },
      excellent:  { bg: "#5b8dd9",              text: "!!" },
      good:       { bg: "var(--col-good)",      text: "!"  },
      inaccuracy: { bg: "var(--col-inaccuracy)",text: "?!" },
      mistake:    { bg: "var(--col-mistake)",   text: "?"  },
      blunder:    { bg: "var(--col-blunder)",   text: "??" },
    };

    const icon = icons[cls];
    if (!icon) { badge.classList.remove("visible"); return; }

    badge.style.left       = `${left}%`;
    badge.style.top        = `${top}%`;
    badge.style.background = icon.bg;
    badge.textContent      = icon.text;
    badge.dataset.cls      = cls;

    badge.classList.remove("visible");
    requestAnimationFrame(() => badge.classList.add("visible"));
  }

  _onReviewMove({ index, move, color }) {
    document.querySelectorAll("[data-move-index]").forEach((el) =>
      el.classList.toggle("active", parseInt(el.dataset.moveIndex) === index));

    this._updateReviewClocks(index);

    this._showMoveBadge(move?.san, move?.classification, move?.color);

    const info = document.getElementById("move-info");
    if (!move) { if (info) info.innerHTML = ""; return; }

    const gameMove = this.currentGame?.moves?.[index];
    const timeSpent = gameMove?.timeSpent;
    const timeChip = timeSpent != null
      ? `<span class="move-time-chip">⏱ &minus;${this._formatClock(timeSpent)}</span>`
      : "";

    const cls = move.classification;
    const isBlunder = cls === "blunder" || cls === "mistake";
    const ghostBtn = isBlunder
      ? `<button class="btn btn--sm" style="margin-left:8px;background:var(--bg-500);border:1px solid var(--border);color:var(--text-secondary)"
           onclick="window.app?._startGhost(${index})">👻 Ghost</button>`
      : "";
    const clsLabel = cls && cls !== "unknown" && cls !== "book" ? `<span style="color:${color}">${cls.toUpperCase()}</span> &nbsp;` : "";
    const accLabel = move.accuracy_score != null ? ` &nbsp;·&nbsp; Précision : ${move.accuracy_score}%` : "";
    if (info) info.innerHTML =
      `<div class="move-info-main">${clsLabel}<strong>${move.san}</strong>${accLabel}${ghostBtn}</div>${timeChip}`;
    document.querySelector(`[data-move-index="${index}"]`)?.scrollIntoView({ block: "nearest" });
  }

  _formatClock(secs) {
    if (secs == null) return "—";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  _setPlayerClock(color, secs) {
    const flipped     = this.boardMgr?.flipped || false;
    const bottomColor = flipped ? "b" : "w";
    const id  = color === bottomColor ? "clock-bottom" : "clock-top";
    const el  = document.getElementById(id);
    if (!el) return;
    el.textContent = this._formatClock(secs);
    el.className = "player-clock" +
      (secs != null && secs < 10 ? " critical" : secs != null && secs < 30 ? " low" : "");
  }

  _updateReviewClocks(index) {
    const moves = this.currentGame?.moves || [];
    const pgn   = this.currentGame?.pgn || "";
    const tcM   = pgn.match(/\[TimeControl\s+"(\d+)/);
    const initialTime = tcM ? parseInt(tcM[1]) : null;

    if (index < 0) {
      this._setPlayerClock("w", initialTime);
      this._setPlayerClock("b", initialTime);
      return;
    }

    let wClock = initialTime, bClock = initialTime;
    for (let i = 0; i <= index; i++) {
      if (!moves[i]) continue;
      if (moves[i].color === "w" && moves[i].clock != null) wClock = moves[i].clock;
      if (moves[i].color === "b" && moves[i].clock != null) bClock = moves[i].clock;
    }
    this._setPlayerClock("w", wClock);
    this._setPlayerClock("b", bClock);
  }

  // ─── Mode Exercice ──────────────────────────────────────────────

  async _startExercise() {
    let due = [];
    if (window.ChessDB) {
      due = await ChessDB.getDueCards().catch(() => []);
    }
    if (!due.length) {
      due = SRS.getDue(SRS.load());
    }
    if (!due.length) { this._toast("✅ Aucune révision aujourd'hui !", "info"); return; }
    const card = due[0];
    this._hideBoardPanels();
    this._showBoardActive();
    this._setModePill("Exercice");

    // PV peut être un tableau UCI (US 4) ou une chaîne SAN (ancien format)
    const pv = card.solution;
    const chess = new Chess();
    let playerColor = "w";
    try { chess.load(card.fen); playerColor = chess.turn(); } catch {}

    this.boardMgr.startExercise(card.fen, pv, playerColor);
    const prompt = document.getElementById("exercise-prompt");
    if (prompt) { prompt.textContent = "🎯 Trouvez le meilleur coup !"; prompt.hidden = false; }
    this._currentCard = card;
  }

  _onExerciseResult({ correct, played, solution, quality }) {
    const q = quality !== undefined ? quality : (correct ? 5 : 1);
    if (correct) {
      this._toast(q >= 5 ? "✅ Excellent !" : "👍 Bien joué !", "success");
      const { xp, level } = XPSystem.add(q >= 5 ? XP_PER_EXERCISE : Math.round(XP_PER_EXERCISE / 2));
      this._renderXP(xp, level);
      if (this._currentCard) {
        SRS.saveCard(SRS.review(this._currentCard, q));
      }
    } else {
      this._toast(`❌ Raté. La solution était ${solution}`, "error");
      if (this._currentCard) SRS.saveCard(SRS.review(this._currentCard, 1));
    }
  }

  // ─── Précision Stockfish ────────────────────────────────────────

  _onMoveAccuracy({ moveIdx, cpLoss, book, evalCp }) {
    const game = this.currentGame;
    if (!game?.moves[moveIdx]) return;
    const classification = book ? "book" : EloEngine.classify(EloEngine.movAccuracy(cpLoss));
    const accuracy_score = book ? 100 : parseFloat(EloEngine.movAccuracy(cpLoss).toFixed(1));
    game.moves[moveIdx]  = { ...game.moves[moveIdx], cpLoss, accuracy_score, classification };

    // Stocker l'évaluation absolue (cp du point de vue des Blancs) pour le graphe WP
    if (evalCp !== undefined && evalCp !== null) {
      game.moves[moveIdx].evalCp = evalCp;
      if (window.WPChart) WPChart.updateMove(moveIdx, evalCp);
    }

    this._updateMoveItem(moveIdx, game.moves[moveIdx]);
    this._updateGameAccuracy();

    // US 4 : créer automatiquement une carte SRS pour les gaffes
    if (classification === "blunder" && moveIdx > 0) {
      const prevFen  = game.moves[moveIdx - 1].fen;
      const prevFenEntry = this.boardMgr?.evalCache?.[prevFen];
      const pv = prevFenEntry?.pv || [];
      if (pv.length >= 1) {
        const cardId = `blunder_${game.game_id || Date.now()}_${moveIdx}`;
        const existing = SRS.load().find((c) => c.id === cardId);
        if (!existing) {
          const card = SRS.createCard(cardId, prevFen, pv);
          SRS.saveCard(card);
        }
      }
    }

    // Sync reviewMoves pour que la navigation garde la bonne classification
    if (this.boardMgr?.reviewMoves?.[moveIdx]) {
      this.boardMgr.reviewMoves[moveIdx].classification = classification;
    }
    // Mettre à jour le badge si ce coup est actuellement affiché
    if (this.boardMgr?.reviewIndex === moveIdx) {
      const m = this.boardMgr.reviewMoves[moveIdx];
      this._showMoveBadge(m?.san, classification, m?.color);
    }
  }

  _updateGameAccuracy() {
    const moves  = this.currentGame?.moves || [];
    const scored = moves.filter((m) => m.accuracy_score != null);
    if (!scored.length) return;
    const accuracy = EloEngine.gameAccuracy(scored.map((m) => m.accuracy_score));
    // Elo estimé sur les parties de l'adversaire
    let oppElo = 1000;
    try {
      const chess = new Chess(); chess.load_pgn(this.currentGame.pgn);
      const h = chess.header();
      oppElo = parseInt(h.BlackElo) || parseInt(h.WhiteElo) || 1000;
    } catch {}
    this.currentGame.accuracy        = parseFloat(accuracy.toFixed(1));
    this.currentGame.estimated_elo   = EloEngine.estimateElo(accuracy, oppElo);
    this.currentGame.blunders_count  = moves.filter((m) => m.classification === "blunder").length;
    this._renderGameStats(this.currentGame);
  }

  // ─── Mode Ghost ─────────────────────────────────────────────────

  _startGhost(blunderIndex) {
    const game = this.currentGame;
    if (!game || !game.moves) return;

    // Reconstruit la partie pour extraire les FEN et les coups adverses
    const chess = new Chess();
    const moves = game.moves;

    // Couleur du joueur détectée depuis les headers PGN (corrige le bug hardcodé)
    const playerColor = this.playerColor || "w";

    // FEN 3 coups avant le blunder (min index 0)
    const startIndex = Math.max(0, blunderIndex - 3);

    // Reconstruire jusqu'à startIndex
    chess.reset();
    for (let i = 0; i < startIndex; i++) {
      chess.move(moves[i].san);
    }
    const startFen = chess.fen();

    // Collecter les coups adverses depuis startIndex jusqu'à la fin
    const opponentTurn = playerColor === "w" ? "b" : "w";
    const opponentMoves = [];
    for (let i = startIndex; i < moves.length; i++) {
      if (moves[i].color === opponentTurn) {
        opponentMoves.push(moves[i].san);
      }
    }

    this._showBoardActive();
    this._setModePill("Ghost");
    this.boardMgr.startGhost(startFen, opponentMoves, playerColor);

    const prompt = document.getElementById("exercise-prompt");
    if (prompt) { prompt.textContent = "👻 Battez votre passé !"; prompt.hidden = false; }

    this._toast("Mode Ghost : corrigez votre gaffe !", "info");
  }

  _onGhostResult({ success, evaluation }) {
    if (success) {
      this._toast(`🎉 Vous avez battu votre passé ! (+${(evaluation/100).toFixed(2)})`, "success");
      const { xp, level } = XPSystem.add(XP_PER_EXERCISE * 2);
      this._renderXP(xp, level);
      StreakSystem.record();
    } else {
      this._toast(`👻 Raté — éval finale : ${(evaluation/100).toFixed(2)}`, "error");
    }
  }

  // ─── US 1 : Bilan (WP Chart) ────────────────────────────────────

  _showBilan() {
    this._showBoardActive();
    // Masquer board-layout, afficher panel-bilan dans la même section-board
    const boardLayout = document.querySelector(".board-layout");
    const allPanels   = document.querySelectorAll(".analysis-panel");
    const bilanPanel  = document.getElementById("panel-bilan");

    allPanels.forEach((p) => { p.hidden = true; });
    if (boardLayout) boardLayout.hidden = true;
    if (bilanPanel) bilanPanel.hidden = false;

    this._setModePill("Bilan");

    if (!this.currentGame || !window.WPChart) return;

    const moves = this.currentGame.moves || [];
    WPChart.render("wp-chart-canvas", moves, (idx) => {
      if (boardLayout) boardLayout.hidden = false;
      bilanPanel.hidden = true;
      this._enterReviewMode(this.currentGame);
      setTimeout(() => this.boardMgr.goToMove(idx), 100);
    });
  }

  _hideBoardPanels() {
    document.querySelectorAll(".analysis-panel").forEach((p) => { p.hidden = true; });
    const boardLayout = document.querySelector(".board-layout");
    if (boardLayout) boardLayout.hidden = false;
  }

  // ─── US 3 : Finales ─────────────────────────────────────────────

  _showEndgame() {
    this._showBoardActive();
    const boardLayout  = document.querySelector(".board-layout");
    const allPanels    = document.querySelectorAll(".analysis-panel");
    const endgamePanel = document.getElementById("panel-endgame");
    allPanels.forEach((p) => { p.hidden = true; });
    if (boardLayout)  boardLayout.hidden  = true;
    if (endgamePanel) endgamePanel.hidden = false;
    this._setModePill("Finales");
  }

  async _runEndgameAnalysis(analysis) {
    if (!window.EndgameDetector || !analysis?.moves?.length) return;
    try {
      const results = await EndgameDetector.analyzeGame(
        analysis.moves,
        this.playerColor || "w",
      );
      analysis.endgame_accuracy = results.endgameAvgAccuracy;
      if (results.syzygyBlunders?.length) {
        analysis.syzygy_blunders = results.syzygyBlunders.length;
      }
      if (window.ChessDB && analysis.game_id) {
        ChessDB.saveGame({ ...analysis, date: analysis.date || new Date().toISOString() }).catch(() => {});
      }
      // Peupler le panel si actuellement affiché
      const panel = document.getElementById("panel-endgame");
      if (panel && !panel.hidden) {
        EndgameDetector.renderStats(results, "endgame-stats-container");
      }
    } catch { /* Syzygy indisponible, on continue */ }
  }

  async _renderEndgameTab() {
    const container = document.getElementById("endgame-global-container");
    if (!container) return;
    let games = [];
    try {
      games = window.ChessDB
        ? await ChessDB.getAllGames()
        : JSON.parse(localStorage.getItem("ci_games") || "[]");
    } catch {}
    const withData = games.filter((g) => g.endgame_accuracy != null);
    if (!withData.length) {
      container.innerHTML = `<p class="empty-state">Aucune donnée de finale disponible.<br>Analysez des parties pour obtenir vos statistiques.</p>`;
      return;
    }
    const avgAcc   = withData.reduce((s, g) => s + g.endgame_accuracy, 0) / withData.length;
    const blunders = games.reduce((s, g) => s + (g.syzygy_blunders || 0), 0);
    container.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-value">${avgAcc.toFixed(1)}%</div><div class="stat-label">Précision finale (moy.)</div></div>
        <div class="stat-card"><div class="stat-value">${withData.length}</div><div class="stat-label">Parties analysées</div></div>
        <div class="stat-card"><div class="stat-value">${blunders}</div><div class="stat-label">Gaffes Syzygy</div></div>
      </div>
      <p class="empty-state" style="margin-top:var(--space-md)">L'analyse Syzygy se lance automatiquement lors de la revue d'une partie.</p>`;
  }

  async _renderPuzzleTab() {
    const container = document.getElementById("puzzle-tab-container");
    if (!container) return;
    let due = [];
    if (window.ChessDB) due = await ChessDB.getDueCards().catch(() => []);
    if (!due.length)    due = SRS.getDue(SRS.load());
    if (!due.length) {
      container.innerHTML = `
        <div class="empty-state">
          <p>✅ Aucune révision en attente !</p>
          <p style="margin-top:var(--space-sm);color:var(--text-muted)">Les puzzles sont créés automatiquement à partir de vos gaffes.</p>
        </div>`;
      return;
    }
    container.innerHTML = `
      <div class="puzzle-tab-header">
        <p><strong>${due.length}</strong> révision${due.length > 1 ? "s" : ""} en attente</p>
        <button class="btn btn--accent" id="btn-start-puzzle">🧠 Commencer</button>
      </div>
      <div class="puzzle-list">
        ${due.slice(0, 8).map((c, i) => `
          <div class="puzzle-item">
            <span class="puzzle-num">#${i + 1}</span>
            <span class="puzzle-due">Due : ${c.due || "maintenant"}</span>
          </div>`).join("")}
      </div>`;
    document.getElementById("btn-start-puzzle")?.addEventListener("click", () => {
      this._startExercise();
      this._showSection("section-board");
    });
  }

  // ─── Auth (US 7) ────────────────────────────────────────────────

  _renderAuthState() {
    const el = document.getElementById("current-user");
    if (!el) return;
    const user = window.Auth?.getUser();
    if (user) {
      el.innerHTML = `<span class="auth-username">${user.username}</span>
        <button class="btn btn--sm btn--ghost auth-profile-btn">Profil</button>
        <button class="btn btn--sm btn--ghost auth-logout-btn">Déconnexion</button>`;
      el.querySelector(".auth-profile-btn")?.addEventListener("click", () => this._openProfileModal());
      el.querySelector(".auth-logout-btn")?.addEventListener("click", () => this._onAuthLogout());
    } else {
      el.innerHTML = `<button class="btn btn--sm btn--secondary" id="btn-open-auth">Connexion</button>`;
      el.querySelector("#btn-open-auth")?.addEventListener("click", () => this._openAuthModal());
    }
  }

  _openAuthModal() {
    const modal = document.getElementById("auth-modal");
    if (modal) modal.hidden = false;
  }

  _closeAuthModal() {
    const modal = document.getElementById("auth-modal");
    if (modal) modal.hidden = true;
    ["login-error", "signup-error"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) { el.textContent = ""; el.hidden = true; }
    });
  }

  async _submitLogin(event) {
    event.preventDefault();
    if (!window.Auth) return;
    const email    = document.getElementById("login-email")?.value.trim();
    const password = document.getElementById("login-password")?.value;
    try {
      const data = await Auth.login(email, password);
      this._onAuthSuccess(data.user);
    } catch (err) {
      const el = document.getElementById("login-error");
      if (el) { el.textContent = err.message; el.hidden = false; }
    }
  }

  async _submitSignup(event) {
    event.preventDefault();
    if (!window.Auth) return;
    const email       = document.getElementById("signup-email")?.value.trim();
    const username    = document.getElementById("signup-username")?.value.trim();
    const chessUser   = document.getElementById("signup-chess-username")?.value.trim();
    const password    = document.getElementById("signup-password")?.value;
    try {
      const data = await Auth.signup(email, username, password);
      let profileUser = data.user;
      if (chessUser) {
        Store.set(STORAGE_KEYS.USERNAME, chessUser);
        this.username = chessUser;
        const input = document.getElementById("username-input");
        if (input) input.value = chessUser;
        // Persiste le pseudo Chess.com sur le profil (US 6.3) ; un format
        // invalide ne doit jamais bloquer une inscription déjà réussie.
        try {
          profileUser = await Auth.updateChessUsername(chessUser);
        } catch { /* le compte est créé ; l'utilisateur pourra corriger via son profil */ }
      }
      this._onAuthSuccess(profileUser);
    } catch (err) {
      const el = document.getElementById("signup-error");
      if (el) { el.textContent = err.message; el.hidden = false; }
    }
  }

  // ─── Profil : liaison Chess.com (US 6.3) ────────────────────────

  _openProfileModal() {
    const input = document.getElementById("profile-chess-username");
    if (input) input.value = window.Auth?.getUser()?.chess_username || "";
    const modal = document.getElementById("profile-modal");
    if (modal) modal.hidden = false;
    const form = document.getElementById("profile-form");
    if (form) form.hidden = false;
  }

  _closeProfileModal() {
    const modal = document.getElementById("profile-modal");
    if (modal) modal.hidden = true;
    ["profile-error", "profile-success"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) { el.textContent = ""; el.hidden = true; }
    });
  }

  async _submitProfile(event) {
    event.preventDefault();
    if (!window.Auth) return;
    const chessUser = document.getElementById("profile-chess-username")?.value.trim();
    const errorEl   = document.getElementById("profile-error");
    const successEl = document.getElementById("profile-success");
    if (errorEl)   { errorEl.hidden = true; }
    if (successEl) { successEl.hidden = true; }
    try {
      await Auth.updateChessUsername(chessUser);
      if (chessUser) {
        Store.set(STORAGE_KEYS.USERNAME, chessUser);
        this.username = chessUser;
        const input = document.getElementById("username-input");
        if (input) input.value = chessUser;
      }
      if (successEl) { successEl.textContent = "Pseudo Chess.com mis à jour."; successEl.hidden = false; }
    } catch (err) {
      if (errorEl) { errorEl.textContent = err.message; errorEl.hidden = false; }
    }
  }

  _onAuthSuccess(user) {
    this._closeAuthModal();
    this._toast(`Bienvenue ${user.username} !`, "success");
    this._renderAuthState();
    this._loadServerGames();
    // Auto-charger les parties Chess.com si un username est mémorisé
    if (this.username && !this.recentGames.length) {
      const input = document.getElementById("username-input");
      if (input) input.value = this.username;
      this._connectUser(this.username);
    }
  }

  /**
   * Récupère la liste des parties déjà soumises/analysées côté serveur
   * (US 7.1), pour permettre plus tard d'éviter de re-soumettre une partie
   * déjà connue (US 7.2). Best-effort : n'affecte jamais le reste du
   * chargement du dashboard en cas d'échec.
   */
  async _loadServerGames() {
    if (!window.ApiClient || !ApiClient.isConfigured()) return;
    this._setLoading(true, "Chargement de vos parties…");
    try {
      const data = await ApiClient.getGames();
      this.serverGames = data?.games || [];
    } catch {
      this.serverGames = [];
    } finally {
      this._setLoading(false);
    }
  }

  _onAuthLogout() {
    window.Auth?.logout();
    this._renderAuthState();
    this._toast("Déconnecté", "info");
  }

  // ─── Tabs Dashboard (US 2, 5, 6) ────────────────────────────────

  _openTabs() {
    const sections = ["section-dashboard","section-pgn","section-board","section-tabs"];
    sections.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.hidden = id !== "section-tabs";
    });
    this._switchTab("tab-openings");
  }

  _switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-content").forEach((c) => {
      c.hidden = c.id !== tabId;
    });

    if (tabId === "tab-openings" && window.OpeningsStats) {
      OpeningsStats.render("openings-global-container");
    }
    if (tabId === "tab-stats" && window.StatsDashboard) {
      StatsDashboard.render(7, "elo-chart-canvas2", "acc-chart-canvas2");
    }
    if (tabId === "tab-coach" && window.PersonalCoach) {
      PersonalCoach.render("coach-diagnosis2");
    }
    if (tabId === "tab-endgame") {
      this._renderEndgameTab();
    }
    if (tabId === "tab-puzzle") {
      this._renderPuzzleTab();
    }
  }

  // ─── Moteur Stockfish ────────────────────────────────────────────

  _onPlayerMove(move, fen) {
    const t = document.getElementById("turn-indicator");
    if (t) t.textContent = this.boardMgr.chess.turn() === "w" ? "Blancs" : "Noirs";
  }

  _onEngineEval({ evaluation, fen }) {
    const el = document.getElementById("engine-eval");
    if (el) {
      const cp = evaluation;
      el.textContent = cp >= 0 ? `+${(cp/100).toFixed(2)}` : `${(cp/100).toFixed(2)}`;
      el.className = `engine-eval ${cp >= 0 ? "positive" : "negative"}`;
    }
    document.dispatchEvent(new CustomEvent("engine:eval", { detail: { fen, evaluation } }));

    // Mettre à jour la classification du coup correspondant à ce FEN
    if (this.currentGame) {
      const idx = this.currentGame.moves.findIndex((m) => m.fen === fen);
      if (idx >= 0 && this.currentGame.moves[idx].cpLoss == null) {
        // On n'a que l'éval après le coup ; on compare avec l'éval précédente si dispo
        const prevFen = idx > 0 ? this.currentGame.moves[idx - 1].fen : null;
        const prevEval = prevFen ? this.boardMgr.evalCache[prevFen]?.evaluation : null;
        if (prevEval != null) {
          const cpLoss = Math.max(0, prevEval - evaluation);
          const accuracy = EloEngine.movAccuracy(cpLoss);
          const classification = EloEngine.classify(accuracy);
          this.currentGame.moves[idx] = {
            ...this.currentGame.moves[idx],
            cpLoss, accuracy_score: parseFloat(accuracy.toFixed(1)), classification,
          };
          this._updateMoveItem(idx, this.currentGame.moves[idx]);
        }
      }
    }
  }

  _updateMoveItem(index, move) {
    const el = document.querySelector(`[data-move-index="${index}"]`);
    if (!el) return;
    const colorVar = {
      book:"var(--text-muted)",
      brilliant:"var(--col-brilliant)", excellent:"var(--col-excellent)",
      good:"var(--col-good)", inaccuracy:"var(--col-inaccuracy)",
      mistake:"var(--col-mistake)", blunder:"var(--col-blunder)",
    };
    const icons = { book:"", brilliant:"✦", excellent:"!", good:"", inaccuracy:"?!", mistake:"?", blunder:"??" };
    const col  = colorVar[move.classification] || "var(--text-muted)";
    const icon = icons[move.classification] ?? "";
    el.style.borderLeftColor = col;
    const iconEl = el.querySelector(".move-icon");
    if (iconEl) { iconEl.textContent = icon; iconEl.style.color = col; }
  }

  // ─── Rendu UI ───────────────────────────────────────────────────

  _renderReviewCard(games) {
    if (!games || !games.length) return;
    const last = games[0];
    const myColor = last.white?.username?.toLowerCase() === this.username?.toLowerCase() ? "white" : "black";
    const me  = myColor === "white" ? last.white : last.black;
    const opp = myColor === "white" ? last.black : last.white;

    const result = me?.result;
    const isWin  = result === "win";
    const isDraw = ["agreed","stalemate","repetition","insufficient","50move","timevsinsufficient"].includes(result);
    const score  = isWin ? (myColor === "white" ? "1–0" : "0–1") : isDraw ? "½–½" : (myColor === "white" ? "0–1" : "1–0");

    const myName  = me?.username  || (myColor === "white" ? "Blancs" : "Noirs");
    const oppName = opp?.username || (myColor === "white" ? "Noirs"  : "Blancs");
    const myAcc   = me?.accuracy  ?? null;
    const oppAcc  = opp?.accuracy ?? null;

    // Set match card fields
    const el = (id) => document.getElementById(id);
    const whiteName = myColor === "white" ? myName  : oppName;
    const blackName = myColor === "white" ? oppName : myName;
    if (el("name-white"))      el("name-white").textContent      = whiteName;
    if (el("name-black"))      el("name-black").textContent      = blackName;
    if (el("head-name-white")) el("head-name-white").textContent = whiteName;
    if (el("head-name-black")) el("head-name-black").textContent = blackName;
    if (el("match-score"))   el("match-score").textContent   = score;
    if (el("prec-bar-white")) el("prec-bar-white").style.width = `${myColor === "white" ? (myAcc ?? 0) : (oppAcc ?? 0)}%`;
    if (el("prec-bar-black")) el("prec-bar-black").style.width = `${myColor === "white" ? (oppAcc ?? 0) : (myAcc ?? 0)}%`;
    if (el("prec-val-white")) el("prec-val-white").textContent = myColor === "white" ? (myAcc != null ? `${myAcc}%` : "—") : (oppAcc != null ? `${oppAcc}%` : "—");
    if (el("prec-val-black")) el("prec-val-black").textContent = myColor === "white" ? (oppAcc != null ? `${oppAcc}%` : "—") : (myAcc != null ? `${myAcc}%` : "—");

    // Pre-load PGN so "Lancer la Révision" works immediately
    if (last.pgn) {
      const analysis = PGNAnalyzer.analyze(last.pgn);
      if (analysis.moves.length) {
        this.currentGame = { game_id: last.uuid || `chess_${Date.now()}`, pgn: last.pgn, ...analysis, blunders_count: 0, accuracy: null, estimated_elo: null };
      }
    }

    // Show the match card, hide connect prompt
    const prompt = document.getElementById("connect-prompt");
    const preview = document.getElementById("last-game-preview");
    if (prompt)  prompt.hidden  = true;
    if (preview) preview.hidden = false;
  }

  async _renderExerciseCard() {
    const container = document.getElementById("exercise-preview-card");
    if (!container) return;
    let due = [];
    if (window.ChessDB) due = await ChessDB.getDueCards().catch(() => []);
    if (!due.length) due = SRS.getDue(SRS.load());
    if (!due.length) {
      container.innerHTML = `<p class="empty-state">Aucun exercice disponible. Analysez des parties pour en générer.</p>`;
      return;
    }
    container.innerHTML = `
      <div class="exercise-preview-inner">
        <span class="exercise-theme-badge">SRS</span>
        <p class="exercise-preview-label"><strong>${due.length}</strong> révision${due.length > 1 ? "s" : ""} en attente</p>
        <button class="btn btn--accent btn--full" onclick="window.app?._startExercise()">Résoudre</button>
      </div>`;
  }

  _renderBilanChart(mode = "progress") {
    const canvas = document.getElementById("bilan-canvas");
    if (!canvas || !window.Chart) return;

    // Update toggle buttons
    document.getElementById("bilan-btn-progress")?.classList.toggle("active", mode === "progress");
    document.getElementById("bilan-btn-elo")?.classList.toggle("active", mode === "elo");

    const games = Store.get(STORAGE_KEYS.GAMES, []).slice(0, 10).reverse();
    if (!games.length) return;

    if (this._bilanChart) { this._bilanChart.destroy(); this._bilanChart = null; }

    const labels = games.map((_, i) => `P${i + 1}`);

    let datasets;
    if (mode === "progress") {
      datasets = [
        {
          label: "Gaffes",
          data: games.map((g) => g.blunders_count || 0),
          borderColor: "#e04444",
          backgroundColor: "rgba(224,68,68,0.12)",
          tension: 0.3,
          fill: true,
        },
        {
          label: "Coups manqués",
          data: games.map((g) => g.missed_forks_count || 0),
          borderColor: "#e09a44",
          backgroundColor: "rgba(224,154,68,0.10)",
          tension: 0.3,
          fill: true,
        },
      ];
    } else {
      datasets = [
        {
          label: "Elo estimé",
          data: games.map((g) => g.estimated_elo || null),
          borderColor: "#81b64c",
          backgroundColor: "rgba(129,182,76,0.12)",
          tension: 0.3,
          fill: true,
        },
      ];
    }

    this._bilanChart = new Chart(canvas, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#888", font: { size: 10 } } },
          y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#888", font: { size: 10 } } },
        },
      },
    });
  }

  _renderAll() {
    const { xp, level } = XPSystem.get();
    this._renderXP(xp, level);
    this._renderStreak(StreakSystem.get());
    this._renderStats();
    this._renderAuthState();
    this._renderBilanChart("progress");
    this._renderExerciseCard();
    if (this.recentGames.length) {
      this._renderGamesList(this.recentGames);
      this._renderReviewCard(this.recentGames);
    }
  }

  _renderXP(xp, level) {
    const needed = XP_PER_LEVEL(level);
    const pct    = Math.min(100, (xp / needed) * 100);
    const xpEl   = document.getElementById("xp-display");
    const lvlEl  = document.getElementById("level-display");
    const barEl  = document.getElementById("xp-bar");
    if (xpEl)  xpEl.textContent  = `${xp} XP`;
    if (lvlEl) lvlEl.textContent = `Niv. ${level}`;
    if (barEl) barEl.style.width = `${pct}%`;
  }

  _renderStreak(streak) {
    const el = document.getElementById("streak-display");
    if (el) el.innerHTML = `🔥 <strong>${streak}</strong>`;
  }

  _renderStats() {
    const games     = Store.get(STORAGE_KEYS.GAMES, []);
    const totalEl   = document.getElementById("stat-games");
    const accEl     = document.getElementById("stat-accuracy");
    const blEl      = document.getElementById("stat-blunders");
    if (totalEl) totalEl.textContent = games.length;
    if (games.length) {
      const avg = games.reduce((s, g) => s + (g.accuracy || 0), 0) / games.length;
      if (accEl) accEl.textContent = `${avg.toFixed(1)}%`;
      const tot = games.reduce((s, g) => s + (g.blunders_count || 0), 0);
      if (blEl)  blEl.textContent  = tot;
    }
  }

  _renderGamesList(games) {
    const list = document.getElementById("games-list");
    if (!list) return;
    if (!games || !games.length) {
      list.innerHTML = `<p class="empty-state">Aucune partie trouvée.</p>`; return;
    }
    list.innerHTML = games.map((g) => {
      const myColor  = g.white?.username?.toLowerCase() === this.username?.toLowerCase() ? "white" : "black";
      const me       = myColor === "white" ? g.white : g.black;
      const opp      = myColor === "white" ? g.black : g.white;
      const result   = me?.result;
      const isWin    = result === "win";
      const isDraw   = ["agreed","stalemate","repetition","insufficient","50move","timevsinsufficient"].includes(result);
      const cls      = isWin ? "win" : isDraw ? "draw" : "loss";
      const icon     = isWin ? "V"  : isDraw ? "½"   : "L";
      const oppName  = opp?.username || "Adversaire";
      const rating   = me?.rating || "?";
      const ts       = g.end_time ? new Date(g.end_time * 1000).toLocaleDateString("fr-FR") : "";
      const timeClass = { bullet:"⚡", blitz:"🔥", rapid:"⏱", daily:"📅" }[g.time_class] || g.time_class || "";
      const pgn      = (g.pgn || "").replace(/"/g, "&quot;");
      return `<div class="game-item ${cls}-item" data-pgn="${pgn}">
        <div class="game-result-badge ${cls}">${icon}</div>
        <div class="game-info">
          <span class="game-opponent">vs ${oppName}</span>
          <div class="game-meta-row"><span>${ts}</span><span>${timeClass}</span></div>
        </div>
        <div class="game-right">
          <span class="game-rating">${rating}</span>
          <span class="game-type">${g.time_class || ""}</span>
        </div>
      </div>`;
    }).join("");
  }

  _renderMovesList(moves) {
    const list = document.getElementById("moves-list");
    if (!list) return;
    const colorVar = {
      book: "var(--text-muted)", unknown: "var(--text-muted)",
      brilliant: "var(--col-brilliant)", excellent: "var(--col-excellent)",
      good: "var(--col-good)", inaccuracy: "var(--col-inaccuracy)",
      mistake: "var(--col-mistake)", blunder: "var(--col-blunder)",
    };
    const icons = { book:"", unknown:"", brilliant:"✦", excellent:"!", good:"", inaccuracy:"?!", mistake:"?", blunder:"??" };

    const fmtClk = (s) => {
      if (s == null) return "";
      return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
    };
    const clkCls = (s) => s != null && s < 10 ? " critical" : s != null && s < 30 ? " low" : "";

    // Layout 2 colonnes : blanc | noir par rangée
    let html = "";
    for (let i = 0; i < moves.length; i++) {
      const m    = moves[i];
      const col  = colorVar[m.classification] || "var(--text-muted)";
      const icon = icons[m.classification] || "";
      const clkStr = fmtClk(m.clock);
      const clkEl  = clkStr ? `<span class="move-clock${clkCls(m.clock)}">${clkStr}</span>` : "";
      const num    = i % 2 === 0 ? `${Math.floor(i / 2) + 1}.` : "";
      html += `<div class="move-item" data-move-index="${i}" style="border-left-color:${col}">
        <span class="move-number">${num}</span>
        <span class="move-san">${m.san}</span>
        <span class="move-icon" style="color:${col}">${icon}</span>
        ${clkEl}
      </div>`;
    }
    list.innerHTML = html;
  }

  _renderGameStats(analysis) {
    const el = document.getElementById("game-stats");
    if (el) {
      const acc = analysis.accuracy != null ? `${analysis.accuracy}%` : "— (Stockfish requis)";
      const elo = analysis.estimated_elo != null ? analysis.estimated_elo : "—";
      el.innerHTML = `
        <div class="stat-chip accuracy">Précision <strong>${acc}</strong></div>
        <div class="stat-chip elo">Elo estimé <strong>${elo}</strong></div>
        <div class="stat-chip blunders">Gaffes <strong>${analysis.blunders_count}</strong></div>`;
    }

    // Accuracy bar — visible seulement si valeur connue
    const bar  = document.getElementById("accuracy-bar");
    const fill = document.getElementById("accuracy-fill");
    const val  = document.getElementById("accuracy-value");
    if (analysis.accuracy != null) {
      if (bar)  bar.hidden = false;
      if (val)  val.textContent = `${analysis.accuracy}%`;
      if (fill) setTimeout(() => { fill.style.width = `${analysis.accuracy}%`; }, 50);
    } else {
      if (bar) bar.hidden = true;
    }

    // Les noms sont mis à jour par _updatePlayerBars (géré avec l'orientation)
  }

  // ─── Utilitaires ────────────────────────────────────────────────

  _showSection(id) {
    // New layout: section-dashboard is always the container
    // Map legacy section IDs to the new panel system
    if (id === "section-board") {
      this._showBoardActive();
    } else if (id === "section-pgn") {
      this._openPgnModal();
    } else if (id === "section-dashboard") {
      this._goHome();
    }
    // section-tabs stays always hidden (content moved to dashboard cards)
  }

  _showBoardActive() {
    const empty  = document.getElementById("board-col-empty");
    const active = document.getElementById("board-active");
    if (empty)  empty.hidden  = true;
    if (active) active.hidden = false;
    document.body.classList.add("board-active");
    // Chessboard.js lit offsetWidth — forcer le reflow après que l'élément soit visible
    if (this.boardMgr?.board) {
      requestAnimationFrame(() => this.boardMgr.board.resize());
    }
  }

  _goHome() {
    const empty  = document.getElementById("board-col-empty");
    const active = document.getElementById("board-active");
    if (empty)  empty.hidden  = false;
    if (active) active.hidden = true;
    document.body.classList.remove("board-active");
  }

  /**
   * Envoie best-effort la partie analysée au backend (EPIC 1) pour persistance
   * et stats serveur. No-op si aucune base API n'est configurée ou si
   * l'utilisateur n'est pas connecté (US 6.4 : la route exige un JWT, le
   * propriétaire n'est plus fourni par le client).
   *
   * En cas de succès, mémorise `serverGameId` sur l'objet `analysis` (US 7.3 :
   * nécessaire pour basculer le statut « déjà étudiée » via `_toggleReviewed`).
   */
  async _syncToBackend(analysis) {
    if (!window.ApiClient || !ApiClient.isConfigured()) return;
    if (!window.Auth?.isLoggedIn()) return;
    const pgn = analysis?.pgn;
    if (!pgn) return;
    const userColor = (this._detectPlayerColor?.(pgn) === "b") ? "black" : "white";
    const tcMatch = pgn.match(/\[TimeControl\s+"([^"]+)"\]/);
    try {
      const data = await ApiClient.analyzeGame(pgn, {
        userColor,
        timeControl: tcMatch ? tcMatch[1] : null,
      });
      const gameId = data?.accepted?.[0]?.game_id;
      if (gameId) {
        analysis.serverGameId = gameId;
        // US 7.2 : une re-soumission du même PGN peut renvoyer une partie déjà
        // marquée comme étudiée — on lit son statut réel plutôt que de
        // supposer false.
        const { game } = await ApiClient.getGame(gameId);
        analysis.isReviewed = !!game?.is_reviewed;
        this._renderReviewedButton();
      }
    } catch { /* best-effort */ }
  }

  /**
   * Affiche/masque #btn-mark-reviewed selon que la partie en cours a un
   * pendant serveur connu (US 7.3), et reflète son statut is_reviewed.
   */
  _renderReviewedButton() {
    const btn = document.getElementById("btn-mark-reviewed");
    if (!btn) return;
    const hasServerGame = !!this.currentGame?.serverGameId;
    btn.hidden = !hasServerGame;
    if (!hasServerGame) return;
    const reviewed = !!this.currentGame.isReviewed;
    btn.classList.toggle("is-reviewed", reviewed);
    btn.textContent = reviewed ? "✓ Étudiée" : "✓ Marquer étudiée";
  }

  /** Bascule le statut « déjà étudiée » de la partie en cours (US 7.3). */
  async _toggleReviewed() {
    const gameId = this.currentGame?.serverGameId;
    if (!gameId || !window.ApiClient) return;
    const next = !this.currentGame.isReviewed;
    try {
      await ApiClient.updateGameStatus(gameId, next);
      this.currentGame.isReviewed = next;
      this._renderReviewedButton();
      this._toast(next ? "Partie marquée comme étudiée" : "Partie remise à étudier", "success");
    } catch {
      this._toast("Impossible de mettre à jour le statut", "error");
    }
  }

  async _showAdvStats() {
    document.body.classList.add("advstats-active");
    await this._loadAdvStats();
  }

  _showCategoryDetail(category) {
    const panel = document.getElementById("adv-detail");
    if (!panel || !window.AdvancedStats || !this._advSummary) return;
    AdvancedStats.renderCategoryDetail(panel, category, this._advSummary);
    panel.hidden = false;
    document.body.classList.add("adv-detail-open");
  }

  _hideCategoryDetail() {
    const panel = document.getElementById("adv-detail");
    if (panel) panel.hidden = true;
    document.body.classList.remove("adv-detail-open");
  }

  _hideAdvStats() {
    document.body.classList.remove("advstats-active");
    document.body.classList.remove("adv-detail-open");
    if (this._advCharts) {
      this._advCharts.forEach((c) => c && c.destroy && c.destroy());
      this._advCharts = null;
    }
    if (this._progressChart) {
      this._progressChart.destroy();
      this._progressChart = null;
    }
  }

  /**
   * Charge et affiche la courbe de progression (US 5.1) pour la cadence et la
   * période courantes. Affiche un état vide explicite si aucun snapshot.
   */
  async _loadProgressChart() {
    if (!window.AdvancedStats) return;
    const wrap = document.getElementById("adv-progress-wrap");
    if (!wrap) return;

    const days = parseInt(this._advPeriod, 10) || 30;
    const history = await AdvancedStats.fetchHistory(this._advCadence, days);

    if (this._progressChart) {
      this._progressChart.destroy();
      this._progressChart = null;
    }

    if (!history.length) {
      wrap.innerHTML = '<p class="empty-state">Pas encore d\'historique pour cette cadence. Analysez plusieurs parties pour voir votre progression.</p>';
      return;
    }

    wrap.innerHTML = '<div class="adv-progress-scroll" id="adv-progress-scroll"><canvas id="adv-progress-canvas"></canvas></div>';
    const scrollEl = document.getElementById("adv-progress-scroll");
    if (scrollEl) scrollEl.style.minWidth = Math.max(600, history.length * 46) + "px";
    this._progressChart = AdvancedStats.renderProgressChart(
      document.getElementById("adv-progress-canvas"), history
    );
  }

  async _loadAdvStats() {
    if (!window.AdvancedStats) return;
    // Détruire les graphes existants avant re-rendu (évite les fuites Chart.js).
    if (this._advCharts) {
      this._advCharts.forEach((c) => c && c.destroy && c.destroy());
    }
    this._advSummary = await AdvancedStats.fetchSummary(this._advPeriod);
    await this._loadProgressChart();

    // État vide : aucune partie analysée → message explicite (pas de tableau cassé).
    if (AdvancedStats.isEmpty(this._advSummary)) {
      this._advCharts = null;
      const empty = '<p class="empty-state">Aucune partie analysée. Importez un PGN pour commencer.</p>';
      const m = document.getElementById("adv-matrix");
      if (m) m.innerHTML = empty;
      ["adv-deepdive", "adv-finales-tiles", "adv-tactics"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = "";
      });
      return;
    }

    const refs = {
      matrix:      document.getElementById("adv-matrix"),
      deepDive:    document.getElementById("adv-deepdive"),
      finales:     document.getElementById("adv-finales-tiles"),
      tactics:     document.getElementById("adv-tactics"),
      acplCanvas:  document.getElementById("adv-acpl-canvas"),
      donutCanvas: document.getElementById("adv-donut-canvas"),
    };
    AdvancedStats.renderMatrix(refs.matrix, this._advSummary);
    AdvancedStats.renderDeepDive(refs.deepDive, this._advSummary, this._advCadence);
    AdvancedStats.renderFinalesTiles(refs.finales, this._advSummary);
    AdvancedStats.renderTacticsCard(refs.tactics, this._advSummary);
    this._advCharts = [
      AdvancedStats.renderAcplChart(refs.acplCanvas, this._advSummary),
      AdvancedStats.renderGaffeDonut(refs.donutCanvas, this._advSummary),
    ];
  }

  _openPgnModal() {
    const modal = document.getElementById("pgn-modal");
    if (modal) modal.hidden = false;
  }

  _closePgnModal() {
    const modal = document.getElementById("pgn-modal");
    if (modal) modal.hidden = true;
  }

  _setModePill(label) {
    document.querySelectorAll(".mode-pill").forEach((el) => {
      el.classList.toggle("active", el.textContent.trim() === label);
    });
  }

  _setLoading(on, msg = "") {
    const el = document.getElementById("loading-overlay");
    if (!el) return;
    el.hidden = !on;
    const m = el.querySelector(".loading-message");
    if (m) m.textContent = msg;
  }

  _toast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const t = document.createElement("div");
    t.className = `toast toast-${type}`;
    t.textContent = message;
    container.appendChild(t);
    requestAnimationFrame(() => t.classList.add("visible"));
    setTimeout(() => { t.classList.remove("visible"); setTimeout(() => t.remove(), 300); }, 3500);
  }
}

// ─── Bootstrap ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // Migrate localStorage → IndexedDB silently before app starts
  if (window.ChessDB) {
    await ChessDB.open();
    await ChessDB.migrateFromLocalStorage();
  }
  window.app = new ChessImproverApp();

  // US 7 : restaurer la session auth si un token existe
  if (window.Auth) {
    const user = await Auth.autoConnect();
    if (user) window.app._onAuthSuccess(user);
    else      window.app._renderAuthState();
  }
});
