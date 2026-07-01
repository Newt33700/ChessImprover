"""Coaching Tactique Adaptatif — sélection de problèmes + validation (US 8.1, EPIC 8).

* ``GET  /api/v1/tactics/next``    — problème le plus proche de l'Elo tactique
  de l'utilisateur authentifié.
* ``POST /api/v1/tactics/attempt`` — valide le coup joué côté serveur (jamais
  une confiance aveugle au client) et ajuste l'Elo tactique (+15/-15).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import (
    TacticalAttemptRequest,
    TacticalAttemptResult,
    TacticalProblemPublic,
)
from app.domain.tactical_elo import update_elo
from app.domain.tactics import is_correct_move
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/tactics", tags=["tactics"])


@router.get("/next", response_model=TacticalProblemPublic)
async def next_problem(user_id: str = Depends(get_current_user_id)) -> TacticalProblemPublic:
    """Sélectionne un problème dont la difficulté est proche de l'Elo tactique
    actuel de l'utilisateur (1000 par défaut tant qu'aucune tentative n'a été
    enregistrée). La solution n'est jamais incluse dans cette réponse.
    """
    tactical_elo = db_client.get_tactical_elo(user_id)
    problem = db_client.get_next_tactical_problem(tactical_elo)
    if problem is None:
        raise HTTPException(status_code=404, detail="Aucun problème tactique disponible.")
    return TacticalProblemPublic(
        id=problem["id"],
        fen=problem["fen"],
        category=problem["category"],
        difficulty_elo=problem["difficulty_elo"],
    )


@router.post("/attempt", response_model=TacticalAttemptResult)
async def submit_attempt(
    body: TacticalAttemptRequest, user_id: str = Depends(get_current_user_id),
) -> TacticalAttemptResult:
    """Valide le coup joué contre la solution stockée côté serveur — jamais
    une validation frontend seule, qui serait trivialement contournable.
    """
    problem = db_client.get_tactical_problem(body.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problème introuvable.")

    success = is_correct_move(problem["fen"], problem["solution"], body.move)
    current_elo = db_client.get_tactical_elo(user_id)
    new_elo = update_elo(current_elo, success)
    db_client.update_tactical_elo(user_id, new_elo)

    return TacticalAttemptResult(success=success, new_elo=new_elo, solution=problem["solution"])
