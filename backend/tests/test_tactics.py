"""Tests unitaires — sélection et validation de problèmes tactiques (US 8.1)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import chess

from app.domain.tactics import (
    TACTICAL_THEMES,
    _parse_move_token,
    advance_tactical_attempt,
    compute_daily_streak,
    compute_stats_by_theme,
    is_correct_move,
    select_nearest_problem,
    solution_sequence,
)

MATE_IN_1_FEN = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"
MATE_IN_1_SOLUTION = "Ra8#"

#: Positions et séquences EPIC 34 — vérifiées via python-chess (voir aussi
#: tests/test_db_tactics.py) : coup 1, réplique noire FORCÉE, mat.
MATE_IN_2_FEN = "8/8/8/8/8/8/8/k1KQ4 w - - 0 1"
MATE_IN_2_SEQUENCE = ["d1d4", "a1a2", "d4b2"]


class TestTacticalThemes:
    def test_contains_the_three_seeded_categories(self):
        assert set(TACTICAL_THEMES) == {"mate_in_1", "mate_in_2", "hanging_piece"}


class TestParseMoveToken:
    """`_parse_move_token` — repli UCI après échec du parsing SAN (EPIC 34)."""

    def test_legal_uci_move_is_parsed(self):
        board = chess.Board(MATE_IN_2_FEN)
        move = _parse_move_token(board, "d1d4")  # Qd1-d4, pas du SAN valide
        assert move == chess.Move.from_uci("d1d4")

    def test_illegal_uci_move_returns_none(self):
        board = chess.Board(MATE_IN_2_FEN)
        # d1f2 : syntaxiquement un coup UCI valide, mais pas un déplacement
        # de Dame légal (ni même rang, colonne, ou diagonale) depuis d1.
        assert _parse_move_token(board, "d1f2") is None


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

    def test_uci_solution_accepted(self):
        # EPIC 34 — les séquences Lichess/mate_in_2 stockent l'UCI, pas le SAN.
        assert is_correct_move(MATE_IN_2_FEN, "d1d4", "Qd4+") is True

    def test_uci_solution_wrong_move_rejected(self):
        assert is_correct_move(MATE_IN_2_FEN, "d1d4", "Kb1") is False

    def test_garbage_uci_solution_rejected_not_raised(self):
        assert is_correct_move(MATE_IN_2_FEN, "not-a-move", "Qd4+") is False


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

    def test_exclude_ids_removes_recently_served_problem(self):
        # EPIC 34 — corrige le bug « toujours le même exercice » : le
        # problème exact le plus proche est écarté, le suivant plus proche
        # est servi à la place.
        assert select_nearest_problem(self._problems(), 1000, exclude_ids=["b"])["id"] == "a"

    def test_exclude_ids_never_empties_the_pool(self):
        # Si TOUS les candidats ont été récemment servis, on retombe sur le
        # pool complet plutôt que de renvoyer None (jamais de 404 par ce biais).
        problems = self._problems()
        all_ids = [p["id"] for p in problems]
        assert select_nearest_problem(problems, 1000, exclude_ids=all_ids)["id"] == "b"

    def test_exclude_ids_none_or_empty_is_a_no_op(self):
        assert select_nearest_problem(self._problems(), 1000, exclude_ids=None)["id"] == "b"
        assert select_nearest_problem(self._problems(), 1000, exclude_ids=[])["id"] == "b"


class TestAdvanceTacticalAttempt:
    def test_single_move_solution_wrong_move(self):
        assert advance_tactical_attempt(MATE_IN_1_FEN, [MATE_IN_1_SOLUTION], "Kg1") == {"result": "wrong"}

    def test_single_move_solution_correct_completes_immediately(self):
        step = advance_tactical_attempt(MATE_IN_1_FEN, [MATE_IN_1_SOLUTION], "Ra8#")
        assert step["result"] == "correct_complete"
        assert "fen" in step

    def test_empty_remaining_is_always_wrong(self):
        assert advance_tactical_attempt(MATE_IN_1_FEN, [], "Ra8#") == {"result": "wrong"}

    def test_multi_ply_first_move_returns_partial_with_auto_played_reply(self):
        step = advance_tactical_attempt(MATE_IN_2_FEN, MATE_IN_2_SEQUENCE, "Qd4+")
        assert step["result"] == "correct_partial"
        assert step["opponent_move"] == "Ka2"
        assert step["remaining"] == ["d4b2"]
        assert "fen" in step

    def test_multi_ply_wrong_first_move(self):
        assert advance_tactical_attempt(MATE_IN_2_FEN, MATE_IN_2_SEQUENCE, "Kb1") == {"result": "wrong"}

    def test_multi_ply_alternate_faster_mate_is_still_rejected(self):
        # Qa4# mate directement (mat en 1) mais n'est pas la solution
        # ATTENDUE de ce problème — la régression exacte du bug rapporté.
        assert advance_tactical_attempt(MATE_IN_2_FEN, MATE_IN_2_SEQUENCE, "Qa4#") == {"result": "wrong"}

    def test_multi_ply_second_move_completes(self):
        step1 = advance_tactical_attempt(MATE_IN_2_FEN, MATE_IN_2_SEQUENCE, "Qd4+")
        step2 = advance_tactical_attempt(step1["fen"], step1["remaining"], "Qb2#")
        assert step2["result"] == "correct_complete"

    def test_multi_ply_wrong_second_move(self):
        step1 = advance_tactical_attempt(MATE_IN_2_FEN, MATE_IN_2_SEQUENCE, "Qd4+")
        step2 = advance_tactical_attempt(step1["fen"], step1["remaining"], "Qd1")
        assert step2 == {"result": "wrong"}

    def test_garbage_played_move_rejected_not_raised(self):
        assert advance_tactical_attempt(MATE_IN_1_FEN, [MATE_IN_1_SOLUTION], "not a move") == {"result": "wrong"}

    def test_garbage_opponent_reply_treated_as_complete(self):
        # Réplique adverse illisible (donnée corrompue) : on ne plante pas,
        # on traite comme terminé sur le dernier coup validé — forme exacte
        # attendue, pas seulement "ne lève pas d'exception".
        sequence = ["d1d4", "garbage-token", "d4b2"]
        result = advance_tactical_attempt(MATE_IN_2_FEN, sequence, "Qd4+")
        assert result == {"result": "correct_complete", "fen": result["fen"]}
        assert set(result.keys()) == {"result", "fen"}


class TestSolutionSequence:
    def test_wraps_plain_string_in_a_list(self):
        assert solution_sequence("Ra8#") == ["Ra8#"]

    def test_leaves_a_list_untouched(self):
        assert solution_sequence(["d1d4", "a1a2", "d4b2"]) == ["d1d4", "a1a2", "d4b2"]

    def test_accepts_a_tuple(self):
        assert solution_sequence(("d1d4", "a1a2")) == ["d1d4", "a1a2"]


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

    def test_successes_accumulate_not_stuck_at_one(self):
        attempts = [
            {"category": "mate_in_1", "success": True},
            {"category": "mate_in_1", "success": True},
            {"category": "mate_in_1", "success": True},
        ]
        stats = compute_stats_by_theme(attempts)
        assert stats[0]["successes"] == 3
