/**
 * Tests unitaires – BoardManager (modes Review / Ghost / Sandbox)
 *
 * Utilise le vrai moteur chess.js vendorisé (assets/js/chess-0.10.3.js,
 * API snake_case : game_over(), in_checkmate(), ...) pour éviter tout
 * décalage avec le comportement réel en production. Worker et Chessground
 * sont mockés (pas de vrai WebWorker / DOM dans Jest).
 *
 * EPIC 37 : chessboard.js → Chessground. Le fake `set(config)` enregistre le
 * dernier appel pour vérifier `movable.dests`/`movable.color` (source de
 * vérité des règles, calculée depuis chess.js) sans dépendre du DOM réel.
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

function makeFakeChessground() {
  return {
    lastConfig: null,
    set: jest.fn(function (config) { this.lastConfig = config; }),
    toggleOrientation: jest.fn(),
    redrawAll: jest.fn(),
    destroy: jest.fn(),
    setShapes: jest.fn(),
  };
}

let listeners;

beforeEach(() => {
  jest.resetModules();
  jest.useFakeTimers();

  global.Chess = Chess;
  global.Worker = FakeWorker;
  global.Chessground = jest.fn(() => makeFakeChessground());

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
  test("s'initialise sans erreur et crée un board Chessground + un worker WASM", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    expect(Chessground).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({
      fen: new Chess().fen(),
      orientation: "white",
      events: expect.objectContaining({ move: expect.any(Function) }),
    }));
    expect(bm.worker).toBeInstanceOf(FakeWorker);
    expect(bm.worker.url).toBe("js/engine_worker_wasm.js");
  });

  test("configure des brushes rouge (0.6) et vert (0.8) pour les flèches de feedback", () => {
    const BoardManager = loadBoardManager();
    // eslint-disable-next-line no-unused-vars
    const bm = new BoardManager("board", () => {}, () => {});
    const config = Chessground.mock.calls[0][1];
    expect(config.drawable.brushes.red).toMatchObject({ opacity: 0.6 });
    expect(config.drawable.brushes.green).toMatchObject({ opacity: 0.8 });
  });
});

describe("BoardManager — _currentMovableColor / _syncBoard", () => {
  test("verrouille tout déplacement en mode review", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startReview([]);
    expect(bm._currentMovableColor()).toBeUndefined();
    expect(bm.board.set).toHaveBeenLastCalledWith(expect.objectContaining({
      movable: expect.objectContaining({ color: undefined }),
    }));
  });

  test("mode sandbox : autorise la couleur du joueur à son tour", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startSandbox(new Chess().fen(), "w");
    expect(bm._currentMovableColor()).toBe("white");
  });

  test("mode sandbox : bloque quand ce n'est pas le tour du joueur", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.startSandbox(new Chess().fen(), "b");
    expect(bm._currentMovableColor()).toBeUndefined();
  });

  test("_computeDests reflète les coups légaux chess.js (Map from → [to...])", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const dests = bm._computeDests(bm.chess);
    expect(dests.get("e2")).toEqual(expect.arrayContaining(["e3", "e4"]));
  });
});

describe("BoardManager — mode Sandbox (régression bug isGameOver)", () => {
  test("_onCgMove joue un coup légal et déclenche onMove", () => {
    const BoardManager = loadBoardManager();
    const onMove = jest.fn();
    const bm = new BoardManager("board", onMove, () => {});
    bm.startSandbox(new Chess().fen(), "w");

    expect(() => bm._onCgMove("e2", "e4")).not.toThrow();
    expect(onMove).toHaveBeenCalledWith(expect.objectContaining({ from: "e2", to: "e4" }), expect.any(String));
  });

  test("_onCgMove ne plante pas si la position de départ est déjà terminée (fou's mate, régression bug isGameOver)", () => {
    const BoardManager = loadBoardManager();
    const onMove = jest.fn();
    const bm = new BoardManager("board", onMove, () => {});
    // Position déjà mat (fou's mate) — aucun coup légal, `_onCgMove` doit
    // rester un no-op silencieux plutôt que de planter sur `game_over()`.
    bm.startSandbox("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3", "w");

    expect(() => bm._onCgMove("e1", "e2")).not.toThrow();
    expect(onMove).not.toHaveBeenCalled();
  });

  test("_onCgMove ne fait rien si le coup n'est pas légal (dests désynchronisé, filet de sécurité)", () => {
    const BoardManager = loadBoardManager();
    const onMove = jest.fn();
    const bm = new BoardManager("board", onMove, () => {});
    bm.startSandbox(new Chess().fen(), "w");
    expect(() => bm._onCgMove("e7", "e5")).not.toThrow(); // pièce noire, pas aux blancs de jouer
    expect(onMove).not.toHaveBeenCalled();
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
    expect(bm.board.toggleOrientation).toHaveBeenCalled(); // playerColor "b"
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
    expect(bm.board.toggleOrientation).toHaveBeenCalledTimes(1);
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

  test("refreshTheme force un redraw (thème pièces piloté par CSS depuis EPIC 37)", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    bm.refreshTheme();
    expect(bm.board.redrawAll).toHaveBeenCalled();
  });

  test("destroy arrête le worker et détruit le board Chessground", () => {
    const BoardManager = loadBoardManager();
    const bm = new BoardManager("board", () => {}, () => {});
    const worker = bm.worker;
    const postSpy = jest.spyOn(worker, "postMessage");
    const termSpy = jest.spyOn(worker, "terminate");
    bm.destroy();
    expect(postSpy).toHaveBeenCalledWith("stop");
    expect(termSpy).toHaveBeenCalled();
    expect(bm.board.destroy).toHaveBeenCalled();
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
