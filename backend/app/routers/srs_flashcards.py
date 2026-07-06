"""Le Cimetière des Erreurs — flashcards SRS (EPIC 20, US 20.1/20.2).

* ``GET  /api/v1/flashcards``             — toutes les flashcards (le « cimetière »).
* ``GET  /api/v1/flashcards/due``         — flashcards à réviser aujourd'hui (Recall Training).
* ``POST /api/v1/flashcards/{id}/review`` — soumet une tentative (qualité déduite automatiquement).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import FlashcardPublic, FlashcardReviewRequest, FlashcardReviewResult
from app.domain.srs_engine import infer_quality, sm2_schedule
from app.domain.tactics import is_correct_move
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/flashcards", tags=["flashcards"])


def _to_public(card: dict) -> FlashcardPublic:
    return FlashcardPublic(
        id=card["id"],
        fen=card["fen"],
        due_date=card["due_date"],
        ease_factor=card["ease_factor"],
        interval_days=card["interval_days"],
        repetitions=card["repetitions"],
    )


@router.get("", response_model=List[FlashcardPublic])
async def list_flashcards(user_id: str = Depends(get_current_user_id)) -> List[FlashcardPublic]:
    """Le Cimetière des Erreurs complet (US 20.1) — jamais la solution avant tentative."""
    return [_to_public(c) for c in db_client.get_flashcards(user_id)]


@router.get("/due", response_model=List[FlashcardPublic])
async def due_flashcards(user_id: str = Depends(get_current_user_id)) -> List[FlashcardPublic]:
    """Flashcards dont l'échéance de révision est atteinte (US 20.2, Recall Training)."""
    today = datetime.now(timezone.utc).date().isoformat()
    return [_to_public(c) for c in db_client.get_due_flashcards(user_id, today)]


@router.post("/{card_id}/review", response_model=FlashcardReviewResult)
async def review_flashcard(
    card_id: str, body: FlashcardReviewRequest, user_id: str = Depends(get_current_user_id),
) -> FlashcardReviewResult:
    """Rappel actif (US 20.2) : validation du coup exclusivement serveur (jamais
    de confiance aveugle au client). La qualité SM-2 est déduite automatiquement
    du résultat (succès/échec) via ``infer_quality`` — même mécanisme que la
    révision du répertoire d'ouvertures (EPIC 9) : pas de notation manuelle,
    pour rester ludique.
    """
    card = db_client.get_flashcard(card_id)
    if card is None or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Flashcard introuvable.")

    success = is_correct_move(card["fen"], card["solution"], body.move)
    # `infer_quality` distingue 3 paliers pour une révision à *plusieurs* coups
    # (répertoire d'ouvertures, EPIC 9) : 0 erreur -> 5, 1 erreur -> 3 (crédit
    # partiel), 2+ -> 1 (reset). Un rappel de flashcard est une tentative
    # unique : un échec doit toujours réinitialiser le calendrier (pas de
    # crédit partiel), d'où le mapping sur 2 « erreurs » plutôt que 1.
    quality = infer_quality(0 if success else 2)
    today = datetime.now(timezone.utc).date()
    schedule = sm2_schedule(
        card["ease_factor"], card["interval_days"], card["repetitions"], quality, today
    )
    updated = db_client.update_flashcard_schedule(
        card_id,
        schedule["ease_factor"],
        schedule["interval"],
        schedule["repetitions"],
        schedule["due_date"].isoformat(),
    )
    return FlashcardReviewResult(
        success=success,
        solution=card["solution"],
        ease_factor=updated["ease_factor"],
        interval_days=updated["interval_days"],
        repetitions=updated["repetitions"],
        due_date=updated["due_date"],
    )
