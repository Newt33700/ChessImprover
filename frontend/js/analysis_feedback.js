/**
 * analysis_feedback.js — Anti-spam du feedback d'analyse (EPIC 22, US 22.1).
 *
 * Le moteur Stockfish émet plusieurs messages `info` par position analysée
 * (un par profondeur atteinte) : sans garde-fou, chaque coup déclenche des
 * dizaines d'événements `move:accuracy` identiques, donc autant d'alertes
 * empilées au-dessus de l'échiquier (bug « toast-spamming », Image 1).
 *
 * Ce module PUR (aucune dépendance DOM) centralise deux décisions :
 *   - `shouldDispatch` : n'émettre `move:accuracy` que si le résultat du coup
 *     a réellement changé depuis la dernière émission (dédoublonnage) ;
 *   - `shouldAlert`    : ne déclencher l'alerte Coach (bandeau + beep + voix)
 *     qu'UNE SEULE fois par coup et par partie, quelle que soit la
 *     classification raffinée ensuite par le moteur.
 */

const AnalysisFeedback = (() => {
  "use strict";

  /** État neuf, à recréer à chaque nouvelle partie/review. */
  function createState() {
    return {
      dispatched: Object.create(null), // moveIdx -> signature du dernier dispatch
      alerted: Object.create(null),    // moveIdx -> true si l'alerte Coach a déjà été émise
    };
  }

  /** Signature stable d'un résultat d'analyse (cpLoss arrondi + flag book). */
  function _signature(cpLoss, book) {
    return `${book ? "b" : "m"}:${Math.round(cpLoss ?? 0)}`;
  }

  /**
   * Vrai si l'événement `move:accuracy` pour ce coup apporte une information
   * nouvelle (première évaluation, ou cpLoss/flag book modifié). Enregistre
   * la signature en cas d'émission — l'appelant DOIT alors dispatcher.
   */
  function shouldDispatch(state, moveIdx, cpLoss, book) {
    if (!state || moveIdx == null || moveIdx < 0) return false;
    const sig = _signature(cpLoss, book);
    if (state.dispatched[moveIdx] === sig) return false;
    state.dispatched[moveIdx] = sig;
    return true;
  }

  /**
   * Vrai si l'alerte Coach (blunder/mistake) doit être émise pour ce coup :
   * classification alertable ET jamais alerté auparavant. Marque le coup
   * comme alerté en cas d'émission (une seule alerte par coup, US 22.1).
   */
  function shouldAlert(state, moveIdx, classification) {
    if (!state || moveIdx == null || moveIdx < 0) return false;
    if (classification !== "blunder" && classification !== "mistake") return false;
    if (state.alerted[moveIdx]) return false;
    state.alerted[moveIdx] = true;
    return true;
  }

  /**
   * EPIC 25 (US 25.3, ex-gap §10.3) — Évaluation du point de vue du joueur :
   * le moteur renvoie toujours le score du camp AU TRAIT ; après le coup du
   * joueur c'est l'adversaire qui est au trait, il faut donc inverser.
   * @returns {number|null} centipions positifs = avantage joueur
   */
  function evalForPlayer(evaluation, sideToMove, playerColor) {
    if (evaluation == null || typeof evaluation !== "number") return null;
    return sideToMove === playerColor ? evaluation : -evaluation;
  }

  /**
   * EPIC 25 (US 25.3) — Qualité SM-2 nuancée d'une tentative d'exercice :
   *   5 = coup correct ;
   *   3 = coup différent de la solution mais la position reste avantageuse
   *       pour le joueur (`playerEvalCp > 0`) — « correct mais non optimal » ;
   *   1 = raté (position non avantageuse, ou évaluation inconnue : pas de
   *       crédit sans preuve moteur).
   */
  function exerciseQuality(correct, playerEvalCp) {
    if (correct) return 5;
    if (typeof playerEvalCp === "number" && playerEvalCp > 0) return 3;
    return 1;
  }

  return { createState, shouldDispatch, shouldAlert, evalForPlayer, exerciseQuality };
})();

if (typeof window !== "undefined") window.AnalysisFeedback = AnalysisFeedback;
if (typeof module !== "undefined" && module.exports != null) module.exports = AnalysisFeedback;
