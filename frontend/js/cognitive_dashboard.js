/**
 * cognitive_dashboard.js — Dashboard de Performance Cognitive (EPIC 19, US 19.1/19.2)
 *
 * Affiche deux angles d'analyse calculés côté serveur (`GET /api/v1/stats/cognitive-load`,
 * « zéro calcul client », même politique que `advanced_stats.js`) :
 *   - US 19.1 : répartition du temps de réflexion par phase de jeu et par
 *     niveau de pression (« temps morts »).
 *   - US 19.2 : fluidité de décision (temps moyen sur les coups Top 3 vs
 *     les coups perdants, drapeau « fatigue décisionnelle »).
 *
 * La logique pure (mise en forme, messages d'insight) est isolée et testée ;
 * `renderChart`/`render` ne sont que de la glue DOM/Chart.js.
 */

const CognitiveDashboard = (() => {
  "use strict";

  const PHASE_LABELS = { opening: "Ouverture", middlegame: "Milieu de jeu", endgame: "Finale" };
  const PHASE_ORDER = ["opening", "middlegame", "endgame"];

  //: Part du temps de réflexion sur UNE phase au-delà de laquelle on signale
  //: une "dominance" (valeur métier : "80% de ton temps en ouverture").
  const DOMINANT_SHARE_PCT = 60;

  const EMPTY_REPORT = {
    time_allocation: {
      by_phase: {
        opening: { avg_seconds: null, total_seconds: 0, count: 0, share_pct: 0 },
        middlegame: { avg_seconds: null, total_seconds: 0, count: 0, share_pct: 0 },
        endgame: { avg_seconds: null, total_seconds: 0, count: 0, share_pct: 0 },
      },
      by_pressure: {
        under_pressure: { avg_seconds: null, total_seconds: 0, count: 0 },
        equality: { avg_seconds: null, total_seconds: 0, count: 0 },
      },
      sample_size: 0,
    },
    decision_fluidity: {
      top3: { avg_seconds: null, total_seconds: 0, count: 0 },
      weak: { avg_seconds: null, total_seconds: 0, count: 0 },
      decision_fatigue: false,
    },
  };

  // ── Mise en forme ───────────────────────────────────────────────────

  /** Formate des secondes en libellé lisible ("1m 20s", "45s", "—" si inconnu). */
  function formatSeconds(seconds) {
    if (seconds == null) return "—";
    const rounded = Math.round(seconds);
    if (rounded < 60) return `${rounded}s`;
    const minutes = Math.floor(rounded / 60);
    const rest = rounded % 60;
    return rest === 0 ? `${minutes}m` : `${minutes}m ${rest}s`;
  }

  /** Données pour un graphe barre Chart.js (temps moyen par phase). */
  function buildPhaseChartData(timeAllocation) {
    const byPhase = (timeAllocation && timeAllocation.by_phase) || {};
    return {
      labels: PHASE_ORDER.map((p) => PHASE_LABELS[p]),
      avgSeconds: PHASE_ORDER.map((p) => (byPhase[p] ? byPhase[p].avg_seconds : null)),
      sharePct: PHASE_ORDER.map((p) => (byPhase[p] ? byPhase[p].share_pct : 0)),
    };
  }

  /**
   * Messages d'insight en langage naturel (US 19.1/19.2) — la valeur métier
   * du dashboard n'est pas d'afficher des nombres bruts mais de pointer un
   * comportement actionnable (ex. temps perdu en ouverture non maîtrisée).
   */
  function buildInsightMessages(report) {
    const r = report || EMPTY_REPORT;
    const messages = [];

    if (r.time_allocation.sample_size === 0) {
      return ["Analysez des parties avec horodatage (parties chronométrées) pour activer ce dashboard."];
    }

    const byPhase = r.time_allocation.by_phase;
    const dominant = PHASE_ORDER.filter((p) => (byPhase[p]?.share_pct || 0) >= DOMINANT_SHARE_PCT);
    if (dominant.length) {
      const p = dominant[0];
      messages.push(
        `Tu passes ${byPhase[p].share_pct}% de ton temps de réflexion en ${PHASE_LABELS[p].toLowerCase()} — ` +
        `un signe que cette phase n'est pas encore automatisée.`
      );
    }

    const pressure = r.time_allocation.by_pressure.under_pressure;
    const equality = r.time_allocation.by_pressure.equality;
    if (pressure.avg_seconds != null && equality.avg_seconds != null && pressure.avg_seconds > equality.avg_seconds) {
      messages.push(
        `Sous pression, tu réfléchis en moyenne ${formatSeconds(pressure.avg_seconds)} contre ` +
        `${formatSeconds(equality.avg_seconds)} en position équilibrée : gère bien ton temps dans les phases difficiles.`
      );
    }

    if (r.decision_fluidity.decision_fatigue) {
      messages.push(
        `Fatigue décisionnelle détectée : tu réfléchis plus longtemps sur tes coups perdants ` +
        `(${formatSeconds(r.decision_fluidity.weak.avg_seconds)}) que sur tes coups quasi optimaux ` +
        `(${formatSeconds(r.decision_fluidity.top3.avg_seconds)}).`
      );
    } else if (r.decision_fluidity.top3.count > 0) {
      messages.push(`Bonne fluidité : tes bons coups sont joués vite et avec confiance.`);
    }

    if (!messages.length) messages.push("Aucun signal particulier — ta gestion du temps est équilibrée.");
    return messages;
  }

  // ── API ──────────────────────────────────────────────────────────

  /** Récupère le rapport agrégé depuis le backend, `EMPTY_REPORT` en repli. */
  async function fetchReport() {
    if (typeof ApiClient !== "undefined" && ApiClient.isConfigured()) {
      try {
        return await ApiClient.getCognitiveLoad();
      } catch {
        return EMPTY_REPORT;
      }
    }
    return EMPTY_REPORT;
  }

  // ── Rendu Chart.js ─────────────────────────────────────────────────

  let _phaseChart = null;

  function renderChart(report, canvasId) {
    if (typeof Chart === "undefined") return;
    const canvas = document.getElementById(canvasId || "cognitive-phase-chart");
    if (!canvas) return;

    if (_phaseChart) { _phaseChart.destroy(); _phaseChart = null; }

    const data = buildPhaseChartData(report.time_allocation);
    _phaseChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          label: "Temps de réflexion moyen (s)",
          data: data.avgSeconds,
          backgroundColor: ["#5b8dd9", "#81b64c", "#e8c97e"],
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.06)" } },
          x: { ticks: { color: "#aaa" }, grid: { display: false } },
        },
      },
    });
  }

  function renderHTML(report) {
    const messages = buildInsightMessages(report);
    const items = messages.map((m) => `<li class="cog-insight">${m}</li>`).join("");
    return `<ul class="cog-insights">${items}</ul>`;
  }

  // ── Point d'entrée public ─────────────────────────────────────────

  async function render(containerId, canvasId) {
    const container = typeof document !== "undefined" ? document.getElementById(containerId) : null;
    const report = await fetchReport();
    if (container) container.innerHTML = renderHTML(report);
    renderChart(report, canvasId);
    return report;
  }

  return {
    PHASE_LABELS,
    PHASE_ORDER,
    DOMINANT_SHARE_PCT,
    EMPTY_REPORT,
    formatSeconds,
    buildPhaseChartData,
    buildInsightMessages,
    fetchReport,
    renderHTML,
    render,
  };
})();

if (typeof window !== "undefined") window.CognitiveDashboard = CognitiveDashboard;
if (typeof module !== "undefined" && module.exports != null) module.exports = CognitiveDashboard;
