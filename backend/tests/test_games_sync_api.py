"""Tests d'intégration — POST /api/v1/games/sync (EPIC 23).

Client Chess.com mocké (aucun appel réseau). Les analyses de fond tournent
sans moteur (évaluations ``None``) : ``TestClient`` exécute les
``BackgroundTasks`` à la fin de chaque requête, donc les effets (statut
``completed``, parties persistées) sont observables immédiatement.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain import game_sync
from app.infrastructure import db_client
from app.routers import games as games_router_module
from app.routers.auth import router as auth_router
from app.routers.games import router as games_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(games_router)
client = TestClient(_app)

PGN_1 = '[White "fabdek"]\n[Black "adv1"]\n\n1. e4 e5 2. Nf3 Nc6 1-0'
PGN_2 = '[White "adv2"]\n[Black "fabdek"]\n\n1. d4 d5 2. c4 e6 0-1'
PGN_3 = '[White "fabdek"]\n[Black "adv3"]\n\n1. c4 c5 2. Nc3 Nc6 1/2-1/2'


def _raw(pgn: str, white: str = "fabdek", black: str = "adv", tc: str = "180") -> dict:
    return {
        "pgn": pgn,
        "time_control": tc,
        "white": {"username": white},
        "black": {"username": black},
    }


class _FakeChessComClient:
    """Client mocké : renvoie un jeu de parties fixé, mémorise les appels."""

    def __init__(self, games=None, error: Exception | None = None):
        self.games = games or []
        self.error = error
        self.calls: list = []

    async def get_latest_games(self, username: str, limit: int = 10):
        self.calls.append((username, limit))
        if self.error is not None:
            raise self.error
        return self.games


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _signup_with_chess_username(chess_username="fabdek") -> tuple[str, str]:
    r = client.post(
        "/auth/signup",
        json={
            "email": "alice@ex.com",
            "username": "alice",
            "password": "pass123",
        },
    )
    token = r.json()["token"]
    user_id = r.json()["user"]["id"]
    if chess_username:
        db_client.update_chess_username(user_id, chess_username)
    return token, user_id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _install_fake(monkeypatch, fake: _FakeChessComClient) -> None:
    monkeypatch.setattr(games_router_module, "_get_chess_com_client", lambda: fake)


class TestSyncGames:
    def test_requires_jwt(self):
        assert client.post("/api/v1/games/sync").status_code in (401, 403)

    def test_without_chess_username_returns_422(self, monkeypatch):
        token, _ = _signup_with_chess_username(chess_username=None)
        _install_fake(monkeypatch, _FakeChessComClient())
        r = client.post("/api/v1/games/sync", headers=_auth(token))
        assert r.status_code == 422

    def test_queues_new_games_and_completes_analysis(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        fake = _FakeChessComClient(
            [_raw(PGN_1), _raw(PGN_2, white="adv2", black="fabdek")]
        )
        _install_fake(monkeypatch, fake)

        r = client.post("/api/v1/games/sync", headers=_auth(token))
        assert r.status_code == 202
        body = r.json()
        assert body == {
            "fetched": 2,
            "queued": 2,
            "skipped": 0,
            "deferred": 0,
            "requeued": 0,
        }

        games = db_client.get_games_for_user(user_id)
        assert len(games) == 2
        # BackgroundTasks exécutées par TestClient : analyses terminées.
        assert {g["status"] for g in games} == {"completed"}

    def test_fetches_last_10_games(self, monkeypatch):
        token, _ = _signup_with_chess_username()
        fake = _FakeChessComClient([])
        _install_fake(monkeypatch, fake)
        client.post("/api/v1/games/sync", headers=_auth(token))
        assert fake.calls == [("fabdek", game_sync.FETCH_LAST_GAMES)]

    def test_second_sync_is_idempotent(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        fake = _FakeChessComClient([_raw(PGN_1)])
        _install_fake(monkeypatch, fake)

        client.post("/api/v1/games/sync", headers=_auth(token))
        r2 = client.post("/api/v1/games/sync", headers=_auth(token))
        body = r2.json()
        assert body["skipped"] == 1
        assert body["queued"] == 0
        assert len(db_client.get_games_for_user(user_id)) == 1

    def test_cap_of_5_new_analyses_per_sync(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        # 8 PGNs distincts (l'adversaire diffère dans les en-têtes → hash différent).
        raw_games = [
            _raw(f'[White "fabdek"]\n[Black "adv{i}"]\n\n1. e4 e5 2. Nf3 Nc6 1-0')
            for i in range(8)
        ]
        fake = _FakeChessComClient(raw_games)
        _install_fake(monkeypatch, fake)

        r = client.post("/api/v1/games/sync", headers=_auth(token))
        body = r.json()
        assert body["fetched"] == 8
        assert body["queued"] == game_sync.MAX_ANALYSES_PER_SYNC == 5
        assert body["deferred"] == 3
        assert len(db_client.get_games_for_user(user_id)) == 5

    def test_deferred_games_are_queued_on_next_sync(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        raw_games = [
            _raw(f'[White "fabdek"]\n[Black "adv{i}"]\n\n1. e4 e5 2. Nf3 Nc6 1-0')
            for i in range(8)
        ]
        _install_fake(monkeypatch, _FakeChessComClient(raw_games))

        client.post("/api/v1/games/sync", headers=_auth(token))
        r2 = client.post("/api/v1/games/sync", headers=_auth(token))
        body = r2.json()
        assert body["skipped"] == 5
        assert body["queued"] == 3
        assert len(db_client.get_games_for_user(user_id)) == 8

    def test_user_color_detected_from_black_side(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        fake = _FakeChessComClient([_raw(PGN_2, white="adv2", black="FabDek")])
        _install_fake(monkeypatch, fake)
        client.post("/api/v1/games/sync", headers=_auth(token))
        game = db_client.get_games_for_user(user_id)[0]
        assert game["user_color"] == "black"

    def test_chess_com_unavailable_returns_502(self, monkeypatch):
        token, _ = _signup_with_chess_username()
        _install_fake(monkeypatch, _FakeChessComClient(error=RuntimeError("boom")))
        r = client.post("/api/v1/games/sync", headers=_auth(token))
        assert r.status_code == 502
        # Message générique, sans fuite du détail interne.
        assert "boom" not in r.json()["detail"]

    def test_requeues_stale_processing_game(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        # Partie orpheline : processing depuis 1 h (instance endormie).
        stale = db_client.create_game(
            pgn=PGN_3,
            user_id=user_id,
            user_color="white",
            status="processing",
        )
        stale["created_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        _install_fake(monkeypatch, _FakeChessComClient([]))

        r = client.post("/api/v1/games/sync", headers=_auth(token))
        assert r.json()["requeued"] == 1
        assert db_client.get_game(stale["id"])["status"] == "completed"

    def test_recent_processing_game_is_not_requeued(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        db_client.create_game(
            pgn=PGN_3,
            user_id=user_id,
            user_color="white",
            status="processing",
        )
        _install_fake(monkeypatch, _FakeChessComClient([]))
        r = client.post("/api/v1/games/sync", headers=_auth(token))
        assert r.json()["requeued"] == 0

    def test_games_without_pgn_are_ignored(self, monkeypatch):
        token, user_id = _signup_with_chess_username()
        fake = _FakeChessComClient([{"time_control": "60"}, _raw(PGN_1)])
        _install_fake(monkeypatch, fake)
        r = client.post("/api/v1/games/sync", headers=_auth(token))
        body = r.json()
        assert body["fetched"] == 2
        assert body["queued"] == 1
        assert len(db_client.get_games_for_user(user_id)) == 1
