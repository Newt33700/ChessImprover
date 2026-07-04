/**
 * theme_service.js — Personnalisation Visuelle (EPIC 18, US 18.1/18.2/18.3)
 *
 * Gère le thème des pièces (jeu de SVG servi depuis `assets/pieces/{theme}/`)
 * et les couleurs du plateau (variables CSS lues par `style.css`), avec
 * persistance locale (US 18.3, anti-flash) + serveur (US 18.2, multi-appareil).
 *
 * Indépendance (EPIC 13/17) : tous les assets (SVG des pièces) sont servis
 * localement depuis le dépôt, aucun appel réseau externe.
 *
 * Résilience (contrainte PO explicite) : toute valeur invalide/inconnue
 * (thème inexistant, `settings` corrompu ou absent) retombe silencieusement
 * sur le thème par défaut — ne lève jamais d'exception, pour ne jamais
 * empêcher l'échiquier de s'afficher.
 */

const ThemeService = (() => {
  "use strict";

  const LOCAL_CACHE_KEY = "ci_theme_settings";

  //: Thèmes de pièces valides — chaque entrée doit avoir un dossier
  //: `assets/pieces/{theme}/` avec les 12 SVG `{w,b}{K,Q,R,B,N,P}.svg`
  //: (cf. `scripts/validate_assets.py`, US 18.1).
  const PIECE_THEMES = ["cburnett", "cyber-tactics"];
  const DEFAULT_PIECE_THEME = "cburnett";

  //: Présets de couleurs de plateau — dupliqués (volontairement) depuis
  //: `assets/boards/presets.json`, qui reste la référence documentée pour cet
  //: EPIC ; la constante ci-dessous est la source synchrone utilisée à
  //: l'exécution pour appliquer le thème sans attendre un fetch réseau (US
  //: 18.3 : éviter le flash de thème par défaut avant qu'une requête async ne
  //: résolve).
  const BOARD_THEMES = {
    classic: { light: "#f0d9b5", dark: "#b58863" },
    slate: { light: "#e2e8f0", dark: "#4a5568" },
    ocean: { light: "#dce8f0", dark: "#3f6b8f" },
    cyber: { light: "#c9d6e3", dark: "#1f2733" },
  };
  const DEFAULT_BOARD_THEME = "classic";

  //: EPIC 29 (US 29.3) — Cosmétiques débloqués par niveau : réutilise les
  //: thèmes existants (aucun nouvel asset d'avatar à fabriquer) comme
  //: catalogue de déblocages. Le thème par défaut de chaque catégorie reste
  //: au niveau 1 (jamais rien de verrouillé au tout premier lancement).
  //: Gate purement côté sélection (UI) : `applySettings` continue d'honorer
  //: n'importe quelle valeur déjà enregistrée, aucun enjeu de sécurité/jeu
  //: à verrouiller côté serveur un choix purement cosmétique.
  const UNLOCK_LEVELS = {
    piece: { cburnett: 1, "cyber-tactics": 3 },
    board: { classic: 1, slate: 1, ocean: 4, cyber: 7 },
  };

  //: Thème actuellement appliqué (mis à jour par `applySettings`) — permet à
  //: `getPieceThemePath()`/`getBoardColors()` sans argument de refléter le
  //: choix courant de l'utilisateur (utilisé par `board_manager.js` et les
  //: échiquiers indépendants d'`app.js`, qui n'ont pas accès direct aux
  //: `settings` au moment de leur construction).
  let _currentPieceTheme = DEFAULT_PIECE_THEME;
  let _currentBoardTheme = DEFAULT_BOARD_THEME;

  /** Nom de thème sûr : retombe sur `fallback` si `name` n'est pas dans `allowed`. */
  function _sanitizeThemeName(name, allowed, fallback) {
    return typeof name === "string" && allowed.includes(name) ? name : fallback;
  }

  /** Liste des thèmes de pièces disponibles (pour peupler un menu UI). */
  function listPieceThemes() {
    return PIECE_THEMES.slice();
  }

  /** Liste des thèmes de plateau disponibles (pour peupler un menu UI). */
  function listBoardThemes() {
    return Object.keys(BOARD_THEMES);
  }

  /**
   * Chemin (template `{piece}`, résolu par chessboard.js) vers le jeu de
   * pièces du thème demandé — ou du thème **actuellement appliqué** si
   * `themeName` est omis (US 18.1, utilisé par `BoardManager._initBoard()`).
   * Toujours un chemin valide : un thème inconnu retombe silencieusement
   * sur `cburnett`.
   */
  function getPieceThemePath(themeName) {
    const requested = themeName !== undefined ? themeName : _currentPieceTheme;
    const theme = _sanitizeThemeName(requested, PIECE_THEMES, DEFAULT_PIECE_THEME);
    return `assets/pieces/${theme}/{piece}.svg`;
  }

  /**
   * Couleurs `{light, dark}` du thème de plateau demandé — ou du thème
   * **actuellement appliqué** si `themeName` est omis. Toujours un objet
   * valide : un thème inconnu retombe silencieusement sur `classic`.
   */
  function getBoardColors(themeName) {
    const requested = themeName !== undefined ? themeName : _currentBoardTheme;
    const theme = _sanitizeThemeName(requested, Object.keys(BOARD_THEMES), DEFAULT_BOARD_THEME);
    return { ...BOARD_THEMES[theme] };
  }

  /** Persiste un instantané local des préférences (anti-flash, US 18.3). */
  function saveLocalCache(settings) {
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(LOCAL_CACHE_KEY, JSON.stringify(settings || {}));
      }
    } catch { /* localStorage indisponible : dégrade sans plantage */ }
  }

  /** Relit le dernier instantané local (avant toute réponse serveur). */
  function loadLocalCache() {
    try {
      if (typeof localStorage === "undefined") return {};
      const raw = localStorage.getItem(LOCAL_CACHE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  /**
   * Applique un objet `settings` (issu du profil serveur ou du cache local)
   * au DOM : couleurs de plateau (variables CSS) + classe de thème de pièces
   * sur `<body>`. Ne lève jamais — `settings` peut être `null`/`undefined`/
   * corrompu (valeurs de mauvais type) sans faire planter l'échiquier.
   */
  function applySettings(settings) {
    const safe = settings && typeof settings === "object" ? settings : {};
    const pieceTheme = _sanitizeThemeName(safe.piece_theme, PIECE_THEMES, DEFAULT_PIECE_THEME);
    const boardTheme = _sanitizeThemeName(safe.board_theme, Object.keys(BOARD_THEMES), DEFAULT_BOARD_THEME);
    const colors = getBoardColors(boardTheme);

    if (typeof document !== "undefined") {
      if (document.documentElement && document.documentElement.style) {
        document.documentElement.style.setProperty("--board-square-light", colors.light);
        document.documentElement.style.setProperty("--board-square-dark", colors.dark);
      }
      if (document.body && document.body.classList) {
        PIECE_THEMES.forEach((t) => document.body.classList.remove(`theme-${t}`));
        document.body.classList.add(`theme-${pieceTheme}`);
      }
    }
    _currentPieceTheme = pieceTheme;
    _currentBoardTheme = boardTheme;
    return { pieceTheme, boardTheme };
  }

  /** EPIC 29 (US 29.3) — Niveau requis pour débloquer `name` (1 = toujours disponible). */
  function getUnlockLevel(kind, name) {
    return UNLOCK_LEVELS[kind]?.[name] ?? 1;
  }

  /** Vrai si `name` (thème pièces/plateau) est débloqué au niveau `level`. */
  function isUnlocked(kind, name, level) {
    return getUnlockLevel(kind, name) <= (level || 1);
  }

  return {
    listPieceThemes, listBoardThemes,
    getPieceThemePath, getBoardColors,
    saveLocalCache, loadLocalCache, applySettings,
    getUnlockLevel, isUnlocked,
    DEFAULT_PIECE_THEME, DEFAULT_BOARD_THEME,
  };
})();

if (typeof window !== "undefined") window.ThemeService = ThemeService;
if (typeof module !== "undefined" && module.exports != null) module.exports = ThemeService;
