"""Routes d'ingestion & d'analyse asynchrone — EPIC 1 (US 1.1 / 1.2) & US 5.1.

* ``POST /api/v1/games/analyze``  — crée la (les) partie(s) au statut
  ``processing``, répond immédiatement en ``202`` avec les UUID, et délègue
  l'analyse Stockfish à une tâche de fond (``BackgroundTasks``).
* ``GET  /api/v1/games/{game_id}`` — statut + métriques par coup.
* ``GET  /api/v1/stats/summary``   — résumé agrégé pour le frontend (US 4.1).
* ``GET  /api/v1/stats/history``   — historique des snapshots Elo (US 5.1).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response

logger = logging.getLogger(__name__)

from app.config import settings
from app.domain.analysis_pipeline import analyze_pgn, build_client_engine, compute_pgn_hash
from app.domain.cognitive_load import build_decision_fluidity_report, build_time_allocation_report
from app.domain.error_profile import ERROR_TYPES, detect_error_occurrences, update_frequency_score
from app.domain import elo_curve, game_sync
from app.domain.game_salvage import find_defeat_pivot, reconstruct_position_before_move
from app.domain.models import (
    AnalyzeAccepted,
    AnalyzeAcceptedItem,
    AnalyzeGamesRequest,
    EloCurvePoint,
    EloCurveResponse,
    GamesSyncResult,
    GameStatus,
    GameStatusUpdate,
)
from app.domain.progress_history import build_snapshot, filter_history_by_days
from app.domain.srs_flashcards import extract_blunder_flashcards
from app.domain.stats_aggregator import build_summary
from app.infrastructure import db_client
from app.infrastructure.engine import EngineProvider, NativeStockfishEngine
from app.routers.deps import get_current_user_id

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


def run_analysis(
    game_id: str,
    pgn: str,
    evals: Optional[Dict[str, Any]],
    user_id: Optional[str] = None,
    user_color: str = "white",
    time_control: Optional[str] = None,
) -> None:
    """Analyse une partie et persiste les métriques (bulk), puis met à jour le statut."""

    def _on_progress(current: int, total: int) -> None:
        # EPIC 28 (US 28.1) — Smart Loader : progression publiée en direct,
        # best-effort (ne doit jamais interrompre l'analyse elle-même).
        try:
            db_client.update_game(game_id, progress_current=current, progress_total=total)
        except Exception:  # pragma: no cover - garde-fou worker
            pass

    try:
        engine = _select_engine(evals)
        outcome = analyze_pgn(pgn, engine, time_control, on_progress=_on_progress)
        db_client.bulk_insert_moves(game_id, outcome["moves"])
        db_client.update_game(
            game_id,
            status=GameStatus.COMPLETED.value,
            result=outcome.get("result"),
            eco=outcome.get("eco"),
            opening_name=outcome.get("opening_name"),
            # EPIC 15 (US 15.1) : pivot de défaite — premier coup DU JOUEUR
            # (`user_color`) dont la perte de centipions atteint le seuil de
            # gaffe, pour proposer une reprise en sandbox (US 15.2).
            pivot_move_index=find_defeat_pivot(outcome["moves"], user_color),
        )
    except Exception:  # pragma: no cover - garde-fou worker
        db_client.update_game(game_id, status=GameStatus.FAILED.value)
        return

    # US 5.1 : snapshot de progression — ne doit jamais faire échouer l'analyse
    # elle-même (déjà persistée à ce stade), donc isolé dans son propre garde-fou.
    try:
        snapshot = build_snapshot(outcome["moves"], time_control, user_color, game_id, user_id)
        if snapshot is not None:
            db_client.create_progress_snapshot(
                snapshot["user_id"], snapshot["game_id"], snapshot["cadence"], snapshot["elos"]
            )
    except Exception:  # pragma: no cover - garde-fou worker
        logger.exception("run_analysis: échec de l'enregistrement du snapshot de progression")

    # EPIC 11 (US 9.1) : profil d'erreurs comportementales — même garde-fou
    # que le snapshot ci-dessus, ne doit jamais faire échouer l'analyse déjà
    # persistée. Sans utilisateur authentifié (analyse anonyme), rien à faire.
    try:
        if user_id:
            occurrences = detect_error_occurrences(pgn, user_color, outcome["moves"])
            now_iso = datetime.now(timezone.utc).isoformat()
            for error_type in ERROR_TYPES:
                existing = db_client.get_error_profile(user_id, error_type)
                old_score = existing["frequency_score"] if existing else 0.0
                new_score = update_frequency_score(old_score, occurrences[error_type])
                db_client.upsert_error_profile(user_id, error_type, new_score, now_iso)
    except Exception:  # pragma: no cover - garde-fou worker
        logger.exception("run_analysis: échec de la mise à jour du profil d'erreurs")

    # EPIC 20 (US 20.1) : Le Cimetière des Erreurs — flashcards SRS auto-générées
    # depuis les gaffes de la partie. Même garde-fou que les deux blocs
    # ci-dessus : ne doit jamais faire échouer l'analyse déjà persistée.
    try:
        if user_id:
            own_moves = [m for m in outcome["moves"] if m.get("color") == user_color]
            for candidate in extract_blunder_flashcards(own_moves):
                db_client.create_flashcard(
                    user_id, game_id, candidate["fen"], candidate["solution"]
                )
    except Exception:  # pragma: no cover - garde-fou worker
        logger.exception("run_analysis: échec de la génération des flashcards SRS")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/games/analyze", status_code=202, response_model=AnalyzeAccepted)
async def analyze_games(
    body: AnalyzeGamesRequest, background: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> AnalyzeAccepted:
    """Soumission asynchrone (US 1.1). Répond en 202 avec les UUID des parties.

    ``user_id`` (US 6.4) provient exclusivement du JWT authentifié — jamais
    d'un champ fourni par le client, qui pourrait usurper un autre profil.
    """
    if not body.pgn and not body.game_ids:
        raise HTTPException(status_code=400, detail="Fournir 'pgn' ou 'game_ids'.")

    accepted: List[AnalyzeAcceptedItem] = []

    if body.pgn:
        # US 7.2 : un PGN déjà soumis par cet utilisateur ne relance jamais
        # l'analyse Stockfish (coûteuse) — on renvoie la partie existante
        # avec son statut réel, quel qu'il soit (processing/completed/failed).
        pgn_hash = compute_pgn_hash(body.pgn)
        existing = db_client.find_game_by_pgn_hash(user_id, pgn_hash)
        if existing is not None:
            accepted.append(
                AnalyzeAcceptedItem(game_id=existing["id"], status=existing["status"])
            )
        else:
            game = db_client.create_game(
                pgn=body.pgn,
                user_id=user_id,
                time_control=body.time_control,
                user_color=body.user_color,
                status=GameStatus.PROCESSING.value,
                pgn_hash=pgn_hash,
            )
            background.add_task(
                run_analysis, game["id"], body.pgn, body.evals,
                user_id, body.user_color, body.time_control,
            )
            accepted.append(AnalyzeAcceptedItem(game_id=game["id"]))

    for gid in body.game_ids or []:
        game = db_client.get_game(gid)
        # Une partie introuvable ou appartenant à un autre utilisateur est
        # silencieusement ignorée (même traitement, pour ne pas révéler
        # l'existence de parties tierces).
        if game is None or game.get("user_id") != user_id:
            continue
        db_client.update_game(gid, status=GameStatus.PROCESSING.value)
        db_client.clear_moves(gid)  # purge les anciens coups avant réanalyse
        background.add_task(
            run_analysis, gid, game["pgn"], body.evals,
            user_id, game.get("user_color", "white"), game.get("time_control"),
        )
        accepted.append(AnalyzeAcceptedItem(game_id=gid))

    return AnalyzeAccepted(accepted=accepted)


def _get_chess_com_client():
    """Client Chess.com : réutilise l'instance du lifespan (``app.main``) si
    l'application tourne, sinon en crée une éphémère (tests d'app minimale).
    Import paresseux pour éviter le cycle main ⇄ routers."""
    from app import main as app_main
    from app.infrastructure.chess_com_client import ChessComClient

    return app_main.chess_com_client or ChessComClient()


@router.post("/games/sync", status_code=202, response_model=GamesSyncResult)
async def sync_games(
    background: BackgroundTasks, user_id: str = Depends(get_current_user_id),
) -> GamesSyncResult:
    """EPIC 23 — Synchronisation à la connexion : ratisse les dernières parties
    Chess.com de l'utilisateur et lance leur analyse en tâche de fond.

    Répond immédiatement en 202 (les analyses tournent en arrière-plan et
    mettent à jour tous les KPI en cascade via ``run_analysis``). Idempotent :
    les parties déjà connues sont écartées par leur hash PGN (US 7.2), donc
    appeler la route à chaque connexion est sans risque.
    """
    user = db_client.find_user_by_id(user_id)
    chess_username = (user or {}).get("chess_username")
    if not chess_username:
        raise HTTPException(
            status_code=422,
            detail="Aucun pseudo Chess.com lié au profil — renseignez-le via Profil.",
        )

    client = _get_chess_com_client()
    try:
        raw_games = await client.get_latest_games(
            chess_username, limit=game_sync.FETCH_LAST_GAMES
        )
    except Exception:
        # Chess.com injoignable : pas de sync ce coup-ci, sans fuite du détail
        # interne (même politique que routes /games/{username} de app.main).
        raise HTTPException(
            status_code=502, detail="Chess.com est indisponible pour le moment."
        )

    result = GamesSyncResult(fetched=len(raw_games))
    queued_ids: set = set()

    for candidate in game_sync.extract_sync_candidates(raw_games, chess_username):
        pgn_hash = compute_pgn_hash(candidate["pgn"])
        if db_client.find_game_by_pgn_hash(user_id, pgn_hash) is not None:
            result.skipped += 1
            continue
        if result.queued >= game_sync.MAX_ANALYSES_PER_SYNC:
            # Plafond CPU (instance Render modeste) : différé à la prochaine
            # sync — le hash PGN retrouvera ces parties comme « nouvelles ».
            result.deferred += 1
            continue
        game = db_client.create_game(
            pgn=candidate["pgn"],
            user_id=user_id,
            time_control=candidate["time_control"],
            user_color=candidate["user_color"],
            status=GameStatus.PROCESSING.value,
            pgn_hash=pgn_hash,
        )
        background.add_task(
            run_analysis, game["id"], candidate["pgn"], None,
            user_id, candidate["user_color"], candidate["time_control"],
        )
        queued_ids.add(game["id"])
        result.queued += 1

    # Re-enfilage des analyses orphelines : une partie restée en `processing`
    # au-delà du seuil (instance endormie/redémarrée en plein travail) est
    # relancée — coups purgés d'abord pour ne jamais les dupliquer.
    now = datetime.now(timezone.utc)
    for game in db_client.get_games_for_user(user_id):
        if game["id"] in queued_ids or not game_sync.is_stale_processing(game, now):
            continue
        db_client.clear_moves(game["id"])
        background.add_task(
            run_analysis, game["id"], game["pgn"], None,
            user_id, game.get("user_color", "white"), game.get("time_control"),
        )
        result.requeued += 1

    return result


@router.get("/games")
async def list_games(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """US 7.1 — Liste des parties déjà soumises/analysées de l'utilisateur authentifié."""
    return {"games": db_client.get_games_for_user(user_id)}


