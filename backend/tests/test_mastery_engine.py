"""Tests unitaires — Lotus Mastery Engine (EPIC 38, US 38.1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.mastery_engine import (
    FAILURE_SCORE_DELTA,
    SRS_INTERVAL_MULTIPLIER,
    SUCCESS_SCORE_DELTA,
    UNLOCK_THRESHOLD,
    process_attempt,
    rank_for_score,
)


class TestRankForScore:
    def test_below_20_is_beginner(self):
        assert rank_for_score(0) == "Beginner"
        assert rank_for_score(19) == "Beginner"

    def test_20_to_39_is_novice(self):
        assert rank_for_score(20) == "Novice"
        assert rank_for_score(39) == "Novice"

    def test_40_to_59_is_intermediate(self):
        assert rank_for_score(40) == "Intermediate"
        assert rank_for_score(59) == "Intermediate"

    def test_60_to_79_is_advanced(self):
        assert rank_for_score(60) == "Advanced"
        assert rank_for_score(79) == "Advanced"

    def test_80_to_99_is_master(self):
        assert rank_for_score(80) == "Master"
        assert rank_for_score(99) == "Master"

    def test_100_is_legend(self):
        assert rank_for_score(100) == "Legend"


class TestProcessAttemptSuccess:
    def test_adds_15_to_mastery_score(self):
        result = process_attempt(50, 4, is_success=True)
        assert result["mastery_score"] == 65

    def test_mastery_score_is_capped_at_100(self):
        result = process_attempt(95, 4, is_success=True)
        assert result["mastery_score"] == 100

    def test_srs_interval_is_multiplied(self):
        result = process_attempt(10, 4, is_success=True)
        assert result["srs_interval"] == 4 * SRS_INTERVAL_MULTIPLIER

    def test_status_is_mastered_only_at_100(self):
        assert process_attempt(84, 1, is_success=True)["status"] == "review"
        assert process_attempt(85, 1, is_success=True)["status"] == "mastered"

    def test_should_unlock_children_exactly_at_threshold(self):
        below = process_attempt(UNLOCK_THRESHOLD - SUCCESS_SCORE_DELTA - 1, 1, True)
        at = process_attempt(UNLOCK_THRESHOLD - SUCCESS_SCORE_DELTA, 1, True)
        assert below["should_unlock_children"] is False
        assert at["should_unlock_children"] is True

    def test_next_review_date_is_now_plus_new_interval_days(self):
        now = datetime(2026, 7, 6, tzinfo=timezone.utc)
        result = process_attempt(0, 1, is_success=True, now=now)
        assert result["next_review_date"] == now + timedelta(days=result["srs_interval"])

    def test_rank_reflects_the_new_score(self):
        result = process_attempt(38, 1, is_success=True)  # 38+15=53 -> Intermediate
        assert result["rank"] == "Intermediate"


class TestProcessAttemptFailure:
    def test_subtracts_20_from_mastery_score(self):
        result = process_attempt(50, 4, is_success=False)
        assert result["mastery_score"] == 30

    def test_mastery_score_is_floored_at_0(self):
        result = process_attempt(10, 4, is_success=False)
        assert result["mastery_score"] == 0
        assert FAILURE_SCORE_DELTA == -20

    def test_srs_interval_resets_to_1_day(self):
        result = process_attempt(50, 16, is_success=False)
        assert result["srs_interval"] == 1

    def test_failure_never_reaches_mastered_status(self):
        result = process_attempt(100, 4, is_success=False)
        assert result["status"] == "review"

    def test_should_unlock_children_still_true_if_score_stays_above_threshold(self):
        # Pas de mécanique de re-verrouillage : un échec qui laisse le score
        # au-dessus du seuil ne doit pas bloquer un futur succès ailleurs —
        # devrait rester idempotent côté appelant (ON CONFLICT DO NOTHING).
        result = process_attempt(70, 4, is_success=False)
        assert result["mastery_score"] == 50
        assert result["should_unlock_children"] is True

    def test_should_unlock_children_false_once_dropped_below_threshold(self):
        result = process_attempt(45, 4, is_success=False)
        assert result["mastery_score"] == 25
        assert result["should_unlock_children"] is False


class TestProcessAttemptDefaults:
    def test_defaults_to_current_time_when_now_not_given(self):
        before = datetime.now(timezone.utc)
        result = process_attempt(0, 1, is_success=True)
        after = datetime.now(timezone.utc)
        assert before <= result["next_review_date"] - timedelta(days=result["srs_interval"]) <= after

    def test_srs_interval_never_multiplies_a_non_positive_stored_value(self):
        # Un srs_interval stocké à 0 (donnée historique/incohérente) ne doit
        # jamais bloquer la progression (0 * 2 == 0 serait un intervalle nul).
        result = process_attempt(0, 0, is_success=True)
        assert result["srs_interval"] == SRS_INTERVAL_MULTIPLIER
