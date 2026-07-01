"""Contrats de données du domaine Chess Improver.

Pydantic v1 est utilisé (compatible Python 3.9 sans __future__ annotations).
Ces modèles sont purs et sérialisables ; aucun comportement métier ici.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


# ---------------------------------------------------------------------------
# Énumérations
# ---------------------------------------------------------------------------

class Classification(str, Enum):
    """Classification qualitative d'un coup, alignée avec EloEngine.classify (JS)."""
    BRILLIANT = "brilliant"
    EXCELLENT = "excellent"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


class GameResult(str, Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    IN_PROGRESS = "in_progress"


class TimeClass(str, Enum):
    RAPID = "rapid"
    BLITZ = "blitz"
    BULLET = "bullet"
    DAILY = "daily"


class BoardMode(str, Enum):
    REVIEW = "review"
    EXERCISE = "exercise"
    GHOST = "ghost"


class Phase(str, Enum):
    """Phase de jeu détectée (US 2.1)."""
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"


# ---------------------------------------------------------------------------
# Analyse d'un coup
# ---------------------------------------------------------------------------

class MoveEvaluation(BaseModel):
    """Résultat de l'analyse d'un coup individuel."""
    move_san: str = Field(..., description="Notation SAN du coup")
    evaluation: float = Field(0.0, description="Évaluation Stockfish en centipions")
    classification: Classification = Field(Classification.GOOD, description="Catégorie du coup")
    accuracy_score: float = Field(100.0, ge=0.0, le=100.0, description="Score de précision 0-100")
    cp_loss: float = Field(0.0, ge=0.0, description="Perte en centipions vs meilleur coup")
    fen: Optional[str] = Field(None, description="FEN après le coup")


# ---------------------------------------------------------------------------
# Analyse d'une partie
# ---------------------------------------------------------------------------

class GameAnalysis(BaseModel):
    """Résultat complet de l'analyse d'une partie."""
    game_id: str = Field(..., description="Identifiant unique de la partie")
    accuracy: float = Field(0.0, ge=0.0, le=100.0, description="Précision globale 0-100")
    estimated_elo: int = Field(1000, ge=400, le=2800, description="Elo de performance estimé")
    moves: List[MoveEvaluation] = Field(default_factory=list)
    blunders_count: int = Field(0, ge=0)
    missed_forks_count: int = Field(0, ge=0)
    time_panic_count: int = Field(0, ge=0)
    opponent_elo: int = Field(1000, ge=0)


# ---------------------------------------------------------------------------
# Dashboard agrégé
# ---------------------------------------------------------------------------

class GlobalDashboard(BaseModel):
    """Vue agrégée des statistiques du joueur."""
    total_games: int = Field(0, ge=0)
    average_accuracy: float = Field(0.0, ge=0.0, le=100.0)
    total_blunders: int = Field(0, ge=0)
    total_missed_forks: int = Field(0, ge=0)
    total_time_panics: int = Field(0, ge=0)
    white_ratio: float = Field(0.5, ge=0.0, le=1.0)
    black_ratio: float = Field(0.5, ge=0.0, le=1.0)
    current_streak: int = Field(0, ge=0)
    total_xp: int = Field(0, ge=0)


# ---------------------------------------------------------------------------
# Carte SRS (répétition espacée SM-2)
# ---------------------------------------------------------------------------

class SRSCard(BaseModel):
    """Carte de répétition espacée (algorithme SuperMemo-2)."""
    id: str = Field(..., description="Identifiant unique de la carte")
    fen: str = Field(..., description="Position FEN de l'exercice")
    solution: str = Field(..., description="Coup SAN correct")
    ef: float = Field(2.5, ge=1.3, description="Facteur d'facilité (Easiness Factor)")
    interval: int = Field(1, ge=1, description="Interval en jours avant prochaine révision")
    reps: int = Field(0, ge=0, description="Nombre de répétitions réussies")
    due: str = Field(..., description="Date ISO de la prochaine révision (YYYY-MM-DD)")


# ---------------------------------------------------------------------------
# Requêtes / Réponses API
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Corps d'une demande d'analyse de PGN."""
    pgn: str = Field(..., min_length=10, description="Texte PGN complet")
    opponent_elo: Optional[int] = Field(None, ge=0, le=4000)


class ReviewRequest(BaseModel):
    """Demande de révision d'une carte SRS."""
    card_id: str = Field(...)
    quality: int = Field(..., ge=0, le=5, description="Qualité de la réponse SM-2 (0-5)")


class ExerciseResult(BaseModel):
    """Résultat d'un exercice tactique."""
    card_id: str
    correct: bool
    played_move: str
    solution_move: str


# ---------------------------------------------------------------------------
# Auth & Sync (US 7 / US 6.1)
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserCreate(BaseModel):
    """Demande d'inscription."""
    email: str = Field(..., min_length=5, description="Adresse email")
    username: str = Field(..., min_length=2, max_length=32, description="Pseudo unique")
    password: str = Field(..., min_length=6, description="Mot de passe (min 6 caractères)")

    @validator("email")
    def _validate_email_format(cls, v: str) -> str:  # noqa: N805
        if not _EMAIL_RE.match(v):
            raise ValueError("Adresse email invalide")
        return v


class UserLogin(BaseModel):
    """Demande de connexion."""
    email: str = Field(...)
    password: str = Field(...)


_CHESS_USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,25}$")


