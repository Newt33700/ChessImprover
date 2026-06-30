"""Mapping ACPL → Elo virtuel — US 3.1.

Transforme un ACPL (par phase ou par catégorie) en un classement Elo virtuel
« à la Chess.com Premium » (« Vous avez joué la finale comme un joueur à 2100 »).

Règles métier (DoD US 3.1) :

* **Échelle empirique** (ACPL → Elo) :

    | ACPL | Elo  |
    |------|------|
    | ≤ 10 | 2800 |
    |  20  | 2400 |
    |  35  | 1900 |
    |  50  | 1500 |
    |  75  | 1100 |
    | ≥110 |  600 |

  Interpolation **linéaire par paliers** entre ces ancres (monotone
  décroissante), plafonnée à 2800 et plancher à 600 pour l'Elo de base.

* **Ajustement par cadence** : bonus d'Elo virtuel pour les cadences rapides
  (Bullet/Blitz) par rapport aux cadences lentes, à ACPL égal
  (ex : +200 en Bullet pour un ACPL de 40).

Module PUR.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.domain.models import TimeClass

# ---------------------------------------------------------------------------
# Constantes (règles métier US 3.1)
# ---------------------------------------------------------------------------

#: Ancres empiriques (ACPL, Elo), triées par ACPL croissant.
ACPL_ELO_ANCHORS: List[Tuple[float, int]] = [
    (10.0, 2800),
    (20.0, 2400),
    (35.0, 1900),
    (50.0, 1500),
    (75.0, 1100),
    (110.0, 600),
]

ELO_CEIL: int = 2800  # Elo de base maximal (ACPL ≤ 10)
ELO_FLOOR: int = 600  # Elo de base minimal (ACPL ≥ 110)

#: Bonus d'Elo virtuel par cadence (rapides récompensées vs lentes).
CADENCE_BONUS: dict = {
    TimeClass.BULLET: 200,
    TimeClass.BLITZ: 100,
    TimeClass.RAPID: 0,
    TimeClass.DAILY: 0,
}

#: Bornes finales après application du bonus de cadence.
FINAL_FLOOR: int = 600
FINAL_CEIL: int = 3000


# ---------------------------------------------------------------------------
# Mapping de base
# ---------------------------------------------------------------------------

def acpl_to_elo_base(acpl: float) -> int:
    """Elo de base (sans cadence) par interpolation linéaire des ancres.

    Parameters
    ----------
    acpl : float
        Average Centipawn Loss (≥ 0).

    Returns
    -------
    int
        Elo entre ``ELO_FLOOR`` et ``ELO_CEIL``.
    """
    if acpl <= ACPL_ELO_ANCHORS[0][0]:
        return ELO_CEIL
    if acpl >= ACPL_ELO_ANCHORS[-1][0]:
        return ELO_FLOOR

    for (lo_acpl, lo_elo), (hi_acpl, hi_elo) in zip(
        ACPL_ELO_ANCHORS, ACPL_ELO_ANCHORS[1:]
    ):
        if lo_acpl <= acpl <= hi_acpl:
            span = hi_acpl - lo_acpl
            ratio = (acpl - lo_acpl) / span
            elo = lo_elo + ratio * (hi_elo - lo_elo)
            return int(round(elo))

    # Inatteignable (acpl est borné par les deux gardes ci-dessus).
    return ELO_FLOOR  # pragma: no cover


# ---------------------------------------------------------------------------
# Bonus de cadence
# ---------------------------------------------------------------------------

def cadence_bonus(time_class: Optional[TimeClass]) -> int:
    """Bonus d'Elo virtuel associé à une cadence (0 si inconnue/None)."""
    if time_class is None:
        return 0
    return CADENCE_BONUS.get(time_class, 0)


def acpl_to_elo(acpl: float, time_class: Optional[TimeClass] = None) -> int:
    """Elo virtuel final = Elo de base + bonus de cadence, borné.

    Parameters
    ----------
    acpl : float
        Average Centipawn Loss (≥ 0).
    time_class : TimeClass, optional
        Cadence de la partie ; ``None`` → aucun bonus.

    Returns
    -------
    int
        Elo virtuel borné à ``[FINAL_FLOOR, FINAL_CEIL]``.
    """
    raw = acpl_to_elo_base(acpl) + cadence_bonus(time_class)
    return max(FINAL_FLOOR, min(FINAL_CEIL, raw))
