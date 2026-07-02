"""EPIC 15 (US 15.1/15.2) — Réparation de Partie (Game-Salvage)."""

from __future__ import annotations

import chess

from app.domain.game_salvage import find_defeat_pivot, reconstruct_position_before_move

PGN = '[Event "x"][Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0'


def _moves(colors_and_cpl):
    """Construit une liste de records `game_moves` minimaux (color/cpl)."""
    return [{"color": c, "cpl": cpl} for c, cpl in colors_and_cpl]


class TestFindDefeatPivot:
    def test_no_pivot_when_no_engine_data(self):
        moves = _moves([("white", None), ("black", None)])
        assert find_defeat_pivot(moves, "white") is None

    def test_no_pivot_below_threshold(self):
        moves = _moves([("white", 50), ("black", 30), ("white", 100)])
        assert find_defeat_pivot(moves, "white") is None

    def test_finds_first_player_blunder_at_or_above_threshold(self):
        moves = _moves([
            ("white", 20), ("black", 15), ("white", 250), ("black", 300),
        ])
        assert find_defeat_pivot(moves, "white") == 2

    def test_ignores_opponent_blunders(self):
        # Le seul coup >= 200 est celui de l'adversaire (noir) : aucun pivot
        # pour le joueur blanc.
        moves = _moves([("white", 20), ("black", 300), ("white", 40)])
        assert find_defeat_pivot(moves, "white") is None

    def test_exact_threshold_counts_as_pivot(self):
        moves = _moves([("white", 200)])
        assert find_defeat_pivot(moves, "white") == 0

    def test_player_color_black(self):
        moves = _moves([("white", 20), ("black", 250)])
        assert find_defeat_pivot(moves, "black") == 1


class TestReconstructPositionBeforeMove:
    def test_invalid_pgn_returns_none(self):
        assert reconstruct_position_before_move("not a pgn", 0) is None

    def test_out_of_bounds_index_returns_none(self):
        assert reconstruct_position_before_move(PGN, 99) is None
        assert reconstruct_position_before_move(PGN, -1) is None

    def test_index_zero_is_starting_position(self):
        pos = reconstruct_position_before_move(PGN, 0)
        assert pos is not None
        assert pos["fen"] == chess.Board().fen()
        assert pos["side_to_move"] == "white"
        assert pos["move_number"] == 1

    def test_reconstructs_position_before_given_move(self):
        # Index 2 = 3ᵉ demi-coup joué (Nf3, 0-based) -> position après 1. e4 e5.
        pos = reconstruct_position_before_move(PGN, 2)
        assert pos is not None
        board = chess.Board()
        board.push_san("e4")
        board.push_san("e5")
        assert pos["fen"] == board.fen()
        assert pos["side_to_move"] == "white"
        assert pos["move_number"] == 2

    def test_side_to_move_black(self):
        # Index 1 = 2ᵉ demi-coup (e5) -> c'est aux Noirs de jouer.
        pos = reconstruct_position_before_move(PGN, 1)
        assert pos is not None
        assert pos["side_to_move"] == "black"
