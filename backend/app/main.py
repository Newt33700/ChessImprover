"""API FastAPI — Chess Improver.

Point d'entrée : monte les routers métier (auth, games, tactics, …) et
expose ``GET /health``. Le client Chess.com partagé est construit dans le
lifespan et consommé par ``routers/games.py`` (sync EPIC 23, courbe d'Elo
EPIC 24).

EPIC 25 (US 25.4) : les routes historiques ``POST /analyze``,
``GET /games/{username}``, ``POST /srs/review`` et ``POST /srs/review/full``
— jamais appelées par le frontend (analyse Stockfish côté client, Chess.com
en direct, SRS en LocalStorage/IndexedDB, cf. ex-§9.1 du README) — ont été
supprimées : moins de surface d'attaque publique, zéro code mort.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.infrastructure.chess_com_client import ChessComClient
from app.infrastructure.lichess_client import LichessClient
from app.routers import auth as auth_router
from app.routers import endgames as endgames_router
from app.routers import error_profile as error_profile_router
from app.routers import games as games_router
from app.routers import openings_trainer as openings_trainer_router
from app.routers import quests as quests_router
from app.routers import seasons as seasons_router
from app.routers import srs_flashcards as srs_flashcards_router
from app.routers import sync as sync_router
from app.routers import tactical_sprint as tactical_sprint_router
from app.routers import tactics as tactics_router

# ---------------------------------------------------------------------------
# Lifespan (remplace les événements on_startup / on_shutdown dépréciés)
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

chess_com_client: ChessComClient | None = None
lichess_client: LichessClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global chess_com_client, lichess_client
    if not settings.debug and settings.jwt_secret == "dev-secret-change-in-production":
        # Fail-fast : mieux vaut un démarrage refusé qu'un backend en production
        # dont tous les tokens sont forgeables. En dev local, définir DEBUG=true
        # ou un JWT_SECRET quelconque dans .env.
        raise RuntimeError(
            "JWT_SECRET utilise encore la valeur par défaut : tout token est "
            "forgeable. Définir JWT_SECRET dans l'environnement (ou DEBUG=true en dev)."
        )
    chess_com_client = ChessComClient()
    lichess_client = LichessClient()
    yield
    if chess_com_client:
        await chess_com_client.close()
    if lichess_client:
        await lichess_client.close()


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
app.include_router(error_profile_router.router)
app.include_router(tactical_sprint_router.router)
app.include_router(srs_flashcards_router.router)
app.include_router(quests_router.router)
app.include_router(seasons_router.router)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "version": settings.app_version}
