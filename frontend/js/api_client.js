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
    const qs = query
      ? "?" + Object.entries(query)
          .filter(([, v]) => v != null && v !== "")
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
          .join("&")
      : "";
    return `${baseUrl()}${path}${qs}`;
  }

  async function _json(res) {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  /**
   * Soumet une partie à l'analyse asynchrone (US 1.1). Renvoie la réponse 202.
   * @param {string} pgn
   * @param {object} [opts] { evals, timeControl, userColor, userId }
   */
  async function analyzeGame(pgn, opts = {}) {
    const res = await fetch(url("/api/v1/games/analyze"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pgn,
        evals: opts.evals || null,
        time_control: opts.timeControl || null,
        user_color: opts.userColor || "white",
        user_id: opts.userId || null,
      }),
    });
    return _json(res);
  }

  /** Récupère le statut + les coups d'une partie. */
  async function getGame(gameId) {
    return _json(await fetch(url(`/api/v1/games/${gameId}`)));
  }

  /** Récupère le résumé agrégé des statistiques (US 4.1). */
  async function getStatsSummary(period = "30d", userId) {
    return _json(await fetch(url("/api/v1/stats/summary", { period, user_id: userId })));
  }

  /** Vrai si une base API est configurée (sinon, mode 100 % local). */
  function isConfigured() {
    return baseUrl() !== "";
  }

  return { baseUrl, url, analyzeGame, getGame, getStatsSummary, isConfigured };
})();

if (typeof window !== "undefined") window.ApiClient = ApiClient;
if (typeof module !== "undefined" && module.exports != null) module.exports = ApiClient;
