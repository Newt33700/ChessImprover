/**
 * api_client.js — Client HTTP du backend Chess Improver (EPIC 1).
 *
 * Centralise les appels au serveur d'analyse async + agrégation de stats.
 * La base URL est résolue dans l'ordre : `window.API_BASE`, puis
 * `localStorage['apiBase']`, sinon chaîne vide (chemins relatifs / même origine).
 *
 * Toutes les méthodes sont « best-effort » : en cas d'erreur réseau, elles
 * rejettent — l'appelant décide de retomber sur un comportement local
 * (ex. `AdvancedStats.MOCK_SUMMARY`).
 */

const ApiClient = (() => {
  "use strict";

  function baseUrl() {
    if (typeof window !== "undefined" && window.API_BASE != null) return window.API_BASE;
    try {
      const stored = (typeof localStorage !== "undefined") && localStorage.getItem("apiBase");
      if (stored) return stored;
    } catch {
      /* localStorage indisponible */
    }
    return "";
  }

  /** Construit une URL absolue/relative vers le backend. */
  function url(path, query) {
    const pairs = query
      ? Object.entries(query)
          .filter(([, v]) => v != null && v !== "")
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      : [];
    const qs = pairs.length ? `?${pairs.join("&")}` : "";
    return `${baseUrl()}${path}${qs}`;
  }

  async function _json(res) {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  /**
   * En-tête d'authentification (US 6.4) : ces routes dérivent désormais
   * systématiquement `user_id` du JWT côté serveur — jamais d'un champ
   * fourni par le client. Sans token, l'appel échoue en 401 (l'appelant
   * dégrade déjà proprement, ex. `AdvancedStats.MOCK_SUMMARY`).
   */
  function _authHeaders() {
    const token = typeof window !== "undefined" && window.Auth && window.Auth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /**
   * Soumet une partie à l'analyse asynchrone (US 1.1). Renvoie la réponse 202.
   * @param {string} pgn
   * @param {object} [opts] { evals, timeControl, userColor }
   */
  async function analyzeGame(pgn, opts = {}) {
    const res = await fetch(url("/api/v1/games/analyze"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({
        pgn,
        evals: opts.evals || null,
        time_control: opts.timeControl || null,
        user_color: opts.userColor || "white",
      }),
    });
    return _json(res);
  }

  /** Récupère le statut + les coups d'une partie. */
  async function getGame(gameId) {
    return _json(await fetch(url(`/api/v1/games/${gameId}`), { headers: _authHeaders() }));
  }

  /** Liste les parties déjà soumises/analysées de l'utilisateur authentifié (US 7.1). */
  async function getGames() {
    return _json(await fetch(url("/api/v1/games"), { headers: _authHeaders() }));
  }

  /** Bascule le statut « déjà étudiée » d'une partie (US 7.3). */
  async function updateGameStatus(gameId, isReviewed) {
    const res = await fetch(url(`/api/v1/games/${gameId}/status`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ is_reviewed: isReviewed }),
    });
    return _json(res);
  }

  /**
   * Sélectionne le prochain problème tactique (US 8.1/8.2), proche de l'Elo
   * tactique de l'utilisateur. `themeId` filtre par catégorie ("Aléatoire"
   * = omis/vide). Ne renvoie jamais la solution.
   */
  async function getNextTacticalProblem(themeId) {
    return _json(
      await fetch(url("/api/v1/tactics/next", { theme_id: themeId }), { headers: _authHeaders() })
    );
  }

  /**
   * Soumet le coup joué pour un problème tactique (US 8.3). La validation
   * (coup correct ou non) est faite côté serveur exclusivement — le
   * frontend ne fait que relayer le SAN joué, jamais la solution attendue.
   */
  async function submitTacticalAttempt(problemId, move, timeTaken) {
    const res = await fetch(url("/api/v1/tactics/attempt"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ problem_id: problemId, move, time_taken: timeTaken ?? null }),
    });
    return _json(res);
  }

  /** Récupère le taux de réussite par catégorie + la série en cours (US 8.4). */
  async function getTacticsStats() {
    return _json(await fetch(url("/api/v1/tactics/stats"), { headers: _authHeaders() }));
  }

  /**
   * Profil d'erreurs comportementales (EPIC 11, US 9.1) : un score de
   * fréquence (0-100) par type d'erreur déjà observé, avec `is_recurring`
   * calculé côté serveur (score > 70).
   */
  async function getErrorProfile() {
    return _json(await fetch(url("/api/v1/error-profile"), { headers: _authHeaders() }));
  }

  /**
   * Problème tactique ciblant un type d'erreur du profil comportemental
   * (EPIC 11, US 9.2 — bouton « Entraînement Personnalisé »). `focus` est un
   * `error_type` (`hanging_piece`/`time_pressure`/`missed_mate`), pas un
   * `theme_id` tactique brut : le backend fait la correspondance.
   */
  async function getCustomTacticalProblem(focus) {
    return _json(
      await fetch(url("/api/v1/tactics/custom", { focus }), { headers: _authHeaders() })
    );
  }

  /**
   * Sélectionne la prochaine position de finale (EPIC 10), proche de l'Elo
   * « finales » de l'utilisateur. `themeId` filtre par catégorie de mat.
   */
  async function getNextEndgameProblem(themeId) {
    return _json(
      await fetch(url("/api/v1/endgames/next", { theme_id: themeId }), { headers: _authHeaders() })
    );
  }

  /** Soumet le coup joué pour une position de finale (EPIC 10) ; validation 100 % serveur. */
  async function submitEndgameAttempt(problemId, move) {
    const res = await fetch(url("/api/v1/endgames/attempt"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ problem_id: problemId, move }),
    });
    return _json(res);
  }

  /**
   * Ajoute une ligne au répertoire d'ouvertures (EPIC 9, US 9.1). Le backend
   * rejoue la séquence coup par coup et rejette (422) toute ligne illégale.
   * @param {{name: string, color: 'white'|'black', moves: string[]}} line
   */
  async function createOpeningLine(line) {
    const res = await fetch(url("/api/v1/openings/repertoire"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify(line),
    });
    return _json(res);
  }

  /** Liste tout le répertoire de l'utilisateur (EPIC 9). */
  async function getOpeningLines() {
    return _json(await fetch(url("/api/v1/openings/repertoire"), { headers: _authHeaders() }));
  }

  /** Lignes dont l'échéance de révision est arrivée aujourd'hui (EPIC 9, US 9.2). */
  async function getDueOpeningLines() {
    return _json(
      await fetch(url("/api/v1/openings/repertoire/due"), { headers: _authHeaders() })
    );
  }

  /**
   * Soumet le résultat d'une session de révision (EPIC 9, US 9.2). La
   * qualité SM-2 est déduite côté serveur du nombre d'erreurs commises —
   * pas de notation manuelle, pour rester ludique.
   */
  async function reviewOpeningLine(lineId, mistakeCount) {
    const res = await fetch(url(`/api/v1/openings/repertoire/${lineId}/review`), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ mistake_count: mistakeCount }),
    });
    return _json(res);
  }

  /** Retire une ligne du répertoire (EPIC 9). */
  async function deleteOpeningLine(lineId) {
    const res = await fetch(url(`/api/v1/openings/repertoire/${lineId}`), {
      method: "DELETE",
      headers: _authHeaders(),
    });
    return _json(res);
  }

  /** Récupère le résumé agrégé des statistiques (US 4.1). */
  async function getStatsSummary(period = "30d") {
    return _json(await fetch(url("/api/v1/stats/summary", { period }), { headers: _authHeaders() }));
  }

  /** Récupère l'historique des snapshots Elo virtuel pour une cadence (US 5.1). */
  async function getStatsHistory(cadence = "blitz", days = 30) {
    return _json(
      await fetch(url("/api/v1/stats/history", { cadence, days }), { headers: _authHeaders() })
    );
  }

  /** Démarre un sprint tactique (EPIC 12, US 11.1) — chrono fixé côté serveur. */
  async function startSprint() {
    const res = await fetch(url("/api/v1/sprints/start"), {
      method: "POST",
      headers: _authHeaders(),
    });
    return _json(res);
  }

  /** Soumet un coup pour le problème en cours d'un sprint (EPIC 12, US 11.1). */
  async function submitSprintAttempt(sprintId, problemId, move) {
    const res = await fetch(url(`/api/v1/sprints/${sprintId}/attempt`), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ problem_id: problemId, move }),
    });
    return _json(res);
  }

  /** Clôture un sprint (temps écoulé côté client ou abandon volontaire, EPIC 12). */
  async function finishSprint(sprintId) {
    const res = await fetch(url(`/api/v1/sprints/${sprintId}/finish`), {
      method: "POST",
      headers: _authHeaders(),
    });
    return _json(res);
  }

  /** Meilleur sprint terminé, pour le replay Ghost (EPIC 12, US 11.2). */
  async function getGhostReplay() {
    return _json(await fetch(url("/api/v1/sprints/ghost"), { headers: _authHeaders() }));
  }

  /**
   * Dashboard de Performance Cognitive (EPIC 19, US 19.1/19.2) : répartition
   * du temps de réflexion par phase/pression + fluidité de décision.
   */
  async function getCognitiveLoad() {
    return _json(await fetch(url("/api/v1/stats/cognitive-load"), { headers: _authHeaders() }));
  }

  /** Le Cimetière des Erreurs complet (EPIC 20, US 20.1) — jamais la solution. */
  async function getFlashcards() {
    return _json(await fetch(url("/api/v1/flashcards"), { headers: _authHeaders() }));
  }

  /** Flashcards dont l'échéance de révision est atteinte (EPIC 20, US 20.2). */
  async function getDueFlashcards() {
    return _json(await fetch(url("/api/v1/flashcards/due"), { headers: _authHeaders() }));
  }

  /**
   * Soumet une tentative de rappel actif (EPIC 20, US 20.2). La validation
   * du coup et la qualité SM-2 (déduite du résultat) sont 100 % serveur.
   */
  async function reviewFlashcard(cardId, move) {
    const res = await fetch(url(`/api/v1/flashcards/${cardId}/review`), {
      method: "POST",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ move }),
    });
    return _json(res);
  }

  /** Vrai si une base API est configurée (sinon, mode 100 % local). */
  function isConfigured() {
    return baseUrl() !== "";
  }

  return {
    baseUrl, url, analyzeGame, getGame, getGames, updateGameStatus,
    getNextTacticalProblem, submitTacticalAttempt, getTacticsStats,
    createOpeningLine, getOpeningLines, getDueOpeningLines, reviewOpeningLine, deleteOpeningLine,
    getNextEndgameProblem, submitEndgameAttempt,
    getErrorProfile, getCustomTacticalProblem,
    startSprint, submitSprintAttempt, finishSprint, getGhostReplay,
    getStatsSummary, getStatsHistory, isConfigured,
    getCognitiveLoad, getFlashcards, getDueFlashcards, reviewFlashcard,
  };
})();

if (typeof window !== "undefined") window.ApiClient = ApiClient;
if (typeof module !== "undefined" && module.exports != null) module.exports = ApiClient;
