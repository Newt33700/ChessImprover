/**
 * Chess Improver – Web Worker Stockfish UCI
 *
 * Charge stockfish.js via importScripts (CDN ou fichier local).
 * Relaye les lignes UCI brutes entre le thread principal et Stockfish.
 */

const CDNS = [
  "stockfish.js",  // fichier local (même dossier)
  "https://cdn.jsdelivr.net/npm/stockfish.js@10.0.2/stockfish.js",
  "https://cdnjs.cloudflare.com/ajax/libs/stockfish.js/10.0.2/stockfish.js",
];

let engine     = null;
let currentFen = null;

function log(tag, ...args) {
  postMessage("[WF " + tag + "] " + args.join(" "));
}

function initEngine() {
  log("INIT", "début chargement Stockfish, CDNS:", CDNS.length);

  let loaded = false;
  for (const url of CDNS) {
    try {
      log("INIT", "tentative importScripts:", url);
      importScripts(url);
      loaded = true;
      log("INIT", "✅ chargé depuis:", url);
      break;
    } catch (e) {
      log("INIT", "❌ échec:", url, e.message);
    }
  }

  if (!loaded) {
    log("INIT", "❌ AUCUN CDN disponible");
    return;
  }

  const factory = self.STOCKFISH || self.Stockfish;
  log("INIT", "factory STOCKFISH:", typeof factory);
  if (typeof factory !== "function") {
    log("INIT", "❌ factory non trouvée, self keys:", Object.keys(self).filter(k => k.toLowerCase().includes("stock"))  );
    return;
  }

  try {
    engine = factory();
    log("INIT", "✅ instance créée, type engine.onmessage:", typeof engine.onmessage);
  } catch (e) {
    log("INIT", "❌ instance échouée:", e.message);
    return;
  }

  // Relay TOUTES les lignes UCI brutes vers le thread principal
  engine.onmessage = function (event) {
    const line = typeof event === "string" ? event : String(event.data || event.line || "");
    if (line) postMessage(line);
  };

  engine.postMessage("uci");
  log("INIT", "→ uci envoyé");
  engine.postMessage("setoption name Threads value 1");
  engine.postMessage("setoption name Hash value 16");
  engine.postMessage("isready");
  log("INIT", "→ setoption + isready envoyés, en attente de uciok/readyok");
}

// ---------------------------------------------------------------------------
// Réception des commandes depuis le thread principal (lignes brutes)
// ---------------------------------------------------------------------------

self.onmessage = function (event) {
  const raw = event.data;
  const msg = (raw != null) ? String(raw) : "";
  if (!msg) {
    log("RECV", "⚠️ message vide, type:", typeof raw);
    return;
  }

  // Extraire le FEN pour les bestmove/eval
  if (msg.startsWith("position fen ")) {
    currentFen = msg.replace("position fen ", "");
    log("RECV", "FEN capturé:", currentFen.slice(0, 30) + "...");
  }

  if (msg.startsWith("[WF")) {
    log("RECV", "(ignoré log)");
    return;
  }

  log("RECV", "→ engine:", msg.slice(0, 60));

  if (engine) {
    engine.postMessage(msg);
  } else {
    log("RECV", "⚠️ pas d'engine, message ignoré");
  }
};

log("BOOT", "worker script exécuté, lancement initEngine");
initEngine();
