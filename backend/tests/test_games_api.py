"""Tests d'intégration — routes EPIC 1 (US 1.1 / 1.2 + /stats/summary) + US 6.4.

App de test minimale (games + auth routers) pour éviter le lifespan de
app.main. Le TestClient Starlette exécute les BackgroundTasks après la
réponse, donc l'analyse est terminée au moment des assertions suivantes.

Depuis US 6.4, toutes les routes games/stats exigent un JWT valide et
dérivent `user_id` du token — jamais d'un champ/paramètre client.
"""

from __future__ import annotations

import io

import chess
import chess.pgn
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.games import router as games_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(games_router)
client = TestClient(_app)

PGN = '[Event "x"][Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0'


def _evals(pgn, played=40):
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    evals = {}
    for move in game.mainline_moves():
        evals[board.fen()] = [["0000", played], [move.uci(), played]]
        board.push(move)
    return evals


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


class TestAnalyzeEndpoint:
    def test_accepts_pgn_returns_202(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN)},
            headers=_auth(token),
        )
        assert r.status_code == 202
        body = r.json()
        assert len(body["accepted"]) == 1
        assert body["accepted"][0]["status"] == "processing"
        assert body["accepted"][0]["game_id"]

    def test_without_token_returns_401_or_403(self):
        r = client.post("/api/v1/games/analyze", json={"pgn": PGN})
        assert r.status_code in (401, 403)

    def test_missing_pgn_and_ids_400(self):
        token = _signup_and_token()
        r = client.post("/api/v1/games/analyze", json={}, headers=_auth(token))
        assert r.status_code == 400

    def test_background_completes_and_persists_moves(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN)},
            headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        # Le worker a tourné (TestClient exécute les BackgroundTasks).
        game = db_client.get_game(gid)
        assert game["status"] == "completed"
        assert game["result"] == "1-0"
        assert len(db_client.get_moves_for_game(gid)) == 6

    def test_game_is_owned_by_authenticated_user(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        assert db_client.get_game(gid)["user_id"] is not None

    def test_reanalyze_by_game_id(self):
        token = _signup_and_token()
        first = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        gid = first.json()["accepted"][0]["game_id"]
        r = client.post(
            "/api/v1/games/analyze", json={"game_ids": [gid], "evals": _evals(PGN)}, headers=_auth(token),
        )
        assert r.status_code == 202
        assert r.json()["accepted"][0]["game_id"] == gid
        assert db_client.get_game(gid)["status"] == "completed"

    def test_reanalyze_skips_game_owned_by_another_user(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        first = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token_a),
        )
        gid = first.json()["accepted"][0]["game_id"]
        r = client.post(
            "/api/v1/games/analyze", json={"game_ids": [gid], "evals": _evals(PGN)}, headers=_auth(token_b),
        )
        assert r.status_code == 202
        assert r.json()["accepted"] == []  # ignoré : ne appartient pas à userb

    def test_analysis_records_progress_snapshot(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN, played=40)},
            headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        user_id = db_client.get_game(gid)["user_id"]
        history = db_client.get_progress_history(user_id, "blitz")
        assert len(history) == 1
        assert history[0]["game_id"] == gid
        assert history[0]["elo_openings"] == 2900  # ACPL 0 → 2800 base + 100 bonus blitz

    def test_analysis_without_cadence_records_no_snapshot(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        user_id = db_client.get_game(gid)["user_id"]
        assert db_client.get_progress_history(user_id, "blitz") == []

    def test_reanalyze_records_second_snapshot(self):
        token = _signup_and_token()
        first = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN)},
            headers=_auth(token),
        )
        gid = first.json()["accepted"][0]["game_id"]
        client.post(
            "/api/v1/games/analyze", json={"game_ids": [gid], "evals": _evals(PGN)}, headers=_auth(token),
        )
        user_id = db_client.get_game(gid)["user_id"]
        # Le time_control/user_id du jeu existant sont repris → 2 snapshots au total.
        assert len(db_client.get_progress_history(user_id, "blitz")) == 2

    def test_unknown_game_id_skipped(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze", json={"game_ids": ["does-not-exist"]}, headers=_auth(token),
        )
        assert r.status_code == 202
        assert r.json()["accepted"] == []


