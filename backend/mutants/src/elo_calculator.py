
from inspect import signature as _mutmut_signature

def _mutmut_trampoline(orig, mutants, *args, **kwargs):
    import os
    mutant_under_test = os.environ['MUTANT_UNDER_TEST']
    if mutant_under_test == 'fail':
        from __main__ import MutmutProgrammaticFailException
        raise MutmutProgrammaticFailException('Failed programmatically')      
    elif mutant_under_test == 'stats':
        from __main__ import record_trampoline_hit
        record_trampoline_hit(orig.__module__ + '.' + orig.__name__)
        return orig(*args, **kwargs)
    prefix = orig.__module__ + '.' + orig.__name__ + '__mutmut_'
    if not mutant_under_test.startswith(prefix):
        return orig(*args, **kwargs)
    mutant_name = mutant_under_test.rpartition('.')[-1]
    return mutants[mutant_name](*args, **kwargs)


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

def move_accuracy__mutmut_orig(cp_loss: float) -> float:
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


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_1(cp_loss: float) -> float:
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
    loss = abs(None)
    score = 100.0 * math.exp(-DECAY * loss)
    return score


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_2(cp_loss: float) -> float:
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
    loss = None
    score = 100.0 * math.exp(-DECAY * loss)
    return score


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_3(cp_loss: float) -> float:
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
    score = 101.0 * math.exp(-DECAY * loss)
    return score


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_4(cp_loss: float) -> float:
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
    score = 100.0 / math.exp(-DECAY * loss)
    return score


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_5(cp_loss: float) -> float:
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
    score = 100.0 * math.exp(+DECAY * loss)
    return score


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_6(cp_loss: float) -> float:
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
    score = 100.0 * math.exp(-DECAY / loss)
    return score


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def move_accuracy__mutmut_7(cp_loss: float) -> float:
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
    score = None
    return score

move_accuracy__mutmut_mutants = {
'move_accuracy__mutmut_1': move_accuracy__mutmut_1, 
    'move_accuracy__mutmut_2': move_accuracy__mutmut_2, 
    'move_accuracy__mutmut_3': move_accuracy__mutmut_3, 
    'move_accuracy__mutmut_4': move_accuracy__mutmut_4, 
    'move_accuracy__mutmut_5': move_accuracy__mutmut_5, 
    'move_accuracy__mutmut_6': move_accuracy__mutmut_6, 
    'move_accuracy__mutmut_7': move_accuracy__mutmut_7
}

def move_accuracy(*args, **kwargs):
    return _mutmut_trampoline(move_accuracy__mutmut_orig, move_accuracy__mutmut_mutants, *args, **kwargs) 

move_accuracy.__signature__ = _mutmut_signature(move_accuracy__mutmut_orig)
move_accuracy__mutmut_orig.__name__ = 'move_accuracy'




def game_accuracy__mutmut_orig(scores: List[float]) -> float:
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


def game_accuracy__mutmut_1(scores: List[float]) -> float:
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
    if  scores:
        return 0.0
    return sum(scores) / len(scores)


def game_accuracy__mutmut_2(scores: List[float]) -> float:
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
        return 1.0
    return sum(scores) / len(scores)


def game_accuracy__mutmut_3(scores: List[float]) -> float:
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
    return sum(None) / len(scores)


def game_accuracy__mutmut_4(scores: List[float]) -> float:
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
    return sum(scores) * len(scores)

game_accuracy__mutmut_mutants = {
'game_accuracy__mutmut_1': game_accuracy__mutmut_1, 
    'game_accuracy__mutmut_2': game_accuracy__mutmut_2, 
    'game_accuracy__mutmut_3': game_accuracy__mutmut_3, 
    'game_accuracy__mutmut_4': game_accuracy__mutmut_4
}

def game_accuracy(*args, **kwargs):
    return _mutmut_trampoline(game_accuracy__mutmut_orig, game_accuracy__mutmut_mutants, *args, **kwargs) 

game_accuracy.__signature__ = _mutmut_signature(game_accuracy__mutmut_orig)
game_accuracy__mutmut_orig.__name__ = 'game_accuracy'




def estimate_elo__mutmut_orig(accuracy: float, opponent_elo: int) -> int:
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


