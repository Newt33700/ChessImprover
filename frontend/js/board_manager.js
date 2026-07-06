/**
 * Chess Improver – Gestionnaire d'échiquier
 * Gère chess.js + Chessground (EPIC 37 — ex-chessboard.js) pour 3 modes :
 *   1. Mode Review  : relecture coup par coup avec colorisation
 *   3. Mode Ghost   : rejouer depuis la gaffe avec les coups adverses historiques
 *
 * Chessground ne valide aucun coup lui-même (contrairement à chessboard.js,
 * qui laissait déposer n'importe où puis rejetait via onDrop) : chaque mise à
 * jour de position fournit `movable.dests` (calculé depuis chess.js, seule
 * source de vérité des règles), donc tout coup que l'UI autorise est légal
 * par construction — plus de « snapback ». Le clic-clic (sélection + case
 * d'arrivée en surbrillance) est natif à la lib, `tap_move.js` (EPIC 33)
 * n'est donc plus attaché ici (il reste utilisé par les échiquiers de
 * problèmes ad-hoc d'`app.js`, restés sur chessboard.js).
 */

class BoardManager {
  /**
   * @param {string} containerId  – ID du div échiquier
   * @param {function} onMove     – callback(move, fen) appelé après chaque coup joué
   * @param {function} onAnalysis – callback(evaluation) retour moteur Stockfish
   */
  constructor(containerId, onMove, onAnalysis) {
    this.containerId = containerId;
    this.onMove = onMove;
    this.onAnalysis = onAnalysis;

    this.chess = new Chess();
    this.board = null;
    this.mode = null;  // "review" | "ghost" | "sandbox"
    this.flipped = false;

    // État Review
    this.reviewMoves = [];
    this.reviewIndex = 0;
    this.bookMoveThreshold = 15; // nombre de demi-coups d'ouverture (affiné par setBookDepth)

    // État Ghost
    this.ghostOpponentMoves = [];  // coups historiques adverses
    this.ghostTargetFen = null;    // FEN objectif
    this.ghostPlayerColor = "w";
    this.ghostMoveIndex = 0;

    // Moteur
    this.worker = null;
    this.workerReady = false;
    this.currentFen = null;

    // File d'analyse séquentielle (Stockfish ne peut analyser qu'une position à la fois)
    this.analysisQueue = [];
    this.isAnalyzing = false;

    // Cache des évaluations : fen → { evaluation, bestMove }
    this.evalCache = {};

    // EPIC 22 (US 22.1) : dédoublonnage des événements move:accuracy — le
    // moteur émet plusieurs messages `info` par position, on ne re-dispatche
    // que si le résultat du coup a réellement changé.
    this.feedbackState = window.AnalysisFeedback
      ? AnalysisFeedback.createState()
      : null;

    this._initWorker();
    this._initBoard();
  }

  // -------------------------------------------------------------------------
  // Initialisation
  // -------------------------------------------------------------------------

  _initBoard() {
    const el = document.getElementById(this.containerId);
    this.board = Chessground(el, {
      fen: this.chess.fen(),
      orientation: "white",
      highlight: { lastMove: true, check: true },
      animation: { enabled: true, duration: 200 },
      movable: { free: false, color: undefined, dests: new Map(), showDests: true },
      // Rouge/Vert (EPIC 37, US 37.1) : coup joué (erreur) / suggestion
      // moteur, dessinés par `AnalysisFeedback.drawFeedback` (app.js).
      drawable: {
        brushes: {
          red:    { key: "r", color: "#ca3431", opacity: 0.6, lineWidth: 10 },
          green:  { key: "g", color: "#81b64c", opacity: 0.8, lineWidth: 10 },
          blue:   { key: "b", color: "#3b82f6", opacity: 0.6, lineWidth: 10 },
          yellow: { key: "y", color: "#eab308", opacity: 0.6, lineWidth: 10 },
        },
      },
      events: { move: (orig, dest) => this._onCgMove(orig, dest) },
    });
    // Chessground se redimensionne lui-même en CSS (conteneur en %), sauf
    // s'il a été mesuré alors que caché (`display:none`) — un redraw après
    // resize reste un filet de sécurité peu coûteux (même motif que l'ancien
    // `board.resize()` sur chessboard.js).
    window.addEventListener("resize", () => this.board.redrawAll());
  }

