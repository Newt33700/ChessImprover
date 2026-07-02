"""Mode Tactical Sprint — chrono serveur + scoring (EPIC 12, US 11.1/11.2).

Anti-triche : la durée autorisée est vérifiée en comparant l'horloge serveur
(``started_at`` vs ``now()``) à chaque tentative, jamais un temps "écoulé"
déclaré par le client. Pas de blocage ``asyncio.sleep`` : comme le reste de
l'API, le backend est stateless entre requêtes — la fenêtre de validité est
recalculée à la volée à partir des horodatages persistés, ce qui donne la
même garantie anti-triche qu'un minuteur serveur bloquant sans en payer le
coût (un `asyncio.sleep` par sprint actif ne passerait pas à l'échelle).

Module PUR (les horloges sont injectées par l'appelant, jamais lues ici).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

#: Durée d'un sprint, en secondes (fixe pour l'instant — cf. §10 backlog
#: pour une difficulté configurable).
SPRINT_DURATION_SECONDS: int = 60

#: Points accordés par problème résolu (MVP : pas de bonus de vitesse).
POINTS_PER_SOLVE: int = 10


def elapsed_seconds(started_at: datetime, now: datetime) -> float:
    """Secondes écoulées depuis le début du sprint (horloge serveur, jamais négatif)."""
    return max(0.0, (now - started_at).total_seconds())


def is_sprint_active(
    started_at: datetime, now: datetime, duration_seconds: int = SPRINT_DURATION_SECONDS
) -> bool:
    """Vrai si le sprint est encore dans sa fenêtre de temps autorisée."""
    return elapsed_seconds(started_at, now) <= duration_seconds


def compute_score(problems_solved_count: int) -> int:
    """Score total — points fixes par problème résolu (MVP)."""
    return problems_solved_count * POINTS_PER_SOLVE


def record_ghost_move(
    moves: List[Dict[str, Any]], problem_id: str, move_san: str, elapsed_ms: int
) -> List[Dict[str, Any]]:
    """Ajoute un coup résolu à la séquence de replay Ghost (US 11.2).

    Séquence simple ``{problem_id, move, elapsed_ms}`` — suffisante pour
    rejouer les coups sur le board via `board_manager.js` (cf. recommandation
    PO : « pas besoin de synchronisation WebSocket complexe »), pas de PGN
    littéral nécessaire puisque chaque coup référence sa propre position de
    départ (`problem_id` -> FEN, déjà connu du store `tactical_problems`).
    """
    return moves + [{"problem_id": problem_id, "move": move_san, "elapsed_ms": elapsed_ms}]
