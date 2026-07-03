"""Courbe d'Elo Chess.com par cadence (EPIC 24).

L'API publique Chess.com n'expose pas d'historique de rating : chaque partie
archivée porte en revanche le rating du joueur APRÈS la partie
(``white.rating``/``black.rating``) et son horodatage ``end_time``. La courbe
d'Elo est donc reconstruite depuis les archives mensuelles : un point par
jour joué (dernier rating du jour), par cadence (``time_class``).

Module PUR : aucune I/O — la route (``routers/games.py``) orchestre le client
Chess.com ; ici, uniquement la fenêtre temporelle et l'extraction des points.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

#: Cadences Chess.com valides (``time_class`` des archives). L'UI n'expose que
#: bullet/blitz/rapid mais ``daily`` est accepté par l'API pour l'avenir.
ELO_CURVE_CADENCES = ("bullet", "blitz", "rapid", "daily")

#: Périodes proposées par l'UI (boutons 7j/30j/90j). La route accepte tout
#: ``days`` entre 1 et 365 — ces valeurs ne sont qu'une référence produit.
SUPPORTED_PERIODS_DAYS = (7, 30, 90)


def months_covering(now: datetime, days: int) -> List[Tuple[int, int]]:
    """Mois calendaires ``(année, mois)`` couvrant la fenêtre ``[now-days, now]``.

    Chess.com archive par mois calendaire : une fenêtre de 90 jours peut
    chevaucher jusqu'à 4 mois. Ordre chronologique croissant, sans doublon.
    """
    start = now - timedelta(days=max(1, days))
    months: List[Tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (now.year, now.month):
        months.append((year, month))
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return months


def _rating_for(raw_game: Dict[str, Any], username: str) -> Optional[int]:
    """Rating du joueur ``username`` dans une partie brute (côté blanc ou noir),
    comparé insensiblement à la casse. ``None`` si absent des deux côtés."""
    target = (username or "").lower()
    for side in ("white", "black"):
        player = raw_game.get(side) or {}
        if ((player.get("username") or "").lower()) == target:
            rating = player.get("rating")
            return int(rating) if isinstance(rating, (int, float)) else None
    return None


def build_elo_curve(
    raw_games: List[Dict[str, Any]],
    username: str,
    cadence: str,
    days: int,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Points ``{date, rating}`` (un par jour joué, ordre chronologique).

    - filtre par ``time_class == cadence`` et par fenêtre ``[now-days, now]`` ;
    - le rating retenu pour un jour est celui de la DERNIÈRE partie du jour
      (état de l'Elo en fin de journée) ;
    - les parties sans ``end_time`` exploitable ou sans rating sont ignorées.
    """
    reference = now or datetime.now(timezone.utc)
    window_start = reference - timedelta(days=max(1, days))

    last_by_day: Dict[str, Tuple[int, int]] = {}  # date -> (end_time, rating)
    for raw in raw_games or []:
        if raw.get("time_class") != cadence:
            continue
        end_time = raw.get("end_time")
        if not isinstance(end_time, (int, float)):
            continue
        played_at = datetime.fromtimestamp(int(end_time), tz=timezone.utc)
        if played_at < window_start or played_at > reference:
            continue
        rating = _rating_for(raw, username)
        if rating is None:
            continue
        day = played_at.date().isoformat()
        previous = last_by_day.get(day)
        if previous is None or int(end_time) >= previous[0]:
            last_by_day[day] = (int(end_time), rating)

    return [
        {"date": day, "rating": rating}
        for day, (_, rating) in sorted(last_by_day.items())
    ]
