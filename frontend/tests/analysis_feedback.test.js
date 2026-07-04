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

describe("AnalysisFeedback.evalForPlayer (EPIC 25, US 25.3)", () => {
  test("camp au trait = joueur → score inchangé", () => {
    expect(AnalysisFeedback.evalForPlayer(120, "w", "w")).toBe(120);
    expect(AnalysisFeedback.evalForPlayer(-50, "b", "b")).toBe(-50);
  });

  test("camp au trait = adversaire → score inversé", () => {
    // Après le coup du joueur blanc, c'est aux noirs de jouer : un score
    // négatif pour les noirs est un avantage pour le joueur.
    expect(AnalysisFeedback.evalForPlayer(-80, "b", "w")).toBe(80);
    expect(AnalysisFeedback.evalForPlayer(200, "w", "b")).toBe(-200);
  });

  test("évaluation absente ou invalide → null", () => {
    expect(AnalysisFeedback.evalForPlayer(null, "w", "w")).toBeNull();
    expect(AnalysisFeedback.evalForPlayer(undefined, "b", "w")).toBeNull();
    expect(AnalysisFeedback.evalForPlayer("100", "w", "w")).toBeNull();
  });
});

describe("AnalysisFeedback.exerciseQuality (EPIC 25, US 25.3)", () => {
  test("coup correct → 5", () => {
    expect(AnalysisFeedback.exerciseQuality(true, null)).toBe(5);
    expect(AnalysisFeedback.exerciseQuality(true, -300)).toBe(5);
  });

  test("coup différent mais position avantageuse → 3", () => {
    expect(AnalysisFeedback.exerciseQuality(false, 1)).toBe(3);
    expect(AnalysisFeedback.exerciseQuality(false, 250)).toBe(3);
  });

  test("position égale ou perdante → 1", () => {
    expect(AnalysisFeedback.exerciseQuality(false, 0)).toBe(1);
    expect(AnalysisFeedback.exerciseQuality(false, -120)).toBe(1);
  });

  test("évaluation inconnue → 1 (pas de crédit sans preuve moteur)", () => {
    expect(AnalysisFeedback.exerciseQuality(false, null)).toBe(1);
    expect(AnalysisFeedback.exerciseQuality(false, undefined)).toBe(1);
  });
});

describe("AnalysisFeedback.isExerciseMoveCorrect (EPIC 26, US 26.1)", () => {
  test("égalité SAN stricte", () => {
    expect(AnalysisFeedback.isExerciseMoveCorrect("Ra8#", "Ra8#", "a1a8")).toBe(true);
  });

  test("correspondance UCI départ+arrivée (PV Stockfish)", () => {
    expect(AnalysisFeedback.isExerciseMoveCorrect("a1a8", "Ra8#", "a1a8")).toBe(true);
    expect(AnalysisFeedback.isExerciseMoveCorrect("e7e8q", "e8=Q+", "e7e8")).toBe(true);
  });

  test("coup différent → faux", () => {
    expect(AnalysisFeedback.isExerciseMoveCorrect("Ra8#", "Kg1", "h1g1")).toBe(false);
    expect(AnalysisFeedback.isExerciseMoveCorrect("a1a8", "Kg1", "h1g1")).toBe(false);
  });

  test("solution absente ou invalide → faux (jamais de crédit par défaut)", () => {
    expect(AnalysisFeedback.isExerciseMoveCorrect(null, "Ra8#", "a1a8")).toBe(false);
    expect(AnalysisFeedback.isExerciseMoveCorrect("", "Ra8#", "a1a8")).toBe(false);
    expect(AnalysisFeedback.isExerciseMoveCorrect(42, "Ra8#", "a1a8")).toBe(false);
  });

  test("coup joué manquant → faux", () => {
    expect(AnalysisFeedback.isExerciseMoveCorrect("Ra8#", null, null)).toBe(false);
  });
});

describe("AnalysisFeedback.describeMoveFr (EPIC 31 — coup en langage humain)", () => {
  test("pièce + trajet depuis SAN et cases départ/arrivée", () => {
    expect(AnalysisFeedback.describeMoveFr("Qxd5", "f3", "d5")).toBe("Dame f3 → d5 (prise)");
    expect(AnalysisFeedback.describeMoveFr("Be4", "d3", "e4")).toBe("Fou d3 → e4");
    expect(AnalysisFeedback.describeMoveFr("Nf3", "g1", "f3")).toBe("Cavalier g1 → f3");
  });

  test("pion (pas de lettre de pièce dans le SAN)", () => {
    expect(AnalysisFeedback.describeMoveFr("d5", "d7", "d5")).toBe("Pion d7 → d5");
    expect(AnalysisFeedback.describeMoveFr("exd5", "e4", "d5")).toBe("Pion e4 → d5 (prise)");
  });

  test("roques", () => {
    expect(AnalysisFeedback.describeMoveFr("O-O", "e1", "g1")).toBe("Petit roque");
    expect(AnalysisFeedback.describeMoveFr("O-O-O", "e8", "c8")).toBe("Grand roque");
  });

  test("promotion mentionnée", () => {
    expect(AnalysisFeedback.describeMoveFr("e8=Q", "e7", "e8")).toContain("promotion Dame");
  });

  test("cases inconnues : repli sur la destination du SAN", () => {
    expect(AnalysisFeedback.describeMoveFr("Qxd5")).toBe("Dame → d5 (prise)");
  });

  test("entrées invalides → null", () => {
    expect(AnalysisFeedback.describeMoveFr(null)).toBeNull();
    expect(AnalysisFeedback.describeMoveFr(42)).toBeNull();
  });
});

describe("AnalysisFeedback.explainMoveFr (EPIC 31 — explication pédagogique)", () => {
  test("gaffe sur une prise : conseil de comptage des échanges (POC v0)", () => {
    const txt = AnalysisFeedback.explainMoveFr("blunder", { isCapture: true, cpLoss: 470 });
    expect(txt).toContain("séquence d'échanges");
  });

  test("gaffe hors prise : perte chiffrée en pions + pièces en prise", () => {
    const txt = AnalysisFeedback.explainMoveFr("blunder", { isCapture: false, cpLoss: 300 });
    expect(txt).toContain("3.0 pions");
    expect(txt).toContain("ripostes forcées");
  });

  test("erreur : perte chiffrée + renvoi vers la suggestion moteur", () => {
    const txt = AnalysisFeedback.explainMoveFr("mistake", { cpLoss: 150 });
    expect(txt).toContain("−1.5 pion");
    expect(txt).toContain("suggestion du moteur");
  });

  test("chaque classification connue produit un texte non vide", () => {
    for (const cls of ["inaccuracy", "good", "excellent", "brilliant", "book"]) {
      expect(AnalysisFeedback.explainMoveFr(cls)).toBeTruthy();
    }
  });

  test("classification inconnue ou absente → null (pas de texte vide affiché)", () => {
    expect(AnalysisFeedback.explainMoveFr("unknown")).toBeNull();
    expect(AnalysisFeedback.explainMoveFr(undefined)).toBeNull();
  });
});
