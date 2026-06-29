"""Estimateur d'Elo de performance – algorithme CAPS simplifié.

Règles métier (exactement portées depuis EloEngine JS) :

    Score = 100 × e^(-0.005 × |Perte|)

    PrécisionGlobale = moyenne(scores)

    EloPerformance = (PrécisionGlobale × 20) + (EloAdversaire × 0.5)
    Borné entre 400 et 2800.

Ce module est PUR : aucune dépendance externe, 100 % testable.
"""

from __future__ import annotations

import math
from typing import List

from app.domain.models import Classification

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DECAY: float = 0.005  # coefficient exponentiel (identique JS)

ELO_FLOOR: int = 400
ELO_CEIL: int = 2800

# Seuils de classification (identiques JS EloEngine.classify)
_CLASSIFICATION_THRESHOLDS: List[tuple] = [
    (95, Classification.BRILLIANT),
    (85, Classification.EXCELLENT),
    (70, Classification.GOOD),
    (50, Classification.INACCURACY),
    (25, Classification.MISTAKE),
]


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy(cp_loss: float) -> float:
    """Score de précision d'un coup individuel (0-100).

    Parameters
    ----------
    cp_loss : float
        Perte en centipions : |Eval_top - Eval_joué|.

    Returns
    -------
    float
        Score entre 0.0 et 100.0.
    """
    loss = abs(cp_loss)
    score = 100.0 * math.exp(-DECAY * loss)
    return score


def game_accuracy(scores: List[float]) -> float:
    """Précision globale d'une partie (moyenne des scores de précision).

    Parameters
    ----------
    scores : list[float]
        Liste des scores de précision de chaque coup.

    Returns
    -------
    float
        Moyenne arithmétique, 0.0 si liste vide.
    """
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def estimate_elo(accuracy: float, opponent_elo: int) -> int:
    """Estimation de l'Elo de performance.

    Formule : (PrécisionGlobale × 20) + (EloAdversaire × 0.5)
    Borné entre 400 et 2800.

    Parameters
    ----------
    accuracy : float
        Précision globale de la partie (0-100).
    opponent_elo : int
        Elo de l'adversaire.

    Returns
    -------
    int
        Elo de performance estimé, entre 400 et 2800.
    """
    raw = (accuracy * 20.0) + (opponent_elo * 0.5)
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def classify_move(score: float) -> Classification:
    """Classification qualitative d'un coup selon son score de précision.

    Seuils (identiques JS) :
        >= 95  → brilliant
        >= 85  → excellent
        >= 70  → good
        >= 50  → inaccuracy
        >= 25  → mistake
        <  25  → blunder

    Parameters
    ----------
    score : float
        Score de précision (0-100).

    Returns
    -------
    Classification
    """
    for threshold, classification in _CLASSIFICATION_THRESHOLDS:
        if score >= threshold:
            return classification
    return Classification.BLUNDER
