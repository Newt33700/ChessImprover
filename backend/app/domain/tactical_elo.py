"""Elo tactique du joueur — sélection adaptative (US 8.1, EPIC 8).

Système de notation simplifié (± 15 points par tentative), distinct de
l'Elo virtuel Stats Avancées (EPIC 3) qui mesure la qualité des coups
joués dans de vraies parties plutôt que la réussite de puzzles.
"""

from __future__ import annotations

DEFAULT_TACTICAL_ELO = 1000
ELO_STEP = 15
MIN_TACTICAL_ELO = 100


def update_elo(current_elo: int, success: bool) -> int:
    """Ajuste l'Elo tactique après une tentative : +15 si réussie, -15 sinon.

    Plancher à ``MIN_TACTICAL_ELO`` pour éviter qu'une série d'échecs ne
    fasse dériver l'Elo vers des valeurs négatives absurdes.
    """
    delta = ELO_STEP if success else -ELO_STEP
    return max(MIN_TACTICAL_ELO, current_elo + delta)
