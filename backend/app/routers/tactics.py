"""Coaching Tactique Adaptatif — sélection de problèmes + validation (US 8.1/8.2, EPIC 8).

* ``GET  /api/v1/tactics/next``    — problème le plus proche de l'Elo tactique
  de l'utilisateur authentifié, filtrable par ``theme_id`` (US 8.2). EPIC 34 :
  source PRIMAIRE = API Puzzle Lichess (des millions de positions par thème,
  déjà vérifiées) ; repli sur le petit seed local statique si Lichess est
  injoignable — même politique de résilience que Chess.com (``games.py``).
* ``POST /api/v1/tactics/attempt`` — valide le coup joué côté serveur (jamais
  une confiance aveugle au client) et ajuste l'Elo tactique (+15/-15).
  EPIC 34 : supporte les solutions multi-coups (ex. mat en 2 : coup, réplique
  adverse forcée auto-jouée, coup de mat) via ``advance_tactical_attempt``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.domain.error_profile import ERROR_TYPE_TO_TACTICAL_THEMES, ERROR_TYPES
from app.domain.lichess_puzzles import angle_for_theme, parse_puzzle_payload, resolve_random_puzzles
from app.domain.models import (
    TacticalAttemptRequest,
    TacticalAttemptResult,
    TacticalProblemPublic,
    TacticalStatsResponse,
)
from app.domain.puzzles_models import LichessTheme, PuzzleResponse
from app.domain.tactical_elo import update_elo
from app.domain.tactics import (
    TACTICAL_THEMES,
    advance_tactical_attempt,
    compute_daily_streak,
    compute_stats_by_theme,
    solution_sequence,
)
from app.config import settings
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tactics", tags=["tactics"])


def _get_lichess_client():
    """Client Lichess : réutilise l'instance du lifespan (``app.main``) si
    l'application tourne, sinon en crée une éphémère (tests d'app minimale).
    Import paresseux pour éviter le cycle main ⇄ routers (même motif que
    ``_get_chess_com_client`` dans ``games.py``)."""
    from app import main as app_main
    from app.infrastructure.lichess_client import LichessClient

    return app_main.lichess_client or LichessClient()


async def _fetch_lichess_problem(theme_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Tente de servir un problème depuis l'API Puzzle Lichess. ``None`` sur
    toute panne (réseau, timeout, réponse inattendue) — jamais d'exception
    remontée : l'appelant retombe alors sur le seed local."""
    angle = angle_for_theme(theme_id)
    try:
        client = _get_lichess_client()
        payload = await client.get_next_puzzle(angle)
    except Exception as exc:  # réseau/HTTP : Lichess injoignable ou en erreur
        logger.warning("tactics/next: Lichess injoignable (angle=%r) : %r", angle, exc)
        return None
    parsed = parse_puzzle_payload(payload, category=theme_id)
    if parsed is None:
        # Diagnostic (EPIC 34 hotfix) : la forme exacte de la réponse Lichess
        # n'a pas pu être vérifiée en développement (réseau bloqué dans le
        # bac à sable) — logguer le payload brut (tronqué) permet de corriger
        # le parsing sur la vraie forme plutôt que de deviner à l'aveugle.
        logger.warning(
            "tactics/next: réponse Lichess inexploitable (angle=%r) — payload=%.2000s",
            angle, payload,
        )
        return None
    problem_id = db_client.add_lichess_tactical_problem(parsed)
    return db_client.get_tactical_problem(problem_id)


@router.get("/next", response_model=TacticalProblemPublic)
async def next_problem(
    theme_id: Optional[str] = Query(None, description="mate_in_1 | mate_in_2 | hanging_piece"),
    user_id: str = Depends(get_current_user_id),
) -> TacticalProblemPublic:
    """Sélectionne un problème. La solution n'est jamais incluse dans cette
    réponse.

    ``theme_id`` (US 8.2) filtre par catégorie ; omis ou ``None`` = « Aléatoire »
    (toutes catégories confondues). Une valeur hors de ``TACTICAL_THEMES``
    est rejetée en 422 plutôt que de renvoyer silencieusement 404.

    EPIC 34 : essaie d'abord l'API Puzzle Lichess (variété quasi illimitée) ;
    si injoignable, repli sur le seed local le plus proche de l'Elo tactique
    de l'utilisateur (1000 par défaut), en excluant les derniers problèmes
    servis pour éviter de reservir toujours le même exercice.
    """
    if theme_id is not None and theme_id not in TACTICAL_THEMES:
        raise HTTPException(status_code=422, detail=f"theme_id inconnu : {theme_id!r}")

    problem = None if settings.disable_lichess_puzzles else await _fetch_lichess_problem(theme_id)
    if problem is None:
        tactical_elo = db_client.get_tactical_elo(user_id)
        recent_ids = db_client.get_recent_tactical_problem_ids(user_id)
        problem = db_client.get_next_tactical_problem(
            tactical_elo, category=theme_id, exclude_ids=recent_ids
        )
    if problem is None:
        raise HTTPException(status_code=404, detail="Aucun problème tactique disponible.")

    db_client.record_served_tactical_problem_id(user_id, problem["id"])
    return TacticalProblemPublic(
        id=problem["id"],
        fen=problem["fen"],
        category=problem["category"],
        difficulty_elo=problem["difficulty_elo"],
    )


