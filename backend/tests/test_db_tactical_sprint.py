"""Tests unitaires — store mode Tactical Sprint (EPIC 12, US 11.1/11.2)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestCreateSprint:
    def test_returns_sprint_with_defaults(self):
        sprint = db_client.create_sprint("u1")
        assert sprint["user_id"] == "u1"
        assert sprint["score"] == 0
        assert sprint["problems_solved_count"] == 0
        assert sprint["moves"] == []
        assert sprint["finished_at"] is None
        assert "id" in sprint and "started_at" in sprint


class TestGetSprint:
    def test_returns_none_when_absent(self):
        assert db_client.get_sprint("does-not-exist") is None

    def test_returns_created_sprint(self):
        sprint = db_client.create_sprint("u1")
        assert db_client.get_sprint(sprint["id"])["id"] == sprint["id"]


class TestUpdateSprint:
    def test_updates_fields_in_place(self):
        sprint = db_client.create_sprint("u1")
        updated = db_client.update_sprint(sprint["id"], score=20, problems_solved_count=2)
        assert updated["score"] == 20
        assert updated["problems_solved_count"] == 2

    def test_returns_none_for_unknown_sprint(self):
        assert db_client.update_sprint("does-not-exist", score=10) is None


class TestGetBestSprint:
    def test_none_when_no_finished_sprints(self):
        db_client.create_sprint("u1")
        assert db_client.get_best_sprint() is None

    def test_ignores_unfinished_sprints(self):
        sprint = db_client.create_sprint("u1")
        db_client.update_sprint(sprint["id"], score=999)
        assert db_client.get_best_sprint() is None

    def test_returns_highest_score_among_finished(self):
        s1 = db_client.create_sprint("u1")
        s2 = db_client.create_sprint("u2")
        now = datetime.now(timezone.utc)
        db_client.update_sprint(s1["id"], score=30, finished_at=now)
        db_client.update_sprint(s2["id"], score=50, finished_at=now)
        assert db_client.get_best_sprint()["id"] == s2["id"]

    def test_best_sprint_visible_across_users(self):
        """Le mode Ghost est public (US 11.2) : pas d'isolation par user_id."""
        sprint = db_client.create_sprint("owner")
        db_client.update_sprint(sprint["id"], score=40, finished_at=datetime.now(timezone.utc))
        best = db_client.get_best_sprint()
        assert best["user_id"] == "owner"
