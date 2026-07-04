"""Sélection et validation de problèmes tactiques (US 8.1, EPIC 8)."""

from __future__ import annotations

import random
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Union

import chess

#: Catégories/thèmes valides (US 8.2). "Aléatoire" côté UI = theme_id omis.
TACTICAL_THEMES = ("mate_in_1", "mate_in_2", "hanging_piece")


def _parse_move_token(board: chess.Board, token: str) -> Optional[chess.Move]:
    """Interprète ``token`` comme un coup légal sur ``board`` — SAN d'abord
    (solutions historiques), UCI en repli (EPIC 34 : séquences Lichess et
    coups forcés générés programmatiquement). ``None`` si ni l'un ni l'autre
    ne désigne un coup légal — jamais d'exception.
    """
    try:
        return board.parse_san(token)
    except ValueError:
        pass
    try:
        move = chess.Move.from_uci(token)
    except ValueError:
        return None
    return move if move in board.legal_moves else None


def is_correct_move(fen: str, solution: str, played_san: str) -> bool:
    """Compare le coup joué à la solution attendue sur cette position.

    Compare des objets ``chess.Move`` (python-chess), pas des chaînes
    brutes : des annotations différentes d'un même coup (ex. ``Ra8`` vs
    ``Ra8#``) sont ainsi correctement reconnues comme équivalentes. Toute
    notation invalide ou illégale sur cette position est un échec.

    ``solution`` accepte le SAN (historique) ou l'UCI (EPIC 34 : les coups
    Lichess sont fournis en UCI) — cf. ``_parse_move_token``.
    """
    board = chess.Board(fen)
    try:
        played_move = board.parse_san(played_san)
    except ValueError:
        return False
    solution_move = _parse_move_token(board, solution)
    if solution_move is None:
        return False
    return solution_move == played_move


def select_nearest_problem(
    problems: List[Dict[str, Any]],
    target_elo: int,
    exclude_ids: Optional[Sequence[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Choisit un problème dont la difficulté est la plus proche de ``target_elo``.

    En cas d'égalité entre plusieurs problèmes équidistants, tire au sort
    parmi eux pour éviter de toujours servir le même problème.

    ``exclude_ids`` (EPIC 34) écarte les problèmes récemment servis à
    l'utilisateur *avant* de chercher le plus proche — pour varier les
    exercices même quand un unique problème est numériquement le plus
    proche de l'Elo courant (cas fréquent avec un petit pool par catégorie).
    N'exclut jamais la totalité du pool : si le filtre ne laisse plus rien,
    on retombe sur le pool complet plutôt que de renvoyer ``None``.
    """
    if not problems:
        return None
    pool = problems
    if exclude_ids:
        filtered = [p for p in problems if p.get("id") not in exclude_ids]
        pool = filtered or problems
    best_distance = min(abs(p["difficulty_elo"] - target_elo) for p in pool)
    closest = [p for p in pool if abs(p["difficulty_elo"] - target_elo) == best_distance]
    return random.choice(closest)


def advance_tactical_attempt(
    fen: str, remaining: Sequence[str], played_san: str
) -> Dict[str, Any]:
    """EPIC 34 — Fait progresser une séquence solution potentiellement
    multi-coups (ex. mat en 2 : coup du joueur, réplique adverse forcée,
    coup de mat) d'un demi-coup.

    ``remaining`` est la liste des coups encore attendus (SAN ou UCI),
    en commençant par celui du joueur : ``remaining[0]`` est comparé à
    ``played_san`` ; si ``remaining`` compte plus d'un élément, l'élément
    suivant est auto-joué comme réplique adverse forcée (jamais recalculée :
    la ligne est déterministe, fournie par les données du problème).

    Retourne toujours l'une de ces formes (jamais d'exception) :
    - ``{"result": "wrong"}`` — coup incorrect ou séquence déjà épuisée.
    - ``{"result": "correct_partial", "fen", "remaining", "opponent_move"}``
      — coup juste, il reste au moins un coup à trouver après la réplique
      adverse auto-jouée.
    - ``{"result": "correct_complete", "fen"}`` — dernier coup de la
      séquence, position finale (habituellement mat).
    """
    if not remaining:
        return {"result": "wrong"}
    board = chess.Board(fen)
    try:
        played_move = board.parse_san(played_san)
    except ValueError:
        return {"result": "wrong"}
    expected_move = _parse_move_token(board, remaining[0])
    if expected_move is None or expected_move != played_move:
        return {"result": "wrong"}
    board.push(played_move)
    rest = list(remaining[1:])
    if not rest:
        return {"result": "correct_complete", "fen": board.fen()}
    opponent_move = _parse_move_token(board, rest[0])
    if opponent_move is None:
        # Donnée mal formée : ne pas planter, traiter comme terminé sur le
        # dernier coup validé plutôt que de laisser une réplique invalide.
        return {"result": "correct_complete", "fen": board.fen()}
    opponent_san = board.san(opponent_move)
    board.push(opponent_move)
    return {
        "result": "correct_partial",
        "fen": board.fen(),
        "remaining": rest[1:],
        "opponent_move": opponent_san,
    }


def solution_sequence(solution: Union[str, Sequence[str]]) -> List[str]:
    """Normalise le champ ``solution`` d'un problème (SAN unique historique
    ou liste multi-coups EPIC 34) en une liste, pour un traitement uniforme."""
    return list(solution) if isinstance(solution, (list, tuple)) else [solution]


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
