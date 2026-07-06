/**
 * Stub CDN minimal pour les tests E2E Playwright (chess.js / chessboard.js /
 * jQuery / Chart.js) — nécessaire car le bac à sable de développement bloque
 * les CDN externes (cdnjs, jsdelivr). En CI (accès réseau réel), ce stub
 * n'est PAS utilisé : `helpers.js` ne l'injecte que si `E2E_STUB_CDN=1`.
 *
 * `Chess(fen)` supporte deux mécanismes de pilotage pour les tests :
 *  - `window.__TACTICS_SOLUTIONS[fen]` : SAN à renvoyer pour cette position.
 *  - `window.__FORCE_MOVE_SAN` : SAN forcé pour le prochain appel à move(),
 *    prioritaire sur la table de solutions (permet de simuler un coup faux).
 */
window.Chess = function Chess(fen) {
  this._fen = fen || "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  this.load_pgn = function() { return true; };
  this.load = function() { return true; };
  this.fen = function() { return this._fen; };
  this.header = function() { return {}; };
  this.moves = function() { return []; };
  this.history = function() { return []; };
  this.game_over = function() { return false; };
  this.turn = function() { return (this._fen.split(" ")[1]) || "w"; };
  this.move = function() {
    const sol = (window.__TACTICS_SOLUTIONS || {})[this._fen];
    const san = window.__FORCE_MOVE_SAN || sol;
    if (!san) return null;
    return { san };
  };
  this.undo = function() { return null; };
  this.reset = function() {};
  this.in_checkmate = function() { return false; };
  this.in_draw = function() { return false; };
  this.pgn = function() { return ""; };
};
window.$ = window.jQuery = function() {
  return { on: function(){ return this; }, ready: function(cb){ cb && cb(); return this; }, css: function(){ return this; }, attr: function(){ return this; } };
};
window.$.extend = function() { return {}; };
window.Chessboard = function() {
  return { position: function(){}, destroy: function(){}, orientation: function(){}, resize: function(){} };
};
// EPIC 37 : échiquier principal (board_manager.js) migré vers Chessground —
// les échiquiers de problèmes exercés par ces specs e2e restent sur
// chessboard.js (stub ci-dessus), mais board_manager.js est instancié dès le
// boot de l'appli (indépendamment de la vue affichée), donc ce stub doit
// exister pour que `new BoardManager(...)` ne plante jamais en E2E.
window.Chessground = function() {
  return {
    set: function(){}, toggleOrientation: function(){}, redrawAll: function(){},
    destroy: function(){}, setShapes: function(){},
  };
};
window.Chart = function() {
  return { destroy: function(){}, update: function(){}, data: {} };
};
