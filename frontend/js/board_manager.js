/**
 * Chess Improver – Gestionnaire d'échiquier
 * Gère chess.js + chessboard.js pour 3 modes :
 *   1. Mode Review  : relecture coup par coup avec colorisation
 *   2. Mode Exercice: tactique SRS
 *   3. Mode Ghost   : rejouer depuis la gaffe avec les coups adverses historiques
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
    this.mode = null;  // "review" | "exercise" | "ghost"
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

    this._initWorker();
    this._initBoard();
  }

  // -------------------------------------------------------------------------
  // Initialisation
  // -------------------------------------------------------------------------

  _initBoard() {
    const config = {
      draggable: true,
      position: "start",
      onDragStart: (src, piece) => this._onDragStart(src, piece),
      onDrop: (src, tgt) => this._onDrop(src, tgt),
      onSnapEnd: () => this._onSnapEnd(),
      pieceTheme:
        "https://lichess1.org/assets/piece/cburnett/{piece}.svg",
    };
    this.board = Chessboard(this.containerId, config);
    window.addEventListener("resize", () => this.board.resize());
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

    document.dispatchEvent(new CustomEvent("move:accuracy", {
      detail: { moveIdx, cpLoss, evalCp: whiteAfter },
    }));
  }


  // -------------------------------------------------------------------------
  // Drag & Drop handlers
  // -------------------------------------------------------------------------

  _onDragStart(src, piece) {
    if (this.mode === "review") return false;  // pas de déplacement en review
    if (this.chess.isGameOver()) return false;

    const isWhitePiece = piece.startsWith("w");
    const isWhiteTurn = this.chess.turn() === "w";
    if (isWhitePiece !== isWhiteTurn) return false;

    // Ghost : bloquer si c'est le tour de l'adversaire
    if (this.mode === "ghost" && this.chess.turn() !== this.ghostPlayerColor) {
      return false;
    }
    return true;
  }

  _onDrop(src, tgt) {
    // Tenter le coup
    const move = this.chess.move({ from: src, to: tgt, promotion: "q" });
    if (!move) return "snapback";

    const fen = this.chess.fen();
    if (this.onMove) this.onMove(move, fen);

    // Déclencher l'analyse Stockfish
    this._requestAnalysis(fen);

    // Mode Exercice : vérifier la solution
    if (this.mode === "exercise") {
      this._checkExerciseSolution(move);
    }

    // Mode Ghost : répondre avec le coup historique adverse
    if (this.mode === "ghost") {
      setTimeout(() => this._ghostPlayOpponentMove(), 400);
    }

    return undefined;
  }

  _onSnapEnd() {
    this.board.position(this.chess.fen());
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
    this.chess.reset();
    this.board.position("start");

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
    this.board.position(this.chess.fen());
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
  // Mode Exercice Tactique
  // -------------------------------------------------------------------------

  /**
   * @param {string} fen          – position de départ de l'exercice
   * @param {string} solutionMove – coup SAN correct
   * @param {string} playerColor  – "w" | "b"
   */
  startExercise(fen, solutionMove, playerColor = "w") {
    this.mode = "exercise";
    this.exerciseSolution = solutionMove;
    this.exercisePlayerColor = playerColor;
    this.chess.load(fen);
    this.board.position(fen);
    if (playerColor === "b") this.board.flip();
  }

  _checkExerciseSolution(playedMove) {
    const correct = playedMove.san === this.exerciseSolution;
    document.dispatchEvent(new CustomEvent("exercise:result", {
      detail: { correct, played: playedMove.san, solution: this.exerciseSolution }
    }));
    return correct;
  }

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
    this.board.position(startFen);
    if (playerColor === "b") this.board.flip();

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
    this.board.position(this.chess.fen(), false);

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
  // Analyse Stockfish
  // -------------------------------------------------------------------------

  _requestAnalysis(fen) {
    this._queueAnalysis(fen);
  }

  // -------------------------------------------------------------------------
  // Utilitaires publics
  // -------------------------------------------------------------------------

  flipBoard() {
    this.board.flip();
    this.flipped = !this.flipped;
    document.dispatchEvent(new CustomEvent("board:flip", { detail: { flipped: this.flipped } }));
  }
  reset() { this.chess.reset(); this.board.position("start"); }

  getCurrentFen() { return this.chess.fen(); }

  destroy() {
    if (this.worker) { this.worker.postMessage("stop"); this.worker.terminate(); }
  }
}

// Export global
window.BoardManager = BoardManager;
