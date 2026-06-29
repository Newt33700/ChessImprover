/**
 * US 2 – Opening Statistics
 * Agrège les parties par ouverture et affiche un tableau W/D/L.
 */

const OpeningsStats = (() => {
  const DRAW_RESULTS = new Set([
    "agreed", "stalemate", "repetition", "insufficient",
    "50move", "timevsinsufficient", "draw",
  ]);

  // ── Extraction du résultat d'une partie ───────────────────────────

  function getResult(game, username) {
    const uname = (username || "").toLowerCase();
    if (!uname) return null;

    const whiteName = (game.white?.username || "").toLowerCase();
    const blackName = (game.black?.username || "").toLowerCase();
    if (whiteName !== uname && blackName !== uname) return null;

    const isWhite = whiteName === uname;
    const side    = isWhite ? game.white : game.black;
    const result  = side?.result || game.result || "";

    if (result === "win")     return "win";
    if (DRAW_RESULTS.has(result)) return "draw";
    return "loss";
  }

  // ── Extraction du nom d'ouverture ─────────────────────────────────

  function extractOpeningName(game) {
    // 1. Header PGN ECO + Opening
    const pgn = game.pgn || "";
    const openingMatch = pgn.match(/\[Opening\s+"([^"]+)"\]/);
    if (openingMatch) return openingMatch[1];

    // 2. Header ECO seul
    const ecoMatch = pgn.match(/\[ECO\s+"([^"]+)"\]/);
    if (ecoMatch) return ecoMatch[1];

    // 3. Champ dédié dans l'objet game (Chess.com API)
    if (game.opening) return game.opening;

    return "Inconnue";
  }

  // ── Agrégation ────────────────────────────────────────────────────

  function aggregate(games, username) {
    const map = new Map();

    for (const game of games) {
      const opening = extractOpeningName(game);
      const result  = getResult(game, username);
      if (!result) continue;

      const uname  = (username || "").toLowerCase();
      const isWhite = (game.white?.username || "").toLowerCase() === uname;
      const color   = isWhite ? "Blanc" : "Noir";
      const key     = `${opening}__${color}`;

      if (!map.has(key)) {
        map.set(key, { opening, color, wins: 0, draws: 0, losses: 0, total: 0 });
      }
      const entry = map.get(key);
      entry.total++;
      if (result === "win")  entry.wins++;
      else if (result === "draw") entry.draws++;
      else                   entry.losses++;
    }

    return Array.from(map.values())
      .sort((a, b) => b.total - a.total);
  }

  // ── Calcul des pourcentages ────────────────────────────────────────

  function computeRates(entry) {
    const { wins, draws, losses, total } = entry;
    if (!total) return { winPct: 0, drawPct: 0, lossPct: 0 };
    return {
      winPct:  parseFloat(((wins  / total) * 100).toFixed(1)),
      drawPct: parseFloat(((draws / total) * 100).toFixed(1)),
      lossPct: parseFloat(((losses / total) * 100).toFixed(1)),
    };
  }

  // ── Rendu HTML ────────────────────────────────────────────────────

  function renderTable(entries) {
    if (!entries.length) {
      return `<p class="empty-state">Aucune donnée d'ouverture disponible.<br>
        Connectez-vous à Chess.com et analysez des parties.</p>`;
    }

    const rows = entries.map((e) => {
      const { winPct, drawPct, lossPct } = computeRates(e);
      return `
        <tr>
          <td class="opening-name">${escapeHtml(e.opening)}</td>
          <td class="opening-color">${e.color}</td>
          <td class="opening-total">${e.total}</td>
          <td class="opening-gauge-cell">
            <div class="wdl-gauge" title="V:${winPct}% N:${drawPct}% D:${lossPct}%">
              <div class="wdl-win"  style="width:${winPct}%"></div>
              <div class="wdl-draw" style="width:${drawPct}%"></div>
              <div class="wdl-loss" style="width:${lossPct}%"></div>
            </div>
            <div class="wdl-labels">
              <span class="wdl-win-label">${winPct}%</span>
              <span class="wdl-draw-label">${drawPct}%</span>
              <span class="wdl-loss-label">${lossPct}%</span>
            </div>
          </td>
        </tr>`;
    }).join("");

    return `
      <table class="openings-table">
        <thead>
          <tr>
            <th>Ouverture</th>
            <th>Couleur</th>
            <th>Parties</th>
            <th>V / N / D</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Point d'entrée public ─────────────────────────────────────────

  async function render(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `<p class="empty-state">Chargement…</p>`;

    let games = [];
    let username = "";

    try {
      if (window.ChessDB) {
        games = await ChessDB.getAllGames();
      } else {
        // Fallback localStorage
        const raw = localStorage.getItem("ci_games");
        games = raw ? JSON.parse(raw) : [];
      }
      // Récupérer le username depuis localStorage
      username = localStorage.getItem("ci_username") || "";
      if (username) username = JSON.parse(username);
    } catch {}

    const entries = aggregate(games, username);
    container.innerHTML = renderTable(entries);
  }

  return {
    aggregate,
    computeRates,
    extractOpeningName,
    getResult,
    render,
    // internals exposed for tests
    _renderTable: renderTable,
    _escapeHtml:  escapeHtml,
  };
})();

window.OpeningsStats = OpeningsStats;