  /**
   * EPIC 18 (US 18.3) — Thème de pièces : depuis EPIC 37, entièrement piloté
   * par CSS (classe `body.theme-*`, cf. style.css), Chessground n'a donc rien
   * à reconstruire. Conservé pour compatibilité d'API (appelants existants
   * d'`app.js`) — force juste un redraw défensif.
   */
  refreshTheme() {
    this.board?.redrawAll();
  }

  /** Recalcule `movable.dests` (règles chess.js) pour la position courante. */
  _computeDests(chess) {
    const dests = new Map();
    chess.moves({ verbose: true }).forEach((m) => {
      if (!dests.has(m.from)) dests.set(m.from, []);
      dests.get(m.from).push(m.to);
    });
    return dests;
  }

  /**
   * Couleur autorisée à jouer sur l'échiquier, selon le mode courant —
   * remplace l'ancien `_onDragStart` (qui refusait la préhension au cas par
   * cas) : Chessground n'autorise que les cases de `movable.dests`, pour la
   * couleur `movable.color` — undefined bloque tout déplacement.
   */
  _currentMovableColor() {
    if (this.mode === "review" || !this.mode) return undefined;
    const turn = this.chess.turn() === "w" ? "white" : "black";
    if (this.mode === "ghost") {
      return this.chess.turn() === this.ghostPlayerColor ? turn : undefined;
    }
    if (this.mode === "sandbox") {
      return this.chess.turn() === this.sandboxPlayerColor ? turn : undefined;
    }
    return turn;
  }

  /**
   * Synchronise Chessground sur l'état courant de `this.chess` : position,
   * trait, échec, et surtout `movable.dests` (sans quoi plus aucun coup ne
   * serait proposé après le premier). À appeler après CHAQUE changement de
   * position, qu'il vienne d'un coup joué ou d'une navigation programmatique
   * (Review, Ghost, Sandbox).
   */
  _syncBoard(fen) {
    if (!this.board) return;
    const turnColor = this.chess.turn() === "w" ? "white" : "black";
    const gameOver = this.chess.game_over();
    this.board.set({
      fen,
      turnColor,
      check: !gameOver && this.chess.in_check() ? turnColor : false,
      movable: {
        color: gameOver ? undefined : this._currentMovableColor(),
        dests: gameOver ? new Map() : this._computeDests(this.chess),
      },
    });
  }

  _initWorker() {
    this._tryWorker("js/engine_worker_wasm.js");
  }

