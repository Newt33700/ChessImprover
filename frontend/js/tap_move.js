/**
 * tap_move.js — EPIC 33 : jouer au TAP en plus du glisser-déposer.
 *
 * Sur mobile, le drag & drop est peu pratique : ce module ajoute le mode
 * « clic pièce → clic case d'arrivée » et la surbrillance des destinations
 * légales (point sur case vide, anneau sur prise) à n'importe quel échiquier
 * chessboard.js, sans dupliquer la logique métier : il réutilise le contrat
 * onDragStart/onDrop/onSnapEnd déjà fourni par chaque module.
 *
 * `decide` est une fonction PURE (testée sans DOM) : elle centralise la
 * machine à états de sélection, le reste n'est que câblage DOM.
 */

const TapMove = (() => {
  "use strict";

  /**
   * Prochaine action pour un tap sur `sq` alors que `selected` est la case
   * actuellement sélectionnée (ou null).
   * @returns {"select"|"reselect"|"move"|"clear"|"ignore"}
   */
  function decide(selected, sq, { isOwnPickable = false, isLegalTarget = false } = {}) {
    if (!selected) return isOwnPickable ? "select" : "ignore";
    if (selected === sq) return "clear";
    if (isLegalTarget) return "move";
    if (isOwnPickable) return "reselect";
    return "clear";
  }

  function clearHighlights(container) {
    if (!container) return;
    container
      .querySelectorAll(".square-selected, .square-move-hint, .square-capture-hint")
      .forEach((el) => el.classList.remove("square-selected", "square-move-hint", "square-capture-hint"));
  }

  /** Surligne la case source + toutes ses destinations légales. */
  function highlightMoves(container, chess, square) {
    if (!container || !chess) return;
    clearHighlights(container);
    container.querySelector(`[data-square="${square}"]`)?.classList.add("square-selected");
    let moves = [];
    try { moves = chess.moves({ square, verbose: true }) || []; } catch { /* position illisible */ }
    for (const mv of moves) {
      container.querySelector(`[data-square="${mv.to}"]`)
        ?.classList.add(mv.captured ? "square-capture-hint" : "square-move-hint");
    }
  }

  /**
   * Attache le tap-tap à un conteneur chessboard.js.
   * @param {HTMLElement} container  le div hôte de l'échiquier
   * @param {object} opts { getChess, canPick(sq, pieceStr), tryMove(src, tgt), onMoved() }
   * `tryMove` suit le contrat chessboard.js : "snapback" = coup refusé.
   */
  function attach(container, opts) {
    if (!container || !opts?.getChess || !opts.canPick || !opts.tryMove) return;
    // Le conteneur peut survivre à une reconstruction du board : jamais deux handlers.
    if (container._tapHandler) container.removeEventListener("click", container._tapHandler);
    let selected = null;

    const handler = (e) => {
      const sqEl = e.target.closest("[data-square]");
      if (!sqEl || !container.contains(sqEl)) return;
      const sq = sqEl.getAttribute("data-square");
      const chess = opts.getChess();
      if (!chess) return;

      const p = chess.get(sq);
      const pieceStr = p ? p.color + p.type.toUpperCase() : null;
      const isOwnPickable = !!(pieceStr && opts.canPick(sq, pieceStr));
      let isLegalTarget = false;
      if (selected) {
        try {
          isLegalTarget = (chess.moves({ square: selected, verbose: true }) || [])
            .some((m) => m.to === sq);
        } catch { /* ignore */ }
      }

      switch (decide(selected, sq, { isOwnPickable, isLegalTarget })) {
        case "select":
        case "reselect":
          selected = sq;
          highlightMoves(container, chess, sq);
          break;
        case "move": {
          const res = opts.tryMove(selected, sq);
          selected = null;
          clearHighlights(container);
          if (res !== "snapback") opts.onMoved?.();
          break;
        }
        case "clear":
          selected = null;
          clearHighlights(container);
          break;
        default: // ignore
      }
    };

    container.addEventListener("click", handler);
    container._tapHandler = handler;
  }

  return { decide, clearHighlights, highlightMoves, attach };
})();

if (typeof window !== "undefined") window.TapMove = TapMove;
if (typeof module !== "undefined" && module.exports != null) module.exports = TapMove;
