/**
 * US 7 – Auth & Cloud Persistence
 * Gère l'inscription, la connexion, les JWT et la synchronisation cloud.
 */

const Auth = (() => {
  // Base API résolue à chaque appel (pas au chargement du module) :
  // 1. `window.CI_API_URL`  — surcharge explicite (tests E2E) ;
  // 2. `window.API_BASE`    — configuration de production (config.js) ;
  // 3. fallback dev local. Avant ce correctif, la prod (où seul API_BASE est
  //    défini) retombait silencieusement sur http://localhost:8000.
  function _apiBase() {
    if (typeof window !== "undefined") {
      if (window.CI_API_URL != null) return window.CI_API_URL;
      if (window.API_BASE != null) return window.API_BASE;
    }
    // US 22.3 : même surcharge que ApiClient (`localStorage['apiBase']`) —
    // Auth et ApiClient doivent TOUJOURS parler au même backend, sinon le
    // JWT émis par l'un est invalide pour l'autre (faux « déconnecté »).
    try {
      const stored = (typeof localStorage !== "undefined") && localStorage.getItem("apiBase");
      if (stored) return stored;
    } catch { /* localStorage indisponible */ }
    return "http://localhost:8000";
  }
  const TOKEN_KEY = "ci_jwt";
  const USER_KEY  = "ci_user";

  // ── Stockage JWT ────────────────────────────────────────────────────

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  }

  function getUser() {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }

  function _saveSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  // ── Appels API ──────────────────────────────────────────────────────

  // FastAPI renvoie soit une chaîne (`detail`), soit une liste d'erreurs de
  // validation Pydantic (422, un objet `{msg, loc, type}` par champ invalide).
  function _extractErrorMessage(data) {
    const detail = data && data.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d) => (d && d.msg) || String(d)).join(" ; ");
    }
    return "Erreur serveur";
  }

  async function _request(method, path, body, token) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${_apiBase()}${path}`, {
      method,
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(_extractErrorMessage(data));
    return data;
  }

  async function _post(path, body, token) {
    return _request("POST", path, body, token);
  }

  async function _patch(path, body, token) {
    return _request("PATCH", path, body, token);
  }

  // ── Inscription ─────────────────────────────────────────────────────

  async function signup(email, username, password) {
    const data = await _post("/auth/signup", { email, username, password });
    _saveSession(data.token, data.user);
    return data;
  }

  // ── Connexion ───────────────────────────────────────────────────────

  async function login(email, password) {
    const data = await _post("/auth/login", { email, password });
    _saveSession(data.token, data.user);
    return data;
  }

  // ── Auto-connexion (vérifie le token local) ─────────────────────────

  async function autoConnect() {
    const token = getToken();
    if (!token) return null;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await fetch(`${_apiBase()}/auth/me`, { headers });
      if (!res.ok) { logout(); return null; }
      const user = await res.json();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return user;
    } catch {
      return null;
    }
  }

  // ── Profil : liaison Chess.com (US 6.3) ──────────────────────────────

  async function updateChessUsername(chessUsername) {
    const token = getToken();
    if (!token) throw new Error("Non connecté");
    const user = await _patch("/auth/me", { chess_username: chessUsername || "" }, token);
    _saveSession(token, user);
    return user;
  }

  // ── Personnalisation Visuelle (EPIC 18, US 18.2/18.3) ────────────────

  async function updateSettings(settings) {
    const token = getToken();
    if (!token) throw new Error("Non connecté");
    const user = await _patch("/auth/me/settings", { settings: settings || {} }, token);
    _saveSession(token, user);
    return user;
  }

  // ── Synchronisation (Client Wins) ───────────────────────────────────

  async function syncData(games = [], srsCards = []) {
    const token = getToken();
    if (!token) throw new Error("Non connecté");
    const data = await _post("/sync", { games, srs_cards: srsCards }, token);
    return data;
  }

  return {
    getToken, getUser, isLoggedIn, logout, signup, login, autoConnect,
    updateChessUsername, updateSettings, syncData,
  };
})();

if (typeof window !== "undefined") window.Auth = Auth;
if (typeof module !== "undefined" && module.exports != null) module.exports = Auth;
