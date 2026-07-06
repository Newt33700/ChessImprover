"""Lotus Mastery Engine — progression nœud par nœud (EPIC 38, US 38.1).

Module PUR (aucune I/O, aucun accès `db_client`) : calcule le nouvel état
d'un nœud de répertoire après une tentative, à charge du routeur
(``routers/openings_trainer.py``) de lire l'état courant, appeler
``process_attempt`` et persister le résultat — même séparation domaine/
infrastructure que ``domain.tactical_elo.update_elo`` ou
``domain.srs_engine.sm2_schedule``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict

#: Seuil de déblocage des nœuds enfants (rang "Intermediate") — spec EPIC 38.
UNLOCK_THRESHOLD = 40

#: Constantes de progression (spec EPIC 38, US 38.1) : +15 en cas de succès
#: (borné à 100), -20 en cas d'échec (borné à 0). L'intervalle SRS double en
#: cas de succès (croissance espacée classique) et retombe à 1 jour en cas
#: d'échec — le multiplicateur exact n'est pas fixé par la spec (« multiplier
#: srs_interval »), ×2 est le choix standard le plus courant.
SUCCESS_SCORE_DELTA = 15
FAILURE_SCORE_DELTA = -20
SRS_INTERVAL_MULTIPLIER = 2
FAILURE_SRS_INTERVAL = 1

#: Rangs affichés à l'utilisateur, par tranche de `mastery_score` (spec EPIC 38).
RANK_THRESHOLDS = (
    (20, "Beginner"),
    (40, "Novice"),
    (60, "Intermediate"),
    (80, "Advanced"),
    (100, "Master"),
)
LEGEND_SCORE = 100


class AttemptResult(TypedDict):
    mastery_score: int
    srs_interval: int
    next_review_date: datetime
    status: str
    should_unlock_children: bool
    rank: str


def rank_for_score(mastery_score: int) -> str:
    """Rang affiché pour ce score — bornes exactes de la spec :
    ``<20`` Beginner, ``20-40`` Novice (exclusif haut), ``40-60`` Intermediate,
    ``60-80`` Advanced, ``80-99`` Master, ``100`` Legend."""
    if mastery_score >= LEGEND_SCORE:
        return "Legend"
    for upper_bound, rank in RANK_THRESHOLDS:
        if mastery_score < upper_bound:
            return rank
    return "Legend"  # pragma: no cover - inatteignable (score capé à 100)


def process_attempt(
    mastery_score: int,
    srs_interval: int,
    is_success: bool,
    now: datetime | None = None,
) -> AttemptResult:
    """Calcule le nouvel état d'un nœud après une tentative (US 38.1).

    Succès : ``+15`` (borné à 100), l'intervalle SRS double. Échec : ``-20``
    (borné à 0), l'intervalle retombe à 1 jour. ``should_unlock_children``
    est vrai dès que le nouveau score atteint ``UNLOCK_THRESHOLD`` (rang
    Intermediate) — idempotent côté appelant (`INSERT ... ON CONFLICT DO
    NOTHING`), donc sans danger de le re-vérifier après un échec qui laisse
    le score au-dessus du seuil (pas de mécanique de re-verrouillage).
    Statut : ``mastered`` à 100, ``review`` sinon (une fois qu'une tentative
    a eu lieu, le nœud sort de son statut "learning" initial et entre dans
    le cycle de répétition espacée — la spec ne détaille pas cette
    transition explicitement, ce choix est le plus cohérent avec le reste
    du moteur SRS existant, ``domain.srs_engine``).
    """
    now = now or datetime.now(timezone.utc)

    if is_success:
        new_score = min(100, mastery_score + SUCCESS_SCORE_DELTA)
        new_interval = max(1, srs_interval) * SRS_INTERVAL_MULTIPLIER
    else:
        new_score = max(0, mastery_score + FAILURE_SCORE_DELTA)
        new_interval = FAILURE_SRS_INTERVAL

    status = "mastered" if new_score >= LEGEND_SCORE else "review"

    return {
        "mastery_score": new_score,
        "srs_interval": new_interval,
        "next_review_date": now + timedelta(days=new_interval),
        "status": status,
        "should_unlock_children": new_score >= UNLOCK_THRESHOLD,
        "rank": rank_for_score(new_score),
    }
