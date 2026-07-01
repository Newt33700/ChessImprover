/**
 * advanced_stats.js — Statistiques Avancées (EPIC 4, US 4.1 & 4.2)
 *
 * Vue « type Chess.com Premium » : matrice cadence × catégorie (Elo virtuel
 * coloré), détail par phase (gauge Héros + deltas), tuiles Finales
 * (conversion / résilience), carte Tactiques, graphe ACPL et donut de gaffes.
 *
 * « Zéro calcul client » (US 4.1) : la vue se contente d'afficher des données
 * pré-calculées par le backend (`GET /api/v1/stats/summary`). Tant que l'EPIC 1
 * (ingestion async + agrégation Supabase) n'est pas branché, un jeu de données
 * de démonstration (`MOCK_SUMMARY`) alimente le rendu.
 *
 * La logique pure (couleurs, deltas, gauge, mise en forme) est isolée et
 * testée ; les fonctions `render*` ne sont que de la glue DOM/Chart.js.
 */

const AdvancedStats = (() => {
  "use strict";

  // ── Constantes métier ────────────────────────────────────────────
  const CADENCES = ["bullet", "blitz", "rapid"];
  const CADENCE_LABELS = { bullet: "Bullet", blitz: "Blitz", rapid: "Rapide" };

  // Catégories de la matrice (US 4.1) : libellé + icône + sous-titre deep-dive.
  const CATEGORIES = [
    { key: "openings", label: "Ouvertures", icon: "🏁", sub: "Performance analytique" },
    { key: "tactics",  label: "Tactique",   icon: "⚡", sub: "Vision tactique" },
    { key: "strategy", label: "Stratégie",  icon: "🛡", sub: "Jeu de position" },
    { key: "endgames", label: "Finales",    icon: "🎯", sub: "Conversion technique" },
  ];

  // Bornes de la gauge « Niveau estimé ».
  const GAUGE_MIN = 400;
  const GAUGE_MAX = 2800;

  // Seuils d'intensité de couleur des cellules (écart d'Elo vs classement).
  const STRONG_DELTA = 150;

  // ── Jeu de données de démonstration (calé sur les maquettes) ─────
  const MOCK_SUMMARY = {
    period: "30d",
    rows: {
      bullet: { current: 2700, openings: 2750, tactics: 2600, strategy: 2680, endgames: 2170 },
      blitz:  { current: 1250, openings: 1400, tactics: 1100, strategy: 1280, endgames: 1200 },
      rapid:  { current: 2150, openings: 1950, tactics: 1950, strategy: 2010, endgames: 2350 },
    },
    acplTrend: {
      labels: ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"],
      blunders: [78, 60, 55, 52, 50, 48, 47, 46, 45, 44],
      missed:   [70, 58, 56, 51, 53, 49, 50, 47, 46, 45],
    },
    gaffeRate: { opening: 37.3, middlegame: 37.5, endgame: 25.2 },
    finales: { conversion: 60.7, resilience: 0.5 },
    tactics: { rating: 209, toReview: 43, solved: 23, streak: 1 },
  };

  // ── API ──────────────────────────────────────────────────────────

  /**
   * Récupère le résumé de stats agrégées depuis le backend.
   * En cas d'erreur réseau (backend non déployé), renvoie `MOCK_SUMMARY`.
   * @param {string} period  ex. "7d" | "30d" | "90d"
   * @param {string} [base]  base URL de l'API (par défaut window.STATS_API_BASE)
   * @returns {Promise<object>}
   */
  async function fetchSummary(period = "30d", base) {
    // Délègue au client API partagé si disponible (et qu'aucune base explicite
    // n'est imposée par l'appelant/les tests).
    if (base == null && typeof ApiClient !== "undefined" && ApiClient.isConfigured()) {
      try {
        return await ApiClient.getStatsSummary(period);
      } catch {
        return MOCK_SUMMARY;
      }
    }
    const apiBase =
      base != null
        ? base
        : (typeof window !== "undefined" && window.STATS_API_BASE) || "";
    try {
      const res = await fetch(`${apiBase}/api/v1/stats/summary?period=${period}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return MOCK_SUMMARY;
    }
  }

  // ── Logique pure ─────────────────────────────────────────────────

  /**
   * Classe couleur d'une cellule selon l'écart Elo virtuel vs classement actuel.
   * Vert si supérieur, orange/rouge si inférieur, neutre si égal (US 4.1).
   * @returns {"pos"|"pos-strong"|"neg"|"neg-strong"|"neutral"}
   */
  function cellClass(elo, current) {
    const delta = elo - current;
    if (delta === 0) return "neutral";
    if (delta > 0) return delta >= STRONG_DELTA ? "pos-strong" : "pos";
    return -delta >= STRONG_DELTA ? "neg-strong" : "neg";
  }

  /** Écart signé entre l'Elo d'une catégorie et le classement actuel. */
  function phaseDelta(elo, current) {
    return elo - current;
  }

  /** Formate un delta avec signe explicite ("+150", "-50", "0"). */
  function formatDelta(delta) {
    if (delta > 0) return `+${delta}`;
    return `${delta}`;
  }

  /**
   * Construit le détail par phase d'une cadence (US 4.2, écran mobile).
   * @returns {{cadence:string, estimated:number, phases:Array}}
   */
  function deepDiveFor(summary, cadence) {
    const row = summary.rows[cadence];
    const phases = CATEGORIES.map((c) => {
      const elo = row[c.key];
      return {
        key: c.key,
        label: c.label,
        sub: c.sub,
        icon: c.icon,
        elo,
        delta: phaseDelta(elo, row.current),
      };
    });
    return { cadence, estimated: row.current, phases };
  }

  /**
   * Angle (degrés) de l'aiguille de la gauge, de -90 (min) à +90 (max).
   * Borné aux extrémités.
   */
  function gaugeAngle(value, min = GAUGE_MIN, max = GAUGE_MAX) {
    if (max <= min) return 0;
    const clamped = Math.max(min, Math.min(max, value));
    const ratio = (clamped - min) / (max - min);
    return -90 + ratio * 180;
  }

  /** Lignes prêtes au rendu de la matrice. */
  function matrixRows(summary) {
    return CADENCES.map((cadence) => {
      const row = summary.rows[cadence];
      return {
        cadence,
        label: CADENCE_LABELS[cadence],
        current: row.current,
        cells: CATEGORIES.map((c) => ({
          key: c.key,
          elo: row[c.key],
          cls: cellClass(row[c.key], row.current),
        })),
      };
    });
  }

  /** Vrai si le résumé ne contient aucune partie analysée (état vide UX). */
  function isEmpty(summary) {
    return !!summary && summary.hasData === false;
  }

  // ── Catalogues des vues détaillées (US 4.2, maquettes Finales/Tactiques) ──
  const TACTIC_THEMES = [
    { key: "mate2", label: "Mat en 2", icon: "♚" },
    { key: "pins", label: "Clouages et enfilades", icon: "♝" },
    { key: "discovered", label: "Attaques à la découverte", icon: "♗" },
    { key: "forks", label: "Fourchettes", icon: "♘" },
    { key: "skewers", label: "Enfilades", icon: "♜" },
    { key: "deflection", label: "Déviation", icon: "♛" },
  ];
  const ENDGAME_LESSONS = [
    { key: "pawn_king", label: "Pions et Rois", icon: "♙" },
    { key: "rook", label: "Finales de Tours", icon: "♖" },
    { key: "opposition", label: "Opposition Directe", icon: "♔" },
    { key: "king", label: "Finales de Rois", icon: "♚" },
  ];
  const CATEGORY_TITLES = {
    openings: "Ouvertures",
    tactics: "Tactique",
    strategy: "Stratégie",
    endgames: "Finales",
  };

  function _themeGrid(items, action) {
    return (
      '<div class="theme-grid">' +
      items
        .map(
          (t) =>
            `<div class="theme-card"><div class="theme-icon">${t.icon}</div>` +
            `<div class="theme-name">${t.label}</div>` +
            `<button class="btn btn--accent btn--full btn--sm">${action}</button></div>`
        )
        .join("") +
      "</div>"
    );
  }

  /**
   * HTML de la vue détaillée d'une catégorie (US 4.2). Fonction PURE (testable).
   */
  function categoryDetailHtml(category, summary) {
    const title = CATEGORY_TITLES[category] || category;
    let head =
      `<div class="adv-detail-head"><button class="btn-icon" data-detail-back aria-label="Retour">←</button>` +
      `<h3 class="adv-detail-title">${title}</h3></div>`;

    if (category === "tactics") {
      const t = summary.tactics || {};
      const banner =
        `<div class="tac-banner"><span class="tac-rating">${t.rating != null ? t.rating : "—"}</span>` +
        `<span class="tac-rating-label">Rating de puzzles</span></div>`;
      return head + banner + _themeGrid(TACTIC_THEMES, "Résoudre");
    }
    if (category === "endgames") {
      const f = summary.finales || { conversion: 0, resilience: 0 };
      const tiles =
        `<div class="adv-tiles"><div class="stat-tile stat-tile--good"><div class="stat-tile-head">CONVERSION</div>` +
        `<div class="stat-tile-value">${Number(f.conversion).toFixed(1).replace(".", ",")}%</div></div>` +
        `<div class="stat-tile stat-tile--warn"><div class="stat-tile-head">RÉSILIENCE</div>` +
        `<div class="stat-tile-value">${Number(f.resilience).toFixed(1).replace(".", ",")}%</div></div></div>`;
      return head + tiles + _themeGrid(ENDGAME_LESSONS, "Étudier");
    }
    if (category === "openings") {
      const tops = summary.topOpenings || [];
      const body = tops.length
        ? '<div class="open-list">' +
          tops
            .map(
              (o) =>
                `<div class="open-row"><span class="open-name">${o.name}</span>` +
                `<span class="open-elo">${o.elo}</span></div>`
            )
            .join("") +
          "</div>"
        : '<p class="empty-state">Top 3 ouvertures (codes ECO) — à venir.</p>';
      return head + body;
    }
    return head + '<p class="empty-state">Analyse stratégique détaillée — à venir.</p>';
  }

  // ── Rendu DOM (glue) ─────────────────────────────────────────────

  function renderMatrix(container, summary) {
    if (!container) return;
    const head =
      `<tr><th class="advm-th-cad">Cadence</th><th>Classement</th>` +
      CATEGORIES.map((c) => `<th>${c.label}</th>`).join("") +
      `</tr>`;
    const body = matrixRows(summary)
      .map((r) => {
        const cells = r.cells
          .map(
            (cell) =>
              `<td class="advm-cell advm-cell--${cell.cls}">${cell.elo}</td>`
          )
          .join("");
        return (
          `<tr><th class="advm-row-head">${r.label}</th>` +
          `<td class="advm-current">${r.current}</td>${cells}</tr>`
        );
      })
      .join("");
    container.innerHTML = `<table class="advm-table"><thead>${head}</thead><tbody>${body}</tbody></table>`;
  }

  function renderGauge(value) {
    const angle = gaugeAngle(value);
    return `
      <div class="hero-gauge">
        <svg viewBox="0 0 200 110" class="hero-gauge-svg" aria-hidden="true">
          <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#3d3a36" stroke-width="14" stroke-linecap="round"/>
          <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="url(#gaugeGrad)" stroke-width="14" stroke-linecap="round" stroke-dasharray="251" stroke-dashoffset="${251 - 251 * ((angle + 90) / 180)}"/>
          <defs>
            <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#ca3431"/>
              <stop offset="55%" stop-color="#f6af29"/>
              <stop offset="100%" stop-color="#81b64c"/>
            </linearGradient>
          </defs>
          <line x1="100" y1="100" x2="100" y2="36" stroke="#e4e0d9" stroke-width="3" stroke-linecap="round" transform="rotate(${angle} 100 100)"/>
          <circle cx="100" cy="100" r="6" fill="#e4e0d9"/>
        </svg>
      </div>`;
  }

  function renderDeepDive(container, summary, cadence) {
    if (!container) return;
    const dd = deepDiveFor(summary, cadence);
    const list = dd.phases
      .map((p) => {
        const sign = p.delta >= 0 ? "pos" : "neg";
        return `
          <button class="dd-item" data-cat="${p.key}">
            <span class="dd-icon dd-icon--${p.key}">${p.icon}</span>
            <span class="dd-main">
              <span class="dd-label">${p.label}</span>
              <span class="dd-sub">${p.sub}</span>
            </span>
            <span class="dd-right">
              <span class="dd-elo">${p.elo}</span>
              <span class="dd-delta dd-delta--${sign}">${formatDelta(p.delta)}</span>
            </span>
            <span class="dd-chevron">›</span>
          </button>`;
      })
      .join("");
    container.innerHTML = `
      <div class="hero-card">
        <div class="hero-title">Héros</div>
        <div class="hero-sub">NIVEAU ESTIMÉ (${CADENCE_LABELS[cadence].toUpperCase()})</div>
        <div class="hero-value">${dd.estimated}</div>
        ${renderGauge(dd.estimated)}
      </div>
      <div class="dd-section-title">DÉTAIL PAR PHASE</div>
      <div class="dd-list">${list}</div>`;
  }

  function renderCategoryDetail(container, category, summary) {
    if (!container) return;
    container.innerHTML = categoryDetailHtml(category, summary);
  }

  function renderFinalesTiles(container, summary) {
    if (!container) return;
    const f = summary.finales;
    container.innerHTML = `
      <div class="stat-tile stat-tile--good">
        <div class="stat-tile-head">TAUX DE CONVERSION</div>
        <div class="stat-tile-value">${f.conversion.toFixed(1).replace(".", ",")}%</div>
        <div class="stat-tile-cap">Conversion d'un avantage technique (≥ +1.50)</div>
      </div>
      <div class="stat-tile stat-tile--warn">
        <div class="stat-tile-head">TAUX DE RÉSILIENCE</div>
        <div class="stat-tile-value">${f.resilience.toFixed(1).replace(".", ",")}%</div>
        <div class="stat-tile-cap">Nulles/victoires arrachées en position perdante (≤ −1.50)</div>
      </div>`;
  }

  function renderTacticsCard(container, summary) {
    if (!container) return;
    const t = summary.tactics;
    container.innerHTML = `
      <div class="tac-rating">${t.rating}</div>
      <div class="tac-rating-label">Rating de puzzles</div>
      <div class="tac-stats">
        <div class="tac-stat"><strong>${t.toReview}</strong><span>À RÉVISER</span></div>
        <div class="tac-stat"><strong>${t.solved}</strong><span>RÉSOLUS</span></div>
        <div class="tac-stat"><strong>🔥 ${t.streak}</strong><span>SÉRIE</span></div>
      </div>`;
  }

  function renderAcplChart(canvas, summary) {
    if (!canvas || typeof Chart === "undefined") return null;
    const d = summary.acplTrend;
    return new Chart(canvas, {
      type: "line",
      data: {
        labels: d.labels,
        datasets: [
          { label: "Gaffes", data: d.blunders, borderColor: "#e09a44", backgroundColor: "transparent", tension: 0.35, pointRadius: 0 },
          { label: "Coups manqués", data: d.missed, borderColor: "#81b64c", backgroundColor: "transparent", tension: 0.35, pointRadius: 0 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true }, x: { grid: { display: false } } },
      },
    });
  }

  function renderGaffeDonut(canvas, summary) {
    if (!canvas || typeof Chart === "undefined") return null;
    const g = summary.gaffeRate;
    return new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: ["Ouverture", "Milieu", "Finale"],
        datasets: [{ data: [g.opening, g.middlegame, g.endgame], backgroundColor: ["#81b64c", "#b0aaa0", "#e09a44"], borderWidth: 0 }],
      },
      options: { responsive: true, maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "right" } } },
    });
  }

  /**
   * Monte la vue complète à partir d'un résumé déjà chargé.
   * @param {object} refs  conteneurs DOM (matrix, deepDive, finales, tactics, acplCanvas, donutCanvas)
   */
  function mount(refs, summary, cadence = "blitz") {
    renderMatrix(refs.matrix, summary);
    renderDeepDive(refs.deepDive, summary, cadence);
    renderFinalesTiles(refs.finales, summary);
    renderTacticsCard(refs.tactics, summary);
    renderAcplChart(refs.acplCanvas, summary);
    renderGaffeDonut(refs.donutCanvas, summary);
  }

  return {
    CADENCES,
    CADENCE_LABELS,
    CATEGORIES,
    GAUGE_MIN,
    GAUGE_MAX,
    STRONG_DELTA,
    MOCK_SUMMARY,
    TACTIC_THEMES,
    ENDGAME_LESSONS,
    CATEGORY_TITLES,
    fetchSummary,
    isEmpty,
    categoryDetailHtml,
    renderCategoryDetail,
    cellClass,
    phaseDelta,
    formatDelta,
    deepDiveFor,
    gaugeAngle,
    matrixRows,
    renderMatrix,
    renderDeepDive,
    renderFinalesTiles,
    renderTacticsCard,
    renderAcplChart,
    renderGaffeDonut,
    mount,
  };
})();

if (typeof window !== "undefined") window.AdvancedStats = AdvancedStats;
if (typeof module !== "undefined" && module.exports != null) module.exports = AdvancedStats;
