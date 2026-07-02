"""Analyse Comportementale — profil d'erreurs de l'utilisateur (EPIC 11, US 9.1).

* ``GET /api/v1/error-profile`` — score de fréquence par type d'erreur suivi,
  alimenté après chaque partie analysée (``routers.games.run_analysis``).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.domain.error_profile import is_recurring
from app.domain.models import ErrorProfileEntry, ErrorProfileResponse
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1", tags=["error-profile"])


@router.get("/error-profile", response_model=ErrorProfileResponse)
async def get_error_profile(user_id: str = Depends(get_current_user_id)) -> ErrorProfileResponse:
    """Profils d'erreur de l'utilisateur authentifié — un par type déjà observé.

    ``is_recurring`` est calculé à la lecture (jamais stocké) : c'est un état
    dérivé de ``frequency_score``, pas une donnée en soi (cf. migration).
    """
    rows: list[Dict[str, Any]] = db_client.get_error_profiles(user_id)
    return ErrorProfileResponse(
        profiles=[
            ErrorProfileEntry(
                error_type=row["error_type"],
                frequency_score=row["frequency_score"],
                is_recurring=is_recurring(row["frequency_score"]),
                last_observed=row.get("last_observed"),
            )
            for row in rows
        ]
    )
