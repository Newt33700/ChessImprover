"""Tests d'intégration — GET /api/v1/stats/elo-curve (EPIC 24).

Client Chess.com mocké : aucun appel réseau.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers import games as games_router_module
from app.routers.auth import router as auth_router
from app.routers.games import router as games_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(games_router)
client = TestClient(_app)


class _FakeChessComClient:
    def __init__(self, games=None, error: Exception | None = None):
        self.games = games or []
        self.error = error
        self.calls: list = []

    async def get_games_for_months(self, username: str, months):
        self.calls.append((username, list(months)))
        if self.error is not None:
            raise self.error
        return self.games


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _signup(chess_username="fabdek") -> str:
    r = client.post(
        "/auth/signup",
        json={"email": "alice@ex.com", "username": "alice", "password": "pass123"},
    )
    token = r.json()["token"]
    if chess_username:
        db_client.update_chess_username(r.json()["user"]["id"], chess_username)
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _install_fake(monkeypatch, fake) -> None:
    monkeypatch.setattr(games_router_module, "_get_chess_com_client", lambda: fake)


def _raw_blitz(days_ago: int, rating: int) -> dict:
    end = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "time_class": "blitz",
        "end_time": int(end.timestamp()),
        "white": {"username": "fabdek", "rating": rating},
        "black": {"username": "adv", "rating": 999},
    }


class TestEloCurve:
    def test_requires_jwt(self):
        assert client.get("/api/v1/stats/elo-curve").status_code in (401, 403)

    def test_unknown_cadence_returns_422(self, monkeypatch):
        token = _signup()
        _install_fake(monkeypatch, _FakeChessComClient())
        r = client.get(
            "/api/v1/stats/elo-curve",
            params={"cadence": "hyperbullet"},
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_without_chess_username_returns_422(self, monkeypatch):
        token = _signup(chess_username=None)
        _install_fake(monkeypatch, _FakeChessComClient())
        r = client.get("/api/v1/stats/elo-curve", headers=_auth(token))
        assert r.status_code == 422

    def test_returns_daily_points_for_cadence(self, monkeypatch):
        token = _signup()
        fake = _FakeChessComClient([_raw_blitz(2, 1200), _raw_blitz(1, 1215)])
        _install_fake(monkeypatch, fake)
        r = client.get(
            "/api/v1/stats/elo-curve",
            params={"cadence": "blitz", "days": 7},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["cadence"] == "blitz"
        assert body["days"] == 7
        assert [p["rating"] for p in body["points"]] == [1200, 1215]

    def test_months_match_requested_window(self, monkeypatch):
        token = _signup()
        fake = _FakeChessComClient([])
        _install_fake(monkeypatch, fake)
        client.get("/api/v1/stats/elo-curve", params={"days": 90}, headers=_auth(token))
        _, months = fake.calls[0]
        # 90 jours couvrent 3 à 4 mois calendaires selon la date du jour.
        assert 3 <= len(months) <= 4

    def test_defaults_blitz_30_days(self, monkeypatch):
        token = _signup()
        _install_fake(monkeypatch, _FakeChessComClient([]))
        r = client.get("/api/v1/stats/elo-curve", headers=_auth(token))
        assert r.json() == {"cadence": "blitz", "days": 30, "points": []}

    def test_days_out_of_bounds_rejected(self, monkeypatch):
        token = _signup()
        _install_fake(monkeypatch, _FakeChessComClient([]))
        assert (
            client.get(
                "/api/v1/stats/elo-curve", params={"days": 0}, headers=_auth(token)
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/api/v1/stats/elo-curve", params={"days": 400}, headers=_auth(token)
            ).status_code
            == 422
        )

    def test_chess_com_unavailable_returns_502(self, monkeypatch):
        token = _signup()
        _install_fake(monkeypatch, _FakeChessComClient(error=RuntimeError("boom")))
        r = client.get("/api/v1/stats/elo-curve", headers=_auth(token))
        assert r.status_code == 502
        assert "boom" not in r.json()["detail"]
