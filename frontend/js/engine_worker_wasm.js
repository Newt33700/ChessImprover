/**
 * Chess Improver – Web Worker Stockfish WASM (UCI)
 *
 * Essaie d'abord Stockfish 16 WASM avec NNUE.
 * Fallback sur stockfish.js (asm.js) si WASM indisponible.
 *
 * Renvoie au thread principal :
 *   { type:"info", depth, evaluation, pv }   – mises à jour intermédiaires
 *   { type:"bestmove", move, pv }            – résultat final
 *   { type:"ready" }                          – moteur prêt
 */

// EPIC 13, US 13.1 : fichiers locaux uniquement (aucun appel externe, cf.
// §4.11 du README). Pas de build WASM+NNUE auto-hébergé pour l'instant
// (cf. §10 « reste à faire ») — le worker retombe directement sur le
// moteur asm.js déjà vendorisé (`js/stockfish.js`).
const WASM_CDNS = [];
const ASM_CDNS = ["stockfish.js"];

const MIN_DEPTH   = 15;
const MIN_TIME_MS = 500;

let engine     = null;
let currentFen = null;
let lastPV     = [];
let analysisStart = 0;

// ── Helpers ────────────────────────────────────────────────────────

function parseMateScore(mateIn) {
  const n = parseInt(mateIn, 10);
  return n > 0 ? 10000 : -10000;
}

function parseLine(line) {
  const depthM = line.match(/depth\s+(\d+)/);
  const cpM    = line.match(/score cp\s+(-?\d+)/);
  const mateM  = line.match(/score mate\s+(-?\d+)/);
  const pvM    = line.match(/ pv (.+)$/);
  const depth  = depthM ? parseInt(depthM[1], 10) : 0;

  const evaluation = cpM
    ? parseInt(cpM[1], 10)
    : mateM ? parseMateScore(mateM[1]) : null;

  const pv = pvM
    ? pvM[1].trim().split(/\s+/).slice(0, 5)
    : [];

  return { depth, evaluation, pv };
}

// ── Engine init ────────────────────────────────────────────────────

function tryLoad(urls) {
  for (const url of urls) {
    try {
      importScripts(url);
      return true;
    } catch {
      /* try next */
    }
  }
  return false;
}

function setupEngine(factory) {
  try {
    engine = typeof factory === "function" ? factory() : null;
  } catch {
    engine = null;
  }
  if (!engine) return false;

  engine.onmessage = (event) => {
    const line = typeof event === "string" ? event
               : (event && typeof event.data === "string") ? event.data
               : String((event && event.data) || "");
    handleUCI(line.trim());
  };

  engine.postMessage("uci");
  engine.postMessage("setoption name Threads value 1");
  engine.postMessage("setoption name Hash value 32");
  engine.postMessage("setoption name Use NNUE value true");
  engine.postMessage("isready");
  return true;
}

function initEngine() {
  if (tryLoad(WASM_CDNS)) {
    const factory = self.STOCKFISH || self.Stockfish;
    if (setupEngine(factory)) return;
  }
  if (tryLoad(ASM_CDNS)) {
    const factory = self.STOCKFISH || self.Stockfish;
    if (setupEngine(factory)) return;
  }
  postMessage({ type: "error", message: "Aucun moteur Stockfish disponible" });
}

// ── UCI handler ────────────────────────────────────────────────────

function handleUCI(line) {
  if (!line || line.startsWith("[WF")) return;

  if (line === "uciok" || line === "readyok") {
    postMessage({ type: "ready" });
    return;
  }

  if (line.startsWith("info") && line.includes("score")) {
    const { depth, evaluation, pv } = parseLine(line);
    if (depth < 3 || evaluation === null) return;
    if (pv.length) lastPV = pv;
    postMessage({ type: "info", depth, evaluation, pv, fen: currentFen });
    return;
  }

  if (line.startsWith("bestmove")) {
    const move = line.split(" ")[1] || null;
    postMessage({ type: "bestmove", move, pv: lastPV, fen: currentFen });
    lastPV = [];
    return;
  }
}

// ── Main thread interface ──────────────────────────────────────────

self.onmessage = (event) => {
  const msg = typeof event.data === "string" ? event.data
            : (event.data && event.data.cmd) ? event.data.cmd
            : "";

  if (!engine) {
    postMessage({ type: "error", message: "Moteur non initialisé" });
    return;
  }

  if (msg.startsWith("position fen ")) {
    currentFen = msg.slice("position fen ".length).trim();
    lastPV = [];
    engine.postMessage(msg);
    return;
  }

  if (msg.startsWith("go")) {
    analysisStart = Date.now();
    // Force minimum depth 15 and minimum time 500ms
    const goCmd = `go depth ${MIN_DEPTH} movetime ${MIN_TIME_MS}`;
    engine.postMessage(goCmd);
    return;
  }

  if (msg === "stop") {
    engine.postMessage("stop");
    return;
  }

  if (msg === "ucinewgame") {
    engine.postMessage("ucinewgame");
    return;
  }

  engine.postMessage(msg);
};

initEngine();
