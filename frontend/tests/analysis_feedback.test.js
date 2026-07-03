/**
 * Tests — analysis_feedback.js (EPIC 22, US 22.1)
 *
 * Garantit l'élimination du « toast-spamming » : un seul dispatch par
 * résultat d'analyse identique, une seule alerte Coach par coup.
 */

const AnalysisFeedback = require("../js/analysis_feedback.js");

describe("AnalysisFeedback.createState", () => {
  test("retourne un état vide indépendant à chaque appel", () => {
    const a = AnalysisFeedback.createState();
    const b = AnalysisFeedback.createState();
    expect(a).not.toBe(b);
    expect(Object.keys(a.dispatched)).toHaveLength(0);
    expect(Object.keys(a.alerted)).toHaveLength(0);
  });
});

describe("AnalysisFeedback.shouldDispatch — dédoublonnage move:accuracy", () => {
  let state;
  beforeEach(() => { state = AnalysisFeedback.createState(); });

  test("première évaluation d'un coup → dispatch", () => {
    expect(AnalysisFeedback.shouldDispatch(state, 0, 120, false)).toBe(true);
  });

  test("même cpLoss ré-émis par le moteur (profondeurs successives) → PAS de re-dispatch", () => {
    AnalysisFeedback.shouldDispatch(state, 3, 250, false);
    // Le worker renvoie 20 messages `info` identiques pour le même coup :
    for (let i = 0; i < 20; i++) {
      expect(AnalysisFeedback.shouldDispatch(state, 3, 250, false)).toBe(false);
    }
  });

  test("cpLoss raffiné (valeur différente) → re-dispatch autorisé", () => {
    AnalysisFeedback.shouldDispatch(state, 3, 250, false);
    expect(AnalysisFeedback.shouldDispatch(state, 3, 310, false)).toBe(true);
    expect(AnalysisFeedback.shouldDispatch(state, 3, 310, false)).toBe(false);
  });

  test("variation infra-centipion (arrondi identique) → PAS de re-dispatch", () => {
    AnalysisFeedback.shouldDispatch(state, 5, 100.2, false);
    expect(AnalysisFeedback.shouldDispatch(state, 5, 100.4, false)).toBe(false);
  });

  test("bascule book → moteur re-dispatch (signature différente)", () => {
    AnalysisFeedback.shouldDispatch(state, 2, 0, true);
    expect(AnalysisFeedback.shouldDispatch(state, 2, 0, false)).toBe(true);
  });

  test("coups distincts sont indépendants", () => {
    expect(AnalysisFeedback.shouldDispatch(state, 0, 50, false)).toBe(true);
    expect(AnalysisFeedback.shouldDispatch(state, 1, 50, false)).toBe(true);
  });

  test("entrées invalides (état null, index négatif/absent) → jamais de dispatch", () => {
    expect(AnalysisFeedback.shouldDispatch(null, 0, 50, false)).toBe(false);
    expect(AnalysisFeedback.shouldDispatch(state, -1, 50, false)).toBe(false);
    expect(AnalysisFeedback.shouldDispatch(state, null, 50, false)).toBe(false);
  });

  test("cpLoss null/undefined traité comme 0 sans lever d'exception", () => {
    expect(AnalysisFeedback.shouldDispatch(state, 7, null, false)).toBe(true);
    expect(AnalysisFeedback.shouldDispatch(state, 7, undefined, false)).toBe(false);
  });
});

describe("AnalysisFeedback.shouldAlert — une seule alerte Coach par coup", () => {
  let state;
  beforeEach(() => { state = AnalysisFeedback.createState(); });

  test("blunder → alerte la première fois seulement", () => {
    expect(AnalysisFeedback.shouldAlert(state, 4, "blunder")).toBe(true);
    expect(AnalysisFeedback.shouldAlert(state, 4, "blunder")).toBe(false);
    expect(AnalysisFeedback.shouldAlert(state, 4, "mistake")).toBe(false);
  });

  test("mistake → alerte la première fois seulement", () => {
    expect(AnalysisFeedback.shouldAlert(state, 9, "mistake")).toBe(true);
    expect(AnalysisFeedback.shouldAlert(state, 9, "mistake")).toBe(false);
  });

  test("classifications non alertables → jamais d'alerte", () => {
    for (const cls of ["book", "brilliant", "excellent", "good", "inaccuracy", "unknown", null]) {
      expect(AnalysisFeedback.shouldAlert(state, 1, cls)).toBe(false);
    }
  });

  test("coups distincts alertent indépendamment", () => {
    expect(AnalysisFeedback.shouldAlert(state, 1, "blunder")).toBe(true);
    expect(AnalysisFeedback.shouldAlert(state, 2, "blunder")).toBe(true);
  });

  test("nouvel état (nouvelle partie) ré-autorise l'alerte du même index", () => {
    AnalysisFeedback.shouldAlert(state, 1, "blunder");
    const fresh = AnalysisFeedback.createState();
    expect(AnalysisFeedback.shouldAlert(fresh, 1, "blunder")).toBe(true);
  });

  test("entrées invalides → jamais d'alerte", () => {
    expect(AnalysisFeedback.shouldAlert(null, 1, "blunder")).toBe(false);
    expect(AnalysisFeedback.shouldAlert(state, -1, "blunder")).toBe(false);
    expect(AnalysisFeedback.shouldAlert(state, null, "blunder")).toBe(false);
  });
});
