"""Tests unitaires — sélection et validation de problèmes tactiques (US 8.1)."""

from __future__ import annotations

from app.domain.tactics import is_correct_move, select_nearest_problem

MATE_IN_1_FEN = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"
MATE_IN_1_SOLUTION = "Ra8#"


class TestIsCorrectMove:
    def test_exact_san_match(self):
        assert is_correct_move(MATE_IN_1_FEN, MATE_IN_1_SOLUTION, "Ra8#") is True

    def test_equivalent_notation_without_mate_symbol(self):
        # "Ra8" (sans le "#") désigne le même coup légal — doit être accepté.
        assert is_correct_move(MATE_IN_1_FEN, MATE_IN_1_SOLUTION, "Ra8") is True

    def test_wrong_move_rejected(self):
        assert is_correct_move(MATE_IN_1_FEN, MATE_IN_1_SOLUTION, "Kg1") is False

    def test_illegal_san_rejected_not_raised(self):
        assert is_correct_move(MATE_IN_1_FEN, MATE_IN_1_SOLUTION, "Qh8#") is False

    def test_garbage_input_rejected_not_raised(self):
        assert is_correct_move(MATE_IN_1_FEN, MATE_IN_1_SOLUTION, "not a move") is False


class TestSelectNearestProblem:
    def _problems(self):
        return [
            {"id": "a", "difficulty_elo": 650},
            {"id": "b", "difficulty_elo": 1000},
            {"id": "c", "difficulty_elo": 1400},
        ]

    def test_empty_list_returns_none(self):
        assert select_nearest_problem([], 1000) is None

    def test_picks_exact_match(self):
        assert select_nearest_problem(self._problems(), 1000)["id"] == "b"

    def test_picks_closest_when_no_exact_match(self):
        assert select_nearest_problem(self._problems(), 1350)["id"] == "c"

    def test_picks_closest_low_side(self):
        assert select_nearest_problem(self._problems(), 700)["id"] == "a"

    def test_tie_breaks_randomly_among_equidistant(self):
        problems = [{"id": "low", "difficulty_elo": 900}, {"id": "high", "difficulty_elo": 1100}]
        picks = {select_nearest_problem(problems, 1000)["id"] for _ in range(30)}
        assert picks == {"low", "high"}
