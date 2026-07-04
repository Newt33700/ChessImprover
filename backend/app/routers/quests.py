"""Quêtes quotidiennes — EPIC 29 (US 29.2).

* ``GET /api/v1/quests/daily`` — les 3 quêtes du jour de l'utilisateur
  authentifié, avec leur progression réelle calculée à la volée (aucune
  table dédiée, voir `domain.daily_quests` pour le détail de la décision).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.domain.daily_quests import compute_quest_progress, select_daily_quests
from app.domain.models import DailyQuestsResponse
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/quests", tags=["quests"])


def _is_today(value: Any, today_iso: str) -> bool:
    """Tolère un `datetime` (store in-memory) ou une chaîne ISO (Postgres)."""
    if value is None:
        return False
    if hasattr(value, "date"):
        return value.date().isoformat() == today_iso
    return str(value).startswith(today_iso)


def _counts_for_today(user_id: str, today_iso: str) -> Dict[str, int]:
    games = db_client.get_games_for_user(user_id)
    games_analyzed = sum(1 for g in games if _is_today(g.get("created_at"), today_iso))

    attempts = db_client.get_tactical_attempts(user_id)
    tactics_solved = sum(
        1 for a in attempts if a.get("success") and _is_today(a.get("created_at"), today_iso)
    )

    sprints = db_client.get_sprints_for_user(user_id)
    sprints_finished = sum(1 for s in sprints if _is_today(s.get("finished_at"), today_iso))

    return {
        "games_analyzed": games_analyzed,
        "tactics_solved": tactics_solved,
        "sprints_finished": sprints_finished,
    }


@router.get("/daily", response_model=DailyQuestsResponse)
async def get_daily_quests(user_id: str = Depends(get_current_user_id)) -> DailyQuestsResponse:
    today_iso = datetime.now(timezone.utc).date().isoformat()
    quests = select_daily_quests(today_iso, user_id)
    counts = _counts_for_today(user_id, today_iso)
    return DailyQuestsResponse(
        date=today_iso,
        quests=[compute_quest_progress(q, counts) for q in quests],
    )
