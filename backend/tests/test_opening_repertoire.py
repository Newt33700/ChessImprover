"""Tests unitaires — arbre de répertoire depuis un PGN (EPIC 38, US 38.1).

REMPLACE l'ex-EPIC 9 (``validate_move_sequence``/``infer_quality`` — cf.
``test_srs.py::TestInferQuality`` pour la fonction généralisée dans
``domain.srs_engine``).
"""

from __future__ import annotations

from app.domain.opening_repertoire import parse_pgn_tree

RUY_LOPEZ_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5"


class TestParsePgnTreeSingleLine:
    def test_mainline_only_produces_one_node_per_ply(self):
        nodes = parse_pgn_tree(RUY_LOPEZ_PGN)
        assert len(nodes) == 5
        assert [n["move_san"] for n in nodes] == ["e4", "e5", "Nf3", "Nc6", "Bb5"]

    def test_depth_level_increments_from_1(self):
        nodes = parse_pgn_tree(RUY_LOPEZ_PGN)
        assert [n["depth_level"] for n in nodes] == [1, 2, 3, 4, 5]

    def test_root_nodes_have_no_parent_index(self):
        nodes = parse_pgn_tree(RUY_LOPEZ_PGN)
        assert nodes[0]["parent_index"] is None

    def test_each_non_root_node_points_to_its_predecessor(self):
        nodes = parse_pgn_tree(RUY_LOPEZ_PGN)
        assert nodes[1]["parent_index"] == 0
        assert nodes[2]["parent_index"] == 1
        assert nodes[4]["parent_index"] == 3

    def test_single_mainline_is_all_flagged_mainline(self):
        nodes = parse_pgn_tree(RUY_LOPEZ_PGN)
        assert all(n["is_mainline"] for n in nodes)

    def test_move_fen_reflects_position_after_the_move(self):
        nodes = parse_pgn_tree("1. e4")
        assert nodes[0]["move_fen"] == (
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        )


class TestParsePgnTreeVariations:
    def test_variation_at_first_move_creates_two_root_nodes(self):
        pgn = "1. e4 (1. d4) e5"
        nodes = parse_pgn_tree(pgn)
        roots = [n for n in nodes if n["parent_index"] is None]
        assert {n["move_san"] for n in roots} == {"e4", "d4"}

    def test_first_variation_is_mainline_others_are_not(self):
        pgn = "1. e4 (1. d4) e5"
        nodes = parse_pgn_tree(pgn)
        by_san = {n["move_san"]: n for n in nodes}
        assert by_san["e4"]["is_mainline"] is True
        assert by_san["d4"]["is_mainline"] is False

    def test_variation_deep_in_the_tree_is_not_mainline_even_off_the_mainline_path(self):
        pgn = "1. e4 e5 2. Nf3 (2. Bc4) Nc6"
        nodes = parse_pgn_tree(pgn)
        by_san = {(n["move_san"], n["depth_level"]): n for n in nodes}
        assert by_san[("Nf3", 3)]["is_mainline"] is True
        assert by_san[("Bc4", 3)]["is_mainline"] is False
        # Nc6 (profondeur 4) descend de la ligne principale (Nf3) uniquement.
        assert by_san[("Nc6", 4)]["is_mainline"] is True


class TestParsePgnTreeInvalidInput:
    def test_empty_string_returns_empty_list(self):
        assert parse_pgn_tree("") == []

    def test_garbage_text_returns_empty_list_not_raised(self):
        assert parse_pgn_tree("this is not a pgn at all") == []

    def test_pgn_with_no_moves_returns_empty_list(self):
        assert parse_pgn_tree("*") == []
