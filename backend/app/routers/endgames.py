"""Entraîneur de Finales Essentielles (EPIC 10, fonctionnalité bonus).

* ``GET  /api/v1/endgames/next``    — position la plus proche de l'Elo
  « finales » de l'utilisateur authentifié, filtrable par ``theme_id``.
* ``POST /api/v1/endgames/attempt`` — valide le coup joué côté serveur
  (jamais une confiance au client) et ajuste l'Elo « finales » (+15/-15).

Réutilise directement la logique générique d'EPIC 8 (`domain/tactics.py`,
`domain/tactical_elo.py`) — voir `domain/endgames.py` pour la justification.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.endgames import ENDGAME_THEMES
from app.domain.models import EndgameAttemptRequest, EndgameAttemptResult, EndgameProblemPublic
from app.domain.tactical_elo import update_elo
from app.domain.tactics import is_correct_move
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/endgames", tags=["endgames"])


@router.get("/next", response_model=EndgameProblemPublic)
async def next_problem(
    theme_id: Optional[str] = Query(None, description="queen_mate | rook_mate | two_rooks_mate"),
    user_id: str = Depends(get_current_user_id),
) -> EndgameProblemPublic:
    if theme_id is not None and theme_id not in ENDGAME_THEMES:
        raise HTTPException(status_code=422, detail=f"theme_id inconnu : {theme_id!r}")
    endgame_elo = db_client.get_endgame_elo(user_id)
    problem = db_client.get_next_endgame_problem(endgame_elo, category=theme_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Aucune position de finale disponible.")
    return EndgameProblemPublic(
        id=problem["id"],
        fen=problem["fen"],
        category=problem["category"],
        difficulty_elo=problem["difficulty_elo"],
    )


@router.post("/attempt", response_model=EndgameAttemptResult)
async def submit_attempt(
    body: EndgameAttemptRequest, user_id: str = Depends(get_current_user_id),
) -> EndgameAttemptResult:
    problem = db_client.get_endgame_problem(body.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Position introuvable.")

    success = is_correct_move(problem["fen"], problem["solution"], body.move)
    current_elo = db_client.get_endgame_elo(user_id)
    new_elo = update_elo(current_elo, success)
    db_client.update_endgame_elo(user_id, new_elo)

    return EndgameAttemptResult(success=success, new_elo=new_elo, solution=problem["solution"])
