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
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="EPIC 18 — préférences de personnalisation (thème pièces/plateau), JSONB libre",
    )


class UserSettingsUpdate(BaseModel):
    """EPIC 18 (US 18.2/18.3) — Remplace les préférences de personnalisation du profil.

    Volontairement permissif (``Dict[str, Any]``, pas de schéma de clés figé) :
    l'objectif explicite (cf. UserStory.md) est de pouvoir ajouter de nouveaux
    réglages (sons, animations, taille d'échiquier…) sans jamais modifier ce
    contrat ni le schéma de la colonne JSONB ``profiles.settings``. La
    résilience à une valeur invalide (ex. un nom de thème inconnu) est de la
    responsabilité du frontend (``ThemeService``), qui retombe toujours sur un
    thème par défaut plutôt que de planter l'échiquier.
    """
    settings: Dict[str, Any] = Field(default_factory=dict)


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


class GameStatusUpdate(BaseModel):
    """US 7.3 — Bascule le statut « déjà étudiée » d'une partie."""
    is_reviewed: bool = Field(..., description="Vrai si la partie a déjà été étudiée")


class GamesSyncResult(BaseModel):
    """EPIC 23 — Réponse 202 de POST /api/v1/games/sync (sync à la connexion).

    ``fetched``  : parties récupérées depuis Chess.com ;
    ``queued``   : nouvelles analyses lancées en tâche de fond (≤ plafond) ;
    ``skipped``  : parties déjà connues (hash PGN, US 7.2) ;
    ``deferred`` : nouvelles parties au-delà du plafond, différées à la
                   prochaine sync ;
    ``requeued`` : analyses orphelines (``processing`` trop ancien) relancées.
    """
    fetched: int = 0
    queued: int = 0
    skipped: int = 0
    deferred: int = 0
    requeued: int = 0


# ---------------------------------------------------------------------------
# Coaching Tactique Adaptatif (US 8.1, EPIC 8)
# ---------------------------------------------------------------------------

class TacticalProblemPublic(BaseModel):
    """Problème tactique exposé au client — jamais `solution` avant tentative."""
    id: str
    fen: str
    category: str
    difficulty_elo: int


class TacticalAttemptRequest(BaseModel):
    """Coup joué par l'utilisateur pour résoudre un problème."""
    problem_id: str
    move: str = Field(..., min_length=2, description="Coup joué en notation SAN")
    time_taken: Optional[float] = Field(
        None, ge=0, description="Secondes écoulées pour résoudre (US 8.4)"
    )


class TacticalAttemptResult(BaseModel):
    """Résultat d'une tentative : révèle la solution après coup."""
    success: bool
    new_elo: int
    solution: str
    streak: int = Field(0, description="Problèmes résolus d'affilée aujourd'hui (US 8.4)")


class TacticalThemeStats(BaseModel):
    """Taux de réussite pour une catégorie tactique (US 8.4)."""
    category: str
    attempts: int
    successes: int
    success_rate: float


class TacticalStatsResponse(BaseModel):
    """Historique agrégé des tentatives tactiques de l'utilisateur (US 8.4)."""
    by_theme: List[TacticalThemeStats]
    streak: int


# ---------------------------------------------------------------------------
# Entraîneur de Finales Essentielles (EPIC 10, fonctionnalité bonus)
# ---------------------------------------------------------------------------

class EndgameProblemPublic(BaseModel):
    """Position de finale exposée au client — jamais `solution` avant tentative."""
    id: str
    fen: str
    category: str
    difficulty_elo: int


class EndgameAttemptRequest(BaseModel):
    """Coup joué par l'utilisateur pour résoudre une position de finale."""
    problem_id: str
    move: str = Field(..., min_length=2, description="Coup joué en notation SAN")


class EndgameAttemptResult(BaseModel):
    """Résultat d'une tentative : révèle la solution après coup."""
    success: bool
    new_elo: int
    solution: str


# ---------------------------------------------------------------------------
# Entraîneur d'Ouvertures — Répertoire + SRS (EPIC 9, fonctionnalité bonus)
# ---------------------------------------------------------------------------