def estimate_elo__mutmut_1(accuracy: float, opponent_elo: int) -> int:
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
    raw = (accuracy / 20.0) + (opponent_elo * 0.5)
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_2(accuracy: float, opponent_elo: int) -> int:
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
    raw = (accuracy * 21.0) + (opponent_elo * 0.5)
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_3(accuracy: float, opponent_elo: int) -> int:
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
    raw = (accuracy * 20.0) - (opponent_elo * 0.5)
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_4(accuracy: float, opponent_elo: int) -> int:
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
    raw = (accuracy * 20.0) + (opponent_elo / 0.5)
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_5(accuracy: float, opponent_elo: int) -> int:
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
    raw = (accuracy * 20.0) + (opponent_elo * 1.5)
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_6(accuracy: float, opponent_elo: int) -> int:
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
    raw = None
    clamped = max(ELO_FLOOR, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_7(accuracy: float, opponent_elo: int) -> int:
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
    clamped = max(None, min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_8(accuracy: float, opponent_elo: int) -> int:
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
    clamped = max(ELO_FLOOR, min(None, raw))
    return int(round(clamped))


def estimate_elo__mutmut_9(accuracy: float, opponent_elo: int) -> int:
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
    clamped = max(ELO_FLOOR, min(ELO_CEIL, None))
    return int(round(clamped))


def estimate_elo__mutmut_10(accuracy: float, opponent_elo: int) -> int:
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
    clamped = max(ELO_FLOOR, min( raw))
    return int(round(clamped))


def estimate_elo__mutmut_11(accuracy: float, opponent_elo: int) -> int:
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
    clamped = max(ELO_FLOOR, min(ELO_CEIL,))
    return int(round(clamped))


def estimate_elo__mutmut_12(accuracy: float, opponent_elo: int) -> int:
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
    clamped = max( min(ELO_CEIL, raw))
    return int(round(clamped))


def estimate_elo__mutmut_13(accuracy: float, opponent_elo: int) -> int:
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
    clamped = None
    return int(round(clamped))


def estimate_elo__mutmut_14(accuracy: float, opponent_elo: int) -> int:
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
    return int(round(None))

estimate_elo__mutmut_mutants = {
'estimate_elo__mutmut_1': estimate_elo__mutmut_1, 
    'estimate_elo__mutmut_2': estimate_elo__mutmut_2, 
    'estimate_elo__mutmut_3': estimate_elo__mutmut_3, 
    'estimate_elo__mutmut_4': estimate_elo__mutmut_4, 
    'estimate_elo__mutmut_5': estimate_elo__mutmut_5, 
    'estimate_elo__mutmut_6': estimate_elo__mutmut_6, 
    'estimate_elo__mutmut_7': estimate_elo__mutmut_7, 
    'estimate_elo__mutmut_8': estimate_elo__mutmut_8, 
    'estimate_elo__mutmut_9': estimate_elo__mutmut_9, 
    'estimate_elo__mutmut_10': estimate_elo__mutmut_10, 
    'estimate_elo__mutmut_11': estimate_elo__mutmut_11, 
    'estimate_elo__mutmut_12': estimate_elo__mutmut_12, 
    'estimate_elo__mutmut_13': estimate_elo__mutmut_13, 
    'estimate_elo__mutmut_14': estimate_elo__mutmut_14
}

def estimate_elo(*args, **kwargs):
    return _mutmut_trampoline(estimate_elo__mutmut_orig, estimate_elo__mutmut_mutants, *args, **kwargs) 

estimate_elo.__signature__ = _mutmut_signature(estimate_elo__mutmut_orig)
estimate_elo__mutmut_orig.__name__ = 'estimate_elo'




def classify_move__mutmut_orig(score: float) -> Classification:
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


def classify_move__mutmut_1(score: float) -> Classification:
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
        if score > threshold:
            return classification
    return Classification.BLUNDER

classify_move__mutmut_mutants = {
'classify_move__mutmut_1': classify_move__mutmut_1
}

def classify_move(*args, **kwargs):
    return _mutmut_trampoline(classify_move__mutmut_orig, classify_move__mutmut_mutants, *args, **kwargs) 

classify_move.__signature__ = _mutmut_signature(classify_move__mutmut_orig)
classify_move__mutmut_orig.__name__ = 'classify_move'


