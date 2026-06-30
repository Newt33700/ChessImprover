"""Isolation Tactique vs Stratégie — US 3.2.

Classe chaque position en deux catégories conceptuelles afin de peupler les
colonnes « Exercices tactiques » et « Stratégie » du tableau de bord, puis
calcule les Elo virtuels correspondants.

Règles métier (DoD US 3.2) — les scores sont en centipions du point de vue du
camp au trait, lignes multipv triées du meilleur au pire :

* **Position Tactique** : le 2ᵉ meilleur coup perd **plus de 150 cp** vs le
  meilleur (un seul coup critique à trouver).
    - Coup joué = meilleur coup → *Tactique Réussie*.
    - Coup joué perdant **plus de 100 cp** → *Tactique Loupée*.
    - Entre les deux → tentative partielle (ni l'un ni l'autre).
  L'Elo virtuel « Tactique » est proportionnel au ratio de réussites sur les
  positions tactiques critiques.

* **Position Stratégique** : les 3 meilleurs coups sont séparés par **moins de
  40 cp** (position calme, choix préférentiel). L'Elo « Stratégie » provient de
  l'ACPL exclusif de ces positions calmes, mappé via US 3.1.

Module PUR.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from app.domain.acpl import average_cpl
from app.domain.models import TimeClass
from app.domain.virtual_elo import FINAL_CEIL, FINAL_FLOOR, acpl_to_elo

# ---------------------------------------------------------------------------
# Constantes (règles métier US 3.2)
# ---------------------------------------------------------------------------

#: Écart minimal (cp) entre meilleur et 2ᵉ coup pour qualifier une tactique.
TACTICAL_GAP: int = 150

#: Perte (cp) au-delà de laquelle une tactique est considérée « loupée ».
TACTICAL_MISS_THRESHOLD: int = 100

#: Écart maximal (cp) entre le meilleur et le 3ᵉ coup pour une position calme.
STRATEGIC_SPREAD: int = 40

#: Bornes de l'Elo tactique (mapping linéaire du ratio de réussite).
TACTICAL_ELO_FLOOR: int = FINAL_FLOOR
TACTICAL_ELO_CEIL: int = FINAL_CEIL


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class PositionType(str, Enum):
    """Nature d'une position au regard du choix de coup."""
    TACTICAL = "tactical"
    STRATEGIC = "strategic"
    NEUTRAL = "neutral"


class TacticOutcome(str, Enum):
    """Résultat du joueur sur une position tactique critique."""
    SUCCESS = "success"
    MISSED = "missed"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# Classification de position
# ---------------------------------------------------------------------------

def classify_position(line_scores: List[int]) -> PositionType:
    """Classe une position d'après les scores multipv (triés meilleur→pire).

    Parameters
    ----------
    line_scores : list[int]
        Scores (cp) des meilleurs coups, du meilleur au pire, longueur ≥ 1.

    Returns
    -------
    PositionType
        ``TACTICAL`` (un seul coup critique), ``STRATEGIC`` (calme) ou
        ``NEUTRAL`` (ni l'un ni l'autre, ou trop peu de lignes).
    """
    if not line_scores:
        return PositionType.NEUTRAL

    best = line_scores[0]

    # Tactique : le 2ᵉ coup est bien moins bon (un seul coup critique).
    if len(line_scores) >= 2 and (best - line_scores[1]) > TACTICAL_GAP:
        return PositionType.TACTICAL

    # Stratégique : top 3 resserrés (position calme, choix préférentiel).
    if len(line_scores) >= 3 and (best - line_scores[2]) < STRATEGIC_SPREAD:
        return PositionType.STRATEGIC

    return PositionType.NEUTRAL


# ---------------------------------------------------------------------------
# Résultat tactique
# ---------------------------------------------------------------------------

def tactic_outcome(played_cpl: int) -> TacticOutcome:
    """Issue du joueur sur une position tactique, d'après sa perte (CPL).

    Parameters
    ----------
    played_cpl : int
        Perte en centipions du coup joué (0 = meilleur coup).

    Returns
    -------
    TacticOutcome
        ``SUCCESS`` si meilleur coup, ``MISSED`` si perte > 100 cp,
        ``PARTIAL`` sinon.
    """
    if played_cpl <= 0:
        return TacticOutcome.SUCCESS
    if played_cpl > TACTICAL_MISS_THRESHOLD:
        return TacticOutcome.MISSED
    return TacticOutcome.PARTIAL


def tactical_success_ratio(outcomes: List[TacticOutcome]) -> Optional[float]:
    """Ratio de réussites tactiques (réussies / total critiques).

    Returns
    -------
    float | None
        Ratio dans ``[0, 1]``, ou ``None`` si aucune position tactique.
    """
    if not outcomes:
        return None
    successes = sum(1 for o in outcomes if o is TacticOutcome.SUCCESS)
    return successes / len(outcomes)


def tactical_elo(success_ratio: Optional[float]) -> Optional[int]:
    """Elo virtuel tactique, proportionnel au ratio de réussite.

    Mapping linéaire : ratio 0 → ``TACTICAL_ELO_FLOOR``,
    ratio 1 → ``TACTICAL_ELO_CEIL``.

    Returns
    -------
    int | None
        Elo borné, ou ``None`` si le ratio est indéfini (aucune tactique).
    """
    if success_ratio is None:
        return None
    clamped = max(0.0, min(1.0, success_ratio))
    span = TACTICAL_ELO_CEIL - TACTICAL_ELO_FLOOR
    return int(round(TACTICAL_ELO_FLOOR + clamped * span))


# ---------------------------------------------------------------------------
# Elo stratégique
# ---------------------------------------------------------------------------

def strategic_elo(
    calm_cpls: List[int], time_class: Optional[TimeClass] = None
) -> Optional[int]:
    """Elo virtuel stratégique depuis l'ACPL exclusif des positions calmes.

    Parameters
    ----------
    calm_cpls : list[int]
        CPL du joueur sur les positions classées stratégiques.
    time_class : TimeClass, optional
        Cadence, pour le bonus du mapping US 3.1.

    Returns
    -------
    int | None
        Elo virtuel, ou ``None`` si aucune position stratégique.
    """
    acpl = average_cpl(calm_cpls)
    if acpl is None:
        return None
    return acpl_to_elo(acpl, time_class)
