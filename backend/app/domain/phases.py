"""Segmentation des phases de jeu — US 2.1.

Découpe une partie d'échecs en trois phases : **Ouverture**, **Milieu de jeu**
et **Finale**, afin d'isoler les performances de l'utilisateur par phase.

Règles métier (DoD US 2.1) :

* **Ouverture** : du coup 1 jusqu'à ce que la partie sorte de l'arbre
  d'ouvertures, avec une limite stricte au coup 15. La détection de sortie de
  livre est injectable (``in_book``) ; sans livre fourni, l'ouverture s'arrête
  à la limite dure (coup 15 = 30 demi-coups).
* **Finale** : déclenchée dès que, pour les deux camps cumulés :
    - Pas de Dames ET matériel total ≤ 16 points (Rois exclus ;
      Pion=1, Cavalier=3, Fou=3, Tour=5, Dame=9), **OU**
    - présence de Dames mais chaque camp a au maximum une seule pièce
      lourde/mineure (Tour/Fou/Cavalier) en plus de la Dame.
  Une fois déclenchée, la finale est « verrouillée » (latch) jusqu'à la fin.
* **Milieu de jeu** : tout ce qui est chronologiquement entre la fin de
  l'ouverture et le début de la finale.

Module PUR : ``python-chess`` sert uniquement à manipuler les positions.
"""

from __future__ import annotations

import io as _io
from typing import Callable, List, Optional

import chess
import chess.pgn

from app.domain.models import Phase

# ---------------------------------------------------------------------------
# Constantes (règles métier US 2.1)
# ---------------------------------------------------------------------------

#: Valeur matérielle en *points* (Rois exclus) — base de la règle de finale.
PHASE_PIECE_POINTS: dict = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}

#: Limite dure de l'ouverture : coup 15 → 30 demi-coups (plies).
MAX_OPENING_MOVE: int = 15
MAX_OPENING_PLY: int = MAX_OPENING_MOVE * 2

#: Seuil de matériel (points, Rois exclus) pour la finale sans Dames.
ENDGAME_MATERIAL_THRESHOLD: int = 16

#: Pièces « lourdes/mineures » comptées dans la 2ᵉ règle de finale.
_MINOR_HEAVY: tuple = (chess.ROOK, chess.BISHOP, chess.KNIGHT)

#: Signature d'un détecteur de livre d'ouvertures : ``in_book(board) -> bool``.
BookProbe = Callable[[chess.Board], bool]


# ---------------------------------------------------------------------------
# Matériel
# ---------------------------------------------------------------------------

def total_material_points(board: chess.Board) -> int:
    """Somme des valeurs matérielles des deux camps (Rois exclus, Pions inclus).

    Parameters
    ----------
    board : chess.Board

    Returns
    -------
    int
        Total des points (Pion=1, Cavalier=3, Fou=3, Tour=5, Dame=9).
    """
    total = 0
    for piece_type, value in PHASE_PIECE_POINTS.items():
        total += value * len(board.pieces(piece_type, chess.WHITE))
        total += value * len(board.pieces(piece_type, chess.BLACK))
    return total


def _minor_heavy_count(board: chess.Board, color: chess.Color) -> int:
    """Nombre de pièces lourdes/mineures (Tour/Fou/Cavalier) d'un camp."""
    return sum(len(board.pieces(pt, color)) for pt in _MINOR_HEAVY)


def is_endgame(board: chess.Board) -> bool:
    """Vrai si la position satisfait les conditions matérielles de finale.

    Voir les règles métier en tête de module (DoD US 2.1).
    """
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(
        board.pieces(chess.QUEEN, chess.BLACK)
    )

    # Règle 1 : aucune Dame ET matériel total ≤ 16 points.
    if queens == 0:
        return total_material_points(board) <= ENDGAME_MATERIAL_THRESHOLD

    # Règle 2 : Dames présentes, mais ≤ 1 pièce lourde/mineure par camp.
    return (
        _minor_heavy_count(board, chess.WHITE) <= 1
        and _minor_heavy_count(board, chess.BLACK) <= 1
    )


# ---------------------------------------------------------------------------
# Frontière d'ouverture
# ---------------------------------------------------------------------------

def opening_end_ply(
    board: chess.Board,
    moves: List[chess.Move],
    in_book: Optional[BookProbe] = None,
) -> int:
    """Indice (0-based) du premier demi-coup HORS ouverture.

    L'ouverture couvre les plies ``[0, opening_end_ply[``. Elle s'arrête au
    premier coup joué depuis une position hors livre, et au plus tard à
    ``MAX_OPENING_PLY`` (coup 15).

    Parameters
    ----------
    board : chess.Board
        Position de départ (avant le 1ᵉʳ coup) ; non mutée.
    moves : list[chess.Move]
        Coups de la ligne principale.
    in_book : callable, optional
        ``in_book(board) -> bool`` testant si la position (avant le coup) est
        encore dans le livre. Sans détecteur, seule la limite dure s'applique.

    Returns
    -------
    int
        Nombre de demi-coups appartenant à l'ouverture (borné à MAX_OPENING_PLY
        et au nombre de coups disponibles).
    """
    hard_cap = min(MAX_OPENING_PLY, len(moves))
    if in_book is None:
        return hard_cap

    probe = board.copy(stack=False)
    for ply in range(hard_cap):
        if not in_book(probe):
            return ply
        probe.push(moves[ply])
    return hard_cap


# ---------------------------------------------------------------------------
# Segmentation complète
# ---------------------------------------------------------------------------

def segment_phases(
    board: chess.Board,
    moves: List[chess.Move],
    in_book: Optional[BookProbe] = None,
) -> List[Phase]:
    """Phase de chaque demi-coup d'une partie.

    La phase est déterminée sur la position **avant** chaque coup. La finale est
    verrouillée : dès qu'une position remplit ``is_endgame``, tous les coups
    suivants sont en finale.

    Parameters
    ----------
    board : chess.Board
        Position de départ (non mutée).
    moves : list[chess.Move]
        Coups de la ligne principale.
    in_book : callable, optional
        Détecteur de livre (voir ``opening_end_ply``).

    Returns
    -------
    list[Phase]
        Une phase par demi-coup, dans l'ordre de jeu.
    """
    end_opening = opening_end_ply(board, moves, in_book)
    phases: List[Phase] = []
    cursor = board.copy(stack=False)
    endgame_latched = False

    for ply, move in enumerate(moves):
        if not endgame_latched and ply >= end_opening and is_endgame(cursor):
            endgame_latched = True

        if ply < end_opening:
            phases.append(Phase.OPENING)
        elif endgame_latched:
            phases.append(Phase.ENDGAME)
        else:
            phases.append(Phase.MIDDLEGAME)

        cursor.push(move)

    return phases


def segment_pgn(pgn: str, in_book: Optional[BookProbe] = None) -> List[Phase]:
    """Segmente un PGN en phases (ligne principale).

    Parameters
    ----------
    pgn : str
        Texte PGN complet.
    in_book : callable, optional
        Détecteur de livre d'ouvertures.

    Returns
    -------
    list[Phase]
        Une phase par demi-coup. Liste vide si le PGN est invalide/vide.
    """
    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return []
    if game is None:
        return []

    board = game.board()
    moves = list(game.mainline_moves())
    return segment_phases(board, moves, in_book)
