"""Tests d'intégration — EPIC 29 (US 29.2) : GET /api/v1/quests/daily."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.quests import _counts_for_today, _is_today
from app.routers.quests import router as quests_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(quests_router)
client = TestClient(_app)


def _signup_and_token(email="alice@ex.com", username="alice") -> str:
    r = client.post("/auth/signup", json={"email": email, "username": username, "password": "pass123"})
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestIsToday:
    def test_datetime_object_today(self):
        today_iso = datetime.now(timezone.utc).date().isoformat()
        assert _is_today(datetime.now(timezone.utc), today_iso) is True

    def test_datetime_object_yesterday(self):
        today_iso = datetime.now(timezone.utc).date().isoformat()
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        assert _is_today(yesterday, today_iso) is False

    def test_iso_string_today(self):
        today_iso = datetime.now(timezone.utc).date().isoformat()
        assert _is_today(f"{today_iso}T10:00:00+00:00", today_iso) is True

    def test_none_is_never_today(self):
        assert _is_today(None, "2026-07-04") is False


class TestCountsForToday:
    def test_fresh_user_all_zero(self):
        user = db_client.create_user("a@ex.com", "alice", "hash")
        today_iso = datetime.now(timezone.utc).date().isoformat()
        counts = _counts_for_today(user["id"], today_iso)
        assert counts == {"games_analyzed": 0, "tactics_solved": 0, "sprints_finished": 0}

    def test_counts_games_created_today(self):
        user = db_client.create_user("b@ex.com", "bob", "hash")
        db_client.create_game(pgn="x", user_id=user["id"])
        db_client.create_game(pgn="y", user_id=user["id"])
        today_iso = datetime.now(timezone.utc).date().isoformat()
        assert _counts_for_today(user["id"], today_iso)["games_analyzed"] == 2

    def test_counts_only_successful_tactics_attempts(self):
        user = db_client.create_user("c@ex.com", "carol", "hash")
        db_client.record_tactical_attempt(user["id"], "p1", "fork", True, 5.0)
        db_client.record_tactical_attempt(user["id"], "p2", "fork", False, 5.0)
        today_iso = datetime.now(timezone.utc).date().isoformat()
        assert _counts_for_today(user["id"], today_iso)["tactics_solved"] == 1

    def test_counts_only_finished_sprints(self):
        user = db_client.create_user("d@ex.com", "dave", "hash")
        s1 = db_client.create_sprint(user["id"])
        db_client.update_sprint(s1["id"], finished_at=datetime.now(timezone.utc), duration_seconds=60)
        db_client.create_sprint(user["id"])  # jamais terminé
        today_iso = datetime.now(timezone.utc).date().isoformat()
        assert _counts_for_today(user["id"], today_iso)["sprints_finished"] == 1

    def test_yesterday_activity_not_counted(self):
        user = db_client.create_user("e@ex.com", "eve", "hash")
        game = db_client.create_game(pgn="x", user_id=user["id"])
        game["created_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        today_iso = datetime.now(timezone.utc).date().isoformat()
        assert _counts_for_today(user["id"], today_iso)["games_analyzed"] == 0


class TestDailyQuestsEndpoint:
    def test_returns_three_quests_for_fresh_user(self):
        token = _signup_and_token()
        r = client.get("/api/v1/quests/daily", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert len(body["quests"]) == 3
        assert all(q["progress"] == 0 and q["completed"] is False for q in body["quests"])

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/quests/daily").status_code in (401, 403)

    def test_same_day_returns_same_quests(self):
        token = _signup_and_token()
        r1 = client.get("/api/v1/quests/daily", headers=_auth(token))
        r2 = client.get("/api/v1/quests/daily", headers=_auth(token))
        ids1 = [q["id"] for q in r1.json()["quests"]]
        ids2 = [q["id"] for q in r2.json()["quests"]]
        assert ids1 == ids2

    def test_response_includes_todays_date(self):
        token = _signup_and_token()
        r = client.get("/api/v1/quests/daily", headers=_auth(token))
        assert r.json()["date"] == datetime.now(timezone.utc).date().isoformat()
