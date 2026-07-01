"""Routes d'ingestion & d'analyse asynchrone — EPIC 1 (US 1.1 / 1.2).

* ``POST /api/v1/games/analyze``  — crée la (les) partie(s) au statut
  ``processing``, répond immédiatement en ``202`` avec les UUID, et délègue
  l'analyse Stockfish à une tâche de fond (``BackgroundTasks``).
* ``GET  /api/v1/games/{game_id}`` — statut + métriques par coup.
* ``GET  /api/v1/stats/summary``   — résumé agrégé pour le frontend (US 4.1).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response

logger = logging.getLogger(__name__)

from app.config import settings
from app.domain.analysis_pipeline import analyze_pgn, build_client_engine
from app.domain.models import (
    AnalyzeAccepted,
    AnalyzeAcceptedItem,
    AnalyzeGamesRequest,
    GameStatus,
)
from app.domain.stats_aggregator import build_summary
from app.infrastructure import db_client
from app.infrastructure.engine import EngineProvider, NativeStockfishEngine

router = APIRouter(prefix="/api/v1", tags=["games"])


# ---------------------------------------------------------------------------
# Worker (tâche de fond)
# ---------------------------------------------------------------------------

#: Emplacement du binaire Stockfish dans l'image Docker (Debian).
DEFAULT_STOCKFISH_PATH = "/usr/games/stockfish"


def _select_engine(evals: Optional[Dict[str, Any]]) -> Optional[EngineProvider]:
    """Choisit la source d'évaluations : client > Stockfish natif > aucune."""
    if evals:
        return build_client_engine(evals)
    path = settings.stockfish_path
    if not path and os.path.exists(DEFAULT_STOCKFISH_PATH):
        path = DEFAULT_STOCKFISH_PATH  # fallback binaire Docker
    if path:
        return NativeStockfishEngine(path, depth=settings.engine_depth)
    return None


def run_analysis(game_id: str, pgn: str, evals: Optional[Dict[str, Any]]) -> None:
    """Analyse une partie et persiste les métriques (bulk), puis met à jour le statut."""
    try:
        engine = _select_engine(evals)
        outcome = analyze_pgn(pgn, engine)
        db_client.bulk_insert_moves(game_id, outcome["moves"])
        db_client.update_game(
            game_id, status=GameStatus.COMPLETED.value, result=outcome.get("result")
        )
    except Exception:  # pragma: no cover - garde-fou worker
        db_client.update_game(game_id, status=GameStatus.FAILED.value)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/games/analyze", status_code=202, response_model=AnalyzeAccepted)
async def analyze_games(
    body: AnalyzeGamesRequest, background: BackgroundTasks
) -> AnalyzeAccepted:
    """Soumission asynchrone (US 1.1). Répond en 202 avec les UUID des parties."""
    if not body.pgn and not body.game_ids:
        raise HTTPException(status_code=400, detail="Fournir 'pgn' ou 'game_ids'.")

    accepted: List[AnalyzeAcceptedItem] = []

    if body.pgn:
        game = db_client.create_game(
            pgn=body.pgn,
            user_id=body.user_id,
            time_control=body.time_control,
            user_color=body.user_color,
            status=GameStatus.PROCESSING.value,
        )
        background.add_task(run_analysis, game["id"], body.pgn, body.evals)
        accepted.append(AnalyzeAcceptedItem(game_id=game["id"]))

    for gid in body.game_ids or []:
        game = db_client.get_game(gid)
        if game is None:
            continue
        db_client.update_game(gid, status=GameStatus.PROCESSING.value)
        db_client.clear_moves(gid)  # purge les anciens coups avant réanalyse
        background.add_task(run_analysis, gid, game["pgn"], body.evals)
        accepted.append(AnalyzeAcceptedItem(game_id=gid))

    return AnalyzeAccepted(accepted=accepted)


@router.get("/games/{game_id}")
async def get_game(game_id: str) -> Dict[str, Any]:
    """Statut d'analyse + métriques par coup d'une partie."""
    game = db_client.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Partie introuvable.")
    return {"game": game, "moves": db_client.get_moves_for_game(game_id)}


@router.get("/stats/summary")
async def stats_summary(
    period: str = Query("30d"),
    user_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Résumé agrégé des statistiques avancées (US 4.1) — zéro calcul client.

    En cas d'erreur d'accès aux données (ex. base indisponible), on journalise
    la trace et on renvoie un résumé vide (200) plutôt qu'un 500 : le frontend
    dégrade proprement au lieu de casser.
    """
    try:
        games = db_client.get_completed_games(user_id)
        entries = [
            {"game": g, "moves": db_client.get_moves_for_game(g["id"])} for g in games
        ]
        return build_summary(entries, period=period)
    except Exception:
        logger.exception("stats/summary: échec d'accès aux données, résumé vide renvoyé")
        return build_summary([], period=period)