class TestListGames:
    def test_lists_own_games(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        r = client.get("/api/v1/games", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()["games"]) == 1

    def test_empty_when_no_games(self):
        token = _signup_and_token()
        r = client.get("/api/v1/games", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["games"] == []

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/games").status_code in (401, 403)

    def test_does_not_include_other_users_games(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token_a),
        )
        r_b = client.get("/api/v1/games", headers=_auth(token_b))
        assert r_b.json()["games"] == []


class TestGetGame:
    def test_get_game_with_moves(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        g = client.get(f"/api/v1/games/{gid}", headers=_auth(token))
        assert g.status_code == 200
        assert g.json()["game"]["id"] == gid
        assert len(g.json()["moves"]) == 6

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/games/whatever").status_code in (401, 403)

    def test_unknown_game_404(self):
        token = _signup_and_token()
        assert client.get("/api/v1/games/missing", headers=_auth(token)).status_code == 404

    def test_other_users_game_returns_404(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        r = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token_a),
        )
        gid = r.json()["accepted"][0]["game_id"]
        g = client.get(f"/api/v1/games/{gid}", headers=_auth(token_b))
        assert g.status_code == 404


class TestStatsSummary:
    def test_summary_after_analysis(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN, played=40)},
            headers=_auth(token),
        )
        s = client.get("/api/v1/stats/summary", params={"period": "30d"}, headers=_auth(token))
        assert s.status_code == 200
        body = s.json()
        assert body["period"] == "30d"
        # 6 coups d'ouverture, CPL 0 → ACPL 0 → base 2800 + bonus blitz 100
        assert body["rows"]["blitz"]["openings"] == 2900

    def test_summary_is_scoped_to_authenticated_user(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN, played=40)},
            headers=_auth(token_a),
        )
        s_b = client.get("/api/v1/stats/summary", params={"period": "30d"}, headers=_auth(token_b))
        # userb n'a analysé aucune partie : Elo par défaut (1200), pas celui d'usera (2900).
        assert s_b.json()["rows"]["blitz"]["openings"] == 1200

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/stats/summary").status_code in (401, 403)

    def test_summary_empty(self):
        token = _signup_and_token()
        s = client.get("/api/v1/stats/summary", headers=_auth(token))
        assert s.status_code == 200
        assert set(s.json()["rows"]) == {"bullet", "blitz", "rapid"}

    def test_summary_degrades_on_db_error(self, monkeypatch):
        # Une erreur d'accès aux données ne doit PAS produire un 500.
        def boom(*_a, **_k):
            raise RuntimeError("db down")

        token = _signup_and_token()
        monkeypatch.setattr("app.routers.games.db_client.get_completed_games", boom)
        s = client.get("/api/v1/stats/summary", params={"period": "7d"}, headers=_auth(token))
        assert s.status_code == 200
        assert s.json()["period"] == "7d"
        assert set(s.json()["rows"]) == {"bullet", "blitz", "rapid"}


class TestStatsHistory:
    def test_history_after_analysis(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN, played=40)},
            headers=_auth(token),
        )
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz"}, headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["cadence"] == "blitz"
        assert body["days"] == 30
        assert len(body["history"]) == 1
        point = body["history"][0]
        assert point["openings"] == 2900
        assert "date" in point and point["date"]

    def test_history_is_scoped_to_authenticated_user(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN)},
            headers=_auth(token_a),
        )
        r_b = client.get("/api/v1/stats/history", params={"cadence": "blitz"}, headers=_auth(token_b))
        assert r_b.json()["history"] == []

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/stats/history").status_code in (401, 403)

    def test_history_empty(self):
        token = _signup_and_token()
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["history"] == []

    def test_history_wrong_cadence_returns_empty(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN)},
            headers=_auth(token),
        )
        r = client.get("/api/v1/stats/history", params={"cadence": "bullet"}, headers=_auth(token))
        assert r.json()["history"] == []

    def test_history_respects_days_window(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "time_control": "300", "evals": _evals(PGN)},
            headers=_auth(token),
        )
        # La fenêtre par défaut (30j) couvre le snapshot qui vient d'être créé ;
        # une fenêtre de 0 jour est rejetée par la validation FastAPI (ge=1).
        r = client.get(
            "/api/v1/stats/history", params={"cadence": "blitz", "days": 1}, headers=_auth(token),
        )
        assert len(r.json()["history"]) == 1

    def test_history_invalid_days_rejected(self):
        token = _signup_and_token()
        r = client.get(
            "/api/v1/stats/history", params={"cadence": "blitz", "days": 0}, headers=_auth(token),
        )
        assert r.status_code == 422

    def test_history_degrades_on_db_error(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("db down")

        token = _signup_and_token()
        monkeypatch.setattr("app.routers.games.db_client.get_progress_history", boom)
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["history"] == []
