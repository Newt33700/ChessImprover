"""Tests d'intégration — Le Cimetière des Erreurs (EPIC 20, US 20.1/20.2).

Même stratégie que `test_error_profile_api.py` : app de test minimale, le
TestClient exécute les BackgroundTasks (`run_analysis`) de façon synchrone,
donc les flashcards sont déjà générées au moment des assertions.
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
from app.routers.srs_flashcards import router as flashcards_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(games_router)
_app.include_router(flashcards_router)
client = TestClient(_app)

# 1.e4 d6 2.Nf3 e5 3.Nxe5 — Nxe5 (3e coup blanc, ply index 4) est la gaffe
# ciblée par les evals ci-dessous.
BLUNDER_PGN = '[Event "x"][Result "*"]\n\n1. e4 d6 2. Nf3 e5 3. Nxe5 *'

CLEAN_PGN = '[Event "x"][Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0'


def _blunder_evals(pgn: str) -> dict:
    """Fabrique des evals où Nxe5 (3e coup blanc) est une gaffe (cpl >= 200),
    avec un meilleur coup fictif ``d4`` (légal, distinct du coup joué)."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    evals = {}
    for i, move in enumerate(game.mainline_moves()):
        fen = board.fen()
        if i == 4:  # Nxe5
            evals[fen] = [["d2d4", 300], [move.uci(), -50]]
        else:
            evals[fen] = [["0000", 20], [move.uci(), 20]]
        board.push(move)
    return evals


def _clean_evals(pgn: str) -> dict:
    """Toutes les évals coïncident avec le coup joué (cpl=0 partout) — aucune gaffe."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    evals = {}
    for move in game.mainline_moves():
        evals[board.fen()] = [["0000", 20], [move.uci(), 20]]
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


class TestAutoGenerationFromBlunders:
    def test_blunder_game_creates_a_flashcard(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": BLUNDER_PGN, "evals": _blunder_evals(BLUNDER_PGN)},
            headers=_auth(token),
        )
        r = client.get("/api/v1/flashcards", headers=_auth(token))
        assert r.status_code == 200
        cards = r.json()
        assert len(cards) == 1
        assert "solution" not in cards[0]  # jamais exposée avant tentative
        assert cards[0]["ease_factor"] == 2.5
        assert cards[0]["interval_days"] == 1

    def test_clean_game_creates_no_flashcard(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": CLEAN_PGN, "evals": _clean_evals(CLEAN_PGN)},
            headers=_auth(token),
        )
        r = client.get("/api/v1/flashcards", headers=_auth(token))
        assert r.json() == []

    def test_new_flashcard_is_immediately_due(self):
        token = _signup_and_token()
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": BLUNDER_PGN, "evals": _blunder_evals(BLUNDER_PGN)},
            headers=_auth(token),
        )
        r = client.get("/api/v1/flashcards/due", headers=_auth(token))
        assert len(r.json()) == 1

    def test_flashcards_isolated_between_users(self):
        token_a = _signup_and_token("a@ex.com", "usera")
        token_b = _signup_and_token("b@ex.com", "userb")
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": BLUNDER_PGN, "evals": _blunder_evals(BLUNDER_PGN)},
            headers=_auth(token_a),
        )
        r = client.get("/api/v1/flashcards", headers=_auth(token_b))
        assert r.json() == []

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/flashcards").status_code in (401, 403)
        assert client.get("/api/v1/flashcards/due").status_code in (401, 403)


class TestReviewFlashcard:
    def _create_flashcard_via_blunder(self, token: str) -> str:
        client.post(
            "/api/v1/games/analyze",
            json={"pgn": BLUNDER_PGN, "evals": _blunder_evals(BLUNDER_PGN)},
            headers=_auth(token),
        )
        return client.get("/api/v1/flashcards", headers=_auth(token)).json()[0]["id"]

    def test_correct_recall_advances_schedule(self):
        token = _signup_and_token()
        card_id = self._create_flashcard_via_blunder(token)
        r = client.post(
            f"/api/v1/flashcards/{card_id}/review", json={"move": "d4"}, headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["solution"] == "d4"
        assert body["repetitions"] == 1

    def test_incorrect_recall_resets_schedule(self):
        token = _signup_and_token()
        card_id = self._create_flashcard_via_blunder(token)
        r = client.post(
            f"/api/v1/flashcards/{card_id}/review", json={"move": "Bb5"}, headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is False
        assert body["solution"] == "d4"
        assert body["repetitions"] == 0
        assert body["interval_days"] == 1

    def test_unknown_card_is_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/flashcards/00000000-0000-0000-0000-000000000000/review",
            json={"move": "d4"},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_non_owner_cannot_review(self):
        token_a = _signup_and_token("a3@ex.com", "usera3")
        token_b = _signup_and_token("b3@ex.com", "userb3")
        card_id = self._create_flashcard_via_blunder(token_a)
        r = client.post(
            f"/api/v1/flashcards/{card_id}/review", json={"move": "d4"}, headers=_auth(token_b),
        )
        assert r.status_code == 404

    def test_without_token_returns_401_or_403(self):
        r = client.post("/api/v1/flashcards/some-id/review", json={"move": "d4"})
        assert r.status_code in (401, 403)