class OpeningLineCreate(BaseModel):
    """Nouvelle ligne de répertoire soumise par l'utilisateur."""
    name: str = Field(..., min_length=1, max_length=80)
    color: str = Field(..., description="'white' ou 'black'")
    moves: List[str] = Field(..., min_items=1, description="Coups en notation SAN, dans l'ordre")

    @validator("color")
    def _validate_color(cls, value: str) -> str:  # noqa: N805 - validator Pydantic
        if value not in ("white", "black"):
            raise ValueError("color doit être 'white' ou 'black'")
        return value


class OpeningLinePublic(BaseModel):
    """Ligne de répertoire telle qu'exposée au client."""
    id: str
    name: str
    color: str
    moves: List[str]
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: str


class OpeningLineReviewRequest(BaseModel):
    """Résultat d'une session de révision (US 9.2) — qualité déjà déduite
    automatiquement côté frontend du nombre d'erreurs commises."""
    mistake_count: int = Field(..., ge=0)


class OpeningLineReviewResult(BaseModel):
    """Nouveau calendrier SM-2 après une révision."""
    id: str
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: str


# ---------------------------------------------------------------------------
# Analyse Comportementale — Profil d'erreurs (EPIC 11, US 9.1/9.2)
# ---------------------------------------------------------------------------

class ErrorProfileEntry(BaseModel):
    """Score de fréquence d'un type d'erreur pour l'utilisateur authentifié."""
    error_type: str
    frequency_score: float
    is_recurring: bool = Field(False, description="frequency_score > seuil (70)")
    last_observed: Optional[str] = None


class ErrorProfileResponse(BaseModel):
    """Profil d'erreurs complet (un `ErrorProfileEntry` par type déjà observé)."""
    profiles: List[ErrorProfileEntry]


# ---------------------------------------------------------------------------
# Mode Tactical Sprint (EPIC 12, US 11.1/11.2)
# ---------------------------------------------------------------------------

class SprintStartResponse(BaseModel):
    """Sprint démarré : identifiant, durée autorisée et premier problème."""
    sprint_id: str
    duration_seconds: int
    problem: TacticalProblemPublic


class SprintAttemptRequest(BaseModel):
    """Coup joué pour le problème en cours dans un sprint."""
    problem_id: str
    move: str = Field(..., min_length=2, description="Coup joué en notation SAN")


class SprintAttemptResponse(BaseModel):
    """Résultat d'une tentative de sprint : score courant + problème suivant (si temps restant)."""
    success: bool
    score: int
    problems_solved_count: int
    time_remaining: float
    sprint_active: bool
    next_problem: Optional[TacticalProblemPublic] = None


class SprintFinishResponse(BaseModel):
    """Résultat final d'un sprint (temps écoulé ou arrêt volontaire)."""
    sprint_id: str
    score: int
    problems_solved_count: int
    duration_seconds: int


class GhostMoveEntry(BaseModel):
    """Un coup de la séquence de replay Ghost (US 11.2)."""
    problem_id: str
    move: str
    elapsed_ms: int


class GhostReplayResponse(BaseModel):
    """Meilleur sprint terminé (toutes utilisateurs confondus) à rejouer en surimpression."""
    available: bool
    score: Optional[int] = None
    moves: List[GhostMoveEntry] = Field(default_factory=list)


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
    fen: Optional[str] = Field(None, description="FEN avant le coup (EPIC 19/20)")
    best_move_san: Optional[str] = Field(None, description="Meilleur coup SAN, jamais exposé avant tentative (US 20.1)")
    time_spent_seconds: Optional[float] = Field(None, description="Temps de réflexion du joueur (EPIC 19)")


class FlashcardPublic(BaseModel):
    """Flashcard SRS auto-générée depuis une gaffe (EPIC 20, US 20.1) — jamais
    ``solution`` avant tentative, même politique que les problèmes tactiques."""
    id: str
    fen: str
    due_date: str
    ease_factor: float
    interval_days: int
    repetitions: int


class FlashcardReviewRequest(BaseModel):
    """Coup tenté pour se rappeler la solution d'une flashcard (US 20.2)."""
    move: str = Field(..., min_length=2, description="Coup joué en notation SAN")


class FlashcardReviewResult(BaseModel):
    """Résultat d'une révision : révèle la solution + nouveau calendrier SM-2."""
    success: bool
    solution: str
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: str


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
