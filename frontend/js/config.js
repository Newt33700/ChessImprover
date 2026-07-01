/**
 * config.js — Configuration runtime du frontend (chargé avant les autres scripts).
 *
 * `API_BASE` : URL du backend d'analyse (Render). Laisser vide ("") pour le
 * mode 100 % local (le frontend retombe alors sur les données de démonstration
 * `AdvancedStats.MOCK_SUMMARY`). Peut être surchargé sans redéploiement via
 * `localStorage.setItem("apiBase", "https://…")`.
 */
window.API_BASE = "https://chess-improver-api.onrender.com";
