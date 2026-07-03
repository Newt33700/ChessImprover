/**
 * Tests unitaires – Auth (US 7 / US 6.1 : messages d'erreur exploitables).
 */

const Auth = require("../js/auth.js");

afterEach(() => {
  delete global.fetch;
  try { localStorage.clear(); } catch { /* ignore */ }
});

describe("signup", () => {
  test("succès : enregistre le token et le user en session", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a" } }),
    });
    const data = await Auth.signup("a@b.com", "a", "secret1");
    expect(data.token).toBe("t1");
    expect(Auth.getToken()).toBe("t1");
    expect(Auth.getUser()).toEqual({ id: "u1", email: "a@b.com", username: "a" });
  });

  test("erreur 400 avec detail chaîne (email/pseudo déjà pris)", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Email déjà utilisé" }),
    });
    await expect(Auth.signup("a@b.com", "a", "secret1")).rejects.toThrow("Email déjà utilisé");
  });

  test("erreur 422 de validation Pydantic (liste d'objets) → message lisible, pas [object Object]", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: [{ loc: ["body", "email"], msg: "Adresse email invalide", type: "value_error" }],
      }),
    });
    await expect(Auth.signup("pasunmail", "a", "secret1")).rejects.toThrow("Adresse email invalide");
  });

  test("erreur 422 avec plusieurs champs invalides → messages concaténés", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({
        detail: [
          { msg: "Adresse email invalide" },
          { msg: "ensure this value has at least 6 characters" },
        ],
      }),
    });
    await expect(Auth.signup("pasunmail", "a", "x")).rejects.toThrow(
      "Adresse email invalide ; ensure this value has at least 6 characters"
    );
  });

  test("erreur sans detail exploitable → message générique", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, json: async () => ({}) });
    await expect(Auth.signup("a@b.com", "a", "secret1")).rejects.toThrow("Erreur serveur");
  });
});

describe("login", () => {
  test("identifiants incorrects", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Identifiants incorrects" }),
    });
    await expect(Auth.login("a@b.com", "bad")).rejects.toThrow("Identifiants incorrects");
  });
});

describe("updateChessUsername (US 6.3)", () => {
  test("sans token → rejette sans appeler fetch", async () => {
    global.fetch = jest.fn();
    await expect(Auth.updateChessUsername("Hikaru")).rejects.toThrow("Non connecté");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("succès : PATCH /auth/me, met à jour la session locale", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a", chess_username: null } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "u1", email: "a@b.com", username: "a", chess_username: "Hikaru" }),
      });
    await Auth.signup("a@b.com", "a", "secret1");
    const user = await Auth.updateChessUsername("Hikaru");
    expect(user.chess_username).toBe("Hikaru");
    expect(Auth.getUser().chess_username).toBe("Hikaru");
    const [, patchCall] = global.fetch.mock.calls;
    expect(patchCall[1].method).toBe("PATCH");
    expect(JSON.parse(patchCall[1].body)).toEqual({ chess_username: "Hikaru" });
  });

  test("format invalide (422) → message lisible", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a" } }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: [{ msg: "Pseudo Chess.com invalide (3 à 25 caractères alphanumériques, '_' ou '-')" }] }),
      });
    await Auth.signup("a@b.com", "a", "secret1");
    await expect(Auth.updateChessUsername("a")).rejects.toThrow("Pseudo Chess.com invalide");
  });
});

describe("updateSettings (EPIC 18, US 18.2)", () => {
  test("sans token → rejette sans appeler fetch", async () => {
    global.fetch = jest.fn();
    await expect(Auth.updateSettings({ piece_theme: "cyber-tactics" })).rejects.toThrow("Non connecté");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("succès : PATCH /auth/me/settings, met à jour la session locale", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a", settings: {} } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "u1", email: "a@b.com", username: "a",
          settings: { piece_theme: "cyber-tactics", board_theme: "cyber" },
        }),
      });
    await Auth.signup("a@b.com", "a", "secret1");
    const user = await Auth.updateSettings({ piece_theme: "cyber-tactics", board_theme: "cyber" });
    expect(user.settings).toEqual({ piece_theme: "cyber-tactics", board_theme: "cyber" });
    expect(Auth.getUser().settings).toEqual({ piece_theme: "cyber-tactics", board_theme: "cyber" });
    const [, patchCall] = global.fetch.mock.calls;
    expect(patchCall[1].method).toBe("PATCH");
    expect(JSON.parse(patchCall[1].body)).toEqual({ settings: { piece_theme: "cyber-tactics", board_theme: "cyber" } });
  });

  test("settings absent → envoie un objet vide", async () => {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a", settings: {} } }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ id: "u1", settings: {} }) });
    await Auth.signup("a@b.com", "a", "secret1");
    await Auth.updateSettings();
    const [, patchCall] = global.fetch.mock.calls;
    expect(JSON.parse(patchCall[1].body)).toEqual({ settings: {} });
  });
});

describe("isLoggedIn / logout", () => {
  test("faux par défaut, vrai après signup, faux après logout", async () => {
    expect(Auth.isLoggedIn()).toBe(false);
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a" } }),
    });
    await Auth.signup("a@b.com", "a", "secret1");
    expect(Auth.isLoggedIn()).toBe(true);
    Auth.logout();
    expect(Auth.isLoggedIn()).toBe(false);
  });
});

describe("résolution de la base API (audit sécurité)", () => {
  const okLogin = () => ({
    ok: true,
    json: async () => ({ token: "t1", user: { id: "u1", email: "a@b.com", username: "a" } }),
  });

  afterEach(() => {
    delete global.window.CI_API_URL;
    delete global.window.API_BASE;
  });

  test("sans configuration → fallback dev http://localhost:8000", async () => {
    global.fetch = jest.fn().mockResolvedValue(okLogin());
    await Auth.login("a@b.com", "secret1");
    expect(global.fetch.mock.calls[0][0]).toBe("http://localhost:8000/auth/login");
  });

  test("window.API_BASE (config.js prod) est utilisé — plus de fallback localhost en prod", async () => {
    global.window.API_BASE = "https://chess-improver-api.onrender.com";
    global.fetch = jest.fn().mockResolvedValue(okLogin());
    await Auth.login("a@b.com", "secret1");
    expect(global.fetch.mock.calls[0][0]).toBe(
      "https://chess-improver-api.onrender.com/auth/login"
    );
  });

  test("window.CI_API_URL (E2E) prime sur window.API_BASE", async () => {
    global.window.CI_API_URL = "http://127.0.0.1:9999";
    global.window.API_BASE = "https://prod.example";
    global.fetch = jest.fn().mockResolvedValue(okLogin());
    await Auth.login("a@b.com", "secret1");
    expect(global.fetch.mock.calls[0][0]).toBe("http://127.0.0.1:9999/auth/login");
  });

  test("la base est relue à chaque appel (résolution paresseuse)", async () => {
    global.fetch = jest.fn().mockResolvedValue(okLogin());
    await Auth.login("a@b.com", "secret1");
    global.window.API_BASE = "https://prod.example";
    await Auth.login("a@b.com", "secret1");
    expect(global.fetch.mock.calls[1][0]).toBe("https://prod.example/auth/login");
  });
});
