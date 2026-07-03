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

describe("syncGames (EPIC 23 — sync à la connexion)", () => {
  test("POST /api/v1/games/sync et renvoie les compteurs", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ fetched: 10, queued: 5, skipped: 2, deferred: 3, requeued: 0 }),
    });
    const out = await ApiClient.syncGames();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/games/sync");
    expect(global.fetch.mock.calls[0][1].method).toBe("POST");
    expect(out.queued).toBe(5);
    expect(out.deferred).toBe(3);
  });

  test("attache le JWT quand Auth.getToken() renvoie un token", async () => {
    global.window.Auth = { getToken: () => "jwt-123" };
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    await ApiClient.syncGames();
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer jwt-123");
  });

  test("rejette sur HTTP non-ok (422 pseudo non lié, 502 Chess.com down)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 422 });
    await expect(ApiClient.syncGames()).rejects.toThrow("HTTP 422");
  });
});

describe("salvageGame (EPIC 15, US 15.2)", () => {
  test("POST /api/v1/games/{id}/salvage et renvoie la position du pivot", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        game_id: "g1", pivot_move_index: 4, fen: "startpos", side_to_move: "white", move_number: 3,
      }),
    });
    const out = await ApiClient.salvageGame("g1");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/games/g1/salvage");
    expect(global.fetch.mock.calls[0][1].method).toBe("POST");
    expect(out.pivot_move_index).toBe(4);
    expect(out.side_to_move).toBe("white");
  });

  test("rejette sur HTTP non-ok (ex. aucun pivot détecté)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(ApiClient.salvageGame("g1")).rejects.toThrow("HTTP 404");
  });
});

describe("getNextTacticalProblem (US 8.1/8.2)", () => {
  test("sans themeId : pas de query theme_id (Aléatoire)", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ id: "p1", fen: "x", category: "mate_in_1", difficulty_elo: 1000 }),
    });
    await ApiClient.getNextTacticalProblem();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/tactics/next");
  });

  test("avec themeId : ajoute theme_id à la query", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ id: "p1", fen: "x", category: "mate_in_2", difficulty_elo: 1300 }),
    });
    const out = await ApiClient.getNextTacticalProblem("mate_in_2");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/tactics/next?theme_id=mate_in_2");
    expect(out.category).toBe("mate_in_2");
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.getNextTacticalProblem()).rejects.toThrow("HTTP 401");
  });
});

describe("submitTacticalAttempt (US 8.3/8.4)", () => {
  test("POST /api/v1/tactics/attempt avec problem_id + move et renvoie le JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ success: true, new_elo: 1015, solution: "Qh5#", streak: 1 }),
    });
    const out = await ApiClient.submitTacticalAttempt("p1", "Qh5#");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/tactics/attempt");
    expect(global.fetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({
      problem_id: "p1", move: "Qh5#", time_taken: null,
    });
    expect(out).toEqual({ success: true, new_elo: 1015, solution: "Qh5#", streak: 1 });
  });

  test("transmet time_taken (secondes écoulées, US 8.4) quand fourni", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ success: true, new_elo: 1015, solution: "Qh5#", streak: 2 }),
    });
    await ApiClient.submitTacticalAttempt("p1", "Qh5#", 4.2);
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({
      problem_id: "p1", move: "Qh5#", time_taken: 4.2,
    });
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(ApiClient.submitTacticalAttempt("missing", "e4")).rejects.toThrow("HTTP 404");
  });
});

describe("getTacticsStats (US 8.4)", () => {
  test("appelle GET /api/v1/tactics/stats et renvoie le JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ by_theme: [{ category: "mate_in_1", attempts: 2, successes: 1, success_rate: 0.5 }], streak: 0 }),
    });
    const out = await ApiClient.getTacticsStats();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/tactics/stats");
    expect(out.streak).toBe(0);
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.getTacticsStats()).rejects.toThrow("HTTP 401");
  });
});

