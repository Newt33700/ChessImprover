"""EPIC 12 (US 11.1/11.2) — chrono serveur + scoring du mode Tactical Sprint."""

from datetime import datetime, timedelta, timezone

from app.domain.tactical_sprint import (
    POINTS_PER_SOLVE,
    SPRINT_DURATION_SECONDS,
    compute_score,
    elapsed_seconds,
    is_sprint_active,
    record_ghost_move,
)

T0 = datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)


class TestElapsedSeconds:
    def test_zero_at_start(self):
        assert elapsed_seconds(T0, T0) == 0.0

    def test_positive_after_delay(self):
        assert elapsed_seconds(T0, T0 + timedelta(seconds=30)) == 30.0

    def test_never_negative_if_now_before_start(self):
        assert elapsed_seconds(T0, T0 - timedelta(seconds=5)) == 0.0


class TestIsSprintActive:
    def test_active_within_window(self):
        assert is_sprint_active(T0, T0 + timedelta(seconds=59)) is True

    def test_active_exactly_at_boundary(self):
        assert is_sprint_active(T0, T0 + timedelta(seconds=SPRINT_DURATION_SECONDS)) is True

    def test_inactive_past_window(self):
        assert is_sprint_active(T0, T0 + timedelta(seconds=61)) is False

    def test_custom_duration_respected(self):
        assert is_sprint_active(T0, T0 + timedelta(seconds=100), duration_seconds=120) is True
        assert is_sprint_active(T0, T0 + timedelta(seconds=130), duration_seconds=120) is False


class TestComputeScore:
    def test_zero_solved_is_zero_score(self):
        assert compute_score(0) == 0

    def test_score_scales_with_solves(self):
        assert compute_score(5) == 5 * POINTS_PER_SOLVE

    def test_score_is_deterministic_pure_function(self):
        assert compute_score(3) == compute_score(3)


class TestRecordGhostMove:
    def test_appends_without_mutating_original(self):
        original = [{"problem_id": "p1", "move": "Qh5#", "elapsed_ms": 1200}]
        updated = record_ghost_move(original, "p2", "Ra8#", 3400)
        assert len(original) == 1
        assert updated == [
            {"problem_id": "p1", "move": "Qh5#", "elapsed_ms": 1200},
            {"problem_id": "p2", "move": "Ra8#", "elapsed_ms": 3400},
        ]

    def test_starts_from_empty_list(self):
        assert record_ghost_move([], "p1", "Qh5#", 500) == [
            {"problem_id": "p1", "move": "Qh5#", "elapsed_ms": 500}
        ]
