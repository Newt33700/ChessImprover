"""Tests d'intégration — routes EPIC 1 (US 1.1 / 1.2 + /stats/summary).

App de test minimale (games router seul) pour éviter le lifespan de app.main.
Le TestClient Starlette exécute les BackgroundTasks après la réponse, donc
l'analyse est terminée au moment des assertions suivantes.
"""

from __future__ import annotations

import io

import chess
import chess.pgn
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.games import router as games_router

_app = FastAPI()
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


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestAnalyzeEndpoint:
    def test_accepts_pgn_returns_202(self):
        r = client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN),
        })
        assert r.status_code == 202
        body = r.json()
        assert len(body["accepted"]) == 1
        assert body["accepted"][0]["status"] == "processing"
        assert body["accepted"][0]["game_id"]

    def test_missing_pgn_and_ids_400(self):
        r = client.post("/api/v1/games/analyze", json={})
        assert r.status_code == 400

    def test_background_completes_and_persists_moves(self):
        r = client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "evals": _evals(PGN),
        })
        gid = r.json()["accepted"][0]["game_id"]
        # Le worker a tourné (TestClient exécute les BackgroundTasks).
        game = db_client.get_game(gid)
        assert game["status"] == "completed"
        assert game["result"] == "1-0"
        assert len(db_client.get_moves_for_game(gid)) == 6

    def test_reanalyze_by_game_id(self):
        first = client.post("/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)})
        gid = first.json()["accepted"][0]["game_id"]
        r = client.post("/api/v1/games/analyze", json={"game_ids": [gid], "evals": _evals(PGN)})
        assert r.status_code == 202
        assert r.json()["accepted"][0]["game_id"] == gid
        assert db_client.get_game(gid)["status"] == "completed"

    def test_analysis_records_progress_snapshot(self):
        # US 5.1 : une analyse réussie avec cadence connue enregistre un snapshot.
        r = client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN, played=40),
        })
        gid = r.json()["accepted"][0]["game_id"]
        history = db_client.get_progress_history("u1", "blitz")
        assert len(history) == 1
        assert history[0]["game_id"] == gid
        assert history[0]["elo_openings"] == 2900  # ACPL 0 → 2800 base + 100 bonus blitz

    def test_analysis_without_cadence_records_no_snapshot(self):
        # time_control absent → classify_cadence renvoie None → pas de snapshot.
        client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "user_id": "u1", "evals": _evals(PGN),
        })
        assert db_client.get_progress_history("u1", "blitz") == []

    def test_reanalyze_records_second_snapshot(self):
        first = client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN),
        })
        gid = first.json()["accepted"][0]["game_id"]
        client.post("/api/v1/games/analyze", json={"game_ids": [gid], "evals": _evals(PGN)})
        # Le time_control/user_id du jeu existant sont repris → 2 snapshots au total.
        assert len(db_client.get_progress_history("u1", "blitz")) == 2

    def test_unknown_game_id_skipped(self):
        r = client.post("/api/v1/games/analyze", json={"game_ids": ["does-not-exist"]})
        assert r.status_code == 202
        assert r.json()["accepted"] == []


class TestGetGame:
    def test_get_game_with_moves(self):
        r = client.post("/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)})
        gid = r.json()["accepted"][0]["game_id"]
        g = client.get(f"/api/v1/games/{gid}")
        assert g.status_code == 200
        assert g.json()["game"]["id"] == gid
        assert len(g.json()["moves"]) == 6

    def test_unknown_game_404(self):
        assert client.get("/api/v1/games/missing").status_code == 404


class TestStatsSummary:
    def test_summary_after_analysis(self):
        client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN, played=40),
        })
        s = client.get("/api/v1/stats/summary", params={"period": "30d", "user_id": "u1"})
        assert s.status_code == 200
        body = s.json()
        assert body["period"] == "30d"
        # 6 coups d'ouverture, CPL 0 → ACPL 0 → base 2800 + bonus blitz 100
        assert body["rows"]["blitz"]["openings"] == 2900

    def test_summary_empty(self):
        s = client.get("/api/v1/stats/summary")
        assert s.status_code == 200
        assert set(s.json()["rows"]) == {"bullet", "blitz", "rapid"}

    def test_summary_degrades_on_db_error(self, monkeypatch):
        # Une erreur d'accès aux données ne doit PAS produire un 500.
        def boom(*_a, **_k):
            raise RuntimeError("db down")

        monkeypatch.setattr("app.routers.games.db_client.get_completed_games", boom)
        s = client.get("/api/v1/stats/summary", params={"period": "7d"})
        assert s.status_code == 200
        assert s.json()["period"] == "7d"
        assert set(s.json()["rows"]) == {"bullet", "blitz", "rapid"}


class TestStatsHistory:
    def test_history_after_analysis(self):
        client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN, played=40),
        })
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz", "user_id": "u1"})
        assert r.status_code == 200
        body = r.json()
        assert body["cadence"] == "blitz"
        assert body["days"] == 30
        assert len(body["history"]) == 1
        point = body["history"][0]
        assert point["openings"] == 2900
        assert "date" in point and point["date"]

    def test_history_empty(self):
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz"})
        assert r.status_code == 200
        assert r.json()["history"] == []

    def test_history_wrong_cadence_returns_empty(self):
        client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN),
        })
        r = client.get("/api/v1/stats/history", params={"cadence": "bullet", "user_id": "u1"})
        assert r.json()["history"] == []

    def test_history_respects_days_window(self):
        client.post("/api/v1/games/analyze", json={
            "pgn": PGN, "time_control": "300", "user_id": "u1", "evals": _evals(PGN),
        })
        # La fenêtre par défaut (30j) couvre le snapshot qui vient d'être créé ;
        # une fenêtre de 0 jour est rejetée par la validation FastAPI (ge=1).
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz", "user_id": "u1", "days": 1})
        assert len(r.json()["history"]) == 1

    def test_history_invalid_days_rejected(self):
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz", "days": 0})
        assert r.status_code == 422

    def test_history_degrades_on_db_error(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("db down")

        monkeypatch.setattr("app.routers.games.db_client.get_progress_history", boom)
        r = client.get("/api/v1/stats/history", params={"cadence": "blitz"})
        assert r.status_code == 200
        assert r.json()["history"] == []
