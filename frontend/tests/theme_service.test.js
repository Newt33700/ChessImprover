/**
 * Tests unitaires – ThemeService (EPIC 18, US 18.1/18.2/18.3).
 */

const ThemeService = require("../js/theme_service.js");

beforeEach(() => {
  global.document.documentElement = { style: { setProperty: jest.fn() } };
  global.document.body = { classList: { add: jest.fn(), remove: jest.fn() } };
  // `applySettings` mémorise le dernier thème appliqué (état module) pour que
  // `getPieceThemePath()`/`getBoardColors()` sans argument le reflètent
  // (US 18.1/18.2) — on réinitialise cet état avant chaque test pour éviter
  // toute pollution entre tests.
  ThemeService.applySettings({});
  document.documentElement.style.setProperty.mockClear();
  document.body.classList.add.mockClear();
  document.body.classList.remove.mockClear();
});

afterEach(() => {
  try { localStorage.clear(); } catch { /* ignore */ }
});

describe("getPieceThemePath (US 18.1)", () => {
  test("thème valide résolu vers son dossier", () => {
    expect(ThemeService.getPieceThemePath("cyber-tactics")).toBe("assets/pieces/cyber-tactics/{piece}.svg");
  });

  test("thème par défaut si aucun argument", () => {
    expect(ThemeService.getPieceThemePath()).toBe("assets/pieces/cburnett/{piece}.svg");
  });

  test("retombe sur le thème par défaut si le nom est inconnu (pas de plantage)", () => {
    expect(ThemeService.getPieceThemePath("does-not-exist")).toBe("assets/pieces/cburnett/{piece}.svg");
  });

  test("retombe sur le thème par défaut pour une valeur non-string (JSONB corrompu)", () => {
    expect(ThemeService.getPieceThemePath(123)).toBe("assets/pieces/cburnett/{piece}.svg");
    expect(ThemeService.getPieceThemePath(null)).toBe("assets/pieces/cburnett/{piece}.svg");
    expect(ThemeService.getPieceThemePath({})).toBe("assets/pieces/cburnett/{piece}.svg");
  });

  test("sans argument, reflète le dernier thème appliqué (US 18.1 — BoardManager._initBoard)", () => {
    ThemeService.applySettings({ piece_theme: "cyber-tactics" });
    expect(ThemeService.getPieceThemePath()).toBe("assets/pieces/cyber-tactics/{piece}.svg");
  });
});

describe("getBoardColors (US 18.2)", () => {
  test("thème valide renvoie ses couleurs", () => {
    expect(ThemeService.getBoardColors("slate")).toEqual({ light: "#e2e8f0", dark: "#4a5568" });
  });

  test("thème inconnu retombe sur 'classic' (pas de plantage)", () => {
    expect(ThemeService.getBoardColors("neon-rainbow")).toEqual({ light: "#f0d9b5", dark: "#b58863" });
  });

  test("valeur non-string retombe sur 'classic'", () => {
    expect(ThemeService.getBoardColors(42)).toEqual({ light: "#f0d9b5", dark: "#b58863" });
  });

  test("renvoie une copie (pas la référence interne)", () => {
    const colors = ThemeService.getBoardColors("classic");
    colors.light = "#000000";
    expect(ThemeService.getBoardColors("classic").light).toBe("#f0d9b5");
  });

  test("sans argument, reflète le dernier thème appliqué (US 18.2)", () => {
    ThemeService.applySettings({ board_theme: "ocean" });
    expect(ThemeService.getBoardColors()).toEqual({ light: "#dce8f0", dark: "#3f6b8f" });
  });
});

describe("listPieceThemes / listBoardThemes", () => {
  test("expose les thèmes disponibles pour peupler un menu", () => {
    expect(ThemeService.listPieceThemes()).toEqual(["cburnett", "cyber-tactics"]);
    expect(ThemeService.listBoardThemes()).toEqual(["classic", "slate", "ocean", "cyber"]);
  });
});

describe("saveLocalCache / loadLocalCache (US 18.3)", () => {
  test("round-trip simple", () => {
    ThemeService.saveLocalCache({ piece_theme: "cyber-tactics", board_theme: "cyber" });
    expect(ThemeService.loadLocalCache()).toEqual({ piece_theme: "cyber-tactics", board_theme: "cyber" });
  });

  test("objet vide si rien n'est en cache", () => {
    expect(ThemeService.loadLocalCache()).toEqual({});
  });

  test("objet vide si le cache contient du JSON corrompu (pas de plantage)", () => {
    localStorage.setItem("ci_theme_settings", "{not valid json");
    expect(ThemeService.loadLocalCache()).toEqual({});
  });

  test("objet vide si le cache contient une valeur non-objet", () => {
    localStorage.setItem("ci_theme_settings", "42");
    expect(ThemeService.loadLocalCache()).toEqual({});
  });
});

describe("applySettings (US 18.1/18.2/18.3 — résilience)", () => {
  test("applique les couleurs de plateau en variables CSS", () => {
    ThemeService.applySettings({ board_theme: "ocean" });
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith("--board-square-light", "#dce8f0");
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith("--board-square-dark", "#3f6b8f");
  });

  test("bascule la classe de thème de pièces sur <body>", () => {
    ThemeService.applySettings({ piece_theme: "cyber-tactics" });
    expect(document.body.classList.add).toHaveBeenCalledWith("theme-cyber-tactics");
    // Les autres thèmes sont retirés avant d'ajouter le nouveau (pas de cumul).
    expect(document.body.classList.remove).toHaveBeenCalledWith("theme-cburnett");
    expect(document.body.classList.remove).toHaveBeenCalledWith("theme-cyber-tactics");
  });

  test("renvoie les thèmes réellement appliqués (sanitizés)", () => {
    expect(ThemeService.applySettings({ piece_theme: "cyber-tactics", board_theme: "cyber" }))
      .toEqual({ pieceTheme: "cyber-tactics", boardTheme: "cyber" });
  });

  test("ne plante jamais sur des settings absents/null", () => {
    expect(() => ThemeService.applySettings(undefined)).not.toThrow();
    expect(() => ThemeService.applySettings(null)).not.toThrow();
    expect(ThemeService.applySettings(null)).toEqual({ pieceTheme: "cburnett", boardTheme: "classic" });
  });

  test("ne plante jamais sur un thème invalide dans le JSONB (valeur corrompue) — retombe sur défaut", () => {
    const result = ThemeService.applySettings({ piece_theme: 12345, board_theme: { oops: true } });
    expect(result).toEqual({ pieceTheme: "cburnett", boardTheme: "classic" });
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith("--board-square-light", "#f0d9b5");
  });

  test("ne plante jamais si document/documentElement/body sont indisponibles", () => {
    const savedDoc = global.document;
    global.document = {};
    expect(() => ThemeService.applySettings({ piece_theme: "cyber-tactics" })).not.toThrow();
    global.document = savedDoc;
  });
});
