"""Coaching Tactique Adaptatif — sélection de problèmes + validation (US 8.1/8.2, EPIC 8).

* ``GET  /api/v1/tactics/next``    — problème le plus proche de l'Elo tactique
  de l'utilisateur authentifié, filtrable par ``theme_id`` (US 8.2).
* ``POST /api/v1/tactics/attempt`` — valide le coup joué côté serveur (jamais
  une confiance aveugle au client) et ajuste l'Elo tactique (+15/-15).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.error_profile import ERROR_TYPE_TO_TACTICAL_THEMES, ERROR_TYPES
from app.domain.models import (
    TacticalAttemptRequest,
    TacticalAttemptResult,
    TacticalProblemPublic,
    TacticalStatsResponse,
)
from app.domain.tactical_elo import update_elo
from app.domain.tactics import (
    TACTICAL_THEMES,
    compute_daily_streak,
    compute_stats_by_theme,
    is_correct_move,
)
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/tactics", tags=["tactics"])


@router.get("/next", response_model=TacticalProblemPublic)
async def next_problem(
    theme_id: Optional[str] = Query(None, description="mate_in_1 | mate_in_2 | hanging_piece"),
    user_id: str = Depends(get_current_user_id),
) -> TacticalProblemPublic:
    """Sélectionne un problème dont la difficulté est proche de l'Elo tactique
    actuel de l'utilisateur (1000 par défaut tant qu'aucune tentative n'a été
    enregistrée). La solution n'est jamais incluse dans cette réponse.

    ``theme_id`` (US 8.2) filtre par catégorie ; omis ou ``None`` = « Aléatoire »
    (toutes catégories confondues). Une valeur hors de ``TACTICAL_THEMES``
    est rejetée en 422 plutôt que de renvoyer silencieusement 404.
    """
    if theme_id is not None and theme_id not in TACTICAL_THEMES:
        raise HTTPException(status_code=422, detail=f"theme_id inconnu : {theme_id!r}")
    tactical_elo = db_client.get_tactical_elo(user_id)
    problem = db_client.get_next_tactical_problem(tactical_elo, category=theme_id)
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
    db_client.record_tactical_attempt(
        user_id, problem["id"], problem["category"], success, body.time_taken or 0.0
    )

    attempts = db_client.get_tactical_attempts(user_id)
    streak = compute_daily_streak(attempts, datetime.now(timezone.utc).date())

    return TacticalAttemptResult(
        success=success, new_elo=new_elo, solution=problem["solution"], streak=streak
    )


@router.get("/custom", response_model=TacticalProblemPublic)
async def custom_problem(
    focus: str = Query(..., description="hanging_piece | time_pressure | missed_mate"),
    user_id: str = Depends(get_current_user_id),
) -> TacticalProblemPublic:
    """EPIC 11 (US 9.2) — « Entraînement Personnalisé » ciblant un type d'erreur.

    ``focus`` est un type d'erreur du profil comportemental (`ERROR_TYPES`),
    pas directement un `theme_id` tactique : `ERROR_TYPE_TO_TACTICAL_THEMES`
    fait le lien (ex. `missed_mate` -> problèmes `mate_in_1`/`mate_in_2`).
    Une valeur inconnue est rejetée en 422, comme `theme_id` sur `/next`.
    """
    if focus not in ERROR_TYPES:
        raise HTTPException(status_code=422, detail=f"focus inconnu : {focus!r}")
    themes = ERROR_TYPE_TO_TACTICAL_THEMES[focus]
    tactical_elo = db_client.get_tactical_elo(user_id)
    problem = db_client.get_next_tactical_problem_for_categories(tactical_elo, list(themes))
    if problem is None:
        raise HTTPException(status_code=404, detail="Aucun problème tactique disponible.")
    return TacticalProblemPublic(
        id=problem["id"],
        fen=problem["fen"],
        category=problem["category"],
        difficulty_elo=problem["difficulty_elo"],
    )


@router.get("/stats", response_model=TacticalStatsResponse)
async def tactics_stats(user_id: str = Depends(get_current_user_id)) -> TacticalStatsResponse:
    """US 8.4 — Taux de réussite par catégorie + série en cours aujourd'hui,
    calculés depuis l'historique des tentatives de l'utilisateur authentifié.
    """
    attempts = db_client.get_tactical_attempts(user_id)
    by_theme = compute_stats_by_theme(attempts)
    streak = compute_daily_streak(attempts, datetime.now(timezone.utc).date())
    return TacticalStatsResponse(by_theme=by_theme, streak=streak)