def _get_puzzle_repo():
    """Dépôt du catalogue `lichess_puzzles` si ``DATABASE_URL`` est configuré,
    ``None`` sinon — ce catalogue (EPIC 37, ingéré via
    ``scripts/ingest_lichess_puzzles.py``) n'a pas d'équivalent in-memory :
    contrairement au reste de ``db_client``, il n'existe qu'en base."""
    if not settings.database_url:
        return None
    from app.infrastructure.pg_repository import PgRepository

    return PgRepository(settings.database_url)


@router.get("/random", response_model=List[PuzzleResponse])
async def random_puzzles(
    rating_min: int = Query(1000, ge=0, le=3500),
    rating_max: int = Query(1600, ge=0, le=3500),
    theme: Optional[LichessTheme] = Query(None),
    limit: int = Query(1, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
) -> List[PuzzleResponse]:
    """US 37.1 — puzzles tirés du catalogue local `lichess_puzzles`, dans une
    plage d'Elo donnée. Élargit automatiquement la plage de ±100 (fallback)
    si aucun puzzle ne correspond exactement (cf. `resolve_random_puzzles`).
    """
    if rating_max < rating_min:
        raise HTTPException(status_code=422, detail="rating_max doit être >= rating_min")

    repo = _get_puzzle_repo()
    if repo is None:
        raise HTTPException(
            status_code=503, detail="Catalogue de puzzles indisponible (base non configurée)."
        )

    theme_value = theme.value if theme is not None else None
    puzzles, _strategy = resolve_random_puzzles(repo, rating_min, rating_max, theme_value, limit)
    if not puzzles:
        raise HTTPException(status_code=404, detail="Aucun puzzle disponible pour ces critères.")
    return [PuzzleResponse(**puzzle) for puzzle in puzzles]


@router.post("/attempt", response_model=TacticalAttemptResult)
async def submit_attempt(
    body: TacticalAttemptRequest, user_id: str = Depends(get_current_user_id),
) -> TacticalAttemptResult:
    """Valide le coup joué contre la solution stockée côté serveur — jamais
    une validation frontend seule, qui serait trivialement contournable.

    EPIC 34 — solutions multi-coups (mat en 2, puzzles Lichess) : l'état de
    progression (position courante, coups restants) est gardé côté serveur
    entre deux appels sur le même ``problem_id`` (``db_client``, en mémoire).
    Un coup juste mais pas encore final répond ``complete=False`` avec la
    réplique adverse auto-jouée ; Elo/série ne bougent qu'à la complétion
    (ou à un coup faux, comme avant pour un problème à un seul coup).
    """
    problem = db_client.get_tactical_problem(body.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problème introuvable.")

    full_sequence = solution_sequence(problem["solution"])
    session = db_client.get_tactical_attempt_session(user_id, body.problem_id)
    if session is None:
        session = {"fen": problem["fen"], "remaining": full_sequence}

    step = advance_tactical_attempt(session["fen"], session["remaining"], body.move)

    if step["result"] == "correct_partial":
        db_client.set_tactical_attempt_session(
            user_id, body.problem_id, step["fen"], step["remaining"]
        )
        return TacticalAttemptResult(
            success=True, complete=False, fen=step["fen"], opponent_move=step["opponent_move"],
        )

    db_client.clear_tactical_attempt_session(user_id, body.problem_id)
    success = step["result"] == "correct_complete"
    current_elo = db_client.get_tactical_elo(user_id)
    new_elo = update_elo(current_elo, success)
    db_client.update_tactical_elo(user_id, new_elo)
    db_client.record_tactical_attempt(
        user_id, problem["id"], problem["category"], success, body.time_taken or 0.0
    )

    attempts = db_client.get_tactical_attempts(user_id)
    streak = compute_daily_streak(attempts, datetime.now(timezone.utc).date())

    # Coup attendu à AFFICHER : celui de l'étape où l'utilisateur en est
    # (session["remaining"][0]), pas nécessairement le tout premier coup de
    # la séquence — plus utile pour l'utilisateur qui échoue en cours de route.
    displayed_solution = session["remaining"][0] if session["remaining"] else full_sequence[-1]

    return TacticalAttemptResult(
        success=success, complete=True, new_elo=new_elo, solution=displayed_solution, streak=streak,
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
