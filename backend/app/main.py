"""API FastAPI — Chess Improver.

Routes disponibles :
  POST /analyze          Analyse géométrique d'un PGN
  GET  /games/{username} Récupère les dernières parties Chess.com
  POST /srs/review       Met à jour une carte SRS après révision
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.domain.analyzer import analyze_pgn
from app.domain.elo_calculator import classify_move, estimate_elo, game_accuracy, move_accuracy
from app.domain.models import (
    AnalyzeRequest,
    Classification,
    GameAnalysis,
    MoveEvaluation,
    ReviewRequest,
    SRSCard,
)
from app.domain.srs_engine import review_card
from app.infrastructure.chess_com_client import ChessComClient
from app.routers import auth as auth_router
from app.routers import endgames as endgames_router
from app.routers import games as games_router
from app.routers import openings_trainer as openings_trainer_router
from app.routers import sync as sync_router
from app.routers import tactics as tactics_router

# ---------------------------------------------------------------------------
# Lifespan (remplace les événements on_startup / on_shutdown dépréciés)
# ---------------------------------------------------------------------------

chess_com_client: ChessComClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global chess_com_client
    chess_com_client = ChessComClient()
    yield
    if chess_com_client:
        await chess_com_client.close()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(sync_router.router)
app.include_router(games_router.router)
app.include_router(tactics_router.router)
app.include_router(openings_trainer_router.router)
app.include_router(endgames_router.router)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


@app.post("/analyze", response_model=GameAnalysis)
async def analyze(body: AnalyzeRequest) -> GameAnalysis:
    """Analyse géométrique + estimation Elo d'un PGN.

    Le client envoie le PGN et l'Elo de l'adversaire.
    Les scores Stockfish individuels sont attendus dans le PGN (commentaires) ou
    sont laissés à 0 si l'analyse moteur se fait côté navigateur (Web Worker).
    """
    opponent_elo = body.opponent_elo or 1000

    # Analyse géométrique (blunders, fourchettes, zeitnot)
    geo = analyze_pgn(body.pgn, player_color="w")

    # Estimation Elo à partir de la précision globale (sans évaluations moteur,
    # on utilise un score par défaut de 70 — le client JS enrichit cette valeur).
    default_accuracy = 70.0
    elo = estimate_elo(default_accuracy, opponent_elo)

    return GameAnalysis(
        game_id="local",
        accuracy=default_accuracy,
        estimated_elo=elo,
        moves=[],
        blunders_count=geo.blunders_count,
        missed_forks_count=geo.missed_forks_count,
        time_panic_count=geo.time_panic_count,
        opponent_elo=opponent_elo,
    )


@app.get("/games/{username}")
async def get_games(
    username: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Récupère les dernières parties d'un joueur Chess.com."""
    if chess_com_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    try:
        games = await chess_com_client.get_latest_games(username, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return games


@app.post("/srs/review", response_model=SRSCard)
async def srs_review(body: ReviewRequest) -> SRSCard:
    """Met à jour une carte SRS après révision (algorithme SM-2).

    Le client gère l'état des cartes en LocalStorage et envoie
    la carte complète pour recalcul côté serveur.
    """
    raise HTTPException(
        status_code=400,
        detail="Envoyer la carte SRSCard complète dans le corps (voir /docs)",
    )


@app.post("/srs/review/full", response_model=SRSCard)
async def srs_review_full(card: SRSCard, quality: int = Query(ge=0, le=5)) -> SRSCard:
    """Version complète : reçoit la carte + la qualité, renvoie la carte mise à jour."""
    return review_card(card, quality)
