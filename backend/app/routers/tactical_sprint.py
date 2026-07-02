"""Mode "Tactical Sprint" — Social & Compétitif (EPIC 12, US 11.1/11.2).

* ``POST /api/v1/sprints/start``          — démarre un sprint (chrono serveur).
* ``POST /api/v1/sprints/{id}/attempt``   — soumet un coup, valide 100 % serveur.
* ``POST /api/v1/sprints/{id}/finish``    — clôture le sprint (temps écoulé ou abandon).
* ``GET  /api/v1/sprints/ghost``          — meilleur sprint terminé, pour le replay Ghost.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import (
    GhostMoveEntry,
    GhostReplayResponse,
    SprintAttemptRequest,
    SprintAttemptResponse,
    SprintFinishResponse,
    SprintStartResponse,
    TacticalProblemPublic,
)
from app.domain.tactical_sprint import (
    SPRINT_DURATION_SECONDS,
    compute_score,
    elapsed_seconds,
    is_sprint_active,
    record_ghost_move,
)
from app.domain.tactics import is_correct_move
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/sprints", tags=["tactical-sprint"])


def _public_problem(problem: dict) -> TacticalProblemPublic:
    return TacticalProblemPublic(
        id=problem["id"],
        fen=problem["fen"],
        category=problem["category"],
        difficulty_elo=problem["difficulty_elo"],
    )


def _next_problem(user_id: str) -> dict:
    tactical_elo = db_client.get_tactical_elo(user_id)
    problem = db_client.get_next_tactical_problem(tactical_elo)
    if problem is None:
        raise HTTPException(status_code=404, detail="Aucun problème tactique disponible.")
    return problem


@router.post("/start", response_model=SprintStartResponse)
async def start_sprint(user_id: str = Depends(get_current_user_id)) -> SprintStartResponse:
    """Démarre un sprint : `started_at` fixé côté serveur (chrono anti-triche, US 11.1)."""
    sprint = db_client.create_sprint(user_id)
    problem = _next_problem(user_id)
    return SprintStartResponse(
        sprint_id=sprint["id"],
        duration_seconds=SPRINT_DURATION_SECONDS,
        problem=_public_problem(problem),
    )


@router.post("/{sprint_id}/attempt", response_model=SprintAttemptResponse)
async def submit_sprint_attempt(
    sprint_id: str, body: SprintAttemptRequest, user_id: str = Depends(get_current_user_id),
) -> SprintAttemptResponse:
    """Valide un coup pour le problème en cours d'un sprint actif.

    Le temps restant est calculé côté serveur (`elapsed_seconds`) — jamais un
    temps déclaré par le client. Une tentative reçue hors fenêtre clôture le
    sprint automatiquement plutôt que d'accepter silencieusement un coup
    tardif.
    """
    sprint = db_client.get_sprint(sprint_id)
    if sprint is None or sprint["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Sprint introuvable.")
    if sprint.get("finished_at") is not None:
        raise HTTPException(status_code=409, detail="Ce sprint est déjà terminé.")

    now = datetime.now(timezone.utc)
    active = is_sprint_active(sprint["started_at"], now)
    remaining = max(0.0, SPRINT_DURATION_SECONDS - elapsed_seconds(sprint["started_at"], now))

    if not active:
        db_client.update_sprint(
            sprint_id,
            finished_at=now,
            duration_seconds=int(elapsed_seconds(sprint["started_at"], now)),
        )
        return SprintAttemptResponse(
            success=False,
            score=sprint["score"],
            problems_solved_count=sprint["problems_solved_count"],
            time_remaining=0.0,
            sprint_active=False,
            next_problem=None,
        )

    problem = db_client.get_tactical_problem(body.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problème introuvable.")

    success = is_correct_move(problem["fen"], problem["solution"], body.move)
    solved_count = sprint["problems_solved_count"] + (1 if success else 0)
    score = compute_score(solved_count)
    moves = sprint["moves"]
    if success:
        elapsed_ms = int(elapsed_seconds(sprint["started_at"], now) * 1000)
        moves = record_ghost_move(moves, problem["id"], body.move, elapsed_ms)

    db_client.update_sprint(
        sprint_id, score=score, problems_solved_count=solved_count, moves=moves,
    )

    next_problem = _public_problem(_next_problem(user_id)) if remaining > 0 else None
    return SprintAttemptResponse(
        success=success,
        score=score,
        problems_solved_count=solved_count,
        time_remaining=remaining,
        sprint_active=True,
        next_problem=next_problem,
    )


@router.post("/{sprint_id}/finish", response_model=SprintFinishResponse)
async def finish_sprint(
    sprint_id: str, user_id: str = Depends(get_current_user_id),
) -> SprintFinishResponse:
    """Clôture le sprint (temps écoulé côté client ou abandon volontaire)."""
    sprint = db_client.get_sprint(sprint_id)
    if sprint is None or sprint["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Sprint introuvable.")

    if sprint.get("finished_at") is None:
        now = datetime.now(timezone.utc)
        duration = min(SPRINT_DURATION_SECONDS, int(elapsed_seconds(sprint["started_at"], now)))
        sprint = db_client.update_sprint(sprint_id, finished_at=now, duration_seconds=duration)

    return SprintFinishResponse(
        sprint_id=sprint["id"],
        score=sprint["score"],
        problems_solved_count=sprint["problems_solved_count"],
        duration_seconds=sprint["duration_seconds"],
    )


@router.get("/ghost", response_model=GhostReplayResponse)
async def ghost_replay(_: str = Depends(get_current_user_id)) -> GhostReplayResponse:
    """Meilleur sprint terminé, toutes utilisateurs confondus (US 11.2).

    Simple GET rejoué par le frontend (polling/fetch, cf. recommandation
    PO) — pas de WebSocket : le classement ne change qu'à la clôture d'un
    sprint, une mise à jour temps réel n'apporterait rien.
    """
    best = db_client.get_best_sprint()
    if best is None:
        return GhostReplayResponse(available=False)
    return GhostReplayResponse(
        available=True,
        score=best["score"],
        moves=[GhostMoveEntry(**m) for m in best["moves"]],
    )
