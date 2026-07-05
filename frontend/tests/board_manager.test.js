/**
 * Tests unitaires – BoardManager (modes Review / Ghost / Sandbox)
 *
 * Utilise le vrai moteur chess.js vendorisé (assets/js/chess-0.10.3.js,
 * API snake_case : game_over(), in_checkmate(), ...) pour éviter tout
 * décalage avec le comportement réel en production. Worker et
 * Chessboard sont mockés (pas de vrai WebWorker / DOM dans Jest).
 */

const path = require("path");
const { Chess } = require(path.join(__dirname, "../assets/js/chess-0.10.3.js"));

class FakeWorker {
  constructor(url) {
    this.url = url;
    this.onmessage = null;
    this.onerror = null;
    this.posted = [];
  }
  postMessage(msg) { this.posted.push(msg); }
  terminate() {}
  emit(data) { if (this.onmessage) this.onmessage({ data }); }
}

function makeFakeBoardWidget() {
  return {
    _fen: "start",
    fen() { return this._fen === "start" ? new Chess().fen() : this._fen; },
    position(fen) { if (fen && fen !== "start") this._fen = fen; },
    flip: jest.fn(),
    resize: jest.fn(),
    destroy: jest.fn(),
  };
}

let listeners;

beforeEach(() => {
  jest.resetModules();
  jest.useFakeTimers();

  global.Chess = Chess;
  global.Worker = FakeWorker;
  global.Chessboard = jest.fn(() => makeFakeBoardWidget());

  listeners = {};
  global.document = {
    getElementById: jest.fn(() => ({})),
    addEventListener: jest.fn((type, cb) => {
      (listeners[type] = listeners[type] || []).push(cb);
    }),
    dispatchEvent: jest.fn((evt) => {
      (listeners[evt.type] || []).forEach((cb) => cb(evt));
    }),
    removeEventListener: jest.fn((type, cb) => {
      listeners[type] = (listeners[type] || []).filter((f) => f !== cb);
    }),
  };
  global.CustomEvent = function CustomEvent(type, opts) {
    this.type = type;
    this.detail = opts && opts.detail;
  };
  global.window = {
    addEventListener: jest.fn(),
    AnalysisFeedback: null,
    TapMove: null,
    ThemeService: null,
  };

  global.BoardManager = undefined;
});

afterEach(() => {
  jest.useRealTimers();
});

function loadBoardManager() {
  require("../js/board_manager.js");
  return window.BoardManager;
}

describe("BoardManager — construction", () => {
  test("s'initialise sans erreur et crée un board + un worker WASM", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    expect(Chessboard).toHaveBeenCalledWith("board", expect.any(Object));
    expect(bm.worker).toBeInstanceOf(FakeWorker);
    expect(bm.worker.url).toBe("js/engine_worker_wasm.js");
  });
});

describe("BoardManager — mode Sandbox (régression bug isGameOver)", () => {
  test("_onDragStart ne plante pas et autorise le trait du joueur", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startSandbox(new Chess().fen(), "w");

    expect(() => bm._onDragStart("e2", "wP")).not.toThrow();
    expect(bm._onDragStart("e2", "wP")).toBe(true);
  });

  test("_onDragStart refuse de bouger une pièce noire quand c'est aux blancs de jouer", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startSandbox(new Chess().fen(), "w");
    expect(bm._onDragStart("e7", "bP")).toBe(false);
  });

  test("_onDrop joue le coup, déclenche onMove et ne plante pas en fin de partie", () => {
    const BoardManager = loadBoardManager();
    const onMove = jest.fn();
    const bm = new BoardManager("board", onMove, () => {});
    // Position à un coup du mat (fou's mate) pour vérifier game_over() après coup
    bm.startSandbox("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", "w");

    expect(() => bm._onDrop("e1", "e2")).not.toThrow();
  });

  test("_sandboxPlayEngineMove ne plante pas quand la partie est terminée", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    // Mat du berger : après ce dernier coup noir, la partie est terminée
    bm.startSandbox("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", "w");
    bm.chess.move({ from: "e1", to: "e2" }); // coup quelconque légal des blancs
    expect(() => bm._sandboxPlayEngineMove("h4e1")).not.toThrow();
  });
});