class ChessUsernameUpdate(BaseModel):
    """US 6.3 — Liaison/déliaison du pseudo Chess.com au profil."""
    chess_username: str = Field(..., max_length=25, description="Pseudo Chess.com (vide pour délier)")

    @validator("chess_username")
    def _validate_chess_username_format(cls, v: str) -> str:  # noqa: N805
        v = v.strip()
        if v and not _CHESS_USERNAME_RE.match(v):
            raise ValueError(
                "Pseudo Chess.com invalide (3 à 25 caractères alphanumériques, '_' ou '-')"
            )
        return v


class UserProfile(BaseModel):
    """Profil utilisateur public."""
    id: str
    email: str
    username: str
    chess_username: Optional[str] = Field(
        None, description="Pseudo Chess.com lié (US 6.3), distinct du username de connexion"
    )


class AuthResponse(BaseModel):
    """Réponse d'authentification avec JWT."""
    token: str
    user: UserProfile


class SyncRequest(BaseModel):
    """Données à synchroniser vers le serveur (stratégie Client Wins)."""
    games: List[Dict[str, Any]] = Field(default_factory=list)
    srs_cards: List[Dict[str, Any]] = Field(default_factory=list)


class SyncResponse(BaseModel):
    """Données fusionnées retournées par le serveur."""
    games: List[Dict[str, Any]] = Field(default_factory=list)
    srs_cards: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# EPIC 1 — Ingestion async & persistance (US 1.1 / 1.2)
# ---------------------------------------------------------------------------

class GameStatus(str, Enum):
    """Statut d'analyse d'une partie."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeGamesRequest(BaseModel):
    """Demande d'analyse asynchrone (US 1.1) — PGN ou liste d'IDs de parties.

    Pas de champ ``user_id`` : le propriétaire est dérivé du JWT (US 6.4),
    jamais d'une valeur fournie par le client.
    """
    pgn: Optional[str] = Field(None, description="PGN d'une partie à analyser")
    game_ids: Optional[List[str]] = Field(None, description="IDs de parties déjà persistées à (ré)analyser")
    user_color: str = Field("white", description="Couleur du joueur analysé (white|black)")
    time_control: Optional[str] = Field(None, description="Cadence Chess.com (ex. '600', '180+2')")
    evals: Optional[Dict[str, List[List[Any]]]] = Field(
        None,
        description="Évaluations multipv par FEN : {fen: [[uci, score_cp, is_mate, mate_in], ...]}",
    )


class AnalyzeAcceptedItem(BaseModel):
    """Accusé de prise en charge d'une partie."""
    game_id: str
    status: GameStatus = GameStatus.PROCESSING


class AnalyzeAccepted(BaseModel):
    """Réponse 202 de POST /api/v1/games/analyze."""
    accepted: List[AnalyzeAcceptedItem] = Field(default_factory=list)


class GameMoveRecord(BaseModel):
    """Métriques persistées d'un coup (US 1.2)."""
    move_number: int
    color: str
    move_san: str
    eval_before: Optional[int] = None
    eval_after: Optional[int] = None
    score_cp: Optional[int] = None
    cpl: Optional[int] = None
    is_mate: bool = False
    mate_in: Optional[int] = None
    phase: Phase = Phase.MIDDLEGAME
    position_type: str = "neutral"


class GameRecord(BaseModel):
    """Ligne de la table `games`."""
    id: str
    user_id: Optional[str] = None
    pgn: str
    time_control: Optional[str] = None
    user_color: str = "white"
    result: Optional[str] = None
    status: GameStatus = GameStatus.PROCESSING
    created_at: str
