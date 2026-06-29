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

def create_card(card_id: str, fen: str, solution: str) -> SRSCard:
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


def review_card(card: SRSCard, quality: int) -> SRSCard:
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


def get_due_cards(cards: List[SRSCard], reference_date: date = None) -> List[SRSCard]:
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
