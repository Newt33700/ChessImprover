"""Analyse de la Charge Cognitive — EPIC 19 (US 19.1 / US 19.2).

Deux angles d'analyse du « temps de réflexion » (secondes passées sur un coup,
dérivées des horloges PGN), tous deux calculés à partir des mêmes
enregistrements ``game_moves`` enrichis par ``domain.analysis_pipeline`` :

* **US 19.1** — répartition du temps par phase de jeu (Ouverture / Milieu /
  Finale) et par niveau de pression (sous pression vs équilibré), pour
  détecter les « temps morts » (ex. un joueur qui passe 80 % de son temps en
  ouverture faute de préparation).
* **US 19.2** — « Fluidité de Décision » : temps de réflexion moyen selon que
  le coup joué était quasi optimal (Top 3, cpl faible) ou franchement perdant
  (cpl élevé). Un temps long sur un coup perdant signale une « fatigue
  décisionnelle » ; un temps court sur un coup quasi optimal est valorisé.

Module PUR : consomme uniquement des dictionnaires ``game_moves`` déjà
persistés (aucune I/O, aucun accès moteur).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.acpl import average_cpl
from app.domain.models import Phase

# ---------------------------------------------------------------------------
# US 19.1 — Temps par phase / pression
# ---------------------------------------------------------------------------

#: Seuil (cp, point de vue du joueur) en-dessous duquel la position est jugée
#: « sous pression » (l'adversaire attaque / le joueur est nettement pire).
#: Aligné sur le seuil d'avantage/désavantage déjà utilisé pour l'entrée en
#: finale (`stats_aggregator.ADVANTAGE_CP`) — même intensité de désavantage.
PRESSURE_THRESHOLD_CP: int = -150


class PressureLevel(str, Enum):
    """Niveau de pression positionnelle au moment du coup (US 19.1)."""
    UNDER_PRESSURE = "under_pressure"
    EQUALITY = "equality"


def classify_pressure(eval_before_cp: Optional[int]) -> Optional[PressureLevel]:
    """Classe la pression subie par le joueur avant SON coup.

    ``eval_before_cp`` est l'éval du meilleur coup, du point de vue du camp au
    trait (donc déjà celui du joueur pour un enregistrement de son propre
    coup) — même convention que ``domain.move_class``/``domain.acpl``.
    ``None`` si l'éval est inconnue (pas de moteur pour ce coup).
    """
    if eval_before_cp is None:
        return None
    if eval_before_cp <= PRESSURE_THRESHOLD_CP:
        return PressureLevel.UNDER_PRESSURE
    return PressureLevel.EQUALITY


def _moves_with_time(moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [m for m in moves if m.get("time_spent_seconds") is not None]


def _bucket_stats(seconds: List[float]) -> Dict[str, Any]:
    return {
        "avg_seconds": round(average_cpl(seconds), 1) if seconds else None,
        "total_seconds": round(sum(seconds), 1) if seconds else 0.0,
        "count": len(seconds),
    }


def build_time_allocation_report(own_moves: List[Dict[str, Any]]) -> Dict[str, Any]:
    """US 19.1 — répartition du temps de réflexion par phase et par pression.

    Parameters
    ----------
    own_moves : list[dict]
        Enregistrements ``game_moves`` **du joueur uniquement** (déjà filtrés
        par couleur, une partie pouvant être jouée avec les Blancs ou les
        Noirs selon la partie — même convention que
        ``stats_aggregator.category_elos`` : le filtrage par couleur est la
        responsabilité de l'appelant, par partie, avant concaténation).
        Seuls ceux disposant d'un ``time_spent_seconds`` connu comptent.

    Returns
    -------
    dict
        ``{"by_phase": {phase: {avg_seconds, total_seconds, count}, ...},
           "by_pressure": {level: {...}, ...},
           "sample_size": int}``. Les trois phases et les deux niveaux de
        pression sont toujours présents (buckets vides à ``None``/``0``),
        pour que le frontend n'ait jamais à gérer une clé manquante.
    """
    own_moves = _moves_with_time(own_moves)

    by_phase: Dict[str, List[float]] = {p.value: [] for p in Phase}
    by_pressure: Dict[str, List[float]] = {p.value: [] for p in PressureLevel}

    for m in own_moves:
        seconds = m["time_spent_seconds"]
        phase = m.get("phase")
        if phase in by_phase:
            by_phase[phase].append(seconds)

        pressure = classify_pressure(m.get("eval_before"))
        if pressure is not None:
            by_pressure[pressure.value].append(seconds)

    total_seconds = sum(m["time_spent_seconds"] for m in own_moves)

    phase_report: Dict[str, Any] = {}
    for phase_key, values in by_phase.items():
        stats = _bucket_stats(values)
        stats["share_pct"] = (
            round(100 * stats["total_seconds"] / total_seconds, 1) if total_seconds > 0 else 0.0
        )
        phase_report[phase_key] = stats

    pressure_report = {key: _bucket_stats(values) for key, values in by_pressure.items()}

    return {
        "by_phase": phase_report,
        "by_pressure": pressure_report,
        "sample_size": len(own_moves),
    }


# ---------------------------------------------------------------------------
# US 19.2 — Fluidité de décision
# ---------------------------------------------------------------------------

#: Perte (cp) en-dessous de laquelle un coup est considéré quasi optimal
#: (« Top 3 » de la spécification métier : le joueur a trouvé un excellent coup).
TOP3_CPL_THRESHOLD: int = 50

#: Perte (cp) à partir de laquelle un coup est franchement perdant. Écart
#: volontaire avec ``TOP3_CPL_THRESHOLD`` (zone 50-100 non classée) pour ne
#: comparer que des cas tranchés — cf. `domain.move_class` (même principe de
#: bandes disjointes avec zone neutre entre TACTICAL_GAP et STRATEGIC_SPREAD).
WEAK_MOVE_CPL_THRESHOLD: int = 100

#: Ratio (temps moyen coup perdant / temps moyen coup Top 3) au-delà duquel on
#: signale une « fatigue décisionnelle » : le joueur réfléchit plus longtemps
#: sur ses erreurs que sur ses bons coups, sans que cela l'empêche de se tromper.
DECISION_FATIGUE_RATIO: float = 1.3


class MoveQualityBucket(str, Enum):
    """Bande de qualité d'un coup joué, pour la comparaison de fluidité."""
    TOP3 = "top3"
    WEAK = "weak"


def move_quality_bucket(cpl: Optional[int]) -> Optional[MoveQualityBucket]:
    """Classe un coup joué par sa perte en centipions (``cpl``).

    ``None`` si la perte est inconnue OU si elle tombe dans la zone
    intermédiaire non classée (``TOP3_CPL_THRESHOLD < cpl < WEAK_MOVE_CPL_THRESHOLD``).
    """
    if cpl is None:
        return None
    if cpl <= TOP3_CPL_THRESHOLD:
        return MoveQualityBucket.TOP3
    if cpl >= WEAK_MOVE_CPL_THRESHOLD:
        return MoveQualityBucket.WEAK
    return None


def is_decision_fatigue(top3_avg_seconds: Optional[float], weak_avg_seconds: Optional[float]) -> bool:
    """Vrai si le temps moyen sur les coups perdants dépasse nettement celui
    des coups quasi optimaux (US 19.2 : « 3 minutes pour un coup perdant »).

    Faux (jamais de faux positif) si l'un des deux temps est inconnu, ou si le
    temps de référence (Top 3) est nul.
    """
    if top3_avg_seconds is None or weak_avg_seconds is None or top3_avg_seconds <= 0:
        return False
    return weak_avg_seconds > top3_avg_seconds * DECISION_FATIGUE_RATIO


def build_decision_fluidity_report(own_moves: List[Dict[str, Any]]) -> Dict[str, Any]:
    """US 19.2 — temps de réflexion moyen selon la qualité de la décision.

    Parameters
    ----------
    own_moves : list[dict]
        Enregistrements ``game_moves`` du joueur uniquement (voir
        ``build_time_allocation_report``).

    Returns
    -------
    dict
        ``{"top3": {avg_seconds, count}, "weak": {avg_seconds, count},
           "decision_fatigue": bool}``.
    """
    own_moves = _moves_with_time(own_moves)

    buckets: Dict[str, List[float]] = {b.value: [] for b in MoveQualityBucket}
    for m in own_moves:
        bucket = move_quality_bucket(m.get("cpl"))
        if bucket is not None:
            buckets[bucket.value].append(m["time_spent_seconds"])

    top3_stats = _bucket_stats(buckets[MoveQualityBucket.TOP3.value])
    weak_stats = _bucket_stats(buckets[MoveQualityBucket.WEAK.value])

    return {
        "top3": top3_stats,
        "weak": weak_stats,
        "decision_fatigue": is_decision_fatigue(top3_stats["avg_seconds"], weak_stats["avg_seconds"]),
    }


# ---------------------------------------------------------------------------
# Temps de réflexion par coup — dérivation depuis les horloges PGN
# ---------------------------------------------------------------------------

def derive_time_spent(
    clocks: List[Optional[float]], colors: List[str], increment: int = 0
) -> List[Optional[float]]:
    """Temps de réflexion (secondes) par demi-coup, depuis les horloges après coup.

    Parameters
    ----------
    clocks : list[float | None]
        Horloge restante après chaque demi-coup (index = ply 0-based),
        ``None`` si la balise ``[%clk]`` est absente pour ce coup.
    colors : list[str]
        Couleur du joueur ayant joué chaque demi-coup (même index/longueur).
    increment : int
        Incrément (secondes) ajouté à l'horloge après chaque coup
        (``domain.cadence.parse_increment``) — retranché pour ne pas biaiser
        le temps de réflexion à la baisse (voir docstring de ``parse_increment``).

    Returns
    -------
    list[float | None]
        Temps de réflexion par demi-coup. ``None`` pour le premier coup de
        chaque couleur (pas d'horloge de référence) ou si l'une des deux
        horloges impliquées est inconnue. Jamais négatif (plancher à 0.0) :
        un incrément mal renseigné peut sur-corriger, mais un temps de
        réflexion négatif n'a pas de sens métier.
    """
    result: List[Optional[float]] = []
    last_clock: Dict[str, Optional[float]] = {}

    for clk, color in zip(clocks, colors):
        previous = last_clock.get(color)
        if previous is not None and clk is not None:
            spent = previous - clk + increment
            result.append(max(0.0, spent))
        else:
            result.append(None)
        if clk is not None:
            last_clock[color] = clk

    return result
