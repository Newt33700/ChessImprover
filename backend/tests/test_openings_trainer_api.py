"""Tests d'intégration — routes de l'entraîneur d'ouvertures (EPIC 9, US 9.1/9.2).

App de test minimale (auth + openings_trainer routers), même motif que
test_tactics_api.py. Toutes les routes exigent un JWT valide.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.openings_trainer import router as openings_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(openings_router)
client = TestClient(_app)


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


class TestCreateLine:
    def test_valid_line_is_created_with_default_srs_schedule(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/repertoire",
            json={"name": "Ruy Lopez", "color": "white", "moves": ["e4", "e5", "Nf3", "Nc6", "Bb5"]},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Ruy Lopez"
        assert body["ease_factor"] == 2.5
        assert body["interval_days"] == 1
        assert body["repetitions"] == 0

    def test_invalid_move_sequence_returns_422(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/repertoire",
            json={"name": "Bad", "color": "white", "moves": ["e4", "e5", "Bxh7"]},
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_invalid_color_returns_422(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/repertoire",
            json={"name": "X", "color": "purple", "moves": ["e4"]},
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_without_token_returns_401_or_403(self):
        r = client.post(
            "/api/v1/openings/repertoire", json={"name": "X", "color": "white", "moves": ["e4"]},
        )
        assert r.status_code in (401, 403)


class TestListLines:
    def test_lists_only_own_lines(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        client.post(
            "/api/v1/openings/repertoire",
            json={"name": "A", "color": "white", "moves": ["e4"]},
            headers=_auth(token_a),
        )
        r = client.get("/api/v1/openings/repertoire", headers=_auth(token_b))
        assert r.json() == []

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/openings/repertoire").status_code in (401, 403)


class TestDueLines:
    def test_freshly_created_line_is_due_today(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/openings/repertoire",
            json={"name": "A", "color": "white", "moves": ["e4"]},
            headers=_auth(token),
        )
        r = client.get("/api/v1/openings/repertoire/due", headers=_auth(token))
        assert len(r.json()) == 1


class TestReviewLine:
    def _create_line(self, token: str) -> str:
        r = client.post(
            "/api/v1/openings/repertoire",
            json={"name": "A", "color": "white", "moves": ["e4"]},
            headers=_auth(token),
        )
        return r.json()["id"]

    def test_perfect_review_schedules_next_day(self):
        token = _signup_and_token()
        line_id = self._create_line(token)
        r = client.post(
            f"/api/v1/openings/repertoire/{line_id}/review",
            json={"mistake_count": 0},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["repetitions"] == 1
        assert body["interval_days"] == 1

    def test_failed_review_resets_repetitions(self):
        token = _signup_and_token()
        line_id = self._create_line(token)
        r = client.post(
            f"/api/v1/openings/repertoire/{line_id}/review",
            json={"mistake_count": 3},
            headers=_auth(token),
        )
        assert r.json()["repetitions"] == 0

    def test_unknown_line_returns_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/repertoire/missing/review",
            json={"mistake_count": 0},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_cannot_review_another_users_line(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        line_id = self._create_line(token_a)
        r = client.post(
            f"/api/v1/openings/repertoire/{line_id}/review",
            json={"mistake_count": 0},
            headers=_auth(token_b),
        )
        assert r.status_code == 404

    def test_without_token_returns_401_or_403(self):
        r = client.post("/api/v1/openings/repertoire/x/review", json={"mistake_count": 0})
        assert r.status_code in (401, 403)


class TestDeleteLine:
    def test_owner_can_delete(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/repertoire",
            json={"name": "A", "color": "white", "moves": ["e4"]},
            headers=_auth(token),
        )
        line_id = r.json()["id"]
        r2 = client.delete(f"/api/v1/openings/repertoire/{line_id}", headers=_auth(token))
        assert r2.status_code == 200
        assert r2.json() == {"deleted": True}

    def test_non_owner_cannot_delete(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        r = client.post(
            "/api/v1/openings/repertoire",
            json={"name": "A", "color": "white", "moves": ["e4"]},
            headers=_auth(token_a),
        )
        line_id = r.json()["id"]
        r2 = client.delete(f"/api/v1/openings/repertoire/{line_id}", headers=_auth(token_b))
        assert r2.status_code == 404

    def test_unknown_line_returns_404(self):
        token = _signup_and_token()
        r = client.delete("/api/v1/openings/repertoire/missing", headers=_auth(token))
        assert r.status_code == 404

    def test_without_token_returns_401_or_403(self):
        assert client.delete("/api/v1/openings/repertoire/x").status_code in (401, 403)
