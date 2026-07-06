/**
 * tap_move.js — EPIC 33 : jouer au TAP en plus du glisser-déposer.
 * EPIC 36 (bugfix) : un vrai clic souris/trackpad ne déclenchait JAMAIS le
 * tap — cf. ci-dessous.
 *
 * Sur mobile, le drag & drop est peu pratique : ce module ajoute le mode
 * « clic pièce → clic case d'arrivée » et la surbrillance des destinations
 * légales (point sur case vide, anneau sur prise) à n'importe quel échiquier
 * chessboard.js, sans dupliquer la logique métier : il réutilise le contrat
 * onDragStart/onDrop/onSnapEnd déjà fourni par chaque module.
 *
 * `decide` est une fonction PURE (testée sans DOM) : elle centralise la
 * machine à états de sélection, le reste n'est que câblage DOM.
 *
 * Bug corrigé (retour utilisateur réel, écran sans souris précise) : la
 * première implémentation écoutait l'événement `click` délégué sur le
 * conteneur. Or chessboard.js (draggable:true) détache la pièce cliquée de
 * sa case dès le `mousedown` — même sans aucun mouvement — pour la
 * repositionner en `position:absolute` à même le `<body>` (mécanisme de
 * glisser-déposer). Résultat : l'événement `click` final se déclenche sur
 * ce nœud flottant, qui n'est alors *plus descendant du conteneur* → notre
 * écouteur délégué ne le voyait jamais, et le tap ne fonctionnait donc
 * QUE via un `element.click()` synthétique (tests), jamais via une vraie
 * souris/trackpad. On écoute désormais `pointerdown` (sur le conteneur, pour
 * savoir qu'un geste a démarré ICI) puis `pointerup` (sur le `document` tout
 * entier : au relâchement, l'élément visuellement sous le curseur est ce
 * même nœud flottant, hors du conteneur — un écouteur posé sur le conteneur
 * ne recevrait donc jamais cet événement, qui ne traverse que l'ascendance
 * réelle de sa cible). La case concernée est ensuite résolue par
 * COORDONNÉES (`elementsFromPoint`), jamais via `event.target` : les cases
 * elles-mêmes ne bougent jamais, seule la pièce à l'intérieur est déplacée.
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

  // Au-delà de ce déplacement (px) entre pointerdown et pointerup, on
  // considère que l'utilisateur a fait un vrai glisser-déposer (déjà géré
  // par chessboard.js via son propre onDrop) plutôt qu'un tap.
  const DRAG_THRESHOLD_PX = 10;

  /**
   * Résout la case d'échecs sous le point (x, y) — jamais via
   * `event.target`, qui peut désigner une pièce que chessboard.js a
   * détachée de sa case (cf. commentaire d'en-tête). Les cases elles-mêmes
   * (éléments `[data-square]`) ne sont jamais déplacées, seule une pièce
   * peut flotter au-dessus : on retient donc le premier élément avec
   * `data-square` dans la pile au point donné, en ignorant tout ce qui
   * flotte par-dessus.
   */
  function squareAt(doc, container, x, y) {
    if (!doc?.elementsFromPoint) return null;
    const stack = doc.elementsFromPoint(x, y) || [];
    return (
      stack.find((el) => el?.getAttribute?.("data-square") && (!container || container.contains(el))) || null
    );
  }

  /**
   * Attache le tap-tap à un conteneur chessboard.js.
   * @param {HTMLElement} container  le div hôte de l'échiquier
   * @param {object} opts { getChess, canPick(sq, pieceStr), tryMove(src, tgt), onMoved() }
   * `tryMove` suit le contrat chessboard.js : "snapback" = coup refusé.
   */
  function attach(container, opts) {
    if (!container || !opts?.getChess || !opts.canPick || !opts.tryMove) return;
    const doc = container.ownerDocument || (typeof document !== "undefined" ? document : null);
    // Le conteneur peut survivre à une reconstruction du board : jamais deux handlers.
    if (container._tapHandlers) {
      container.removeEventListener("pointerdown", container._tapHandlers.down);
      container._tapHandlers.doc.removeEventListener("pointerup", container._tapHandlers.up);
    }
    let selected = null;
    let downX = 0;
    let downY = 0;
    let tracking = false;

    const onPointerDown = (e) => {
      downX = e.clientX;
      downY = e.clientY;
      tracking = true;
    };

    const onPointerUp = (e) => {
      if (!tracking) return;
      tracking = false;
      const moved = Math.hypot(e.clientX - downX, e.clientY - downY);
      if (moved > DRAG_THRESHOLD_PX) {
        // Vrai glisser-déposer : chessboard.js a déjà traité le drop via
        // son propre onDrop — ne pas dupliquer le coup, juste désélectionner.
        selected = null;
        clearHighlights(container);
        return;
      }
      const sqEl = squareAt(doc, container, e.clientX, e.clientY);
      const sq = sqEl?.getAttribute("data-square");
      if (!sq) return;
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

    container.addEventListener("pointerdown", onPointerDown);
    doc?.addEventListener("pointerup", onPointerUp);
    container._tapHandlers = { down: onPointerDown, up: onPointerUp, doc };
  }

  return { decide, clearHighlights, highlightMoves, attach, squareAt, DRAG_THRESHOLD_PX };
})();

if (typeof window !== "undefined") window.TapMove = TapMove;
if (typeof module !== "undefined" && module.exports != null) module.exports = TapMove;
