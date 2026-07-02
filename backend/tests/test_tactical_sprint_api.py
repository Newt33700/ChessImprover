"""Tests d'intégration — EPIC 12 (US 11.1/11.2) : mode Tactical Sprint.

App de test minimale (auth + tactical_sprint routers). Le chrono est vérifié
en manipulant directement `started_at` dans le store (au lieu de mocker
`datetime.now`), pour simuler un sprint expiré sans attendre réellement.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.tactical_sprint import SPRINT_DURATION_SECONDS
from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.tactical_sprint import router as sprint_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(sprint_router)
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


class TestStartSprint:
    def test_returns_sprint_id_duration_and_first_problem(self):
        token = _signup_and_token()
        r = client.post("/api/v1/sprints/start", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["duration_seconds"] == SPRINT_DURATION_SECONDS
        assert body["sprint_id"]
        assert "fen" in body["problem"] and "solution" not in body["problem"]

    def test_without_token_returns_401_or_403(self):
        r = client.post("/api/v1/sprints/start")
        assert r.status_code in (401, 403)


class TestSprintAttempt:
    def _start(self, token):
        return client.post("/api/v1/sprints/start", headers=_auth(token)).json()

    def test_correct_move_increments_score_and_returns_next_problem(self):
        token = _signup_and_token()
        started = self._start(token)
        problem = db_client.get_tactical_problem(started["problem"]["id"])

        r = client.post(
            f"/api/v1/sprints/{started['sprint_id']}/attempt",
            json={"problem_id": problem["id"], "move": problem["solution"]},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["score"] == 10
        assert body["problems_solved_count"] == 1
        assert body["sprint_active"] is True
        assert body["next_problem"] is not None

    def test_incorrect_move_does_not_increment_score(self):
        token = _signup_and_token()
        started = self._start(token)
        problem = db_client.get_tactical_problem(started["problem"]["id"])

        r = client.post(
            f"/api/v1/sprints/{started['sprint_id']}/attempt",
            json={"problem_id": problem["id"], "move": "a1a1"},
            headers=_auth(token),
        )
        body = r.json()
        assert body["success"] is False
        assert body["score"] == 0
        assert body["problems_solved_count"] == 0

    def test_expired_sprint_rejects_attempt_and_finalizes(self):
        token = _signup_and_token()
        started = self._start(token)
        problem = db_client.get_tactical_problem(started["problem"]["id"])
        # Simule un sprint démarré il y a longtemps (horloge serveur).
        past = datetime.now(timezone.utc) - timedelta(seconds=SPRINT_DURATION_SECONDS + 10)
        db_client.update_sprint(started["sprint_id"], started_at=past)

        r = client.post(
            f"/api/v1/sprints/{started['sprint_id']}/attempt",
            json={"problem_id": problem["id"], "move": problem["solution"]},
            headers=_auth(token),
        )
        body = r.json()
        assert body["sprint_active"] is False
        assert body["time_remaining"] == 0.0
        assert body["next_problem"] is None
        sprint = db_client.get_sprint(started["sprint_id"])
        assert sprint["finished_at"] is not None

    def test_unknown_sprint_is_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/sprints/does-not-exist/attempt",
            json={"problem_id": "x", "move": "e4"},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_sprint_owned_by_another_user_is_404(self):
        token_a = _signup_and_token("a@ex.com", "usera")
        token_b = _signup_and_token("b@ex.com", "userb")
        started = self._start(token_a)
        r = client.post(
            f"/api/v1/sprints/{started['sprint_id']}/attempt",
            json={"problem_id": started["problem"]["id"], "move": "e4"},
            headers=_auth(token_b),
        )
        assert r.status_code == 404

    def test_already_finished_sprint_returns_409(self):
        token = _signup_and_token()
        started = self._start(token)
        client.post(f"/api/v1/sprints/{started['sprint_id']}/finish", headers=_auth(token))
        r = client.post(
            f"/api/v1/sprints/{started['sprint_id']}/attempt",
            json={"problem_id": started["problem"]["id"], "move": "e4"},
            headers=_auth(token),
        )
        assert r.status_code == 409


class TestFinishSprint:
    def test_finish_persists_final_score_and_duration(self):
        token = _signup_and_token()
        started = client.post("/api/v1/sprints/start", headers=_auth(token)).json()
        problem = db_client.get_tactical_problem(started["problem"]["id"])
        client.post(
            f"/api/v1/sprints/{started['sprint_id']}/attempt",
            json={"problem_id": problem["id"], "move": problem["solution"]},
            headers=_auth(token),
        )
        r = client.post(f"/api/v1/sprints/{started['sprint_id']}/finish", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 10
        assert body["problems_solved_count"] == 1
        assert body["duration_seconds"] >= 0

    def test_finish_is_idempotent(self):
        token = _signup_and_token()
        started = client.post("/api/v1/sprints/start", headers=_auth(token)).json()
        r1 = client.post(f"/api/v1/sprints/{started['sprint_id']}/finish", headers=_auth(token))
        r2 = client.post(f"/api/v1/sprints/{started['sprint_id']}/finish", headers=_auth(token))
        assert r1.json() == r2.json()

    def test_unknown_sprint_is_404(self):
        token = _signup_and_token()
        r = client.post("/api/v1/sprints/does-not-exist/finish", headers=_auth(token))
        assert r.status_code == 404


class TestGhostReplay:
    def test_no_finished_sprint_yields_unavailable(self):
        token = _signup_and_token()
        r = client.get("/api/v1/sprints/ghost", headers=_auth(token))
        assert r.status_code == 200
        assert r.json() == {"available": False, "score": None, "moves": []}

    def test_returns_best_finished_sprint_moves(self):
        token_a = _signup_and_token("a@ex.com", "usera")
        token_b = _signup_and_token("b@ex.com", "userb")

        started_a = client.post("/api/v1/sprints/start", headers=_auth(token_a)).json()
        problem_a = db_client.get_tactical_problem(started_a["problem"]["id"])
        client.post(
            f"/api/v1/sprints/{started_a['sprint_id']}/attempt",
            json={"problem_id": problem_a["id"], "move": problem_a["solution"]},
            headers=_auth(token_a),
        )
        client.post(f"/api/v1/sprints/{started_a['sprint_id']}/finish", headers=_auth(token_a))

        started_b = client.post("/api/v1/sprints/start", headers=_auth(token_b)).json()
        client.post(f"/api/v1/sprints/{started_b['sprint_id']}/finish", headers=_auth(token_b))

        r = client.get("/api/v1/sprints/ghost", headers=_auth(token_b))
        body = r.json()
        assert body["available"] is True
        assert body["score"] == 10
        assert len(body["moves"]) == 1
        assert body["moves"][0]["problem_id"] == problem_a["id"]

    def test_without_token_returns_401_or_403(self):
        r = client.get("/api/v1/sprints/ghost")
        assert r.status_code in (401, 403)
