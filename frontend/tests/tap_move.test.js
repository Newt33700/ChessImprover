/**
 * Tests — tap_move.js (EPIC 33)
 *
 * `decide` centralise la machine à états du mode tap (clic pièce → clic
 * case d'arrivée) : ces tests couvrent les 5 issues possibles sans DOM.
 * Les tests de câblage DOM (clearHighlights/highlightMoves/attach)
 * utilisent un faux échiquier minimal (pas de jsdom dans ce dépôt), à
 * l'image du mock `document` déjà présent dans tests/setup.js.
 */

const TapMove = require("../js/tap_move.js");

describe("TapMove.decide — aucune case sélectionnée", () => {
  test("tap sur une pièce jouable → select", () => {
    expect(TapMove.decide(null, "e2", { isOwnPickable: true })).toBe("select");
  });

  test("tap sur une case/pièce non jouable → ignore", () => {
    expect(TapMove.decide(null, "e7", { isOwnPickable: false })).toBe("ignore");
  });

  test("tap sur une case vide → ignore", () => {
    expect(TapMove.decide(null, "e4", {})).toBe("ignore");
  });
});

describe("TapMove.decide — case déjà sélectionnée", () => {
  test("re-tap sur la même case → clear (désélection)", () => {
    expect(TapMove.decide("e2", "e2", { isOwnPickable: true })).toBe("clear");
  });

  test("tap sur une destination légale → move", () => {
    expect(TapMove.decide("e2", "e4", { isLegalTarget: true })).toBe("move");
  });

  test("destination légale prioritaire même si la case est aussi une pièce du joueur", () => {
    expect(TapMove.decide("e2", "d3", { isLegalTarget: true, isOwnPickable: true })).toBe("move");
  });

  test("tap sur une autre pièce jouable (non destination légale) → reselect", () => {
    expect(TapMove.decide("e2", "d2", { isOwnPickable: true, isLegalTarget: false })).toBe("reselect");
  });

  test("tap sur une case adverse non destination légale → clear", () => {
    expect(TapMove.decide("e2", "e7", { isOwnPickable: false, isLegalTarget: false })).toBe("clear");
  });

  test("tap sur une case vide non destination légale → clear", () => {
    expect(TapMove.decide("e2", "a5", {})).toBe("clear");
  });
});

describe("TapMove.decide — options par défaut", () => {
  test("aucune option fournie ⇒ isOwnPickable/isLegalTarget valent false", () => {
    expect(TapMove.decide(null, "e4")).toBe("ignore");
    expect(TapMove.decide("e2", "e4")).toBe("clear");
  });
});

// ---------------------------------------------------------------------------
// Faux DOM minimal (pas de jsdom dans ce dépôt — cf. tests/setup.js qui mocke
// déjà `document` de façon similaire pour les autres modules).
// ---------------------------------------------------------------------------

class FakeSquareEl {
  constructor(sq) {
    this.sq = sq;
    this._classes = new Set();
    this.classList = {
      add: (...c) => c.forEach((x) => this._classes.add(x)),
      remove: (...c) => c.forEach((x) => this._classes.delete(x)),
      contains: (c) => this._classes.has(c),
    };
  }
  getAttribute(name) { return name === "data-square" ? this.sq : null; }
  get className() { return [...this._classes].join(" "); }
  closest(selector) { return selector === "[data-square]" ? this : null; }
}

// EPIC 36 (bugfix tap-move) : `attach` résout désormais la case tapée via
// `container.ownerDocument.elementsFromPoint(x, y)` (coordonnées), plus
// jamais via `event.target` — cf. tap_move.js pour le pourquoi (chessboard.js
// détache la pièce cliquée de sa case dès le mousedown). Le faux DOM associe
// donc une position (x, y) à chaque case ; `click(sq)` simule un tap complet
// (pointerdown puis pointerup immobile sur la même case) et `drag(from, to)`
// un vrai glisser (déplacement > seuil, sans case résolue au pointerup).
// Le `pointerup` est écouté sur `ownerDocument` (pas le conteneur, cf.
// tap_move.js) : le faux document a donc lui aussi son propre registre
// d'écouteurs, distinct de celui du conteneur.
class FakeDocument {
  constructor(squares) {
    this.squares = squares;
    this._listeners = {};
  }
  elementsFromPoint(x) {
    const el = Object.values(this.squares).find((sqEl) => sqEl.x === x);
    return el ? [el] : [];
  }
  addEventListener(type, handler) { this._listeners[type] = handler; }
  removeEventListener(type, handler) { if (this._listeners[type] === handler) delete this._listeners[type]; }
}

