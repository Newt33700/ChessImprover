
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


"""Moteur de Répétition Espacée — algorithme SuperMemo-2 (SM-2).

Implémentation pure de l'algorithme SM-2 original de Piotr Woźniak.
Les paramètres sont alignés sur l'implémentation JS (SRS object dans app.js).

Référence : https://super-memory.com/english/ol/sm2.htm
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from app.domain.models import SRSCard

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

EF_MIN: float = 1.3  # Facteur de facilité minimum

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_orig(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_1(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=None,
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_2(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=None,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_3(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=None,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_4(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=3.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_5(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=2,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_6(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=1,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_7(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_8(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_9(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        ef=2.5,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_10(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        interval=1,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_11(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=2.5,
        reps=0,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_12(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=1,
        due=date.today().isoformat(),
    )

# Qualité de réponse (0-5) :
#   0 = pas de souvenir
#   1 = incorrect, reconnaît après indice
#   2 = incorrect mais la réponse semblait facile
#   3 = correct avec effort significatif
#   4 = correct avec hésitation
#   5 = correct et confiant

# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def create_card__mutmut_13(card_id: str, fen: str, solution: str) -> SRSCard:
    """Crée une nouvelle carte SRS avec les paramètres initiaux SM-2.

    Parameters
    ----------
    card_id : str
        Identifiant unique de la carte.
    fen : str
        Position FEN de l'exercice.
    solution : str
        Coup SAN correct.

    Returns
    -------
    SRSCard
        Nouvelle carte avec ef=2.5, interval=1, reps=0, due=today.
    """
    return SRSCard(
        id=card_id,
        fen=fen,
        solution=solution,
        ef=2.5,
        interval=1,
        reps=0,
    )

create_card__mutmut_mutants = {
'create_card__mutmut_1': create_card__mutmut_1, 
    'create_card__mutmut_2': create_card__mutmut_2, 
    'create_card__mutmut_3': create_card__mutmut_3, 
    'create_card__mutmut_4': create_card__mutmut_4, 
    'create_card__mutmut_5': create_card__mutmut_5, 
    'create_card__mutmut_6': create_card__mutmut_6, 
    'create_card__mutmut_7': create_card__mutmut_7, 
    'create_card__mutmut_8': create_card__mutmut_8, 
    'create_card__mutmut_9': create_card__mutmut_9, 
    'create_card__mutmut_10': create_card__mutmut_10, 
    'create_card__mutmut_11': create_card__mutmut_11, 
    'create_card__mutmut_12': create_card__mutmut_12, 
    'create_card__mutmut_13': create_card__mutmut_13
}

def create_card(*args, **kwargs):
    return _mutmut_trampoline(create_card__mutmut_orig, create_card__mutmut_mutants, *args, **kwargs) 

create_card.__signature__ = _mutmut_signature(create_card__mutmut_orig)
create_card__mutmut_orig.__name__ = 'create_card'




def review_card__mutmut_orig(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_1(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = None

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_2(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality <= 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_3(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 4:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_4(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=2,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_5(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=1,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_6(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_7(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_8(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_9(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_10(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_11(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_12(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_13(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 1.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_14(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 + (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_15(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (6 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_16(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 + quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_17(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) / (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_18(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (1.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_19(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 - (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_20(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (6 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_21(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 + quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_22(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) / 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_23(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 1.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_24(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = None
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_25(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(None, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_26(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef - delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_27(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max( card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_28(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = None
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_29(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps - 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_30(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 2

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_31(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = None

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_32(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps != 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_33(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 2:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_34(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 2
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_35(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = None
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_36(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps != 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_37(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 3:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_38(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 7
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_39(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = None
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_40(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(2, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_41(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval / new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_42(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = None

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_43(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today - timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_44(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=None)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_45(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = None

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_46(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(None, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_47(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 5),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_48(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round( 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_49(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=None,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_50(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=None,
        due=due_date.isoformat(),
    )


def review_card__mutmut_51(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_52(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_53(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_54(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        interval=new_interval,
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_55(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        reps=new_reps,
        due=due_date.isoformat(),
    )


def review_card__mutmut_56(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        due=due_date.isoformat(),
    )


def review_card__mutmut_57(card: SRSCard, quality: int) -> SRSCard:
    """Applique l'algorithme SM-2 à une carte après une révision.

    Si quality < 3 : la carte est réinitialisée (reps=0, interval=1, due=today).

    Si quality >= 3 :
        - EF' = EF + (0.1 - (5 - quality) × (0.08 + (5 - quality) × 0.02))
        - EF' borné à EF_MIN (1.3)
        - interval dépend du nombre de répétions :
            reps=1 → 1 jour
            reps=2 → 6 jours
            reps>=3 → interval × EF (arrondi)
        - due = today + interval

    Parameters
    ----------
    card : SRSCard
        Carte actuelle à réviser.
    quality : int
        Qualité de la réponse (0-5).

    Returns
    -------
    SRSCard
        Carte mise à jour (nouveau objet immuable).
    """
    today = date.today()

    # Échec : réinitialisation complète
    if quality < 3:
        return SRSCard(
            id=card.id,
            fen=card.fen,
            solution=card.solution,
            ef=card.ef,
            interval=1,
            reps=0,
            due=today.isoformat(),
        )

    # Succès : mise à jour SM-2
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    new_ef = max(EF_MIN, card.ef + delta)
    new_reps = card.reps + 1

    # Calcul de l'intervalle
    if new_reps == 1:
        new_interval = 1
    elif new_reps == 2:
        new_interval = 6
    else:
        new_interval = max(1, round(card.interval * new_ef))

    due_date = today + timedelta(days=new_interval)

    return SRSCard(
        id=card.id,
        fen=card.fen,
        solution=card.solution,
        ef=round(new_ef, 4),
        interval=new_interval,
        reps=new_reps,
    )

review_card__mutmut_mutants = {
'review_card__mutmut_1': review_card__mutmut_1, 
    'review_card__mutmut_2': review_card__mutmut_2, 
    'review_card__mutmut_3': review_card__mutmut_3, 
    'review_card__mutmut_4': review_card__mutmut_4, 
    'review_card__mutmut_5': review_card__mutmut_5, 
    'review_card__mutmut_6': review_card__mutmut_6, 
    'review_card__mutmut_7': review_card__mutmut_7, 
    'review_card__mutmut_8': review_card__mutmut_8, 
    'review_card__mutmut_9': review_card__mutmut_9, 
    'review_card__mutmut_10': review_card__mutmut_10, 
    'review_card__mutmut_11': review_card__mutmut_11, 
    'review_card__mutmut_12': review_card__mutmut_12, 
    'review_card__mutmut_13': review_card__mutmut_13, 
    'review_card__mutmut_14': review_card__mutmut_14, 
    'review_card__mutmut_15': review_card__mutmut_15, 
    'review_card__mutmut_16': review_card__mutmut_16, 
    'review_card__mutmut_17': review_card__mutmut_17, 
    'review_card__mutmut_18': review_card__mutmut_18, 
    'review_card__mutmut_19': review_card__mutmut_19, 
    'review_card__mutmut_20': review_card__mutmut_20, 
    'review_card__mutmut_21': review_card__mutmut_21, 
    'review_card__mutmut_22': review_card__mutmut_22, 
    'review_card__mutmut_23': review_card__mutmut_23, 
    'review_card__mutmut_24': review_card__mutmut_24, 
    'review_card__mutmut_25': review_card__mutmut_25, 
    'review_card__mutmut_26': review_card__mutmut_26, 
    'review_card__mutmut_27': review_card__mutmut_27, 
    'review_card__mutmut_28': review_card__mutmut_28, 
    'review_card__mutmut_29': review_card__mutmut_29, 
    'review_card__mutmut_30': review_card__mutmut_30, 
    'review_card__mutmut_31': review_card__mutmut_31, 
    'review_card__mutmut_32': review_card__mutmut_32, 
    'review_card__mutmut_33': review_card__mutmut_33, 
    'review_card__mutmut_34': review_card__mutmut_34, 
    'review_card__mutmut_35': review_card__mutmut_35, 
    'review_card__mutmut_36': review_card__mutmut_36, 
    'review_card__mutmut_37': review_card__mutmut_37, 
    'review_card__mutmut_38': review_card__mutmut_38, 
    'review_card__mutmut_39': review_card__mutmut_39, 
    'review_card__mutmut_40': review_card__mutmut_40, 
    'review_card__mutmut_41': review_card__mutmut_41, 
    'review_card__mutmut_42': review_card__mutmut_42, 
    'review_card__mutmut_43': review_card__mutmut_43, 
    'review_card__mutmut_44': review_card__mutmut_44, 
    'review_card__mutmut_45': review_card__mutmut_45, 
    'review_card__mutmut_46': review_card__mutmut_46, 
    'review_card__mutmut_47': review_card__mutmut_47, 
    'review_card__mutmut_48': review_card__mutmut_48, 
    'review_card__mutmut_49': review_card__mutmut_49, 
    'review_card__mutmut_50': review_card__mutmut_50, 
    'review_card__mutmut_51': review_card__mutmut_51, 
    'review_card__mutmut_52': review_card__mutmut_52, 
    'review_card__mutmut_53': review_card__mutmut_53, 
    'review_card__mutmut_54': review_card__mutmut_54, 
    'review_card__mutmut_55': review_card__mutmut_55, 
    'review_card__mutmut_56': review_card__mutmut_56, 
    'review_card__mutmut_57': review_card__mutmut_57
}

def review_card(*args, **kwargs):
    return _mutmut_trampoline(review_card__mutmut_orig, review_card__mutmut_mutants, *args, **kwargs) 

review_card.__signature__ = _mutmut_signature(review_card__mutmut_orig)
review_card__mutmut_orig.__name__ = 'review_card'




def get_due_cards__mutmut_orig(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = reference_date or date.today()
    ref_str = ref.isoformat()
    due = [c for c in cards if c.due <= ref_str]
    due.sort(key=lambda c: c.due)
    return due


def get_due_cards__mutmut_1(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = reference_date and date.today()
    ref_str = ref.isoformat()
    due = [c for c in cards if c.due <= ref_str]
    due.sort(key=lambda c: c.due)
    return due


def get_due_cards__mutmut_2(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = None
    ref_str = ref.isoformat()
    due = [c for c in cards if c.due <= ref_str]
    due.sort(key=lambda c: c.due)
    return due


def get_due_cards__mutmut_3(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = reference_date or date.today()
    ref_str = None
    due = [c for c in cards if c.due <= ref_str]
    due.sort(key=lambda c: c.due)
    return due


def get_due_cards__mutmut_4(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = reference_date or date.today()
    ref_str = ref.isoformat()
    due = [c for c in cards if c.due < ref_str]
    due.sort(key=lambda c: c.due)
    return due


def get_due_cards__mutmut_5(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = reference_date or date.today()
    ref_str = ref.isoformat()
    due = None
    due.sort(key=lambda c: c.due)
    return due


def get_due_cards__mutmut_6(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
    """Renvoie les cartes dont la date d'échéance est atteinte.

    Parameters
    ----------
    cards : list[SRSCard]
        Toutes les cartes SRS.
    reference_date : date, optional
        Date de référence pour le calcul (défaut = aujourd'hui).

    Returns
    -------
    list[SRSCard]
        Cartes dues, triées par date d'échéance croissante.
    """
    ref = reference_date or date.today()
    ref_str = ref.isoformat()
    due = [c for c in cards if c.due <= ref_str]
    due.sort(key=lambda c: None)
    return due

get_due_cards__mutmut_mutants = {
'get_due_cards__mutmut_1': get_due_cards__mutmut_1, 
    'get_due_cards__mutmut_2': get_due_cards__mutmut_2, 
    'get_due_cards__mutmut_3': get_due_cards__mutmut_3, 
    'get_due_cards__mutmut_4': get_due_cards__mutmut_4, 
    'get_due_cards__mutmut_5': get_due_cards__mutmut_5, 
    'get_due_cards__mutmut_6': get_due_cards__mutmut_6
}

def get_due_cards(*args, **kwargs):
    return _mutmut_trampoline(get_due_cards__mutmut_orig, get_due_cards__mutmut_mutants, *args, **kwargs) 

get_due_cards.__signature__ = _mutmut_signature(get_due_cards__mutmut_orig)
get_due_cards__mutmut_orig.__name__ = 'get_due_cards'


