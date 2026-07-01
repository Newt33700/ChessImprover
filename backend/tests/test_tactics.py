"""Tests unitaires — sélection et validation de problèmes tactiques (US 8.1)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.domain.tactics import (
    TACTICAL_THEMES,
    compute_daily_streak,
    compute_stats_by_theme,
    is_correct_move,
    select_nearest_problem,
)

MATE_IN_1_FEN = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"
MATE_IN_1_SOLUTION = "Ra8#"


class TestTacticalThemes:
    def test_contains_the_three_seeded_categories(self):
        assert set(TACTICAL_THEMES) == {"mate_in_1", "mate_in_2", "hanging_piece"}


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


class TestComputeDailyStreak:
    TODAY = date(2026, 7, 1)

    def _attempt(self, success, when):
        return {"success": success, "created_at": when}

    def test_no_attempts_returns_zero(self):
        assert compute_daily_streak([], self.TODAY) == 0

    def test_all_successes_today_count_all(self):
        attempts = [
            self._attempt(True, datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)),
            self._attempt(True, datetime(2026, 7, 1, 10, 5, tzinfo=timezone.utc)),
            self._attempt(True, datetime(2026, 7, 1, 10, 10, tzinfo=timezone.utc)),
        ]
        assert compute_daily_streak(attempts, self.TODAY) == 3

    def test_stops_at_first_failure_from_most_recent(self):
        attempts = [
            self._attempt(False, datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)),
            self._attempt(True, datetime(2026, 7, 1, 10, 5, tzinfo=timezone.utc)),
            self._attempt(True, datetime(2026, 7, 1, 10, 10, tzinfo=timezone.utc)),
        ]
        assert compute_daily_streak(attempts, self.TODAY) == 2

    def test_yesterday_successes_do_not_count(self):
        yesterday = self.TODAY - timedelta(days=1)
        attempts = [self._attempt(True, datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=timezone.utc))]
        assert compute_daily_streak(attempts, self.TODAY) == 0

    def test_accepts_plain_date_objects(self):
        attempts = [self._attempt(True, self.TODAY)]
        assert compute_daily_streak(attempts, self.TODAY) == 1


class TestComputeStatsByTheme:
    def test_empty_attempts_returns_empty_list(self):
        assert compute_stats_by_theme([]) == []

    def test_groups_and_computes_success_rate_per_category(self):
        attempts = [
            {"category": "mate_in_1", "success": True},
            {"category": "mate_in_1", "success": False},
            {"category": "hanging_piece", "success": True},
        ]
        stats = compute_stats_by_theme(attempts)
        by_cat = {s["category"]: s for s in stats}
        assert by_cat["mate_in_1"] == {
            "category": "mate_in_1", "attempts": 2, "successes": 1, "success_rate": 0.5,
        }
        assert by_cat["hanging_piece"] == {
            "category": "hanging_piece", "attempts": 1, "successes": 1, "success_rate": 1.0,
        }