class FakeContainer {
  constructor(squareIds) {
    this.squares = {};
    squareIds.forEach((sq, i) => {
      const el = new FakeSquareEl(sq);
      el.x = i * 50; // une position x distincte par case, suffisant pour le calcul de distance
      this.squares[sq] = el;
    });
    this._listeners = {};
    this.ownerDocument = new FakeDocument(this.squares);
  }
  querySelector(selector) {
    const m = selector.match(/\[data-square="([^"]+)"\]/);
    return m ? this.squares[m[1]] || null : null;
  }
  querySelectorAll(selector) {
    const classes = selector.split(",").map((s) => s.trim().replace(/^\./, ""));
    return Object.values(this.squares).filter((el) => classes.some((c) => el.classList.contains(c)));
  }
  contains(el) { return Object.values(this.squares).includes(el); }
  addEventListener(type, handler) { this._listeners[type] = handler; }
  removeEventListener(type, handler) { if (this._listeners[type] === handler) delete this._listeners[type]; }
  /** Simule un tap complet : pointerdown + pointerup immobile sur `sq`. */
  click(sq) {
    const x = this.squares[sq]?.x ?? 0;
    this._listeners.pointerdown?.({ clientX: x, clientY: 0 });
    this.ownerDocument._listeners.pointerup?.({ clientX: x, clientY: 0 });
  }
  /** Simule un vrai glisser-déposer (déplacement > seuil) entre deux cases. */
  drag(fromSq, toSq) {
    const fromX = this.squares[fromSq]?.x ?? 0;
    const toX = this.squares[toSq]?.x ?? 0;
    this._listeners.pointerdown?.({ clientX: fromX, clientY: 0 });
    this.ownerDocument._listeners.pointerup?.({ clientX: toX, clientY: 0 });
  }
}

describe("TapMove.clearHighlights", () => {
  test("ignore un conteneur null sans lever d'exception", () => {
    expect(() => TapMove.clearHighlights(null)).not.toThrow();
  });

  test("retire les classes de surbrillance de toutes les cases concernées", () => {
    const container = new FakeContainer(["e2", "e4", "d4", "a1"]);
    container.squares.e2.classList.add("square-selected");
    container.squares.e4.classList.add("square-move-hint");
    container.squares.d4.classList.add("square-capture-hint");

    TapMove.clearHighlights(container);

    expect(container.squares.e2.className).toBe("");
    expect(container.squares.e4.className).toBe("");
    expect(container.squares.d4.className).toBe("");
  });
});

describe("TapMove.highlightMoves", () => {
  test("marque la case source en square-selected et les destinations selon le type de coup", () => {
    const container = new FakeContainer(["e2", "e3", "e4", "d3"]);
    const chess = {
      moves: () => [
        { to: "e3", captured: undefined },
        { to: "e4", captured: undefined },
        { to: "d3", captured: "p" },
      ],
    };
    TapMove.highlightMoves(container, chess, "e2");
    expect(container.squares.e2.classList.contains("square-selected")).toBe(true);
    expect(container.squares.e3.classList.contains("square-move-hint")).toBe(true);
    expect(container.squares.e4.classList.contains("square-move-hint")).toBe(true);
    expect(container.squares.d3.classList.contains("square-capture-hint")).toBe(true);
  });

  test("ignore silencieusement si chess.moves lève une exception (position illisible)", () => {
    const container = new FakeContainer(["e2"]);
    const chess = { moves: () => { throw new Error("boom"); } };
    expect(() => TapMove.highlightMoves(container, chess, "e2")).not.toThrow();
    expect(container.squares.e2.classList.contains("square-selected")).toBe(true);
  });

  test("conteneur ou chess absent → no-op", () => {
    expect(() => TapMove.highlightMoves(null, {}, "e2")).not.toThrow();
    expect(() => TapMove.highlightMoves(new FakeContainer(["e2"]), null, "e2")).not.toThrow();
  });
});