@router.get("/games/{game_id}")
async def get_game(
    game_id: str, user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Statut d'analyse + métriques par coup d'une partie de l'utilisateur authentifié."""
    game = db_client.get_game(game_id)
    if game is None or game.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Partie introuvable.")
    return {"game": game, "moves": db_client.get_moves_for_game(game_id)}


@router.patch("/games/{game_id}/status")
async def update_game_status(
    game_id: str, body: GameStatusUpdate, user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """US 7.3 — Bascule le statut « déjà étudiée » d'une partie de l'utilisateur authentifié."""
    game = db_client.get_game(game_id)
    if game is None or game.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Partie introuvable.")
    updated = db_client.update_game(game_id, is_reviewed=body.is_reviewed)
    return {"game": updated}


@router.post("/games/{game_id}/salvage")
async def salvage_game(
    game_id: str, user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """EPIC 15 (US 15.2) — Position exacte à rejouer à partir du pivot de
    défaite (US 15.1), pour un mode Sandbox « Sauver la partie ».
    """
    game = db_client.get_game(game_id)
    if game is None or game.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Partie introuvable.")
    if game.get("status") != GameStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="Partie pas encore analysée.")
    pivot_index = game.get("pivot_move_index")
    if pivot_index is None:
        raise HTTPException(
            status_code=404, detail="Aucun pivot de défaite détecté pour cette partie."
        )
    position = reconstruct_position_before_move(game["pgn"], pivot_index)
    if position is None:
        raise HTTPException(status_code=422, detail="Position introuvable pour cette partie.")
    return {"game_id": game_id, "pivot_move_index": pivot_index, **position}


@router.get("/stats/summary")
async def stats_summary(
    period: str = Query("30d"),
    user_id: str = Depends(get_current_user_id),
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


@router.get("/stats/history")
async def stats_history(
    cadence: str = Query("blitz"),
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """Historique des snapshots Elo virtuel pour une cadence (US 5.1).

    Alimente la courbe de progression frontend. Dégrade en historique vide
    (200) plutôt qu'un 500 si la base est indisponible.
    """
    try:
        rows = db_client.get_progress_history(user_id, cadence)
    except Exception:
        logger.exception("stats/history: échec d'accès aux données, historique vide renvoyé")
        rows = []

    filtered = filter_history_by_days(rows, days=days)
    return {
        "cadence": cadence,
        "days": days,
        "history": [
            {
                "date": row["recorded_at"],
                "openings": row["elo_openings"],
                "tactics": row["elo_tactics"],
                "strategy": row["elo_strategy"],
                "endgames": row["elo_endgames"],
            }
            for row in filtered
        ],
    }


@router.get("/stats/elo-curve", response_model=EloCurveResponse)
async def stats_elo_curve(
    cadence: str = Query("blitz", description="bullet | blitz | rapid | daily"),
    days: int = Query(30, ge=1, le=365),
    user_id: str = Depends(get_current_user_id),
) -> EloCurveResponse:
    """EPIC 24 — Courbe d'Elo Chess.com RÉELLE pour une cadence.

    Reconstruite depuis les archives mensuelles (chaque partie porte le rating
    du joueur après la partie) : un point par jour joué (dernier rating du
    jour) sur la fenêtre demandée. Nécessite un pseudo Chess.com lié au
    profil (US 6.3) — 422 explicite sinon, 502 générique si Chess.com est
    injoignable (mêmes politiques que ``/games/sync``).
    """
    if cadence not in elo_curve.ELO_CURVE_CADENCES:
        raise HTTPException(status_code=422, detail=f"cadence inconnue : {cadence!r}")
    user = db_client.find_user_by_id(user_id)
    chess_username = (user or {}).get("chess_username")
    if not chess_username:
        raise HTTPException(
            status_code=422,
            detail="Aucun pseudo Chess.com lié au profil — renseignez-le via Profil.",
        )

    now = datetime.now(timezone.utc)
    client = _get_chess_com_client()
    try:
        raw_games = await client.get_games_for_months(
            chess_username, elo_curve.months_covering(now, days)
        )
    except Exception:
        raise HTTPException(
            status_code=502, detail="Chess.com est indisponible pour le moment."
        )

    points = elo_curve.build_elo_curve(raw_games, chess_username, cadence, days, now)
    return EloCurveResponse(
        cadence=cadence,
        days=days,
        points=[EloCurvePoint(**p) for p in points],
    )


@router.get("/stats/cognitive-load")
async def stats_cognitive_load(user_id: str = Depends(get_current_user_id)) -> Dict[str, Any]:
    """Dashboard de Performance Cognitive (EPIC 19, US 19.1/19.2).

    Agrège tous les coups (toutes parties analysées confondues, comme
    ``/stats/summary``) en deux vues : répartition du temps de réflexion par
    phase/pression (US 19.1) et fluidité de décision (US 19.2). Dégrade en
    résumé vide (200) plutôt qu'un 500 si la base est indisponible.
    """
    try:
        games = db_client.get_completed_games(user_id)
        own_moves: List[Dict[str, Any]] = []
        for g in games:
            color = g.get("user_color", "white")
            own_moves.extend(
                m for m in db_client.get_moves_for_game(g["id"]) if m.get("color") == color
            )
        return {
            "time_allocation": build_time_allocation_report(own_moves),
            "decision_fluidity": build_decision_fluidity_report(own_moves),
        }
    except Exception:
        logger.exception("stats/cognitive-load: échec d'accès aux données, résumé vide renvoyé")
        return {
            "time_allocation": build_time_allocation_report([]),
            "decision_fluidity": build_decision_fluidity_report([]),
        }
