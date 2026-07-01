/**
 * Tests unitaires – ApiClient (EPIC 1, câblage frontend → backend).
 */

const ApiClient = require("../js/api_client.js");

afterEach(() => {
  delete global.fetch;
  if (global.window) delete global.window.API_BASE;
  try { localStorage.clear(); } catch { /* ignore */ }
});

describe("baseUrl / isConfigured", () => {
  test("vide par défaut → non configuré", () => {
    expect(ApiClient.baseUrl()).toBe("");
    expect(ApiClient.isConfigured()).toBe(false);
  });

  test("window.API_BASE prioritaire", () => {
    global.window.API_BASE = "http://api.test";
    expect(ApiClient.baseUrl()).toBe("http://api.test");
    expect(ApiClient.isConfigured()).toBe(true);
  });

  test("repli sur localStorage['apiBase']", () => {
    localStorage.setItem("apiBase", "http://stored.test");
    expect(ApiClient.baseUrl()).toBe("http://stored.test");
  });
});

describe("url", () => {
  test("ajoute la query en filtrant les valeurs vides", () => {
    expect(ApiClient.url("/x", { a: 1, b: null, c: "" })).toBe("/x?a=1");
  });

  test("sans query", () => {
    expect(ApiClient.url("/x")).toBe("/x");
  });
});

afterEach(() => {
  if (global.window) delete global.window.Auth;
});

describe("analyzeGame", () => {
  test("POST le PGN + options et renvoie le JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ accepted: [] }) });
    const out = await ApiClient.analyzeGame("1. e4", { timeControl: "300", userColor: "black" });
    expect(out).toEqual({ accepted: [] });
    const [, opts] = global.fetch.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.pgn).toBe("1. e4");
    expect(body.time_control).toBe("300");
    expect(body.user_color).toBe("black");
    expect(body.user_id).toBeUndefined();
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(ApiClient.analyzeGame("x")).rejects.toThrow("HTTP 500");
  });
});

describe("authentification (US 6.4)", () => {
  test("sans Auth.getToken() → pas d'en-tête Authorization", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ rows: {} }) });
    await ApiClient.getStatsSummary("7d");
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  test("avec Auth.getToken() → en-tête Authorization Bearer sur toutes les routes", async () => {
    global.window.Auth = { getToken: () => "jwt-123" };
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ rows: {} }) });

    await ApiClient.getStatsSummary("7d");
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer jwt-123");

    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ history: [] }) });
    await ApiClient.getStatsHistory();
    expect(global.fetch.mock.calls[1][1].headers.Authorization).toBe("Bearer jwt-123");

    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ game: {} }) });
    await ApiClient.getGame("abc");
    expect(global.fetch.mock.calls[2][1].headers.Authorization).toBe("Bearer jwt-123");

    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ accepted: [] }) });
    await ApiClient.analyzeGame("1. e4");
    expect(global.fetch.mock.calls[3][1].headers.Authorization).toBe("Bearer jwt-123");

    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ games: [] }) });
    await ApiClient.getGames();
    expect(global.fetch.mock.calls[4][1].headers.Authorization).toBe("Bearer jwt-123");
  });
});

describe("getGames (US 7.1)", () => {
  test("appelle GET /api/v1/games et renvoie le JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ games: [{ id: "g1" }] }) });
    const out = await ApiClient.getGames();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/games");
    expect(out).toEqual({ games: [{ id: "g1" }] });
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.getGames()).rejects.toThrow("HTTP 401");
  });
});

describe("updateGameStatus (US 7.3)", () => {
  test("PATCH /api/v1/games/{id}/status avec is_reviewed", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ game: { id: "g1", is_reviewed: true } }),
    });
    const out = await ApiClient.updateGameStatus("g1", true);
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/games/g1/status");
    expect(global.fetch.mock.calls[0][1].method).toBe("PATCH");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ is_reviewed: true });
    expect(out).toEqual({ game: { id: "g1", is_reviewed: true } });
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(ApiClient.updateGameStatus("missing", true)).rejects.toThrow("HTTP 404");
  });
});

describe("getStatsSummary / getGame", () => {
  test("getStatsSummary construit la query period (sans user_id, dérivé du JWT serveur)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ rows: {} }) });
    await ApiClient.getStatsSummary("7d");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/summary?period=7d");
  });

  test("getGame appelle l'URL de la partie", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ game: {} }) });
    await ApiClient.getGame("abc");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/games/abc");
  });
});

describe("getStatsHistory", () => {
  test("construit la query cadence+days (sans user_id)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ history: [] }) });
    await ApiClient.getStatsHistory("bullet", 7);
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/history?cadence=bullet&days=7");
  });

  test("valeurs par défaut (blitz, 30 jours)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ history: [] }) });
    await ApiClient.getStatsHistory();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/history?cadence=blitz&days=30");
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 503 });
    await expect(ApiClient.getStatsHistory()).rejects.toThrow("HTTP 503");
  });
});