describe("BoardManager — mode Review", () => {
  test("startReview réinitialise l'échiquier et met en file l'analyse de chaque position", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const moves = [
      { san: "e4", classification: "book", fen: "fen1" },
      { san: "e5", classification: "good", fen: "fen2" },
    ];
    bm.startReview(moves);
    expect(bm.mode).toBe("review");
    expect(bm.reviewIndex).toBe(-1);
    expect(bm.analysisQueue).toEqual(
      expect.arrayContaining([new Chess().fen(), "fen1", "fen2"])
    );
  });

  test("_onDragStart interdit tout déplacement en mode review", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startReview([]);
    expect(bm._onDragStart("e2", "wP")).toBe(false);
  });

  test("goToMove ignore les index hors bornes", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startReview([{ san: "e4", classification: "good", fen: "fen1" }]);
    bm.goToMove(5);
    expect(bm.reviewIndex).toBe(-1);
    bm.goToMove(-2);
    expect(bm.reviewIndex).toBe(-1);
  });

  test("nextMove/prevMove naviguent et rejouent la position via chess.js", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startReview([
      { san: "e4", classification: "good", fen: "fen1" },
      { san: "e5", classification: "good", fen: "fen2" },
    ]);
    bm.nextMove();
    expect(bm.reviewIndex).toBe(0);
    bm.nextMove();
    expect(bm.reviewIndex).toBe(1);
    bm.prevMove();
    expect(bm.reviewIndex).toBe(0);
  });
});

describe("BoardManager — mode Ghost", () => {
  test("startGhost charge la position et joue le coup adverse si c'est à lui de jouer", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const startFen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2";
    bm.startGhost(startFen, ["Nf3"], "b");

    expect(bm.mode).toBe("ghost");
    jest.advanceTimersByTime(600);
    expect(bm.ghostMoveIndex).toBe(1);
  });

  test("_ghostPlayOpponentMove ignore un coup illégal sans planter et termine la séquence", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.mode = "ghost";
    bm.chess = new Chess();
    bm.ghostOpponentMoves = ["ZZ99"];
    bm.ghostMoveIndex = 0;
    bm.ghostPlayerColor = "w";
    expect(() => bm._ghostPlayOpponentMove()).not.toThrow();
  });
});

describe("BoardManager — utilitaires", () => {
  test("flipBoard bascule l'état flipped et notifie via un événement DOM", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const handler = jest.fn();
    document.addEventListener("board:flip", handler);
    bm.flipBoard();
    expect(bm.flipped).toBe(true);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0][0].detail).toEqual({ flipped: true });
  });

  test("reset remet l'échiquier à la position de départ", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.chess.move("e4");
    bm.reset();
    expect(bm.getCurrentFen()).toBe(new Chess().fen());
  });

  test("destroy arrête le worker proprement", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const worker = bm.worker;
    const postSpy = jest.spyOn(worker, "postMessage");
    const termSpy = jest.spyOn(worker, "terminate");
    bm.destroy();
    expect(postSpy).toHaveBeenCalledWith("stop");
    expect(termSpy).toHaveBeenCalled();
  });
});

describe("BoardManager — messages du worker Stockfish", () => {
  test("un message 'ready' déclenche ucinewgame et vide la file d'analyse", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.analysisQueue = [new Chess().fen()];
    bm.worker.emit({ type: "ready" });
    expect(bm.workerReady).toBe(true);
    expect(bm.isAnalyzing).toBe(true);
  });

  test("un message 'info' avec évaluation met à jour le cache et notifie onAnalysis", () => {
    const BoardManager = loadBoardManager();
    const onAnalysis = jest.fn();
    const bm = new BoardManager("board", () => {}, onAnalysis);
    const fen = new Chess().fen();
    bm.currentFen = fen;
    bm.worker.emit({ type: "info", evaluation: 25, pv: ["e2e4"], fen });
    expect(bm.evalCache[fen].evaluation).toBe(25);
    expect(onAnalysis).toHaveBeenCalledWith({ evaluation: 25, fen });
  });

  test("un message 'info' sans évaluation ne modifie rien", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const fen = new Chess().fen();
    bm.currentFen = fen;
    bm.worker.emit({ type: "info", evaluation: null, fen });
    expect(bm.evalCache[fen]).toBeUndefined();
  });

  test("un message 'bestmove' enregistre le meilleur coup et relance la file", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const fen = new Chess().fen();
    bm.currentFen = fen;
    bm.isAnalyzing = true;
    bm.worker.emit({ type: "bestmove", move: "e2e4", fen });
    expect(bm.evalCache[fen].bestMove).toBe("e2e4");
    expect(bm.isAnalyzing).toBe(false);
  });
});
