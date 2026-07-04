"""Tests unitaires — Quêtes quotidiennes sans état (EPIC 29, US 29.2)."""

from __future__ import annotations

from app.domain.daily_quests import (
    DAILY_QUEST_COUNT,
    QUEST_POOL,
    compute_quest_progress,
    select_daily_quests,
)


class TestSelectDailyQuests:
    def test_returns_exactly_n_quests(self):
        quests = select_daily_quests("2026-07-04", "user-1")
        assert len(quests) == DAILY_QUEST_COUNT

    def test_deterministic_same_day_same_user(self):
        a = select_daily_quests("2026-07-04", "user-1")
        b = select_daily_quests("2026-07-04", "user-1")
        assert [q["id"] for q in a] == [q["id"] for q in b]

    def test_no_duplicate_quests_same_call(self):
        quests = select_daily_quests("2026-07-04", "user-1")
        ids = [q["id"] for q in quests]
        assert len(ids) == len(set(ids))

    def test_different_users_can_get_different_quests(self):
        # Pas garanti dans l'absolu, mais vrai avec ce pool/seed sur cet échantillon
        # d'utilisateurs — verrouille la variabilité de la sélection (US 29.2).
        combos = {
            tuple(q["id"] for q in select_daily_quests("2026-07-04", f"user-{i}"))
            for i in range(10)
        }
        assert len(combos) > 1

    def test_different_days_can_yield_different_quests(self):
        combos = {
            tuple(q["id"] for q in select_daily_quests(f"2026-07-{d:02d}", "user-1"))
            for d in range(1, 15)
        }
        assert len(combos) > 1

    def test_all_selected_quests_come_from_pool(self):
        pool_ids = {q["id"] for q in QUEST_POOL}
        quests = select_daily_quests("2026-07-04", "user-1")
        assert all(q["id"] in pool_ids for q in quests)

    def test_n_capped_at_pool_size(self):
        quests = select_daily_quests("2026-07-04", "user-1", n=999)
        assert len(quests) == len(QUEST_POOL)


class TestComputeQuestProgress:
    def test_progress_below_target_not_completed(self):
        quest = {"id": "x", "label": "X", "metric": "games_analyzed", "target": 3, "xp_reward": 10}
        result = compute_quest_progress(quest, {"games_analyzed": 1})
        assert result["progress"] == 1
        assert result["completed"] is False

    def test_progress_reaching_target_completed(self):
        quest = {"id": "x", "label": "X", "metric": "games_analyzed", "target": 3, "xp_reward": 10}
        result = compute_quest_progress(quest, {"games_analyzed": 3})
        assert result["completed"] is True

    def test_progress_exceeding_target_clamped(self):
        quest = {"id": "x", "label": "X", "metric": "games_analyzed", "target": 3, "xp_reward": 10}
        result = compute_quest_progress(quest, {"games_analyzed": 99})
        assert result["progress"] == 3

    def test_missing_metric_counts_as_zero(self):
        quest = {"id": "x", "label": "X", "metric": "unknown_metric", "target": 1, "xp_reward": 10}
        result = compute_quest_progress(quest, {"games_analyzed": 5})
        assert result["progress"] == 0
        assert result["completed"] is False

    def test_preserves_original_quest_fields(self):
        quest = {"id": "x", "label": "X", "metric": "games_analyzed", "target": 1, "xp_reward": 20}
        result = compute_quest_progress(quest, {"games_analyzed": 1})
        assert result["id"] == "x"
        assert result["label"] == "X"
        assert result["xp_reward"] == 20
