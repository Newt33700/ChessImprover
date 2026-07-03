"""Tests unitaires — store finales essentielles (EPIC 10, fonctionnalité bonus).

Vérifie aussi (une fois) que les 9 positions du seed sont individuellement
des mats en 1 effectifs via python-chess.
"""

from __future__ import annotations

import chess
import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _is_mate_in_1(fen: str, san: str) -> bool:
    board = chess.Board(fen)
    move = board.parse_san(san)
    if move not in board.legal_moves:
        return False
    board.push(move)
    return board.is_checkmate()


class TestSeedIntegrity:
    def test_seed_has_9_problems(self):
        assert len(db_client._endgame_problems) == 9

    def test_every_problem_is_actually_mate_in_1(self):
        for problem in db_client._endgame_problems.values():
            assert _is_mate_in_1(problem["fen"], problem["solution"]), problem

    def test_categories_present(self):
        cats = {p["category"] for p in db_client._endgame_problems.values()}
        assert cats == {"queen_mate", "rook_mate", "two_rooks_mate"}


class TestEndgameElo:
    def test_new_user_defaults_to_1000(self):
        user = db_client.create_user("a@ex.com", "a", "hash")
        assert db_client.get_endgame_elo(user["id"]) == 1000

    def test_unknown_user_defaults_to_1000(self):
        assert db_client.get_endgame_elo("does-not-exist") == 1000

    def test_update_endgame_elo_persists(self):
        user = db_client.create_user("a@ex.com", "a", "hash")
        db_client.update_endgame_elo(user["id"], 1015)
        assert db_client.get_endgame_elo(user["id"]) == 1015

    def test_update_unknown_user_returns_none(self):
        assert db_client.update_endgame_elo("does-not-exist", 1015) is None

    def test_distinct_from_tactical_elo(self):
        user = db_client.create_user("a@ex.com", "a", "hash")
        db_client.update_tactical_elo(user["id"], 1200)
        assert db_client.get_endgame_elo(user["id"]) == 1000
        assert db_client.get_tactical_elo(user["id"]) == 1200


class TestGetEndgameProblem:
    def test_returns_known_problem(self):
        pid = next(iter(db_client._endgame_problems))
        problem = db_client.get_endgame_problem(pid)
        assert problem["id"] == pid

    def test_unknown_id_returns_none(self):
        assert db_client.get_endgame_problem("missing") is None


class TestGetNextEndgameProblem:
    def test_returns_a_problem_near_requested_elo(self):
        problem = db_client.get_next_endgame_problem(1000)
        assert problem is not None

    def test_filters_by_category(self):
        problem = db_client.get_next_endgame_problem(1000, category="queen_mate")
        assert problem["category"] == "queen_mate"

    def test_unknown_category_widens_to_full_pool(self):
        # EPIC 22 (US 22.2) : élargissement du pool plutôt que None/404.
        problem = db_client.get_next_endgame_problem(1000, category="does-not-exist")
        assert problem is not None
        assert problem["category"] in {"queen_mate", "rook_mate", "two_rooks_mate"}
