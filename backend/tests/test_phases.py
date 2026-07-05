"""Tests unitaires — segmentation des phases (US 2.1).

Couvre le matériel, la règle de finale (deux branches + bornes), la frontière
d'ouverture (livre injecté + limite dure au coup 15) et la segmentation
complète d'une partie.
"""

from __future__ import annotations

import chess

from app.domain.models import Phase
from app.domain.phases import (
    ENDGAME_MATERIAL_THRESHOLD,
    MAX_OPENING_MOVE,
    MAX_OPENING_PLY,
    PHASE_PIECE_POINTS,
    is_endgame,
    opening_end_ply,
    segment_phases,
    segment_pgn,
    total_material_points,
)


# ===================================================================
# Constantes
# ===================================================================

class TestConstants:
    def test_piece_points_values(self):
        assert PHASE_PIECE_POINTS[chess.PAWN] == 1
        assert PHASE_PIECE_POINTS[chess.KNIGHT] == 3
        assert PHASE_PIECE_POINTS[chess.BISHOP] == 3
        assert PHASE_PIECE_POINTS[chess.ROOK] == 5
        assert PHASE_PIECE_POINTS[chess.QUEEN] == 9

    def test_king_excluded(self):
        assert chess.KING not in PHASE_PIECE_POINTS

    def test_opening_caps(self):
        assert MAX_OPENING_MOVE == 15
        assert MAX_OPENING_PLY == 30

    def test_endgame_threshold(self):
        assert ENDGAME_MATERIAL_THRESHOLD == 16


# ===================================================================
# total_material_points
# ===================================================================

class TestMaterial:
    def test_starting_position(self):
        # 2 × (8×1 + 2×3 + 2×3 + 2×5 + 1×9) = 2 × 39 = 78
        assert total_material_points(chess.Board()) == 78

    def test_kings_only(self):
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        assert total_material_points(board) == 0

    def test_two_rooks(self):
        board = chess.Board("4k2r/8/8/8/8/8/8/R3K3 w - - 0 1")
        assert total_material_points(board) == 10


# ===================================================================
# is_endgame
# ===================================================================

class TestIsEndgame:
    def test_start_is_not_endgame(self):
        assert is_endgame(chess.Board()) is False

    def test_no_queens_below_threshold(self):
        # KR vs KR : 10 ≤ 16, pas de Dame → finale
        board = chess.Board("4k2r/8/8/8/8/8/8/R3K3 w - - 0 1")
        assert is_endgame(board) is True

    def test_no_queens_exactly_threshold(self):
        # KRB vs KRB : (5+3)+(5+3) = 16 → finale (≤ 16)
        board = chess.Board("3bk2r/8/8/8/8/8/8/R1B1K3 w - - 0 1")
        assert total_material_points(board) == 16
        assert is_endgame(board) is True

    def test_no_queens_above_threshold(self):
        # KRB + pion vs KRB : 17 > 16 → pas finale
        board = chess.Board("3bk2r/7p/8/8/8/8/8/R1B1K3 w - - 0 1")
        assert total_material_points(board) == 17
        assert is_endgame(board) is False

    def test_queens_each_side_no_extra(self):
        # KQ vs KQ : Dames présentes, 0 pièce mineure/lourde → finale
        board = chess.Board("4k3/6q1/8/8/8/8/1Q6/4K3 w - - 0 1")
        assert is_endgame(board) is True

    def test_queens_one_extra_each(self):
        # KQR vs KQ : un seul extra par camp max (blanc 1 tour, noir 0) → finale
        board = chess.Board("4k3/6q1/8/8/8/8/1Q6/R3K3 w - - 0 1")
        assert is_endgame(board) is True

    def test_queens_two_extra_one_side(self):
        # KQRN vs KQ : blanc a 2 pièces (Tour + Cavalier) en plus → pas finale
        board = chess.Board("4k3/6q1/8/8/8/8/1Q6/R3K1N1 w - - 0 1")
        assert is_endgame(board) is False

    def test_queens_two_extra_other_side(self):
        # Symétrie : c'est le camp noir qui a 2 extras → pas finale
        board = chess.Board("r3k1n1/6q1/8/8/8/8/1Q6/4K3 w - - 0 1")
        assert is_endgame(board) is False

    def test_queens_one_extra_black_side(self):
        # Symétrie de test_queens_one_extra_each : exactement 1 extra côté
        # noir (borne `<= 1` du camp noir), blanc à 0 → finale.
        board = chess.Board("r3k3/6q1/8/8/8/8/1Q6/4K3 w - - 0 1")
        assert is_endgame(board) is True


