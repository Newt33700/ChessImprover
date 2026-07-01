"""Validation + SRS pour le répertoire d'ouvertures (EPIC 9, US 9.1/9.2)."""

from __future__ import annotations

from typing import List

import chess

#: Calendrier SM-2 initial d'une ligne fraîchement ajoutée (aligné sur
#: `domain.srs_engine.create_card` : ef=2.5, interval=1 jour).
DEFAULT_EASE_FACTOR = 2.5
DEFAULT_INTERVAL_DAYS = 1


def validate_move_sequence(moves: List[str]) -> bool:
    """Vérifie qu'une séquence de coups SAN est légale depuis la position
    initiale, coup après coup. Jamais une confiance aveugle au client :
    une ligne invalide ne doit pas pouvoir être enregistrée.
    """
    if not moves:
        return False
    board = chess.Board()
    for san in moves:
        try:
            move = board.parse_san(san)
        except ValueError:
            return False
        board.push(move)
    return True


def infer_quality(mistake_count: int) -> int:
    """Déduit une qualité SM-2 (0-5) du nombre d'erreurs commises pendant la
    révision (US 9.2) — pas de notation manuelle, pour rester ludique.
    """
    if mistake_count <= 0:
        return 5
    if mistake_count == 1:
        return 3
    return 1
