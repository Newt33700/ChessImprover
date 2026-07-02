/**
 * coaching_voice.js — Coach Vocal (EPIC 14, US 14.1 / US 14.2)
 *
 * Alertes tactiques instantanées (US 14.1) + synthèse vocale de l'idée
 * principale du meilleur coup (US 14.2), branchées sur le mode Review
 * existant (`_onMoveAccuracy`, temps réel pendant l'analyse Stockfish).
 *
 * 100% local (EPIC 13 « Zero External Assets ») : la synthèse vocale utilise
 * l'API Web Speech native du navigateur (`speechSynthesis`), le signal sonore
 * un simple oscillateur `AudioContext` généré en code — aucun fichier audio,
 * aucun appel réseau.
 */

const CoachingVoice = (() => {
  "use strict";

  const PREFERENCE_KEY = "ci_voice_coach";

  //: Messages contextuels par gravité (US 14.1) — seules les classifications
  //: "mistake"/"blunder" méritent une coupure de concentration du joueur.
  const ALERT_BUILDERS = {
    blunder: (san) => `Gaffe ! ${san} est une erreur importante.`,
    mistake: (san) => `Attention, ${san} n'était pas précis.`,
  };

  const state = { enabled: false };

  function isSupported() {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  /** Active/désactive la lecture vocale et persiste le choix (US 14.2). */
  function setEnabled(on) {
    state.enabled = !!on;
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(PREFERENCE_KEY, state.enabled ? "1" : "0");
      }
    } catch { /* localStorage indisponible */ }
    return state.enabled;
  }

  function isEnabled() {
    return state.enabled;
  }

  /** Restaure la préférence utilisateur (à appeler au boot). */
  function loadPreference() {
    try {
      state.enabled = typeof localStorage !== "undefined"
        && localStorage.getItem(PREFERENCE_KEY) === "1";
    } catch {
      state.enabled = false;
    }
    return state.enabled;
  }

  /**
   * Construit l'alerte tactique d'un coup selon sa classification.
   * @returns {{severity: string, text: string}|null} `null` si le coup ne
   *   déclenche aucune alerte (classification inconnue ou trop bonne).
   */
  function alertFor(classification, san) {
    const builder = ALERT_BUILDERS[classification];
    if (!builder) return null;
    return { severity: classification, text: builder(san || "ce coup") };
  }

  /** Phrase de synthèse vocale narrant le meilleur coup recommandé (US 14.2). */
  function bestMoveNarration(bestMoveSan) {
    if (!bestMoveSan) return null;
    return `Le meilleur coup était ${bestMoveSan}.`;
  }

  /** Signal sonore bref (US 14.1) — tonalité grave pour une gaffe, plus aiguë
   * pour une simple erreur. No-op silencieux si WebAudio est indisponible. */
  function beep(severity) {
    if (typeof window === "undefined") return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    try {
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = severity === "blunder" ? 220 : 330;
      osc.connect(gain);
      gain.connect(ctx.destination);
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc.start();
      osc.stop(ctx.currentTime + 0.4);
    } catch { /* best-effort, jamais bloquant */ }
  }

  /** Lit `text` à voix haute si la synthèse vocale est activée et disponible. */
  function speak(text) {
    if (!state.enabled || !text || !isSupported()) return;
    try {
      window.speechSynthesis.cancel();
      const utter = new window.SpeechSynthesisUtterance(text);
      utter.lang = "fr-FR";
      utter.rate = 1.05;
      window.speechSynthesis.speak(utter);
    } catch { /* best-effort, jamais bloquant */ }
  }

  return {
    isSupported, setEnabled, isEnabled, loadPreference,
    alertFor, bestMoveNarration, beep, speak,
  };
})();

if (typeof window !== "undefined") window.CoachingVoice = CoachingVoice;
if (typeof module !== "undefined" && module.exports != null) module.exports = CoachingVoice;