describe("getErrorProfile (EPIC 11, US 9.1)", () => {
  test("appelle GET /api/v1/error-profile et renvoie le JSON", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        profiles: [{ error_type: "hanging_piece", frequency_score: 76.3, is_recurring: true, last_observed: "2026-07-02T00:00:00Z" }],
      }),
    });
    const out = await ApiClient.getErrorProfile();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/error-profile");
    expect(out.profiles[0].is_recurring).toBe(true);
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.getErrorProfile()).rejects.toThrow("HTTP 401");
  });
});

describe("getCustomTacticalProblem (EPIC 11, US 9.2)", () => {
  test("ajoute focus à la query", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ id: "p1", fen: "x", category: "hanging_piece", difficulty_elo: 1000 }),
    });
    const out = await ApiClient.getCustomTacticalProblem("hanging_piece");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/tactics/custom?focus=hanging_piece");
    expect(out.category).toBe("hanging_piece");
  });

  test("rejette sur HTTP non-ok (422 focus inconnu)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 422 });
    await expect(ApiClient.getCustomTacticalProblem("nonsense")).rejects.toThrow("HTTP 422");
  });
});

describe("Mode Tactical Sprint (EPIC 12)", () => {
  test("startSprint POST /api/v1/sprints/start", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sprint_id: "s1", duration_seconds: 60, problem: { id: "p1", fen: "x", category: "hanging_piece", difficulty_elo: 1000 } }),
    });
    const out = await ApiClient.startSprint();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/sprints/start");
    expect(global.fetch.mock.calls[0][1].method).toBe("POST");
    expect(out.sprint_id).toBe("s1");
  });

  test("submitSprintAttempt POST /api/v1/sprints/{id}/attempt avec problem_id + move", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, score: 10, problems_solved_count: 1, time_remaining: 55, sprint_active: true, next_problem: null }),
    });
    const out = await ApiClient.submitSprintAttempt("s1", "p1", "Qh5#");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/sprints/s1/attempt");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ problem_id: "p1", move: "Qh5#" });
    expect(out.score).toBe(10);
  });

  test("finishSprint POST /api/v1/sprints/{id}/finish", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ sprint_id: "s1", score: 30, problems_solved_count: 3, duration_seconds: 60 }),
    });
    const out = await ApiClient.finishSprint("s1");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/sprints/s1/finish");
    expect(out.score).toBe(30);
  });

  test("getGhostReplay GET /api/v1/sprints/ghost", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ available: true, score: 40, moves: [{ problem_id: "p1", move: "Qh5#", elapsed_ms: 1200 }] }),
    });
    const out = await ApiClient.getGhostReplay();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/sprints/ghost");
    expect(out.available).toBe(true);
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.startSprint()).rejects.toThrow("HTTP 401");
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

describe("Entraîneur de Finales (EPIC 10)", () => {
  test("getNextEndgameProblem sans themeId : pas de query theme_id", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ id: "e1", fen: "x", category: "queen_mate", difficulty_elo: 700 }),
    });
    await ApiClient.getNextEndgameProblem();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/endgames/next");
  });

  test("getNextEndgameProblem avec themeId : ajoute theme_id à la query", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ id: "e1", fen: "x", category: "rook_mate", difficulty_elo: 850 }),
    });
    const out = await ApiClient.getNextEndgameProblem("rook_mate");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/endgames/next?theme_id=rook_mate");
    expect(out.category).toBe("rook_mate");
  });

  test("getNextEndgameProblem rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.getNextEndgameProblem()).rejects.toThrow("HTTP 401");
  });

  test("submitEndgameAttempt POST /api/v1/endgames/attempt", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ success: true, new_elo: 1015, solution: "Qa4#" }),
    });
    const out = await ApiClient.submitEndgameAttempt("e1", "Qa4#");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/endgames/attempt");
    expect(global.fetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ problem_id: "e1", move: "Qa4#" });
    expect(out).toEqual({ success: true, new_elo: 1015, solution: "Qa4#" });
  });

  test("submitEndgameAttempt rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(ApiClient.submitEndgameAttempt("missing", "e4")).rejects.toThrow("HTTP 404");
  });
});

