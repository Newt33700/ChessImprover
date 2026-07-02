/**
 * Tests unitaires – CoachingVoice (EPIC 14, US 14.1/14.2).
 */

const CoachingVoice = require("../js/coaching_voice.js");

afterEach(() => {
  delete global.window.AudioContext;
  delete global.window.webkitAudioContext;
  delete global.window.speechSynthesis;
  delete global.window.SpeechSynthesisUtterance;
  try { localStorage.clear(); } catch { /* ignore */ }
  CoachingVoice.setEnabled(false);
});

describe("isSupported", () => {
  test("faux sans speechSynthesis", () => {
    expect(CoachingVoice.isSupported()).toBe(false);
  });

  test("vrai si window.speechSynthesis existe", () => {
    global.window.speechSynthesis = {};
    expect(CoachingVoice.isSupported()).toBe(true);
  });
});

describe("setEnabled / isEnabled / loadPreference", () => {
  test("désactivé par défaut", () => {
    expect(CoachingVoice.isEnabled()).toBe(false);
  });

  test("setEnabled bascule et persiste", () => {
    CoachingVoice.setEnabled(true);
    expect(CoachingVoice.isEnabled()).toBe(true);
    expect(localStorage.getItem("ci_voice_coach")).toBe("1");
  });

  test("loadPreference restaure depuis localStorage", () => {
    localStorage.setItem("ci_voice_coach", "1");
    expect(CoachingVoice.loadPreference()).toBe(true);
    expect(CoachingVoice.isEnabled()).toBe(true);
  });

  test("loadPreference renvoie false si rien n'est stocké", () => {
    expect(CoachingVoice.loadPreference()).toBe(false);
  });
});

describe("alertFor", () => {
  test("null pour une classification qui ne mérite pas d'alerte", () => {
    expect(CoachingVoice.alertFor("good", "Nf3")).toBeNull();
    expect(CoachingVoice.alertFor("brilliant", "Nf3")).toBeNull();
    expect(CoachingVoice.alertFor("book", "Nf3")).toBeNull();
  });

  test("alerte blunder mentionne le coup joué", () => {
    const alert = CoachingVoice.alertFor("blunder", "Qxh7");
    expect(alert).toEqual({ severity: "blunder", text: expect.stringContaining("Qxh7") });
  });

  test("alerte mistake distincte du blunder", () => {
    const alert = CoachingVoice.alertFor("mistake", "Bd3");
    expect(alert.severity).toBe("mistake");
    expect(alert.text).toContain("Bd3");
  });

  test("coup absent retombe sur un libellé générique", () => {
    const alert = CoachingVoice.alertFor("blunder");
    expect(alert.text).toContain("ce coup");
  });
});

describe("bestMoveNarration", () => {
  test("null sans coup", () => {
    expect(CoachingVoice.bestMoveNarration(null)).toBeNull();
    expect(CoachingVoice.bestMoveNarration("")).toBeNull();
  });

  test("phrase mentionnant le meilleur coup", () => {
    expect(CoachingVoice.bestMoveNarration("Nxe5")).toBe("Le meilleur coup était Nxe5.");
  });
});

describe("beep", () => {
  test("no-op silencieux sans AudioContext", () => {
    expect(() => CoachingVoice.beep("blunder")).not.toThrow();
  });

  test("crée et démarre un oscillateur si AudioContext est disponible", () => {
    const start = jest.fn();
    const stop = jest.fn();
    const connect = jest.fn();
    const osc = { frequency: {}, connect, start, stop };
    const gain = { connect, gain: { setValueAtTime: jest.fn(), exponentialRampToValueAtTime: jest.fn() } };
    global.window.AudioContext = jest.fn().mockImplementation(() => ({
      createOscillator: () => osc,
      createGain: () => gain,
      currentTime: 0,
      destination: {},
    }));

    CoachingVoice.beep("blunder");

    expect(osc.frequency.value).toBe(220);
    expect(start).toHaveBeenCalled();
    expect(stop).toHaveBeenCalled();
  });

  test("fréquence plus aiguë pour une simple erreur", () => {
    const osc = { frequency: {}, connect: jest.fn(), start: jest.fn(), stop: jest.fn() };
    const gain = { connect: jest.fn(), gain: { setValueAtTime: jest.fn(), exponentialRampToValueAtTime: jest.fn() } };
    global.window.AudioContext = jest.fn().mockImplementation(() => ({
      createOscillator: () => osc,
      createGain: () => gain,
      currentTime: 0,
      destination: {},
    }));

    CoachingVoice.beep("mistake");

    expect(osc.frequency.value).toBe(330);
  });
});

describe("speak", () => {
  test("no-op si désactivé", () => {
    global.window.speechSynthesis = { speak: jest.fn(), cancel: jest.fn() };
    CoachingVoice.speak("Attention");
    expect(global.window.speechSynthesis.speak).not.toHaveBeenCalled();
  });

  test("no-op si non supporté même si activé", () => {
    CoachingVoice.setEnabled(true);
    expect(() => CoachingVoice.speak("Attention")).not.toThrow();
  });

  test("appelle speechSynthesis.speak avec le texte fourni si activé et supporté", () => {
    const speak = jest.fn();
    const cancel = jest.fn();
    global.window.speechSynthesis = { speak, cancel };
    global.window.SpeechSynthesisUtterance = jest.fn().mockImplementation((text) => ({ text }));
    CoachingVoice.setEnabled(true);

    CoachingVoice.speak("Attention, ce coup expose ta dame.");

    expect(cancel).toHaveBeenCalled();
    expect(speak).toHaveBeenCalledTimes(1);
    expect(global.window.SpeechSynthesisUtterance).toHaveBeenCalledWith("Attention, ce coup expose ta dame.");
  });

  test("no-op silencieux sur texte vide", () => {
    global.window.speechSynthesis = { speak: jest.fn(), cancel: jest.fn() };
    CoachingVoice.setEnabled(true);
    CoachingVoice.speak("");
    expect(global.window.speechSynthesis.speak).not.toHaveBeenCalled();
  });
});
