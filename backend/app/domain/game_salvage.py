"""Moteur de « Réparation de Partie » — Replay Correction (EPIC 15, US 14.1/14.2
du backlog PO fourni, renumérotées EPIC 15 pour éviter la collision avec les
EPIC déjà enregistrés dans ce dépôt, cf. UserStory.md).

Identifie automatiquement le « pivot de défaite » : le premier coup JOUÉ PAR
LE JOUEUR (pas l'adversaire) où la perte de centipions atteint le seuil de
gaffe déjà défini par ``stats_aggregator.BLUNDER_CPL`` (200), puis reconstruit
la position exacte juste AVANT ce coup — pour permettre à l'utilisateur de
rejouer un autre coup à la place de la gaffe (sandbox, US 15.2).

Module PUR (hormis la relecture du PGN via python-chess, sans appel moteur) :
``find_defeat_pivot`` opère sur les enregistrements ``game_moves`` déjà
produits par ``analysis_pipeline.analyze_pgn`` (pas de recalcul d'évaluation).
"""

from __future__ import annotations

import io as _io
from typing import Any, Dict, List, Optional

import chess
import chess.pgn

from app.domain.stats_aggregator import BLUNDER_CPL


def find_defeat_pivot(moves: List[Dict[str, Any]], user_color: str) -> Optional[int]:
    """Index (0-based, ligne principale) du premier coup DU JOUEUR dont la
    perte de centipions atteint le seuil de gaffe (``BLUNDER_CPL`` = 200).

    ``None`` si aucun coup du joueur n'atteint ce seuil, ou si la partie n'a
    pas été évaluée par un moteur (``cpl`` alors toujours ``None``).
    """
    for i, move in enumerate(moves):
        if move.get("color") != user_color:
            continue
        cpl = move.get("cpl")
        if cpl is not None and cpl >= BLUNDER_CPL:
            return i
    return None


def reconstruct_position_before_move(pgn: str, move_index: int) -> Optional[Dict[str, Any]]:
    """Position juste AVANT que le coup ``move_index`` (0-based) ne soit joué.

    Renvoie ``{"fen", "side_to_move", "move_number"}`` — le joueur peut alors
    rejouer un autre coup que la gaffe historique à partir de cette FEN.
    ``None`` si le PGN est invalide ou que ``move_index`` est hors bornes.
    """
    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return None
    if game is None:
        return None

    board = game.board()
    moves = list(game.mainline_moves())
    if move_index < 0 or move_index >= len(moves):
        return None

    for move in moves[:move_index]:
        board.push(move)

    return {
        "fen": board.fen(),
        "side_to_move": "white" if board.turn == chess.WHITE else "black",
        "move_number": board.fullmove_number,
    }