describe("TapMove.attach", () => {
  function makeChess({ whiteAtE2 = true } = {}) {
    return {
      get: (sq) => (sq === "e2" && whiteAtE2 ? { color: "w", type: "p" } : null),
      moves: ({ square } = {}) => (square === "e2" ? [{ to: "e4", captured: undefined }] : []),
    };
  }

  test("ne fait rien si les options requises manquent", () => {
    const container = new FakeContainer(["e2"]);
    expect(() => TapMove.attach(container, {})).not.toThrow();
    expect(container._tapHandlers).toBeUndefined();
  });

  test("sélectionne une pièce jouable puis joue le coup légal sur la case tapée ensuite", () => {
    const container = new FakeContainer(["e2", "e4", "d5"]);
    const chess = makeChess();
    const tryMove = jest.fn(() => "played");
    const onMoved = jest.fn();
    TapMove.attach(container, { getChess: () => chess, canPick: (sq) => sq === "e2", tryMove, onMoved });

    container.click("e2");
    expect(container.squares.e2.classList.contains("square-selected")).toBe(true);

    container.click("e4");
    expect(tryMove).toHaveBeenCalledWith("e2", "e4");
    expect(onMoved).toHaveBeenCalledTimes(1);
    expect(container.squares.e2.classList.contains("square-selected")).toBe(false);
  });

  test("un coup refusé (snapback) ne déclenche pas onMoved", () => {
    const container = new FakeContainer(["e2", "e4"]);
    const chess = makeChess();
    const tryMove = jest.fn(() => "snapback");
    const onMoved = jest.fn();
    TapMove.attach(container, { getChess: () => chess, canPick: (sq) => sq === "e2", tryMove, onMoved });

    container.click("e2");
    container.click("e4");
    expect(onMoved).not.toHaveBeenCalled();
  });

  test("un second attach sur le même conteneur ne double pas les écouteurs", () => {
    const container = new FakeContainer(["e2", "e4"]);
    const chess = makeChess();
    const tryMove = jest.fn(() => "played");
    const opts = { getChess: () => chess, canPick: (sq) => sq === "e2", tryMove, onMoved: jest.fn() };
    TapMove.attach(container, opts);
    TapMove.attach(container, opts);

    container.click("e2");
    container.click("e4");
    expect(tryMove).toHaveBeenCalledTimes(1);
  });

  test("chess indisponible (getChess renvoie null) → clic ignoré", () => {
    const container = new FakeContainer(["e2"]);
    const tryMove = jest.fn();
    TapMove.attach(container, { getChess: () => null, canPick: () => true, tryMove });
    container.click("e2");
    expect(tryMove).not.toHaveBeenCalled();
  });

  // EPIC 36 (bugfix) : chessboard.js détache la pièce cliquée de sa case dès
  // le pointerdown pour son propre glisser-déposer — même un tap immobile
  // provoque ce détachement. `attach` ne doit donc jamais dépendre de
  // `event.target` (qui désignerait alors la pièce flottante, hors case) et
  // doit résoudre la case par coordonnées à la place.
  test("un vrai glisser (déplacement > seuil) ne déclenche pas tryMove — déjà géré par chessboard.js", () => {
    const container = new FakeContainer(["e2", "e4", "d5"]);
    const chess = makeChess();
    const tryMove = jest.fn(() => "played");
    TapMove.attach(container, { getChess: () => chess, canPick: (sq) => sq === "e2", tryMove });

    container.drag("e2", "e4");
    expect(tryMove).not.toHaveBeenCalled();
  });

  test("un pointerup sans pointerdown préalable (ex. pointercancel) est ignoré", () => {
    const container = new FakeContainer(["e2"]);
    const chess = makeChess();
    const tryMove = jest.fn();
    TapMove.attach(container, { getChess: () => chess, canPick: (sq) => sq === "e2", tryMove });

    container.ownerDocument._listeners.pointerup?.({ clientX: 0, clientY: 0 });
    expect(tryMove).not.toHaveBeenCalled();
  });
});
