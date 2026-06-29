/**
 * US 5 – Statistics Dashboard
 * Suivi de la progression Elo et précision sur 7/30/90 jours.
 * Formule Elo logistique basée sur la Win Probability moyenne.
 * Lissage par moyenne mobile sur 5 parties.
 */

const StatsDashboard = (() => {
  const WP_K      = 0.003682;
  const ELO_BASE  = 1000;
  const ELO_SCALE = 400;
  const SMOOTH_WINDOW = 5;

  // ── Formule logistique Elo ─────────────────────────────────────────

  function wpFromCp(cp) {
    const clamped = Math.max(-10000, Math.min(10000, cp));
    return 50 + 50 * (2 / (1 + Math.exp(-WP_K * clamped)) - 1);
  }

  function estimateEloLogistic(avgAccuracy, opponentElo = 1000) {
    const acc = Math.max(0, Math.min(100, avgAccuracy));
    // Elo logistique : WP moyenne → différence Elo → Elo estimé
    // Formule : expectedScore = acc/100 ; eloAdvantage = ELO_SCALE * log10(es / (1-es))
    const es = Math.max(0.001, Math.min(0.999, acc / 100));
    const eloAdvantage = ELO_SCALE * Math.log10(es / (1 - es));
    const estimated = Math.round(opponentElo + eloAdvantage);
    return Math.max(400, Math.min(2800, estimated));
  }

  // ── Moyenne mobile ─────────────────────────────────────────────────

  function movingAverage(values, window = SMOOTH_WINDOW) {
    return values.map((_, i) => {
      const start = Math.max(0, i - window + 1);
      const slice = values.slice(start, i + 1).filter((v) => v != null);
      if (!slice.length) return null;
      return parseFloat((slice.reduce((a, b) => a + b, 0) / slice.length).toFixed(1));
    });
  }

  // ── Filtrage par période ───────────────────────────────────────────

  function filterByDays(games, days) {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString();
    return games
      .filter((g) => g.date && g.date >= cutoffStr)
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  // ── Préparer les données ───────────────────────────────────────────

  function buildChartData(games, days) {
    const filtered = filterByDays(games, days);

    const labels   = [];
    const rawElo   = [];
    const rawAcc   = [];

    for (const g of filtered) {
      const dateStr = g.date ? g.date.slice(0, 10) : "?";
      labels.push(dateStr);

      const acc    = g.accuracy != null ? g.accuracy : null;
      const oppElo = g.opponent_elo || 1000;
      const elo    = acc != null ? estimateEloLogistic(acc, oppElo) : null;

      rawAcc.push(acc);
      rawElo.push(elo);
    }

    return {
      labels,
      eloData:    movingAverage(rawElo),
      accData:    movingAverage(rawAcc),
      rawElo,
      rawAcc,
    };
  }

  // ── Rendu Chart.js ─────────────────────────────────────────────────

  let _eloChart = null;
  let _accChart = null;

  function renderCharts(data, eloCanvasId, accCanvasId) {
    if (typeof Chart === "undefined") return;

    if (_eloChart) { _eloChart.destroy(); _eloChart = null; }
    if (_accChart) { _accChart.destroy(); _accChart = null; }

    const eloCanvas = document.getElementById(eloCanvasId || "elo-chart-canvas2");
    const accCanvas = document.getElementById(accCanvasId || "acc-chart-canvas2");

    const commonOptions = (yLabel, min, max, suffix) => ({
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 200 },
      plugins: { legend: { display: false } },
      scales: {
        y: {
          min, max,
          ticks: { color: "#aaa", callback: (v) => `${v}${suffix}` },
          grid:  { color: "rgba(255,255,255,0.06)" },
        },
        x: {
          ticks: { color: "#aaa", maxTicksLimit: 8, maxRotation: 30 },
          grid:  { color: "rgba(255,255,255,0.06)" },
        },
      },
    });

    if (eloCanvas) {
      _eloChart = new Chart(eloCanvas, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Elo (lissé)",
              data: data.eloData,
              borderColor: "#e8c97e",
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.4,
              spanGaps: true,
            },
            {
              label: "Elo brut",
              data: data.rawElo,
              borderColor: "rgba(232,201,126,0.25)",
              borderWidth: 1,
              pointRadius: 2,
              tension: 0.2,
              spanGaps: true,
            },
          ],
        },
        options: commonOptions("Elo", 400, 2800, ""),
      });
    }

    if (accCanvas) {
      _accChart = new Chart(accCanvas, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Précision (lissée)",
              data: data.accData,
              borderColor: "#5b8dd9",
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.4,
              spanGaps: true,
            },
            {
              label: "Précision brute",
              data: data.rawAcc,
              borderColor: "rgba(91,141,217,0.25)",
              borderWidth: 1,
              pointRadius: 2,
              tension: 0.2,
              spanGaps: true,
            },
          ],
        },
        options: commonOptions("Précision", 0, 100, "%"),
      });
    }
  }

  // ── Point d'entrée public ─────────────────────────────────────────

  async function render(days = 30, eloCanvasId, accCanvasId) {
    let games = [];
    try {
      if (window.ChessDB) {
        games = await ChessDB.getAllGames();
      } else {
        const raw = localStorage.getItem("ci_games");
        games = raw ? JSON.parse(raw) : [];
      }
    } catch {}

    const data = buildChartData(games, days);
    renderCharts(data, eloCanvasId, accCanvasId);
    return data;
  }

  return {
    wpFromCp,
    estimateEloLogistic,
    movingAverage,
    filterByDays,
    buildChartData,
    render,
  };
})();

window.StatsDashboard = StatsDashboard;
