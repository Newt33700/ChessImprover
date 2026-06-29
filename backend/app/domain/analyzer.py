"""Moteur de règles géométriques — analyse PGN sans moteur d'échecs.

Détecte les failles évidentes du débutant à partir du PGN textuel :
  - Blunders (pièces données en 1 coup, non défendues)
  - Fourchettes manquées (pion/cavalier attaquant 2 pièces adverses de
    valeur supérieure, mais non jouées)
  - Zeitnot (panique temporelle : chute > 50 % du temps sur un coup = gaffe)

La bibliothèque ``python-chess`` sert uniquement à manipuler les positions ;
l'analyse elle-même est pure et testable (Clean Architecture : couche domaine).
"""

from __future__ import annotations

import io as _io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import chess
import chess.pgn


# ---------------------------------------------------------------------------
# Structures de sortie
# ---------------------------------------------------------------------------

@dataclass
class GeometricReport:
    """Résultat de l'analyse géométrique d'une partie."""
    blunders_count: int = 0
    missed_forks_count: int = 0
    time_panic_count: int = 0
    blunder_moves: List[str] = field(default_factory=list)
    missed_fork_moves: List[str] = field(default_factory=list)
    time_panic_moves: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constantes internes
# ---------------------------------------------------------------------------

# Valeur matérielle standard des pièces (en centipions).
PIECE_VALUES: dict = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Seuil de chute de temps pour la zeitnot : > 50 % sur un seul coup.
TIME_PANIC_RATIO: float = 0.5

# Regex pour extraire les balises [%clk H:MM:SS] du PGN.
_CLK_PATTERN: re.Pattern = re.compile(r"\[%clk\s+(\d{1,2}):(\d{2}):(\d{2})\]")


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


def extract_comment_clock(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def is_piece_hanging(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(player_color, square)
    return attacked and not defended


def _target_is_high_value(target: chess.Piece, forking_value: int) -> bool:
    """Vrai si une pièce adverse mérite d'être comptée dans une fourchette.

    Le roi compte toujours (force une réponse) ; sinon il faut que la valeur
    matérielle de la cible soit strictement supérieure à celle de la pièce qui
    fourchette (gain matériel potentiel).
    """
    if target.piece_type == chess.KING:
        return True
    return PIECE_VALUES[target.piece_type] > forking_value


def find_fork_moves(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def _read_mainline_clocks(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = game
    while node.variations:
        child = node.variations[0]
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# Alias conservé pour compatibilité avec la spécification historique.
analyze_blunders = analyze_pgn
