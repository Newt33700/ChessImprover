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


def _evals_with_blunder(pgn, blunder_index, loss=300, base=40):
    """Comme `_evals`, mais le coup d'index `blunder_index` (0-based, ligne
    principale) perd `loss` centipions face à une meilleure ligne fictive
    (EPIC 15 — pivot de défaite)."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    evals = {}
    for i, move in enumerate(game.mainline_moves()):
        fen = board.fen()
        best = base + loss if i == blunder_index else base
        evals[fen] = [["0000", best], [move.uci(), base]]
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


class TestPgnHashDedup:
    """US 7.2 — un PGN déjà soumis par le même utilisateur n'est jamais réanalysé."""

    def test_same_pgn_same_user_returns_existing_game(self):
        token = _signup_and_token()
        first = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        second = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        assert first.json()["accepted"][0]["game_id"] == second.json()["accepted"][0]["game_id"]

    def test_same_pgn_same_user_does_not_duplicate_game(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        r = client.get("/api/v1/games", headers=_auth(token))
        assert len(r.json()["games"]) == 1

    def test_second_submission_reports_actual_status(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        # Le worker a déjà tourné (BackgroundTasks synchrones du TestClient) :
        # la 2e soumission doit refléter le statut réel, pas "processing" par défaut.
        second = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        assert second.json()["accepted"][0]["status"] == "completed"

    def test_same_pgn_different_users_creates_separate_games(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        r_a = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token_a),
        )
        r_b = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token_b),
        )
        assert r_a.json()["accepted"][0]["game_id"] != r_b.json()["accepted"][0]["game_id"]
        assert len(client.get("/api/v1/games", headers=_auth(token_a)).json()["games"]) == 1
        assert len(client.get("/api/v1/games", headers=_auth(token_b)).json()["games"]) == 1

    def test_different_pgn_same_user_creates_separate_games(self):
        token = _signup_and_token()
        other_pgn = '[Event "y"][Result "0-1"]\n\n1. d4 d5 0-1'
        r1 = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        r2 = client.post(
            "/api/v1/games/analyze", json={"pgn": other_pgn}, headers=_auth(token),
        )
        assert r1.json()["accepted"][0]["game_id"] != r2.json()["accepted"][0]["game_id"]


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

    def test_new_game_defaults_to_not_reviewed(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        r = client.get("/api/v1/games", headers=_auth(token))
        assert r.json()["games"][0]["is_reviewed"] is False


class TestUpdateGameStatus:
    """US 7.3 — PATCH /api/v1/games/{game_id}/status."""

    def _create_game(self, token: str) -> str:
        r = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        return r.json()["accepted"][0]["game_id"]

    def test_marks_game_as_reviewed(self):
        token = _signup_and_token()
        gid = self._create_game(token)
        r = client.patch(
            f"/api/v1/games/{gid}/status", json={"is_reviewed": True}, headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["game"]["is_reviewed"] is True

    def test_unmarks_game_as_reviewed(self):
        token = _signup_and_token()
        gid = self._create_game(token)
        client.patch(f"/api/v1/games/{gid}/status", json={"is_reviewed": True}, headers=_auth(token))
        r = client.patch(f"/api/v1/games/{gid}/status", json={"is_reviewed": False}, headers=_auth(token))
        assert r.json()["game"]["is_reviewed"] is False

    def test_persists_across_get(self):
        token = _signup_and_token()
        gid = self._create_game(token)
        client.patch(f"/api/v1/games/{gid}/status", json={"is_reviewed": True}, headers=_auth(token))
        r = client.get(f"/api/v1/games/{gid}", headers=_auth(token))
        assert r.json()["game"]["is_reviewed"] is True

    def test_without_token_returns_401_or_403(self):
        assert client.patch("/api/v1/games/whatever/status", json={"is_reviewed": True}).status_code in (401, 403)

    def test_unknown_game_returns_404(self):
        token = _signup_and_token()
        r = client.patch(
            "/api/v1/games/missing/status", json={"is_reviewed": True}, headers=_auth(token),
        )
        assert r.status_code == 404

    def test_other_users_game_returns_404(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        gid = self._create_game(token_a)
        r = client.patch(
            f"/api/v1/games/{gid}/status", json={"is_reviewed": True}, headers=_auth(token_b),
        )
        assert r.status_code == 404
        # Vérifie que la partie de usera n'a pas été modifiée par la tentative.
        g = client.get(f"/api/v1/games/{gid}", headers=_auth(token_a))
        assert g.json()["game"]["is_reviewed"] is False

    def test_missing_body_field_returns_422(self):
        token = _signup_and_token()
        gid = self._create_game(token)
        r = client.patch(f"/api/v1/games/{gid}/status", json={}, headers=_auth(token))
        assert r.status_code == 422


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


class TestAnalysisProgress:
    """EPIC 28 (US 28.1) — progression coup-par-coup exposée via GET /games/{id}."""

    def test_progress_reaches_total_after_completion(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze", json={"pgn": PGN, "evals": _evals(PGN)}, headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        g = client.get(f"/api/v1/games/{gid}", headers=_auth(token)).json()["game"]
        assert g["progress_total"] == 6
        assert g["progress_current"] == 6

    def test_fresh_game_starts_at_zero(self):
        # Avant toute exécution de tâche de fond (create_game seul).
        game = db_client.create_game("[Result \"*\"]\n\n*", user_id="u1")
        assert game["progress_current"] == 0
        assert game["progress_total"] == 0


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


# 1.e4 e5 2.Nf3 Nc6, horloges annotées (base 600s, incrément nul) : le 2e coup
# blanc (Nf3) chute de 10:00 à 9:40 = 20s de réflexion (le 1er coup de chaque
# camp n'a pas de référence antérieure, donc time_spent_seconds=None).
CLOCK_PGN = (
    '[Event "x"][Result "1-0"]\n\n'
    "1. e4 {[%clk 0:10:00]} e5 {[%clk 0:10:00]} "
    "2. Nf3 {[%clk 0:09:40]} Nc6 {[%clk 0:09:50]} 1-0"
)


class TestStatsCognitiveLoad:
    def test_empty_shape(self):
        token = _signup_and_token()
        r = client.get("/api/v1/stats/cognitive-load", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert set(body["time_allocation"]["by_phase"]) == {"opening", "middlegame", "endgame"}
        assert set(body["time_allocation"]["by_pressure"]) == {"under_pressure", "equality"}
        assert body["time_allocation"]["sample_size"] == 0
        assert body["decision_fluidity"]["decision_fatigue"] is False

    def test_after_analysis_with_clocks(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={
                "pgn": CLOCK_PGN,
                "time_control": "600+0",
                "evals": _evals(CLOCK_PGN, played=40),
            },
            headers=_auth(token),
        )
        r = client.get("/api/v1/stats/cognitive-load", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        # Seul le 2e coup blanc (Nf3) a un temps de réflexion connu (1er coup
        # de chaque camp sans référence antérieure).
        assert body["time_allocation"]["sample_size"] == 1
        assert body["time_allocation"]["by_phase"]["opening"]["avg_seconds"] == 20.0
        assert body["time_allocation"]["by_phase"]["opening"]["share_pct"] == 100.0
        # cpl=0 (coup joué = meilleur coup, cf. `_evals`) -> bucket "top3".
        assert body["decision_fluidity"]["top3"]["count"] == 1
        assert body["decision_fluidity"]["weak"]["count"] == 0

    def test_scoped_to_authenticated_user(self):
        token_a = _signup_and_token(email="a2@ex.com", username="usera2")
        token_b = _signup_and_token(email="b2@ex.com", username="userb2")
        client.post(
            "/api/v1/games/analyze",
            json={
                "pgn": CLOCK_PGN,
                "time_control": "600+0",
                "evals": _evals(CLOCK_PGN, played=40),
            },
            headers=_auth(token_a),
        )
        r_b = client.get("/api/v1/stats/cognitive-load", headers=_auth(token_b))
        assert r_b.json()["time_allocation"]["sample_size"] == 0

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/stats/cognitive-load").status_code in (401, 403)

    def test_degrades_on_db_error(self, monkeypatch):
        def boom(*_a, **_k):
            raise RuntimeError("db down")

        token = _signup_and_token()
        monkeypatch.setattr("app.routers.games.db_client.get_completed_games", boom)
        r = client.get("/api/v1/stats/cognitive-load", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["time_allocation"]["sample_size"] == 0


class TestSalvageEndpoint:
    """EPIC 15 (US 15.1/15.2) — POST /api/v1/games/{game_id}/salvage."""

    def test_salvage_returns_position_before_pivot(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "user_color": "white", "evals": _evals_with_blunder(PGN, 2)},
            headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        s = client.post(f"/api/v1/games/{gid}/salvage", headers=_auth(token))
        assert s.status_code == 200
        body = s.json()
        assert body["game_id"] == gid
        assert body["pivot_move_index"] == 2
        assert body["side_to_move"] == "white"
        assert body["move_number"] == 2
        expected = chess.Board()
        expected.push_san("e4")
        expected.push_san("e5")
        assert body["fen"] == expected.fen()

    def test_salvage_without_token_returns_401_or_403(self):
        assert client.post("/api/v1/games/whatever/salvage").status_code in (401, 403)

    def test_salvage_unknown_game_404(self):
        token = _signup_and_token()
        assert client.post("/api/v1/games/missing/salvage", headers=_auth(token)).status_code == 404

    def test_salvage_other_users_game_returns_404(self):
        token_a = _signup_and_token(email="a2@ex.com", username="usera2")
        token_b = _signup_and_token(email="b2@ex.com", username="userb2")
        r = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "user_color": "white", "evals": _evals_with_blunder(PGN, 2)},
            headers=_auth(token_a),
        )
        gid = r.json()["accepted"][0]["game_id"]
        s = client.post(f"/api/v1/games/{gid}/salvage", headers=_auth(token_b))
        assert s.status_code == 404

    def test_salvage_no_pivot_detected_returns_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/games/analyze",
            json={"pgn": PGN, "user_color": "white", "evals": _evals(PGN)},
            headers=_auth(token),
        )
        gid = r.json()["accepted"][0]["game_id"]
        s = client.post(f"/api/v1/games/{gid}/salvage", headers=_auth(token))
        assert s.status_code == 404
        assert "pivot" in s.json()["detail"].lower()

    def test_salvage_processing_game_returns_409(self):
        from app.domain.auth import decode_token

        token = _signup_and_token()
        user_id = decode_token(token)["sub"]
        game = db_client.create_game(pgn=PGN, user_id=user_id, status="processing")
        s = client.post(f"/api/v1/games/{game['id']}/salvage", headers=_auth(token))
        assert s.status_code == 409
