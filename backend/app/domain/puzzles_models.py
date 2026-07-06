"""Schémas du catalogue de puzzles Lichess (EPIC 37, US 37.1).

Note technique : le reste du backend est figé en Pydantic v1
(``pydantic>=1.10,<2.0`` — FastAPI plafonné ``<0.112`` pour l'éviter, cf.
``requirements.txt``). Ces schémas suivent donc la même syntaxe v1
(``BaseModel``/``@validator``) pour rester cohérents avec ``domain/models.py``
plutôt que de figer une exception isolée à deux fichiers de distance.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class LichessTheme(str, Enum):
    """Thèmes tactiques Lichess utilisables pour filtrer le catalogue."""

    MATE_IN_1 = "mateIn1"
    MATE_IN_2 = "mateIn2"
    MATE_IN_3 = "mateIn3"
    MATE_IN_4 = "mateIn4"
    FORK = "fork"
    PIN = "pin"
    SKEWER = "skewer"
    DEFLECTION = "deflection"
    ATTRACTION = "attraction"
    CLEARANCE = "clearance"
    DECOY = "decoy"
    HANGING_PIECE = "hangingPiece"
    TRAPPED_PIECE = "trappedPiece"
    ENDGAME = "endgame"
    OPENING = "opening"
    MIDDLEGAME = "middlegame"


class PuzzleQueryParams(BaseModel):
    """Paramètres de sélection d'un ou plusieurs puzzles (``GET /tactics/random``)."""

    rating_min: int = Field(1000, ge=0, le=3500)
    rating_max: int = Field(1600, ge=0, le=3500)
    theme: Optional[LichessTheme] = None
    limit: int = Field(1, ge=1, le=50)

    @validator("rating_max")
    def _rating_max_gte_min(cls, value: int, values: dict) -> int:
        rating_min = values.get("rating_min")
        if rating_min is not None and value < rating_min:
            raise ValueError("rating_max doit être supérieur ou égal à rating_min")
        return value


class PuzzleResponse(BaseModel):
    """Représentation publique d'un puzzle du catalogue ``lichess_puzzles``."""

    puzzle_id: str
    fen: str
    moves: str
    rating: int
    rating_deviation: int
    popularity: int
    nb_plays: int
    themes: List[str] = Field(default_factory=list)
    game_url: Optional[str] = None
    opening_tags: List[str] = Field(default_factory=list)
