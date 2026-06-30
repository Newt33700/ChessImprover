"""Sync router — synchronisation cloud des parties et cartes SRS (US 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.domain.models import SyncRequest, SyncResponse
from app.infrastructure import db_client
from app.routers.auth import _current_user

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", response_model=SyncResponse)
def sync_data(body: SyncRequest, user: dict = Depends(_current_user)) -> SyncResponse:
    """Stratégie Client Wins : les données du client écrasent le serveur en cas de conflit."""
    merged = db_client.upsert_user_data(user["id"], body.games, body.srs_cards)
    return SyncResponse(games=merged["games"], srs_cards=merged["srs_cards"])
