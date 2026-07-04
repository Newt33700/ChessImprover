"""Tests unitaires — XP/Niveau authoritatifs (EPIC 29, US 29.1)."""

from __future__ import annotations

import pytest

from app.domain.gamification import (
    XP_PER_ANALYSIS,
    XP_PER_PROBLEM_SOLVED,
    apply_xp_gain,
    xp_required_for_level,
)
from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestXpRequiredForLevel:
    def test_level_1_requires_100(self):
        assert xp_required_for_level(1) == 100

    def test_level_5_requires_500(self):
        assert xp_required_for_level(5) == 500


class TestApplyXpGain:
    def test_gain_without_level_up(self):
        result = apply_xp_gain(current_xp=0, current_level=1, amount=50)
        assert result == {"xp": 50, "level": 1, "leveled_up": False}

    def test_gain_reaching_exact_threshold_levels_up(self):
        result = apply_xp_gain(current_xp=50, current_level=1, amount=50)
        assert result == {"xp": 0, "level": 2, "leveled_up": True}

    def test_gain_overflowing_threshold_carries_remainder(self):
        result = apply_xp_gain(current_xp=80, current_level=1, amount=50)
        # 80 + 50 = 130 ; seuil niveau 1 = 100 -> niveau 2, reste 30
        assert result == {"xp": 30, "level": 2, "leveled_up": True}

    def test_multiple_level_ups_in_one_gain(self):
        # Un très gros gain peut faire sauter plusieurs niveaux d'un coup.
        result = apply_xp_gain(current_xp=0, current_level=1, amount=350)
        # niveau 1 (100) + niveau 2 (200) = 300 consommés -> niveau 3, reste 50
        assert result == {"xp": 50, "level": 3, "leveled_up": True}

    def test_zero_amount_never_levels_up(self):
        result = apply_xp_gain(current_xp=10, current_level=2, amount=0)
        assert result == {"xp": 10, "level": 2, "leveled_up": False}

    def test_negative_current_xp_clamped_to_zero(self):
        result = apply_xp_gain(current_xp=-5, current_level=1, amount=10)
        assert result["xp"] == 10

    def test_negative_amount_clamped_to_zero(self):
        result = apply_xp_gain(current_xp=10, current_level=1, amount=-100)
        assert result == {"xp": 10, "level": 1, "leveled_up": False}

    def test_level_below_one_clamped(self):
        result = apply_xp_gain(current_xp=0, current_level=0, amount=50)
        assert result["level"] >= 1


class TestConstants:
    def test_xp_per_analysis_is_fifty(self):
        assert XP_PER_ANALYSIS == 50

    def test_xp_per_problem_solved_is_fifteen(self):
        assert XP_PER_PROBLEM_SOLVED == 15


class TestDbClientXp:
    """Persistance in-memory (db_client) — la délégation Postgres est ``pragma: no cover``."""

    def test_new_user_starts_at_zero_one(self):
        user = db_client.create_user("a@ex.com", "alice", "hash")
        assert db_client.get_xp_level(user["id"]) == {"xp": 0, "level": 1}

    def test_add_xp_persists_gain(self):
        user = db_client.create_user("b@ex.com", "bob", "hash")
        updated = db_client.add_xp(user["id"], 30)
        assert updated["xp"] == 30
        assert updated["level"] == 1
        assert db_client.get_xp_level(user["id"]) == {"xp": 30, "level": 1}

    def test_add_xp_levels_up(self):
        user = db_client.create_user("c@ex.com", "carol", "hash")
        db_client.add_xp(user["id"], 90)
        updated = db_client.add_xp(user["id"], 20)
        assert updated == {**updated, "xp": 10, "level": 2}

    def test_add_xp_unknown_user_returns_none(self):
        assert db_client.add_xp("does-not-exist", 50) is None

    def test_get_xp_level_unknown_user_defaults(self):
        assert db_client.get_xp_level("does-not-exist") == {"xp": 0, "level": 1}
