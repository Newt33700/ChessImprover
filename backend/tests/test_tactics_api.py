"""Tests d'intégration — routes tactiques (US 8.1, EPIC 8).

App de test minimale (auth + tactics routers) pour éviter le lifespan de
app.main. Toutes les routes exigent un JWT valide, comme games.py (US 6.4).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.tactics import router as tactics_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(tactics_router)
client = TestClient(_app)

MATE_IN_1_SOLUTION = "Ra8#"


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _signup_and_token(email="alice@ex.com", username="alice") -> str:
    r = client.post("/auth/signup", json={"email": email, "username": username, "password": "pass123"})
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestNextProblem:
    def test_returns_a_problem_without_solution(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/next", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"id", "fen", "category", "difficulty_elo"}
        assert "solution" not in body

    def test_new_user_gets_problem_near_default_1000(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/next", headers=_auth(token))
        # Le seed n'a pas de problème exactement à 1000 mais un proche.
        assert r.json()["difficulty_elo"] in {950, 1000, 1250}

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/tactics/next").status_code in (401, 403)

    def test_theme_id_mate_in_1(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/next", params={"theme_id": "mate_in_1"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["category"] == "mate_in_1"

    def test_theme_id_mate_in_2(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/next", params={"theme_id": "mate_in_2"}, headers=_auth(token))
        assert r.json()["category"] == "mate_in_2"

    def test_theme_id_hanging_piece(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/next", params={"theme_id": "hanging_piece"}, headers=_auth(token))
        assert r.json()["category"] == "hanging_piece"

    def test_unknown_theme_id_returns_422(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/next", params={"theme_id": "not-a-theme"}, headers=_auth(token))
        assert r.status_code == 422


class TestSubmitAttempt:
    def _get_mate_in_1_problem_id(self, token: str) -> str:
        # Force plusieurs tirages pour retomber sur un mate_in_1 identifiable
        # par sa solution connue (le pool contient plusieurs mate_in_1 à Ra8#).
        for problem_id, p in db_client._tactical_problems.items():
            if p["solution"] == MATE_IN_1_SOLUTION:
                return problem_id
        raise AssertionError("aucun problème Ra8# dans le seed")

    def test_correct_move_increases_elo_by_15(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id(token)
        r = client.post(
            "/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["new_elo"] == 1015
        assert body["solution"] == "Ra8#"
        assert body["streak"] == 1

    def test_wrong_move_decreases_elo_by_15(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id(token)
        r = client.post(
            "/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Kg1"}, headers=_auth(token),
        )
        body = r.json()
        assert body["success"] is False
        assert body["new_elo"] == 985
        assert body["streak"] == 0

    def test_equivalent_notation_without_check_symbol_is_accepted(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id(token)
        r = client.post(
            "/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8"}, headers=_auth(token),
        )
        assert r.json()["success"] is True

    def test_elo_persists_across_attempts(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id(token)
        client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token))
        r = client.post(
            "/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token),
        )
        assert r.json()["new_elo"] == 1030

    def test_unknown_problem_returns_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/tactics/attempt", json={"problem_id": "missing", "move": "Ra8#"}, headers=_auth(token),
        )
        assert r.status_code == 404

    def test_without_token_returns_401_or_403(self):
        r = client.post("/api/v1/tactics/attempt", json={"problem_id": "x", "move": "Ra8#"})
        assert r.status_code in (401, 403)

    def test_attempts_are_isolated_between_users(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        pid = self._get_mate_in_1_problem_id(token_a)
        client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token_a))
        r_b = client.get("/api/v1/tactics/next", headers=_auth(token_b))
        # userb n'a fait aucune tentative : son elo est resté à 1000 par défaut.
        assert r_b.json()["difficulty_elo"] in {950, 1000, 1250}

    def test_streak_increments_across_consecutive_successes_only(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id(token)
        r1 = client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token))
        r2 = client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token))
        r3 = client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Kg1"}, headers=_auth(token))
        assert [r1.json()["streak"], r2.json()["streak"], r3.json()["streak"]] == [1, 2, 0]

    def test_time_taken_is_optional(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id(token)
        r = client.post(
            "/api/v1/tactics/attempt",
            json={"problem_id": pid, "move": "Ra8#", "time_taken": 3.5},
            headers=_auth(token),
        )
        assert r.status_code == 200


class TestTacticsStats:
    def _get_mate_in_1_problem_id(self) -> str:
        for problem_id, p in db_client._tactical_problems.items():
            if p["solution"] == MATE_IN_1_SOLUTION:
                return problem_id
        raise AssertionError("aucun problème Ra8# dans le seed")

    def test_no_attempts_returns_empty_stats(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/stats", headers=_auth(token))
        assert r.status_code == 200
        assert r.json() == {"by_theme": [], "streak": 0}

    def test_stats_reflect_recorded_attempts(self):
        token = _signup_and_token()
        pid = self._get_mate_in_1_problem_id()
        client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Ra8#"}, headers=_auth(token))
        client.post("/api/v1/tactics/attempt", json={"problem_id": pid, "move": "Kg1"}, headers=_auth(token))

        r = client.get("/api/v1/tactics/stats", headers=_auth(token))
        body = r.json()
        assert body["by_theme"] == [
            {"category": "mate_in_1", "attempts": 2, "successes": 1, "success_rate": 0.5},
        ]
        assert body["streak"] == 0  # dernière tentative = échec

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/tactics/stats").status_code in (401, 403)
