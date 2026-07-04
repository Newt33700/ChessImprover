"""Moteur de saisons — EPIC 30.

* ``GET /api/v1/seasons/active`` — l'évènement saisonnier actif (fenêtre UTC
  serveur), s'il y en a un. Public (aucune donnée liée à un utilisateur) :
  la bannière FOMO doit s'afficher même avant connexion.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.domain.models import ActiveSeasonResponse, SeasonPublic
from app.domain.seasons import get_active_season, load_seasons, seconds_remaining

router = APIRouter(prefix="/api/v1/seasons", tags=["seasons"])


@router.get("/active", response_model=ActiveSeasonResponse)
async def get_active() -> ActiveSeasonResponse:
    now = datetime.now(timezone.utc)
    seasons = load_seasons()
    season = get_active_season(seasons, now)
    if season is None:
        return ActiveSeasonResponse(active=False)
    return ActiveSeasonResponse(
        active=True,
        season=SeasonPublic(
            id=season["id"],
            name=season["name"],
            end=season["end"],
            banner_message=season["banner_message"],
            cosmetic_piece_theme=season.get("cosmetic_piece_theme"),
            cosmetic_board_theme=season.get("cosmetic_board_theme"),
        ),
        seconds_remaining=seconds_remaining(season, now),
    )
