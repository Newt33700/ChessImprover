/**
 * US 6 – Personal Coach (Decision Tree)
 * Analyse croisée des statistiques pour générer un diagnostic d'entraînement.
 * 100% offline – pas d'API externe.
 */

const PersonalCoach = (() => {

  // ── Collecte des métriques ─────────────────────────────────────────

  function computeMetrics(games, username) {
    if (!games || !games.length) return null;

    const recent = games.slice(0, 30); // 30 dernières parties max

    // Taux de gaffes global
    let totalMoves = 0;
    let totalBlunders = 0;
    let earlyBlunders = 0; // coups 1-15
    let earlyMoves = 0;

    for (const g of recent) {
      const moves = g.moves || [];
      totalMoves   += moves.length;
      totalBlunders += g.blunders_count || 0;

      const userColor = detectUserColor(g, username);
      const userMoves = moves.filter((m) => m.color === userColor);
      const early = userMoves.slice(0, 15);
      earlyMoves   += early.length;
      earlyBlunders += early.filter((m) => m.classification === "blunder").length;
    }

    const blunderRate      = totalMoves ? (totalBlunders / totalMoves) * 100 : 0;
    const earlyBlunderRate = earlyMoves  ? (earlyBlunders  / earlyMoves)  * 100 : 0;

    // Précision moyenne globale
    const gamesWithAcc = recent.filter((g) => g.accuracy != null);
    const avgAccuracy  = gamesWithAcc.length
      ? gamesWithAcc.reduce((s, g) => s + g.accuracy, 0) / gamesWithAcc.length
      : null;

    // Pire ouverture (winrate le plus bas, min 5 parties)
    const openingMap = new Map();
    for (const g of games) {
      const opening = extractOpening(g);
      const result  = detectResult(g, username);
      if (!result || !opening) continue;
      if (!openingMap.has(opening)) openingMap.set(opening, { wins: 0, total: 0 });
      const e = openingMap.get(opening);
      e.total++;
      if (result === "win") e.wins++;
    }
    let worstOpening = null;
    let worstWinRate = Infinity;
    for (const [name, stats] of openingMap.entries()) {
      if (stats.total >= 5) {
        const wr = stats.wins / stats.total;
        if (wr < worstWinRate) { worstWinRate = wr; worstOpening = name; }
      }
    }

    // Précision en finale
    let endgameAccuracies = [];
    for (const g of recent) {
      if (g.endgame_accuracy != null) endgameAccuracies.push(g.endgame_accuracy);
    }
    const avgEndgameAcc = endgameAccuracies.length
      ? endgameAccuracies.reduce((a, b) => a + b, 0) / endgameAccuracies.length
      : null;

    return {
      blunderRate:      parseFloat(blunderRate.toFixed(1)),
      earlyBlunderRate: parseFloat(earlyBlunderRate.toFixed(1)),
      avgAccuracy:      avgAccuracy != null ? parseFloat(avgAccuracy.toFixed(1)) : null,
      worstOpening,
      worstWinRate:     worstWinRate < Infinity ? parseFloat((worstWinRate * 100).toFixed(1)) : null,
      avgEndgameAcc:    avgEndgameAcc != null ? parseFloat(avgEndgameAcc.toFixed(1)) : null,
      totalGames:       recent.length,
    };
  }

  function detectUserColor(game, username) {
    const u = (username || "").toLowerCase();
    if (!u) return "w";
    if ((game.white?.username || "").toLowerCase() === u) return "w";
    if ((game.black?.username || "").toLowerCase() === u) return "b";
    return "w";
  }

  function detectResult(game, username) {
    const u = (username || "").toLowerCase();
    if (!u) return null;
    const whiteName = (game.white?.username || "").toLowerCase();
    const blackName = (game.black?.username || "").toLowerCase();
    if (whiteName !== u && blackName !== u) return null;
    const isWhite = whiteName === u;
    const res = isWhite ? game.white?.result : game.black?.result;
    if (res === "win") return "win";
    const drawSet = new Set(["agreed","stalemate","repetition","insufficient","50move","timevsinsufficient"]);
    return drawSet.has(res) ? "draw" : "loss";
  }

  function extractOpening(game) {
    const pgn = game.pgn || "";
    const m   = pgn.match(/\[Opening\s+"([^"]+)"\]/);
    if (m) return m[1];
    if (game.opening) return game.opening;
    return null;
  }

  // ── Arbre de décision ─────────────────────────────────────────────

  function diagnose(metrics) {
    if (!metrics) {
      return [{
        priority: 0,
        message: "Analysez au moins quelques parties pour obtenir des conseils personnalisés.",
        action: null,
        target: null,
      }];
    }

    const advices = [];

    // Règle 1 : trop de gaffes précoces
    if (metrics.earlyBlunderRate > 20) {
      advices.push({
        priority: 10,
        message: `Tu perds trop vite tes parties à cause d'erreurs tactiques précoces (${metrics.earlyBlunderRate}% de gaffes dans les 15 premiers coups).`,
        action: "Réviser mes ouvertures",
        target: "tab-openings",
      });
    }

    // Règle 2 : pire ouverture sous 30% sur 5+ parties
    if (metrics.worstOpening && metrics.worstWinRate !== null && metrics.worstWinRate < 30) {
      advices.push({
        priority: 9,
        message: `La "${metrics.worstOpening}" te coûte des points (${metrics.worstWinRate}% de victoires). Revois tes lignes.`,
        action: "Voir mes ouvertures",
        target: "tab-openings",
      });
    }

    // Règle 3 : taux de gaffes global élevé
    if (metrics.blunderRate > 5) {
      advices.push({
        priority: 8,
        message: `Ton taux de gaffes global est élevé (${metrics.blunderRate}%). Travailler les puzzles tactiques te ferait progresser rapidement.`,
        action: "Faire mes puzzles SRS",
        target: "exercise",
      });
    }

    // Règle 4 : précision en finale faible
    if (metrics.avgEndgameAcc !== null && metrics.avgEndgameAcc < 60) {
      advices.push({
        priority: 7,
        message: `Ta technique en finale est fragile (précision moyenne : ${metrics.avgEndgameAcc}%). Tu convertis mal tes positions gagnantes.`,
        action: "Analyser mes finales",
        target: "tab-endgame",
      });
    }

    // Règle 5 : précision globale correcte mais progressable
    if (metrics.avgAccuracy !== null && metrics.avgAccuracy >= 75 && metrics.avgAccuracy < 85) {
      advices.push({
        priority: 5,
        message: `Ta précision de ${metrics.avgAccuracy}% est bonne. Pour passer le cap, concentre-toi sur la qualité de tes coups en milieu de partie.`,
        action: "Revoir mes parties",
        target: "review",
      });
    }

    // Règle 6 : pas assez de données
    if (metrics.totalGames < 5) {
      advices.push({
        priority: 1,
        message: "Analysez davantage de parties (min 5) pour obtenir des conseils précis.",
        action: null,
        target: null,
      });
    }

    // Fallback si tout va bien
    if (!advices.length || (advices.length === 1 && advices[0].priority === 1)) {
      advices.push({
        priority: 3,
        message: `Ton niveau est solide (précision ${metrics.avgAccuracy}%). Continue à analyser régulièrement tes parties pour progresser.`,
        action: "Faire mes révisions",
        target: "exercise",
      });
    }

    return advices.sort((a, b) => b.priority - a.priority);
  }

  // ── Rendu HTML ─────────────────────────────────────────────────────

  function renderHTML(advices) {
    return advices.map((advice, i) => {
      const actionBtn = advice.action
        ? `<button class="btn btn--primary btn--sm coach-action-btn" data-target="${advice.target}">${advice.action}</button>`
        : "";
      const priorityClass = advice.priority >= 8 ? "coach-high" : advice.priority >= 5 ? "coach-mid" : "coach-low";
      return `
        <div class="coach-card ${priorityClass}">
          <div class="coach-msg">${advice.message}</div>
          ${actionBtn}
        </div>`;
    }).join("");
  }

  // ── Point d'entrée public ─────────────────────────────────────────

  async function render(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `<p class="empty-state">Analyse en cours…</p>`;

    let games = [];
    let username = "";
    try {
      if (window.ChessDB) {
        games = await ChessDB.getAllGames();
      } else {
        const raw = localStorage.getItem("ci_games");
        games = raw ? JSON.parse(raw) : [];
      }
      const rawUser = localStorage.getItem("ci_username");
      username = rawUser ? JSON.parse(rawUser) : "";
    } catch {}

    const metrics = computeMetrics(games, username);
    const advices = diagnose(metrics);
    container.innerHTML = renderHTML(advices);

    // Câbler les boutons d'action
    container.querySelectorAll(".coach-action-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.dataset.target;
        if (!target) return;
        if (target === "exercise" && window.app) { window.app._startExercise(); return; }
        if (target === "review"   && window.app?.currentGame) { window.app._enterReviewMode(window.app.currentGame); return; }
        if (target.startsWith("tab-") && window.app) { window.app._switchTab(target); return; }
      });
    });
  }

  return {
    computeMetrics,
    diagnose,
    renderHTML,
    render,
    // internals for tests
    _detectResult: detectResult,
    _extractOpening: extractOpening,
    _detectUserColor: detectUserColor,
  };
})();

if (typeof window !== "undefined") window.PersonalCoach = PersonalCoach;
if (typeof module !== "undefined" && module.exports != null) module.exports = PersonalCoach;
