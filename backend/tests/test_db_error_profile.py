"""Tests unitaires — store profils d'erreur comportementale (EPIC 11, US 9.1/9.2)."""

from __future__ import annotations

import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestUpsertErrorProfile:
    def test_creates_profile_when_absent(self):
        profile = db_client.upsert_error_profile("u1", "hanging_piece", 30.0, "2026-07-02T00:00:00Z")
        assert profile["user_id"] == "u1"
        assert profile["error_type"] == "hanging_piece"
        assert profile["frequency_score"] == 30.0
        assert profile["last_observed"] == "2026-07-02T00:00:00Z"

    def test_updates_existing_profile_in_place(self):
        db_client.upsert_error_profile("u1", "hanging_piece", 30.0, "2026-07-01T00:00:00Z")
        updated = db_client.upsert_error_profile("u1", "hanging_piece", 51.0, "2026-07-02T00:00:00Z")
        assert updated["frequency_score"] == 51.0
        assert len(db_client.get_error_profiles("u1")) == 1

    def test_different_error_types_are_independent_rows(self):
        db_client.upsert_error_profile("u1", "hanging_piece", 30.0, "2026-07-02T00:00:00Z")
        db_client.upsert_error_profile("u1", "missed_mate", 10.0, "2026-07-02T00:00:00Z")
        assert len(db_client.get_error_profiles("u1")) == 2


class TestGetErrorProfile:
    def test_returns_none_when_absent(self):
        assert db_client.get_error_profile("u1", "hanging_piece") is None

    def test_returns_profile_when_present(self):
        db_client.upsert_error_profile("u1", "time_pressure", 80.0, "2026-07-02T00:00:00Z")
        profile = db_client.get_error_profile("u1", "time_pressure")
        assert profile["frequency_score"] == 80.0


class TestGetErrorProfiles:
    def test_isolated_between_users(self):
        db_client.upsert_error_profile("u1", "hanging_piece", 30.0, "2026-07-02T00:00:00Z")
        db_client.upsert_error_profile("u2", "hanging_piece", 90.0, "2026-07-02T00:00:00Z")
        assert len(db_client.get_error_profiles("u1")) == 1
        assert db_client.get_error_profiles("u1")[0]["frequency_score"] == 30.0

    def test_unknown_user_has_empty_profiles(self):
        assert db_client.get_error_profiles("does-not-exist") == []


class TestGetNextTacticalProblemForCategories:
    def test_pool_restricted_to_given_categories(self):
        problem = db_client.get_next_tactical_problem_for_categories(1000, ["mate_in_1", "mate_in_2"])
        assert problem is not None
        assert problem["category"] in ("mate_in_1", "mate_in_2")

    def test_empty_category_list_widens_to_full_pool(self):
        # EPIC 22 (US 22.2) : un pool vide est élargi à toutes les catégories
        # plutôt que de renvoyer None (404 → « Impossible de charger »).
        problem = db_client.get_next_tactical_problem_for_categories(1000, [])
        assert problem is not None

    def test_single_category_matches_theme_filter(self):
        problem = db_client.get_next_tactical_problem_for_categories(1000, ["hanging_piece"])
        assert problem is not None
        assert problem["category"] == "hanging_piece"
