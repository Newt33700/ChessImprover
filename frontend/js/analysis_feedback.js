/**
 * analysis_feedback.js — Anti-spam du feedback d'analyse (EPIC 22, US 22.1).
 *
 * Le moteur Stockfish émet plusieurs messages `info` par position analysée
 * (un par profondeur atteinte) : sans garde-fou, chaque coup déclenche des
 * dizaines d'événements `move:accuracy` identiques, donc autant d'alertes
 * empilées au-dessus de l'échiquier (bug « toast-spamming », Image 1).
 *
 * Ce module est PUR à l'exception de `drawFeedback` (EPIC 37, US 37.1) —
 * seule fonction qui touche le monde extérieur, et seulement via l'API
 * Chessground reçue en paramètre (jamais `document`/`window` directement),
 * donc testable avec un simple double (`{ setShapes: jest.fn() }`).
 *
 *   - `shouldDispatch` : n'émettre `move:accuracy` que si le résultat du coup
 *     a réellement changé depuis la dernière émission (dédoublonnage) ;
 *   - `shouldAlert`    : ne déclencher l'alerte Coach (bandeau + beep + voix)
 *     qu'UNE SEULE fois par coup et par partie, quelle que soit la
 *     classification raffinée ensuite par le moteur ;
 *   - `drawFeedback`   : flèches rouge (coup joué/erreur, opacité 0.6) et
 *     verte (suggestion moteur, opacité 0.8) sur l'échiquier principal, à la
 *     place de l'ancien overlay SVG maison (les brushes `red`/`green` sont
 *     configurées avec ces opacités à la construction du board, cf.
 *     `board_manager.js:_initBoard`).
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

  /**
   * EPIC 26 (US 26.1) — Un coup joué correspond-il au coup attendu de la
   * solution ? Les cartes SRS stockent la PV soit en SAN (`"Ra8#"`), soit en
   * UCI (`"a1a8"`) : on accepte l'égalité SAN stricte OU la correspondance
   * des cases départ+arrivée (préfixe UCI, la promotion étant normalisée en
   * dame des deux côtés). Fonction pure, partagée par la page Exercice.
   */
  function isExerciseMoveCorrect(expected, playedSan, playedFromTo) {
    if (!expected || typeof expected !== "string") return false;
    if (playedSan && playedSan === expected) return true;
    return !!(playedFromTo && playedFromTo === expected.slice(0, 4));
  }

  // ── EPIC 31 — Commentaires pédagogiques par coup (retour du POC v0) ──

  const PIECE_NAMES_FR = { K: "Roi", Q: "Dame", R: "Tour", B: "Fou", N: "Cavalier" };

  /**
   * Description humaine d'un coup en français (POC v0 : « Queen f3xd5 » →
   * « Dame f3 → d5 (prise) ») depuis le SAN et, si connues, les cases
   * départ/arrivée. Roques et promotions gérés ; entrées invalides → null.
   */
  function describeMoveFr(san, from, to) {
    if (!san || typeof san !== "string") return null;
    if (san.startsWith("O-O-O")) return "Grand roque";
    if (san.startsWith("O-O"))   return "Petit roque";
    const piece = PIECE_NAMES_FR[san[0]] || "Pion";
    const capture = san.includes("x") ? " (prise)" : "";
    const promo = /=([QRBN])/.exec(san);
    const promoTxt = promo ? ` — promotion ${PIECE_NAMES_FR[promo[1]] || "Dame"}` : "";
    const path = from && to ? `${from} → ${to}` : `→ ${san.replace(/[+#]$/, "").replace(/=[QRBN]/, "").slice(-2)}`;
    return `${piece} ${path}${capture}${promoTxt}`;
  }

  /**
   * Explication pédagogique en français selon la classification du coup —
   * l'esprit du POC v0 (« The capture gave too much back… ») : comprendre
   * QUOI faire la prochaine fois, pas seulement voir un badge. Fonction
   * pure ; classification inconnue → null (pas de texte vide affiché).
   */
  function explainMoveFr(classification, { isCapture = false, cpLoss = null } = {}) {
    const pawns = typeof cpLoss === "number" ? (cpLoss / 100).toFixed(1) : null;
    switch (classification) {
      case "blunder":
        if (isCapture) {
          return "Cette prise rend trop de matériel. Avant de prendre, comptez toute la séquence d'échanges : votre prise, la reprise adverse, votre suite — et le bilan matériel final.";
        }
        return `Ce coup perd environ ${pawns ?? "plusieurs"} pion${pawns && parseFloat(pawns) < 2 ? "" : "s"} d'avantage. Avant de jouer, cherchez les pièces laissées en prise et les ripostes forcées (échecs, prises, menaces).`;
      case "mistake":
        return `Ce coup dégrade nettement votre position${pawns ? ` (−${pawns} pion${parseFloat(pawns) < 2 ? "" : "s"})` : ""}. Comparez avec la suggestion du moteur pour repérer l'idée manquée.`;
      case "inaccuracy":
        return "Imprécision : un coup plus actif conservait un meilleur contrôle de la position.";
      case "good":
        return "Bon choix — ce coup garde l'évaluation stable.";
      case "excellent":
        return "Excellent — pratiquement le meilleur coup de la position.";
      case "brilliant":
        return "Brillant ! Le meilleur coup du moteur, difficile à trouver.";
      case "book":
        return "Coup de théorie : cette position fait partie des ouvertures connues.";
      default:
        return null;
    }
  }

  // ── EPIC 37 (US 37.1) — Coaching visuel : flèches sur l'échiquier ──

  /** Vrai si `m` a la forme minimale `{from, to}` (cases algébriques). */
  function _isSquarePair(m) {
    return !!(m && /^[a-h][1-8]$/.test(m.from || "") && /^[a-h][1-8]$/.test(m.to || ""));
  }

  /**
   * Dessine (ou efface) les flèches de feedback sur l'échiquier principal :
   * rouge pour `playedMove` (le coup joué, s'il est en erreur), verte pour
   * `bestMove` (la suggestion moteur). `cg` est l'instance Chessground
   * (`board_manager.js:this.board`) — `null`/sans `setShapes` ne fait rien
   * (échiquier pas encore prêt). `playedMove`/`bestMove` : `{from, to}` ou
   * `null`/`undefined` pour ne pas dessiner cette flèche (ex. hors Review,
   * ou coup joué == suggestion moteur, cf. appelant `app.js:_drawReviewArrows`).
   * Les couleurs/opacités (rouge 0.6, verte 0.8) sont celles configurées dans
   * `drawable.brushes` à la construction du board, pas ici.
   */
  function drawFeedback(cg, playedMove, bestMove) {
    if (!cg || typeof cg.setShapes !== "function") return;
    const shapes = [];
    if (_isSquarePair(playedMove)) {
      shapes.push({ orig: playedMove.from, dest: playedMove.to, brush: "red" });
    }
    if (_isSquarePair(bestMove)) {
      shapes.push({ orig: bestMove.from, dest: bestMove.to, brush: "green" });
    }
    cg.setShapes(shapes);
  }

  return {
    createState, shouldDispatch, shouldAlert, drawFeedback,
    evalForPlayer, exerciseQuality, isExerciseMoveCorrect,
    describeMoveFr, explainMoveFr,
  };
})();

if (typeof window !== "undefined") window.AnalysisFeedback = AnalysisFeedback;
if (typeof module !== "undefined" && module.exports != null) module.exports = AnalysisFeedback;
