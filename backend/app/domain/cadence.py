"""Classification de cadence — du `time_control` Chess.com vers `TimeClass`.

Chess.com exprime la cadence en secondes de base, éventuellement suivie d'un
incrément (``"600"``, ``"180+2"``, ``"1/86400"`` pour le daily). On classe selon
le **temps estimé d'une partie** = base + 40 × incrément (heuristique standard) :

* daily (``"1/..."``)            → DAILY
* temps estimé < 180 s           → BULLET
* 180 s ≤ temps estimé < 600 s   → BLITZ
* ≥ 600 s                        → RAPID

Module PUR.
"""

from __future__ import annotations

from typing import Optional

from app.domain.models import TimeClass

# Seuils (secondes de temps estimé) — bornes inférieures Blitz / Rapide.
BLITZ_MIN_SECONDS: int = 180
RAPID_MIN_SECONDS: int = 600

#: Nombre de coups servant à estimer l'impact de l'incrément.
INCREMENT_MOVES: int = 40


def estimate_seconds(time_control: Optional[str]) -> Optional[int]:
    """Temps estimé d'une partie (secondes) depuis un ``time_control``.

    Renvoie ``None`` si la chaîne est vide ou illisible. Les cadences daily
    (``"1/86400"``) renvoient leur base en secondes par coup (non utilisée pour
    le classement, qui les détecte via le ``/``).
    """
    if not time_control:
        return None
    tc = time_control.strip()
    try:
        if "/" in tc:  # daily : "1/86400" → secondes par coup
            return int(tc.split("/", 1)[1])
        if "+" in tc:
            base, inc = tc.split("+", 1)
            return int(base) + INCREMENT_MOVES * int(inc)
        return int(tc)
    except (ValueError, IndexError):
        return None


def classify_cadence(time_control: Optional[str]) -> Optional[TimeClass]:
    """Classe un ``time_control`` Chess.com en ``TimeClass``.

    Renvoie ``None`` si la cadence est inconnue/illisible.
    """
    if not time_control:
        return None
    if "/" in time_control:
        return TimeClass.DAILY

    seconds = estimate_seconds(time_control)
    if seconds is None:
        return None
    if seconds < BLITZ_MIN_SECONDS:
        return TimeClass.BULLET
    if seconds < RAPID_MIN_SECONDS:
        return TimeClass.BLITZ
    return TimeClass.RAPID
