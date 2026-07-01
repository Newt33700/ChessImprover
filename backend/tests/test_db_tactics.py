"""Tests unitaires — store tactique (US 8.1, EPIC 8).

Vérifie aussi (une fois) que les 15 problèmes du seed sont individuellement
corrects via python-chess : coup légal + mat effectif pour mate_in_1/
mate_in_2, capture non défendue pour hanging_piece.
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


def _is_mate_in_n(fen: str, san: str, n: int) -> bool:
    board = chess.Board(fen)
    move = board.parse_san(san)
    if move not in board.legal_moves:
        return False
    board.push(move)
    if n == 1:
        return board.is_checkmate()
    if board.is_checkmate():
        return False
    replies = list(board.legal_moves)
    if not replies:
        return False
    for reply in replies:
        board.push(reply)
        found = any(
            (board.push(mv2), board.is_checkmate(), board.pop())[1]
            for mv2 in board.legal_moves
        )
        board.pop()
        if not found:
            return False
    return True


def _is_undefended_capture(fen: str, san: str) -> bool:
    board = chess.Board(fen)
    move = board.parse_san(san)
    if move not in board.legal_moves or not board.is_capture(move):
        return False
    return len(board.attackers(not board.turn, move.to_square)) == 0


class TestSeedIntegrity:
    """Verrouille l'exactitude du jeu de données (une régression ici casserait
    silencieusement le jeu pour les utilisateurs).
    """

    def test_seed_has_15_problems(self):
        assert len(db_client._tactical_problems) == 15

    def test_every_problem_is_actually_correct(self):
        for problem in db_client._tactical_problems.values():
            cat = problem["category"]
            if cat == "mate_in_1":
                assert _is_mate_in_n(problem["fen"], problem["solution"], 1), problem
            elif cat == "mate_in_2":
                assert _is_mate_in_n(problem["fen"], problem["solution"], 2), problem
            elif cat == "hanging_piece":
                assert _is_undefended_capture(problem["fen"], problem["solution"]), problem
            else:
                pytest.fail(f"catégorie inconnue : {cat}")

    def test_categories_present(self):
        cats = {p["category"] for p in db_client._tactical_problems.values()}
        assert cats == {"mate_in_1", "mate_in_2", "hanging_piece"}


class TestTacticalElo:
    def test_new_user_defaults_to_1000(self):
        user = db_client.create_user("a@ex.com", "a", "hash")
        assert db_client.get_tactical_elo(user["id"]) == 1000

    def test_unknown_user_defaults_to_1000(self):
        assert db_client.get_tactical_elo("does-not-exist") == 1000

    def test_update_tactical_elo_persists(self):
        user = db_client.create_user("a@ex.com", "a", "hash")
        db_client.update_tactical_elo(user["id"], 1015)
        assert db_client.get_tactical_elo(user["id"]) == 1015

    def test_update_unknown_user_returns_none(self):
        assert db_client.update_tactical_elo("does-not-exist", 1015) is None


class TestGetTacticalProblem:
    def test_returns_known_problem(self):
        pid = next(iter(db_client._tactical_problems))
        problem = db_client.get_tactical_problem(pid)
        assert problem["id"] == pid

    def test_unknown_id_returns_none(self):
        assert db_client.get_tactical_problem("missing") is None


class TestGetNextTacticalProblem:
    def test_returns_a_problem_near_requested_elo(self):
        problem = db_client.get_next_tactical_problem(1000)
        assert problem is not None
        assert problem["difficulty_elo"] in {950, 1000, 1250}  # les plus proches de 1000 dans le seed

    def test_filters_by_category(self):
        problem = db_client.get_next_tactical_problem(1000, category="mate_in_1")
        assert problem["category"] == "mate_in_1"

    def test_unknown_category_returns_none(self):
        assert db_client.get_next_tactical_problem(1000, category="does-not-exist") is None
