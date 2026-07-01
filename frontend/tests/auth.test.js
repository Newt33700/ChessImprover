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
