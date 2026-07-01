/**
 * US 7 – Auth & Cloud Persistence
 * Gère l'inscription, la connexion, les JWT et la synchronisation cloud.
 */

const Auth = (() => {
  const API_BASE = (typeof window !== "undefined" && window.CI_API_URL) || "http://localhost:8000";
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

  async function _post(path, body, token) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(_extractErrorMessage(data));
    return data;
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
      const res = await fetch(`${API_BASE}/auth/me`, { headers });
      if (!res.ok) { logout(); return null; }
      const user = await res.json();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return user;
    } catch {
      return null;
    }
  }

  // ── Synchronisation (Client Wins) ───────────────────────────────────

  async function syncData(games = [], srsCards = []) {
    const token = getToken();
    if (!token) throw new Error("Non connecté");
    const data = await _post("/sync", { games, srs_cards: srsCards }, token);
    return data;
  }

  return { getToken, getUser, isLoggedIn, logout, signup, login, autoConnect, syncData };
})();

if (typeof window !== "undefined") window.Auth = Auth;
if (typeof module !== "undefined" && module.exports != null) module.exports = Auth;
