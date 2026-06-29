/**
 * US 3 – Endgame Detector & Syzygy Tablebases
 * Détecte les finales, évalue via l'API Syzygy de Lichess (<= 7 pièces),
 * et tague les coups qui convertissent une position gagnante en nulle/perdue.
 */

const EndgameDetector = (() => {
  const PIECE_VALUES = { q: 9, r: 5, b: 3, n: 3, p: 0, k: 0 };
  const ENDGAME_THRESHOLD = 13; // pts hors Rois et Pions
  const SYZYGY_API = "https://tablebase.lichess.ovh/standard";
  const MAX_PIECES_SYZYGY = 7;

  // ── Analyse matérielle ─────────────────────────────────────────────

  function countMaterial(fen) {
    const board = fen.split(" ")[0];
    let total = 0;
    let pieces = 0;

    for (const ch of board) {
      const lower = ch.toLowerCase();
      if (lower === "k" || lower === "/") continue;
      if (lower in PIECE_VALUES) {
        total  += PIECE_VALUES[lower];
        pieces++;
      }
    }
    // Rois (2) + pièces non-pion + pions
    const totalPieces = 2 + pieces;
    return { material: total, totalPieces };
  }

  function detectEndgamePhase(fen) {
    const { material } = countMaterial(fen);
    return material <= ENDGAME_THRESHOLD;
  }

  function isEligibleForSyzygy(fen) {
    const { totalPieces } = countMaterial(fen);
    return totalPieces <= MAX_PIECES_SYZYGY;
  }

  // ── API Syzygy (Lichess) ───────────────────────────────────────────

  async function querySyzygy(fen) {
    const url = `${SYZYGY_API}?fen=${encodeURIComponent(fen)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Syzygy API error ${res.status}`);
    return res.json();
  }

  function classifyCategory(syzygyData) {
    const cat = syzygyData?.category;
    if (!cat) return null;
    if (cat === "win" || cat === "cursed-win")   return "win";
    if (cat === "draw" || cat === "blessed-loss") return "draw";
    if (cat === "loss" || cat === "cursed-loss")  return "loss";
    return "unknown";
  }

  // ── Analyse d'une partie ────────────────────────────────────────────

  async function analyzeGame(moves, playerColor, onProgress) {
    const results = {
      endgameStartIndex: null,
      endgameAccuracies: [],
      endgameMistakes:   [],
      syzygyBlunders:    [],
    };

    let inEndgame = false;
    let prevCategory = null;

    for (let i = 0; i < moves.length; i++) {
      const move = moves[i];
      if (!move.fen) continue;

      if (!inEndgame && detectEndgamePhase(move.fen)) {
        inEndgame = true;
        results.endgameStartIndex = i;
      }

      if (!inEndgame) continue;

      if (move.accuracy_score != null) {
        results.endgameAccuracies.push(move.accuracy_score);
      }

      if (isEligibleForSyzygy(move.fen)) {
        try {
          const data = await querySyzygy(move.fen);
          const category = classifyCategory(data);

          if (onProgress) onProgress({ index: i, category });

          if (move.color === playerColor && prevCategory === "win" && category !== "win") {
            results.syzygyBlunders.push({ moveIndex: i, san: move.san, from: prevCategory, to: category });
          }

          prevCategory = category;
        } catch {
          // API indisponible – on continue sans Syzygy
        }
      }
    }

    results.endgameAvgAccuracy = results.endgameAccuracies.length
      ? parseFloat((results.endgameAccuracies.reduce((a, b) => a + b, 0) / results.endgameAccuracies.length).toFixed(1))
      : null;

    return results;
  }

  // ── Rendu HTML ─────────────────────────────────────────────────────

  function renderStats(results, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (results.endgameStartIndex === null) {
      container.innerHTML = `<p class="empty-state">Aucune finale détectée dans cette partie.</p>`;
      return;
    }

    const blunderRows = results.syzygyBlunders.length
      ? results.syzygyBlunders.map((b) =>
          `<tr><td>${b.san}</td><td class="endgame-win">${b.from}</td><td class="endgame-loss">${b.to}</td></tr>`
        ).join("")
      : `<tr><td colspan="3" class="empty-state">Aucune gaffe de finale détectée ✓</td></tr>`;

    container.innerHTML = `
      <div class="endgame-summary">
        <div class="stat-chip">
          Précision en finale :
          <strong>${results.endgameAvgAccuracy !== null ? results.endgameAvgAccuracy + "%" : "—"}</strong>
        </div>
        <div class="stat-chip">
          Gaffes Syzygy : <strong>${results.syzygyBlunders.length}</strong>
        </div>
      </div>
      <table class="endgame-table">
        <thead><tr><th>Coup</th><th>Avant</th><th>Après</th></tr></thead>
        <tbody>${blunderRows}</tbody>
      </table>`;
  }

  return {
    detectEndgamePhase,
    isEligibleForSyzygy,
    countMaterial,
    classifyCategory,
    analyzeGame,
    renderStats,
    querySyzygy,
    _ENDGAME_THRESHOLD: ENDGAME_THRESHOLD,
    _MAX_PIECES_SYZYGY: MAX_PIECES_SYZYGY,
  };
})();

window.EndgameDetector = EndgameDetector;
