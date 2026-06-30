"""Perte de centipions (CPL) et ACPL calibré par phase — US 2.2.

Pour chaque coup, on calcule la **perte en centipions** (Centipawn Loss) du
joueur, puis l'**ACPL** (Average Centipawn Loss) moyenné séparément par phase
(Ouverture / Milieu de jeu / Finale).

Règles métier (DoD US 2.2) :

* ``CPL = Eval_meilleurCoup − Eval_coupJoué`` (du point de vue du camp au trait).
* Plancher à 0 : un coup au moins aussi bon que le meilleur ne « gagne » pas
  de centipions (CPL négatif ramené à 0).
* **Plafonnement des gaffes** : CPL plafonné à 400 centipions pour éviter qu'une
  unique énorme erreur ne ruine la moyenne.
* ACPL = moyenne des CPL, calculée **séparément** par phase.

Module PUR : il consomme des évaluations déjà calculées (peu importe que la
source soit Stockfish navigateur ou natif — cf. ``infrastructure.engine``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.domain.models import Phase

# ---------------------------------------------------------------------------
# Constantes (règles métier US 2.2)
# ---------------------------------------------------------------------------

#: Plafond de perte par coup (centipions) — limite l'impact d'une gaffe massive.
CPL_CAP: int = 400


# ---------------------------------------------------------------------------
# CPL d'un coup
# ---------------------------------------------------------------------------

def centipawn_loss(eval_best_cp: int, eval_played_cp: int) -> int:
    """Perte en centipions d'un coup, plancher 0 et plafond ``CPL_CAP``.

    Les deux évaluations sont exprimées dans le **même** repère : centipions du
    point de vue du camp qui joue le coup (positif = bon pour lui).

    Parameters
    ----------
    eval_best_cp : int
        Évaluation du meilleur coup disponible.
    eval_played_cp : int
        Évaluation du coup réellement joué.

    Returns
    -------
    int
        ``min(max(best − played, 0), CPL_CAP)``.
    """
    loss = eval_best_cp - eval_played_cp
    if loss < 0:
        loss = 0
    if loss > CPL_CAP:
        loss = CPL_CAP
    return loss


# ---------------------------------------------------------------------------
# Coup analysé
# ---------------------------------------------------------------------------

@dataclass
class PhasedMove:
    """Un coup du joueur analysé, rattaché à sa phase et sa perte."""
    phase: Phase
    cpl: int


# ---------------------------------------------------------------------------
# Agrégation ACPL
# ---------------------------------------------------------------------------

def average_cpl(cpls: List[int]) -> Optional[float]:
    """Moyenne d'une liste de CPL, ou ``None`` si la liste est vide."""
    if not cpls:
        return None
    return sum(cpls) / len(cpls)


def acpl_by_phase(moves: List[PhasedMove]) -> Dict[Phase, Optional[float]]:
    """ACPL moyenné séparément pour chaque phase.

    Parameters
    ----------
    moves : list[PhasedMove]
        Coups du joueur (uniquement les siens), avec phase et CPL.

    Returns
    -------
    dict[Phase, float | None]
        ACPL par phase. ``None`` pour une phase sans aucun coup joué.
        Les trois phases sont toujours présentes dans le dictionnaire.
    """
    buckets: Dict[Phase, List[int]] = {
        Phase.OPENING: [],
        Phase.MIDDLEGAME: [],
        Phase.ENDGAME: [],
    }
    for move in moves:
        buckets[move.phase].append(move.cpl)
    return {phase: average_cpl(cpls) for phase, cpls in buckets.items()}


def overall_acpl(moves: List[PhasedMove]) -> Optional[float]:
    """ACPL global (toutes phases confondues), ou ``None`` si aucun coup."""
    return average_cpl([m.cpl for m in moves])
