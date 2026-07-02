"""Tests d'intégration — EPIC 11 (US 9.1/9.2) : profil d'erreurs + entraînement
personnalisé.

Même stratégie que `test_games_api.py` : app de test minimale, le TestClient
exécute les BackgroundTasks (`run_analysis`) de façon synchrone, donc le
profil d'erreurs est déjà à jour au moment des assertions.
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
from app.routers.error_profile import router as error_profile_router
from app.routers.games import router as games_router
from app.routers.tactics import router as tactics_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(games_router)
_app.include_router(error_profile_router)
_app.include_router(tactics_router)
client = TestClient(_app)

# 1.e4 d6 2.Nf3 e5 3.Nxe5 — Nxe5 est une gaffe blanche vérifiée (cf.
# test_analyzer.py::TestExactCounters). Sans evals -> hanging_piece.
BLUNDER_PGN = '[Event "x"][Result "*"]\n\n1. e4 d6 2. Nf3 e5 3. Nxe5 *'

CLEAN_PGN = '[Event "x"][Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0'


def _signup_and_token(email="alice@ex.com", username="alice") -> str:
    r = client.post("/auth/signup", json={"email": email, "username": username, "password": "pass123"})
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _missed_mate_evals(pgn: str) -> dict:
    """Fabrique des evals où le 3ᵉ coup blanc (Bb5) manque un mat fictif."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    evals = {}
    for i, move in enumerate(game.mainline_moves()):
        if i == 4:  # 3ᵉ coup blanc (0-based, demi-coups) : Bb5
            evals[board.fen()] = [["h5f7", 100000, True, 1], [move.uci(), 40]]
        else:
            evals[board.fen()] = [["0000", 20], [move.uci(), 20]]
        board.push(move)
    return evals


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestErrorProfileWiring:
    def test_blunder_game_updates_hanging_piece_profile(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze", json={"pgn": BLUNDER_PGN}, headers=_auth(token),
        )
        r = client.get("/api/v1/error-profile", headers=_auth(token))
        assert r.status_code == 200
        entries = {p["error_type"]: p for p in r.json()["profiles"]}
        assert entries["hanging_piece"]["frequency_score"] == 30.0
        assert entries["hanging_piece"]["is_recurring"] is False
        assert entries["time_pressure"]["frequency_score"] == 0.0
        assert entries["missed_mate"]["frequency_score"] == 0.0

    def test_missed_mate_detected_from_evals(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": CLEAN_PGN, "evals": _missed_mate_evals(CLEAN_PGN)},
            headers=_auth(token),
        )
        r = client.get("/api/v1/error-profile", headers=_auth(token))
        entries = {p["error_type"]: p for p in r.json()["profiles"]}
        assert entries["missed_mate"]["frequency_score"] == 30.0

    def test_repeated_blunders_cross_recurring_threshold(self):
        # PGN dédupliqué par (user_id, hash) — US 7.2 : varier un en-tête
        # pour forcer 4 analyses distinctes plutôt que 4 fois la même partie.
        token = _signup_and_token()
        for i in range(4):
            pgn = f'[Event "game-{i}"][Result "*"]\n\n1. e4 d6 2. Nf3 e5 3. Nxe5 *'
            client.post("/api/v1/games/analyze", json={"pgn": pgn}, headers=_auth(token))
        r = client.get("/api/v1/error-profile", headers=_auth(token))
        entries = {p["error_type"]: p for p in r.json()["profiles"]}
        assert entries["hanging_piece"]["is_recurring"] is True

    def test_no_games_yields_empty_profile(self):
        token = _signup_and_token()
        r = client.get("/api/v1/error-profile", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["profiles"] == []

    def test_without_token_returns_401_or_403(self):
        r = client.get("/api/v1/error-profile")
        assert r.status_code in (401, 403)

    def test_profiles_isolated_between_users(self):
        token_a = _signup_and_token("a@ex.com", "usera")
        token_b = _signup_and_token("b@ex.com", "userb")
        client.post("/api/v1/games/analyze", json={"pgn": BLUNDER_PGN}, headers=_auth(token_a))
        r = client.get("/api/v1/error-profile", headers=_auth(token_b))
        assert r.json()["profiles"] == []


class TestCustomTacticsEndpoint:
    def test_focus_hanging_piece_returns_matching_theme(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/custom", params={"focus": "hanging_piece"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["category"] == "hanging_piece"

    def test_focus_missed_mate_returns_mate_theme(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/custom", params={"focus": "missed_mate"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["category"] in ("mate_in_1", "mate_in_2")

    def test_unknown_focus_is_422(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/custom", params={"focus": "nonsense"}, headers=_auth(token))
        assert r.status_code == 422

    def test_missing_focus_is_422(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/custom", headers=_auth(token))
        assert r.status_code == 422

    def test_without_token_returns_401_or_403(self):
        r = client.get("/api/v1/tactics/custom", params={"focus": "hanging_piece"})
        assert r.status_code in (401, 403)

    def test_solution_never_leaked(self):
        token = _signup_and_token()
        r = client.get("/api/v1/tactics/custom", params={"focus": "hanging_piece"}, headers=_auth(token))
        assert "solution" not in r.json()