# ===================================================================
# opening_end_ply
# ===================================================================

def _line(board: chess.Board, sans):
    """Construit une liste de coups depuis des SAN successifs."""
    probe = board.copy()
    moves = []
    for san in sans:
        mv = probe.parse_san(san)
        moves.append(mv)
        probe.push(mv)
    return moves


class TestOpeningEndPly:
    def test_no_book_caps_at_move_count(self):
        board = chess.Board()
        moves = _line(board, ["e4", "e5", "Nf3", "Nc6"])
        # 4 coups < 30 → toute la séquence est ouverture
        assert opening_end_ply(board, moves) == 4

    def test_no_book_caps_at_30_plies(self):
        board = chess.Board()
        # 40 coups nuls Cf3/Cf6/Cg1/Cg8… on génère assez de coups légaux répétés
        sans = []
        seq = ["Nf3", "Nf6", "Ng1", "Ng8"]
        for i in range(40):
            sans.append(seq[i % 4])
        moves = _line(board, sans)
        assert len(moves) == 40
        assert opening_end_ply(board, moves) == MAX_OPENING_PLY

    def test_book_probe_stops_early(self):
        board = chess.Board()
        moves = _line(board, ["e4", "e5", "Nf3", "Nc6", "Bb5"])
        # "En livre" tant que < 3 coups joués → sort à l'index 3
        in_book = lambda b: len(b.move_stack) < 3
        assert opening_end_ply(board, moves, in_book) == 3

    def test_book_probe_always_true_hits_cap(self):
        board = chess.Board()
        moves = _line(board, ["e4", "e5", "Nf3"])
        assert opening_end_ply(board, moves, lambda b: True) == 3

    def test_does_not_mutate_board(self):
        board = chess.Board()
        moves = _line(board, ["e4", "e5"])
        opening_end_ply(board, moves)
        assert board == chess.Board()


# ===================================================================
# segment_phases
# ===================================================================

class TestSegmentPhases:
    def test_all_opening_short_game(self):
        board = chess.Board()
        moves = _line(board, ["e4", "e5", "Nf3", "Nc6"])
        assert segment_phases(board, moves) == [Phase.OPENING] * 4

    def test_middlegame_when_out_of_book_and_not_endgame(self):
        board = chess.Board()
        moves = _line(board, ["e4", "e5", "Nf3", "Nc6"])
        # Hors livre dès le départ → aucune ouverture, position pleine → milieu
        phases = segment_phases(board, moves, in_book=lambda b: False)
        assert phases == [Phase.MIDDLEGAME] * 4

    def test_endgame_latched(self):
        # KR vs KR, hors livre dès le départ → toutes les positions en finale
        board = chess.Board("4k2r/8/8/8/8/8/4R3/4K3 w - - 0 1")
        moves = _line(board, ["Re3", "Kd7", "Re4"])
        phases = segment_phases(board, moves, in_book=lambda b: False)
        assert phases == [Phase.ENDGAME] * 3

    def test_empty_moves(self):
        assert segment_phases(chess.Board(), []) == []


# ===================================================================
# segment_pgn
# ===================================================================

class TestSegmentPgn:
    def test_valid_pgn_length(self):
        pgn = '[Event "x"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *'
        phases = segment_pgn(pgn)
        assert len(phases) == 6
        assert all(p == Phase.OPENING for p in phases)

    def test_empty_pgn(self):
        assert segment_pgn("") == []

    def test_invalid_pgn(self):
        assert segment_pgn("ceci n'est pas un pgn") == []