describe("Entraîneur d'Ouvertures (EPIC 9)", () => {
  test("createOpeningLine POST /api/v1/openings/repertoire", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "l1", name: "Ruy Lopez", color: "white", moves: ["e4"], ease_factor: 2.5, interval_days: 1, repetitions: 0, due_date: "2026-07-01" }),
    });
    const out = await ApiClient.createOpeningLine({ name: "Ruy Lopez", color: "white", moves: ["e4"] });
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/openings/repertoire");
    expect(global.fetch.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ name: "Ruy Lopez", color: "white", moves: ["e4"] });
    expect(out.id).toBe("l1");
  });

  test("createOpeningLine rejette sur HTTP non-ok (422)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 422 });
    await expect(ApiClient.createOpeningLine({ name: "X", color: "white", moves: ["e4"] })).rejects.toThrow("HTTP 422");
  });

  test("getOpeningLines GET /api/v1/openings/repertoire", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ([]) });
    await ApiClient.getOpeningLines();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/openings/repertoire");
  });

  test("getDueOpeningLines GET /api/v1/openings/repertoire/due", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ([]) });
    await ApiClient.getDueOpeningLines();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/openings/repertoire/due");
  });

  test("reviewOpeningLine POST .../review avec mistake_count", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "l1", ease_factor: 2.6, interval_days: 1, repetitions: 1, due_date: "2026-07-02" }),
    });
    await ApiClient.reviewOpeningLine("l1", 0);
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/openings/repertoire/l1/review");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ mistake_count: 0 });
  });

  test("deleteOpeningLine DELETE /api/v1/openings/repertoire/{id}", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ deleted: true }) });
    const out = await ApiClient.deleteOpeningLine("l1");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/openings/repertoire/l1");
    expect(global.fetch.mock.calls[0][1].method).toBe("DELETE");
    expect(out).toEqual({ deleted: true });
  });
});

describe("Dashboard Cognitif (EPIC 19, US 19.1/19.2)", () => {
  test("getCognitiveLoad GET /api/v1/stats/cognitive-load", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ time_allocation: { by_phase: {}, by_pressure: {}, sample_size: 0 }, decision_fluidity: { top3: {}, weak: {}, decision_fatigue: false } }),
    });
    const out = await ApiClient.getCognitiveLoad();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/stats/cognitive-load");
    expect(out.decision_fluidity.decision_fatigue).toBe(false);
  });

  test("rejette sur HTTP non-ok", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });
    await expect(ApiClient.getCognitiveLoad()).rejects.toThrow("HTTP 401");
  });
});

describe("Le Cimetière des Erreurs (EPIC 20, US 20.1/20.2)", () => {
  test("getFlashcards GET /api/v1/flashcards", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ([]) });
    await ApiClient.getFlashcards();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/flashcards");
  });

  test("getDueFlashcards GET /api/v1/flashcards/due", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ([]) });
    await ApiClient.getDueFlashcards();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/flashcards/due");
  });

  test("reviewFlashcard POST .../review avec le coup joué", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, solution: "Qd4+", ease_factor: 2.6, interval_days: 1, repetitions: 1, due_date: "2026-07-02" }),
    });
    const out = await ApiClient.reviewFlashcard("c1", "Qd4+");
    expect(global.fetch.mock.calls[0][0]).toBe("/api/v1/flashcards/c1/review");
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ move: "Qd4+" });
    expect(out.success).toBe(true);
  });

  test("rejette sur HTTP non-ok (404 carte inconnue)", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(ApiClient.reviewFlashcard("missing", "Qd4+")).rejects.toThrow("HTTP 404");
  });
});
