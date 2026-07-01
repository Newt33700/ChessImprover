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

describe("analyzeGame", () => {
  test("POST le PGN + options et renvoie le JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ accepted: [] }) });
    const out = await ApiClient.analyzeGame("1. e4", { timeControl: "300", userColor: "black", userId: "u1" });
    expect(out).toEqual({ accepted: [] });
    const [, opts] = global.fetch.mock.calls[0];
    const body = JSON.parse(opts.body);
    expect(body.pgn).toBe("1. e4");
    expect(body.time_control).toBe("300");
    expect(body.user_color).toBe("black");
    expect(body.user_id).toBe("u1");
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(ApiClient.analyzeGame("x")).rejects.toThrow("HTTP 500");
  });
});

describe("getStatsSummary / getGame", () => {
  test("getStatsSummary construit la query period+user_id", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ rows: {} }) });
    await ApiClient.getStatsSummary("7d", "u9");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/summary?period=7d&user_id=u9");
  });

  test("getGame appelle l'URL de la partie", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ game: {} }) });
    await ApiClient.getGame("abc");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/games/abc");
  });
});

describe("getStatsHistory", () => {
  test("construit la query cadence+days+user_id", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ history: [] }) });
    await ApiClient.getStatsHistory("bullet", 7, "u9");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/history?cadence=bullet&days=7&user_id=u9");
  });

  test("valeurs par défaut (blitz, 30 jours, sans user_id)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ history: [] }) });
    await ApiClient.getStatsHistory();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/history?cadence=blitz&days=30");
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 503 });
    await expect(ApiClient.getStatsHistory()).rejects.toThrow("HTTP 503");
  });
});
