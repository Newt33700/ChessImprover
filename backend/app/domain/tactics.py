"""Sélection et validation de problèmes tactiques (US 8.1, EPIC 8)."""

from __future__ import annotations

import random
from datetime import date, datetime
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


def compute_daily_streak(attempts: List[Dict[str, Any]], today: date) -> int:
    """US 8.4 — Nombre de problèmes résolus d'affilée aujourd'hui.

    Parcourt les tentatives de la plus récente à la plus ancienne : la série
    s'arrête au premier échec rencontré, ou dès qu'une tentative ne date pas
    d'aujourd'hui (une tentative réussie hier ne prolonge pas la série de
    l'utilisateur qui recommence à zéro ce matin).
    """
    ordered = sorted(attempts, key=lambda a: a["created_at"], reverse=True)
    streak = 0
    for attempt in ordered:
        created_at = attempt["created_at"]
        attempt_date = created_at.date() if isinstance(created_at, datetime) else created_at
        if attempt_date != today or not attempt["success"]:
            break
        streak += 1
    return streak


def compute_stats_by_theme(attempts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """US 8.4 — Taux de réussite par catégorie, calculé depuis l'historique."""
    totals: Dict[str, Dict[str, int]] = {}
    for attempt in attempts:
        bucket = totals.setdefault(attempt["category"], {"attempts": 0, "successes": 0})
        bucket["attempts"] += 1
        if attempt["success"]:
            bucket["successes"] += 1
    return [
        {
            "category": category,
            "attempts": bucket["attempts"],
            "successes": bucket["successes"],
            "success_rate": bucket["successes"] / bucket["attempts"],
        }
        for category, bucket in sorted(totals.items())
    ]
