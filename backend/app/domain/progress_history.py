"""Historisation de la progression Elo virtuelle — US 5.1.

Construit un « instantané » (snapshot) des Elo virtuels par catégorie
(Ouvertures/Tactique/Stratégie/Finales) après chaque analyse de partie, afin
d'alimenter une table d'historique et de tracer une courbe de progression sur
les N derniers jours.

Règles métier (DoD US 5.1) :

* Un snapshot est enregistré **par cadence** : si la cadence de la partie
  analysée est inconnue (``time_control`` absent/illisible), **aucun**
  snapshot n'est créé — on ne veut pas polluer une courbe avec une cadence
  indéterminée.
* Les Elo par catégorie réutilisent **exactement** le même calcul que la
  matrice US 4.1 (``stats_aggregator.category_elos``), pour que le point le
  plus récent de la courbe corresponde à la ligne courante de la matrice.
* L'historique affiché ne couvre que les ``days`` derniers jours (30 par
  défaut) : le filtrage se fait en Python (et non en SQL) pour rester
  identique quel que soit le backend de stockage (in-memory ou Postgres).

Module PUR.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional

from app.domain.cadence import classify_cadence
from app.domain.stats_aggregator import category_elos

# ---------------------------------------------------------------------------
# Construction du snapshot
# ---------------------------------------------------------------------------

def build_snapshot(
    moves: List[Dict[str, Any]],
    time_control: Optional[str],
    user_color: str = "white",
    game_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Construit un enregistrement prêt à insérer dans ``user_progress_history``.

    Parameters
    ----------
    moves : list[dict]
        Tous les coups de la partie analysée (les deux camps).
    time_control : str, optional
        Cadence Chess.com de la partie (ex. ``"180+2"``).
    user_color : str
        Couleur jouée par l'utilisateur (``"white"`` ou ``"black"``).
    game_id : str, optional
        Identifiant de la partie source (traçabilité).
    user_id : str, optional
        Propriétaire du snapshot.

    Returns
    -------
    dict | None
        ``{user_id, game_id, cadence, elos}`` où ``elos`` a les clés
        ``openings``/``tactics``/``strategy``/``endgames`` (même forme que
        ``category_elos``, prête pour ``db_client.create_progress_snapshot``).
        ``None`` si la cadence est inconnue (aucun snapshot n'est enregistré).
    """
    cadence = classify_cadence(time_control)
    if cadence is None:
        return None

    user_moves = [m for m in moves if m.get("color") == user_color]
    elos = category_elos(user_moves, cadence)

    return {
        "user_id": user_id,
        "game_id": game_id,
        "cadence": cadence.value,
        "elos": elos,
    }


# ---------------------------------------------------------------------------
# Filtrage temporel (fenêtre glissante)
# ---------------------------------------------------------------------------

def _parse_iso(value: Any) -> Optional[_dt.datetime]:
    """Parse une date ISO 8601 en ``datetime`` aware UTC ; ``None`` si invalide."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed


def filter_history_by_days(
    history: List[Dict[str, Any]],
    days: int = 30,
    now: Optional[_dt.datetime] = None,
) -> List[Dict[str, Any]]:
    """Filtre l'historique aux ``days`` derniers jours (par ``recorded_at``).

    Parameters
    ----------
    history : list[dict]
        Lignes de ``user_progress_history`` (doivent contenir ``recorded_at``,
        une chaîne ISO 8601).
    days : int
        Fenêtre glissante en jours. ``days <= 0`` renvoie une liste vide
        (fenêtre dégénérée : rien n'est dans les « 0 derniers jours »).
    now : datetime, optional
        Instant de référence (injecté pour des tests déterministes) ; sinon
        ``datetime.now(timezone.utc)``.

    Returns
    -------
    list[dict]
        Sous-ensemble de ``history`` dont ``recorded_at`` est dans la fenêtre.
        Les lignes sans date valide sont exclues (donnée corrompue).
    """
    if days <= 0:
        return []
    reference = now or _dt.datetime.now(_dt.timezone.utc)
    cutoff = reference - _dt.timedelta(days=days)

    filtered: List[Dict[str, Any]] = []
    for row in history:
        recorded = _parse_iso(row.get("recorded_at"))
        if recorded is not None and recorded >= cutoff:
            filtered.append(row)
    return filtered
