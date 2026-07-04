/**
 * US 1 – Win Probability Chart
 * Graphique interactif d'évolution de l'avantage sur la partie.
 * Formule WP = 50 + 50 * (2 / (1 + exp(-0.003682 * cp)) - 1)
 */

const WPChart = (() => {
  const WP_K = 0.003682;
  let _chartInstance = null;

  // ── Formule ────────────────────────────────────────────────────────

  function cpToWP(cp) {
    return 50 + 50 * (2 / (1 + Math.exp(-WP_K * cp)) - 1);
  }

  // cp est toujours du point de vue des Blancs (positif = blanc gagne)
  function evalToWP(evalCp) {
    if (evalCp >= 10000)  return 100;
    if (evalCp <= -10000) return 0;
    return parseFloat(cpToWP(evalCp).toFixed(2));
  }

  /**
   * EPIC 31 — Libellé de la barre d'évaluation (POC v0) : centipions
   * (point de vue Blancs) → pions signés à une décimale (« +0.3 »,
   * « -1.2 »). Évals de mat (|cp| ≥ 10000) → « M » signé ; null → « 0.0 ».
   */
  function formatEval(evalCp) {
    if (evalCp == null || Number.isNaN(evalCp)) return "0.0";
    if (evalCp >= 10000)  return "+M";
    if (evalCp <= -10000) return "-M";
    const pawns = evalCp / 100;
    return `${pawns >= 0 ? "+" : ""}${pawns.toFixed(1)}`;
  }

  // ── Construire les données depuis game.moves[] ─────────────────────

  function buildDataset(moves) {
    const labels = [];
    const data   = [];

    // Point de départ : position initiale = 50%
    labels.push("Début");
    data.push(50);

    moves.forEach((m, i) => {
      const moveNum = Math.floor(i / 2) + 1;
      const side    = m.color === "w" ? "B" : "N";
      labels.push(`${moveNum}.${side} ${m.san}`);

      const evalCp = m.evalCp !== undefined ? m.evalCp
                   : m.cpLoss !== undefined  ? null  // pas encore d'éval absolue
                   : null;

      data.push(evalCp !== null ? evalToWP(evalCp) : null);
    });

    return { labels, data };
  }

  // ── Rendu Chart.js ─────────────────────────────────────────────────

  function render(canvasId, moves, onPointClick) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (typeof Chart === "undefined") return;

    if (_chartInstance) {
      _chartInstance.destroy();
      _chartInstance = null;
    }

    const { labels, data } = buildDataset(moves);

    _chartInstance = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Avantage Blancs (%)",
          data,
          fill: {
            target: { value: 50 },
            above: "rgba(255,255,255,0.12)",
            below: "rgba(0,0,0,0.25)",
          },
          borderColor: "#e8c97e",
          borderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: data.map((v) => {
            if (v === null) return "#555";
            if (v >= 60)  return "#5b8dd9";
            if (v <= 40)  return "#c0392b";
            return "#888";
          }),
          tension: 0.3,
          spanGaps: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = ctx.raw;
                if (v === null) return "Calcul…";
                const side = v > 50 ? "Blancs" : v < 50 ? "Noirs" : "Égalité";
                return `${side} : ${v.toFixed(1)}%`;
              },
            },
          },
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: {
              color: "#aaa",
              callback: (v) => `${v}%`,
            },
            grid: { color: "rgba(255,255,255,0.06)" },
          },
          x: {
            ticks: {
              color: "#aaa",
              maxTicksLimit: 12,
              maxRotation: 30,
            },
            grid: { color: "rgba(255,255,255,0.06)" },
          },
        },
        onClick: (event, elements) => {
          if (!elements.length) return;
          const pointIndex = elements[0].index;
          // index 0 = position initiale (avant le coup 0)
          if (typeof onPointClick === "function") {
            onPointClick(pointIndex - 1); // -1 = position initiale
          }
        },
      },
    });
  }

  // ── Mise à jour incrémentale ───────────────────────────────────────

  function updateMove(moveIndex, evalCp) {
    if (!_chartInstance) return;
    // +1 car l'index 0 est "Début"
    _chartInstance.data.datasets[0].data[moveIndex + 1] = evalToWP(evalCp);
    _chartInstance.update("none");
  }

  function highlightMove(moveIndex) {
    if (!_chartInstance) return;
    _chartInstance.data.datasets[0].pointRadius = _chartInstance.data.datasets[0].data.map((_, i) =>
      i === moveIndex + 1 ? 9 : 4
    );
    _chartInstance.update("none");
  }

  function destroy() {
    if (_chartInstance) { _chartInstance.destroy(); _chartInstance = null; }
  }

  return { cpToWP, evalToWP, formatEval, buildDataset, render, updateMove, highlightMove, destroy };
})();

if (typeof window !== "undefined") window.WPChart = WPChart;
if (typeof module !== "undefined" && module.exports != null) module.exports = WPChart;
