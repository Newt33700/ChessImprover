"""Entraîneur d'Ouvertures — Répertoire personnel + SRS (EPIC 9, US 9.1/9.2).

* ``POST   /api/v1/openings/repertoire``            — ajoute une ligne (validée).
* ``GET    /api/v1/openings/repertoire``             — liste le répertoire complet.
* ``GET    /api/v1/openings/repertoire/due``         — lignes à réviser aujourd'hui.
* ``POST   /api/v1/openings/repertoire/{id}/review`` — soumet une révision (SM-2).
* ``DELETE /api/v1/openings/repertoire/{id}``        — retire une ligne.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import (
    OpeningLineCreate,
    OpeningLinePublic,
    OpeningLineReviewRequest,
    OpeningLineReviewResult,
)
from app.domain.opening_repertoire import infer_quality, validate_move_sequence
from app.domain.srs_engine import sm2_schedule
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/openings/repertoire", tags=["openings"])


def _to_public(line: dict) -> OpeningLinePublic:
    return OpeningLinePublic(
        id=line["id"],
        name=line["name"],
        color=line["color"],
        moves=line["moves"],
        ease_factor=line["ease_factor"],
        interval_days=line["interval_days"],
        repetitions=line["repetitions"],
        due_date=line["due_date"],
    )


@router.post("", response_model=OpeningLinePublic)
async def create_line(
    body: OpeningLineCreate, user_id: str = Depends(get_current_user_id)
) -> OpeningLinePublic:
    """Enregistre une nouvelle ligne — jamais de confiance aveugle au client :
    la séquence est rejouée coup par coup pour vérifier sa légalité."""
    if not validate_move_sequence(body.moves):
        raise HTTPException(status_code=422, detail="Séquence de coups invalide.")
    line = db_client.create_opening_line(user_id, body.name, body.color, body.moves)
    return _to_public(line)


@router.get("", response_model=List[OpeningLinePublic])
async def list_lines(user_id: str = Depends(get_current_user_id)) -> List[OpeningLinePublic]:
    return [_to_public(line) for line in db_client.get_opening_lines(user_id)]


@router.get("/due", response_model=List[OpeningLinePublic])
async def due_lines(user_id: str = Depends(get_current_user_id)) -> List[OpeningLinePublic]:
    today = datetime.now(timezone.utc).date().isoformat()
    return [_to_public(line) for line in db_client.get_due_opening_lines(user_id, today)]


@router.post("/{line_id}/review", response_model=OpeningLineReviewResult)
async def review_line(
    line_id: str, body: OpeningLineReviewRequest, user_id: str = Depends(get_current_user_id),
) -> OpeningLineReviewResult:
    """Reprogramme une ligne selon SM-2. La qualité (0-5) est déduite du
    nombre d'erreurs commises pendant la révision (US 9.2) — pas de
    notation manuelle, pour rester ludique.
    """
    line = db_client.get_opening_line(line_id)
    if line is None or line["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Ligne introuvable.")

    quality = infer_quality(body.mistake_count)
    today = datetime.now(timezone.utc).date()
    schedule = sm2_schedule(
        line["ease_factor"], line["interval_days"], line["repetitions"], quality, today
    )
    updated = db_client.update_opening_line_schedule(
        line_id,
        schedule["ease_factor"],
        schedule["interval"],
        schedule["repetitions"],
        schedule["due_date"].isoformat(),
    )
    return OpeningLineReviewResult(
        id=line_id,
        ease_factor=updated["ease_factor"],
        interval_days=updated["interval_days"],
        repetitions=updated["repetitions"],
        due_date=updated["due_date"],
    )


@router.delete("/{line_id}")
async def delete_line(line_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    deleted = db_client.delete_opening_line(line_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ligne introuvable.")
    return {"deleted": True}
