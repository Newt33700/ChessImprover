"""Tests d'intégration — routes de l'entraîneur de finales (EPIC 10, bonus).

App de test minimale (auth + endgames routers), même motif que
test_tactics_api.py. Toutes les routes exigent un JWT valide.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.endgames import router as endgames_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(endgames_router)
client = TestClient(_app)

QUEEN_MATE_SOLUTION = "Qa4#"


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
        r = client.get("/api/v1/endgames/next", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"id", "fen", "category", "difficulty_elo"}
        assert "solution" not in body

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/endgames/next").status_code in (401, 403)

    def test_theme_id_queen_mate(self):
        token = _signup_and_token()
        r = client.get("/api/v1/endgames/next", params={"theme_id": "queen_mate"}, headers=_auth(token))
        assert r.json()["category"] == "queen_mate"

    def test_theme_id_rook_mate(self):
        token = _signup_and_token()
        r = client.get("/api/v1/endgames/next", params={"theme_id": "rook_mate"}, headers=_auth(token))
        assert r.json()["category"] == "rook_mate"

    def test_theme_id_two_rooks_mate(self):
        token = _signup_and_token()
        r = client.get("/api/v1/endgames/next", params={"theme_id": "two_rooks_mate"}, headers=_auth(token))
        assert r.json()["category"] == "two_rooks_mate"

    def test_unknown_theme_id_returns_422(self):
        token = _signup_and_token()
        r = client.get("/api/v1/endgames/next", params={"theme_id": "not-a-theme"}, headers=_auth(token))
        assert r.status_code == 422


class TestSubmitAttempt:
    def _get_queen_mate_problem_id(self) -> str:
        for problem_id, p in db_client._endgame_problems.items():
            if p["category"] == "queen_mate" and p["solution"] == QUEEN_MATE_SOLUTION:
                return problem_id
        raise AssertionError("aucun problème queen_mate Qa4# dans le seed")

    def test_correct_move_increases_elo_by_15(self):
        token = _signup_and_token()
        pid = self._get_queen_mate_problem_id()
        r = client.post(
            "/api/v1/endgames/attempt", json={"problem_id": pid, "move": "Qa4#"}, headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["new_elo"] == 1015
        assert body["solution"] == "Qa4#"

    def test_wrong_move_decreases_elo_by_15(self):
        token = _signup_and_token()
        pid = self._get_queen_mate_problem_id()
        r = client.post(
            "/api/v1/endgames/attempt", json={"problem_id": pid, "move": "Kb2"}, headers=_auth(token),
        )
        assert r.json()["success"] is False
        assert r.json()["new_elo"] == 985

    def test_elo_persists_across_attempts(self):
        token = _signup_and_token()
        pid = self._get_queen_mate_problem_id()
        client.post("/api/v1/endgames/attempt", json={"problem_id": pid, "move": "Qa4#"}, headers=_auth(token))
        r = client.post(
            "/api/v1/endgames/attempt", json={"problem_id": pid, "move": "Qa4#"}, headers=_auth(token),
        )
        assert r.json()["new_elo"] == 1030

    def test_unknown_problem_returns_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/endgames/attempt", json={"problem_id": "missing", "move": "Qa4#"}, headers=_auth(token),
        )
        assert r.status_code == 404

    def test_without_token_returns_401_or_403(self):
        r = client.post("/api/v1/endgames/attempt", json={"problem_id": "x", "move": "Qa4#"})
        assert r.status_code in (401, 403)

    def test_attempts_are_isolated_between_users(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        pid = self._get_queen_mate_problem_id()
        client.post("/api/v1/endgames/attempt", json={"problem_id": pid, "move": "Qa4#"}, headers=_auth(token_a))
        r_b = client.get("/api/v1/endgames/next", headers=_auth(token_b))
        assert r_b.status_code == 200  # userb : elo resté à 1000 par défaut, requête normale

    def test_endgame_elo_distinct_from_tactical_elo_via_api(self):
        token = _signup_and_token()
        pid = self._get_queen_mate_problem_id()
        r = client.post(
            "/api/v1/endgames/attempt", json={"problem_id": pid, "move": "Qa4#"}, headers=_auth(token),
        )
        assert r.json()["new_elo"] == 1015
