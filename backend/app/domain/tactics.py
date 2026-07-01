"""Sélection et validation de problèmes tactiques (US 8.1, EPIC 8)."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

import chess

#: Catégories/thèmes valides (US 8.2). "Aléatoire" côté UI = theme_id omis.
TACTICAL_THEMES = ("mate_in_1", "mate_in_2", "hanging_piece")


def is_correct_move(fen: str, solution_san: str, played_san: str) -> bool:
    """Compare le coup joué à la solution attendue sur cette position.

    Compare des objets ``chess.Move`` (python-chess), pas des chaînes
    brutes : des annotations différentes d'un même coup (ex. ``Ra8`` vs
    ``Ra8#``) sont ainsi correctement reconnues comme équivalentes. Toute
    notation invalide ou illégale sur cette position est un échec.
    """
    board = chess.Board(fen)
    try:
        solution_move = board.parse_san(solution_san)
        played_move = board.parse_san(played_san)
    except ValueError:
        return False
    return solution_move == played_move


def select_nearest_problem(
    problems: List[Dict[str, Any]], target_elo: int
) -> Optional[Dict[str, Any]]:
    """Choisit un problème dont la difficulté est la plus proche de ``target_elo``.

    En cas d'égalité entre plusieurs problèmes équidistants, tire au sort
    parmi eux pour éviter de toujours servir le même problème.
    """
    if not problems:
        return None
    best_distance = min(abs(p["difficulty_elo"] - target_elo) for p in problems)
    closest = [p for p in problems if abs(p["difficulty_elo"] - target_elo) == best_distance]
    return random.choice(closest)