  _tryWorker(url) {
    try {
      const worker = new Worker(url);
      worker.onmessage = (e) => {
        const data = e.data;
        if (data && typeof data === "object" && data.type) {
          this._handleWorkerMsg(data);
        } else {
          // Fallback : ancien format texte brut
          const line = typeof data === "string" ? data : String(data || "");
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith("[")) return;
          this._handleWorkerUCILegacy(trimmed);
        }
      };
      worker.onerror = (err) => {
        console.error("[Stockfish] erreur worker:", err.message);
        worker.terminate();
        this.worker = null;
      };
      this.worker = worker;
      setTimeout(() => {
        if (!this.workerReady) {
          console.warn("[Stockfish] timeout WASM — fallback asm.js");
          this._tryWorkerLegacy("js/stockfish.js");
        }
      }, 10000);
    } catch (err) {
      console.error("[Stockfish] création worker WASM échouée:", err.message);
      this._tryWorkerLegacy("js/stockfish.js");
    }
  }

  _tryWorkerLegacy(url) {
    if (this.workerReady) return;
    try {
      const worker = new Worker(url);
      worker.onmessage = (e) => {
        const line = typeof e.data === "string" ? e.data : String(e.data || "");
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("[")) return;
        this._handleWorkerUCILegacy(trimmed);
      };
      worker.onerror = () => {};
      if (this.worker) this.worker.terminate();
      this.worker = worker;
      worker.postMessage("uci");
    } catch {}
  }

  _handleWorkerMsg(msg) {
    switch (msg.type) {
      case "ready":
        this.worker.postMessage("ucinewgame");
        this.workerReady = true;
        this._processQueue();
        break;

      case "info": {
        const { evaluation, pv, fen } = msg;
        if (evaluation === null || evaluation === undefined) return;
        const f = fen || this.currentFen;
        if (f) {
          this.evalCache[f] = this.evalCache[f] || {};
          this.evalCache[f].evaluation = evaluation;
          if (pv && pv.length) this.evalCache[f].pv = pv;
          this._tryUpdateMoveAccuracy(f, evaluation);
        }
        if (this.onAnalysis) this.onAnalysis({ evaluation, fen: f });
        break;
      }

      case "bestmove": {
        const { move, pv, fen } = msg;
        const f = fen || this.currentFen;
        if (f) {
          this.evalCache[f] = this.evalCache[f] || {};
          if (move) this.evalCache[f].bestMove = move;
          if (pv && pv.length) this.evalCache[f].pv = pv;
        }
        this.isAnalyzing = false;
        if (this.mode === "sandbox" && move && f === this.chess.fen()
            && this.chess.turn() !== this.sandboxPlayerColor) {
          this._sandboxPlayEngineMove(move);
        }
        this._processQueue();
        break;
      }

      case "error":
        console.error("[Stockfish]", msg.message);
        break;
    }
  }

  _handleWorkerUCILegacy(line) {
    if (!line || line.startsWith("[WF")) return;

    if (line === "uciok") {
      this.worker.postMessage("setoption name Hash value 16");
      this.worker.postMessage("ucinewgame");
      this.workerReady = true;
      this._processQueue();
      return;
    }

    if (line === "readyok") {
      if (!this.workerReady) {
        this.workerReady = true;
        this._processQueue();
      }
      return;
    }

    if (line.startsWith("bestmove")) {
      const bestMove = line.split(" ")[1] || "(none)";
      if (this.currentFen) {
        this.evalCache[this.currentFen] = this.evalCache[this.currentFen] || {};
        this.evalCache[this.currentFen].bestMove = bestMove;
      }
      this.isAnalyzing = false;
      this._processQueue();
      return;
    }

    if (line.startsWith("info") && line.includes("score")) {
      const depthM = line.match(/depth\s+(\d+)/);
      const cpM    = line.match(/score cp\s+(-?\d+)/);
      const mateM  = line.match(/score mate\s+(-?\d+)/);
      const pvM    = line.match(/ pv (.+)$/);
      const depth  = depthM ? parseInt(depthM[1], 10) : 0;
      if (depth < 3) return;

      const evaluation = cpM
        ? parseInt(cpM[1], 10)
        : (mateM ? (parseInt(mateM[1], 10) > 0 ? 10000 : -10000) : 0);
      const pv = pvM ? pvM[1].trim().split(/\s+/).slice(0, 5) : [];
      const fen = this.currentFen;

      if (fen) {
        this.evalCache[fen] = this.evalCache[fen] || {};
        this.evalCache[fen].evaluation = evaluation;
        if (pv.length) this.evalCache[fen].pv = pv;
        this._tryUpdateMoveAccuracy(fen, evaluation);
      }
      if (this.onAnalysis) this.onAnalysis({ evaluation, fen });
    }
  }

  _queueAnalysis(fen) {
    if (this.evalCache[fen]?.evaluation !== undefined) return;
    if (this.analysisQueue.includes(fen)) return;
    this.analysisQueue.push(fen);
    if (this.workerReady && !this.isAnalyzing) this._processQueue();
  }

  _processQueue() {
    if (!this.worker || !this.workerReady || this.isAnalyzing || !this.analysisQueue.length) return;
    this.isAnalyzing = true;
    this.currentFen = this.analysisQueue.shift();
    this.worker.postMessage("position fen " + this.currentFen);
    // Min depth 15 and min 500ms – enforced by engine_worker_wasm; legacy worker uses depth 15 directly
    this.worker.postMessage("go depth 15 movetime 500");
  }

  _tryUpdateMoveAccuracy(fen, evalAfter) {
    if (this.mode !== "review") return;
    const moveIdx = this.reviewMoves.findIndex((m) => m.fen === fen);
    if (moveIdx < 0) return;

    if (moveIdx < this.bookMoveThreshold) {
      if (this.feedbackState
          && !AnalysisFeedback.shouldDispatch(this.feedbackState, moveIdx, 0, true)) return;
      document.dispatchEvent(new CustomEvent("move:accuracy", {
        detail: { moveIdx, cpLoss: 0, book: true },
      }));
      return;
    }

    const prevFen = moveIdx === 0
      ? "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
      : this.reviewMoves[moveIdx - 1].fen;
    const prevEntry = this.evalCache[prevFen];
    if (!prevEntry || prevEntry.evaluation === undefined) return;

    const evalBefore  = prevEntry.evaluation;
    const sideToMove  = (f) => f.split(" ")[1] === "w";
    const whiteBefore = sideToMove(prevFen) ?  evalBefore : -evalBefore;
    const whiteAfter  = sideToMove(fen)     ?  evalAfter  : -evalAfter;

    const playerColor = this.reviewMoves[moveIdx].color;
    const cpLoss = playerColor === "w"
      ? Math.max(0, whiteBefore - whiteAfter)
      : Math.max(0, whiteAfter  - whiteBefore);

    if (this.feedbackState
        && !AnalysisFeedback.shouldDispatch(this.feedbackState, moveIdx, cpLoss, false)) return;
    document.dispatchEvent(new CustomEvent("move:accuracy", {
      detail: { moveIdx, cpLoss, evalCp: whiteAfter },
    }));
  }


  // -------------------------------------------------------------------------
  // Coup joué sur l'échiquier (glisser-déposer OU clic-clic natif Chessground)
  // -------------------------------------------------------------------------

  /**
   * Appelé par Chessground (`events.move`) une fois le coup déjà joué côté
   * UI — toujours légal par construction puisque `orig`/`dest` viennent
   * forcément de `movable.dests` (calculé depuis chess.js). `chess.move`
   * reste néanmoins la source de vérité (met à jour l'historique/FEN) ; un
   * retour `null` ici trahirait un dests désynchronisé (filet de sécurité,
   * ne devrait jamais arriver en pratique).
   */
  _onCgMove(orig, dest) {
    const move = this.chess.move({ from: orig, to: dest, promotion: "q" });
    if (!move) return;

    const fen = this.chess.fen();
    this._syncBoard(fen);
    if (this.onMove) this.onMove(move, fen);

    // Déclencher l'analyse Stockfish
    this._requestAnalysis(fen);

    // Mode Ghost : répondre avec le coup historique adverse
    if (this.mode === "ghost") {
      setTimeout(() => this._ghostPlayOpponentMove(), 400);
    }

    // Mode Sandbox (Game-Salvage) : le moteur répond après le coup du joueur
    if (this.mode === "sandbox" && !this.chess.game_over()) {
      this._requestSandboxEngineMove();
    }
  }

  // -------------------------------------------------------------------------
  // Mode Review
  // -------------------------------------------------------------------------

  /**
   * Lance le mode relecture d'une partie.
   * @param {Array<{san: string, classification: string, fen: string}>} moves
   */
  startReview(moves) {
    this.mode = "review";
    this.reviewMoves = moves;
    this.reviewIndex = -1;
    this.bookMoveThreshold = 15; // valeur provisoire, affinée par setBookDepth()
    // US 22.1 : nouvelle partie = nouvel état de dédoublonnage
    if (window.AnalysisFeedback) this.feedbackState = AnalysisFeedback.createState();
    this.chess.reset();
    this._syncBoard(this.chess.fen());

    const startFen = new Chess().fen();
    this._queueAnalysis(startFen);
    moves.forEach((m) => this._queueAnalysis(m.fen));
  }

  goToMove(index) {
    // -1 = retour à la position initiale ; index max = dernier coup
    if (index < -1 || index >= this.reviewMoves.length) return;
    this.chess.reset();
    for (let i = 0; i <= index; i++) {
      this.chess.move(this.reviewMoves[i].san);
    }
    this.reviewIndex = index;
    this._syncBoard(this.chess.fen());
    this._updateReviewHighlight();
  }

  nextMove() { this.goToMove(this.reviewIndex + 1); }
  prevMove() { this.goToMove(this.reviewIndex - 1); }

  setBookDepth(n) {
    const old = this.bookMoveThreshold;
    this.bookMoveThreshold = n;
    // Reclassifier les coups qui étaient "book" mais ne le sont plus
    for (let i = n; i < old; i++) {
      const move = this.reviewMoves[i];
      if (!move) break;
      const cached = this.evalCache[move.fen];
      if (cached?.evaluation !== undefined) {
        this._tryUpdateMoveAccuracy(move.fen, cached.evaluation);
      }
    }
  }

  _updateReviewHighlight() {
    if (this.reviewIndex < 0) {
      document.dispatchEvent(new CustomEvent("review:move", {
        detail: { index: -1, move: null, color: null },
      }));
      return;
    }
    const move = this.reviewMoves[this.reviewIndex];
    if (!move) return;
    const colorMap = {
      book: "var(--text-muted)",
      brilliant: "var(--col-brilliant)", excellent: "var(--col-excellent)",
      good: "var(--col-good)", inaccuracy: "var(--col-inaccuracy)",
      mistake: "var(--col-mistake)", blunder: "var(--col-blunder)",
    };
    document.dispatchEvent(new CustomEvent("review:move", {
      detail: { index: this.reviewIndex, move, color: colorMap[move.classification] || "var(--text-muted)" },
    }));
  }

  // -------------------------------------------------------------------------
  // Mode Exercice : SUPPRIMÉ (EPIC 26, US 26.1) — l'Exercice SRS a désormais
  // sa propre page plein écran (#exercise-col, logique dans app.js), 100 %
  // indépendante du board partagé. Le BoardManager ne gère plus que les
  // modes review / ghost / sandbox, tous liés à la partie en cours.
  // -------------------------------------------------------------------------

  // -------------------------------------------------------------------------
  // Mode Ghost
  // -------------------------------------------------------------------------

  /**
   * Lance le Mode Ghost.
   * @param {string} startFen         – FEN 3 coups avant la gaffe
   * @param {string[]} opponentMoves  – coups SAN historiques de l'adversaire
   * @param {string} playerColor      – couleur du joueur ("w" | "b")
   */
  startGhost(startFen, opponentMoves, playerColor = "w") {
    this.mode = "ghost";
    this.ghostOpponentMoves = opponentMoves;
    this.ghostPlayerColor = playerColor;
    this.ghostMoveIndex = 0;
    this.chess.load(startFen);
    this._syncBoard(startFen);
    if (playerColor === "b") this.board.toggleOrientation();

    // Si c'est l'adversaire qui joue en premier, jouer son coup immédiatement
    if (this.chess.turn() !== playerColor) {
      setTimeout(() => this._ghostPlayOpponentMove(), 500);
    }
  }

  _ghostPlayOpponentMove() {
    if (this.ghostMoveIndex >= this.ghostOpponentMoves.length) {
      this._evaluateGhostResult();
      return;
    }

    const moveSan = this.ghostOpponentMoves[this.ghostMoveIndex];
    const move = this.chess.move(moveSan);
    if (!move) {
      this._evaluateGhostResult();
      return;
    }

    this.ghostMoveIndex++;
    this._syncBoard(this.chess.fen());

    // Vérifier si la séquence est terminée
    if (this.ghostMoveIndex >= this.ghostOpponentMoves.length) {
      setTimeout(() => this._evaluateGhostResult(), 300);
    }
  }

  _evaluateGhostResult() {
    const fen = this.chess.fen();
    const cached = this.evalCache[fen];

    if (cached && cached.evaluation !== undefined) {
      this._emitGhostResult(cached.evaluation);
    } else {
      // Demander l'évaluation au moteur et attendre
      this._requestAnalysis(fen);
      const handler = (e) => {
        if (e.detail.fen === fen) {
          this._emitGhostResult(e.detail.evaluation);
          document.removeEventListener("engine:eval", handler);
        }
      };
      document.addEventListener("engine:eval", handler);
    }
  }

  _emitGhostResult(evaluation) {
    // Positif = bon pour le joueur blanc ; inverser si noir
    const playerEval =
      this.ghostPlayerColor === "w" ? evaluation : -evaluation;
    const success = playerEval > 0;

    document.dispatchEvent(new CustomEvent("ghost:result", {
      detail: { success, evaluation: playerEval }
    }));
  }

  // -------------------------------------------------------------------------
  // Mode Sandbox (EPIC 15 — « Réparation de Partie » / Game-Salvage)
  // -------------------------------------------------------------------------

  /**
   * Lance le mode Sandbox : rejouer librement contre Stockfish à partir du
   * pivot de défaite (US 15.1), pour tenter de sauver la position (US 15.2).
   * @param {string} fen          – position de départ (juste avant la gaffe)
   * @param {string} playerColor  – couleur du joueur ("w" | "b")
   */
  startSandbox(fen, playerColor = "w") {
    this.mode = "sandbox";
    this.sandboxPlayerColor = playerColor;
    this.chess.load(fen);
    this._syncBoard(fen);
    if (playerColor === "b") this.board.toggleOrientation();
  }

  _requestSandboxEngineMove() {
    const fen = this.chess.fen();
    const cached = this.evalCache[fen];
    if (cached && cached.bestMove) {
      setTimeout(() => this._sandboxPlayEngineMove(cached.bestMove), 300);
      return;
    }
    this._queueAnalysis(fen);
  }

  _sandboxPlayEngineMove(uciMove) {
    if (this.mode !== "sandbox" || this.chess.game_over()) return;
    const from = uciMove.slice(0, 2);
    const to = uciMove.slice(2, 4);
    const promotion = uciMove.length > 4 ? uciMove.slice(4) : "q";
    const move = this.chess.move({ from, to, promotion });
    if (!move) return;
    const fen = this.chess.fen();
    this._syncBoard(fen);
    if (this.onMove) this.onMove(move, fen);
    this._requestAnalysis(fen);
  }

  // -------------------------------------------------------------------------
  // Analyse Stockfish
  // -------------------------------------------------------------------------

  _requestAnalysis(fen) {
    this._queueAnalysis(fen);
  }

  // -------------------------------------------------------------------------
  // Utilitaires publics
  // -------------------------------------------------------------------------

  flipBoard() {
    this.board.toggleOrientation();
    this.flipped = !this.flipped;
    document.dispatchEvent(new CustomEvent("board:flip", { detail: { flipped: this.flipped } }));
  }
  reset() { this.chess.reset(); this._syncBoard(this.chess.fen()); }

  getCurrentFen() { return this.chess.fen(); }

  destroy() {
    if (this.worker) { this.worker.postMessage("stop"); this.worker.terminate(); }
    this.board?.destroy();
  }
}

// Export global
window.BoardManager = BoardManager;
