"""Tests — Moteur de Puzzles : sélection aléatoire + fallback Elo (EPIC 37, US 37.1).

`resolve_random_puzzles` (domain/lichess_puzzles.py) est pure vis-à-vis de la
base : le dépôt est injecté (`PuzzleRepository`, typage structurel), donc ces
tests utilisent un double en mémoire plutôt qu'une vraie connexion Postgres —
même approche que `test_tactics_fallback.py`.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.lichess_puzzles import PUZZLE_FALLBACK_ELO_WINDOW, resolve_random_puzzles
from app.domain.puzzles_models import LichessTheme, PuzzleQueryParams, PuzzleResponse
from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.tactics import router as tactics_router


def _puzzle(puzzle_id: str, rating: int, themes=None) -> dict:
    return {
        "puzzle_id": puzzle_id,
        "fen": "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        "moves": "a1a8",
        "rating": rating,
        "rating_deviation": 80,
        "popularity": 90,
        "nb_plays": 1000,
        "themes": themes or ["mateIn1"],
        "game_url": "https://lichess.org/abcd1234",
        "opening_tags": [],
    }


class _FakePuzzleRepo:
    """Double en mémoire du contrat `PuzzleRepository` (count + select paginé),
    sans jamais trier sur la collection entière (comme la vraie requête SQL)."""

    def __init__(self, puzzles):
        self._puzzles = list(puzzles)

    def _filtered(self, rating_min, rating_max, theme):
        return [
            p for p in self._puzzles
            if rating_min <= p["rating"] <= rating_max
            and (theme is None or theme in p["themes"])
        ]

    def count_puzzles(self, rating_min, rating_max, theme=None):
        return len(self._filtered(rating_min, rating_max, theme))

    def get_random_puzzles(self, rating_min, rating_max, theme, limit, offset):
        matches = self._filtered(rating_min, rating_max, theme)
        return matches[offset:offset + limit]


class TestResolveRandomPuzzlesStandard:
    def test_theme_mate_in_1_within_range_returns_puzzle(self):
        repo = _FakePuzzleRepo([
            _puzzle("p1", 1200, themes=["mateIn1", "opening"]),
            _puzzle("p2", 1550, themes=["fork"]),
        ])

        puzzles, strategy = resolve_random_puzzles(repo, 1000, 1600, "mateIn1", limit=1)

        assert strategy == "standard"
        assert len(puzzles) == 1
        assert puzzles[0]["puzzle_id"] == "p1"

    def test_limit_caps_result_size(self):
        repo = _FakePuzzleRepo([_puzzle(f"p{i}", 1200) for i in range(5)])

        puzzles, strategy = resolve_random_puzzles(repo, 1000, 1600, "mateIn1", limit=3)

        assert strategy == "standard"
        assert len(puzzles) == 3

    def test_no_theme_filters_only_by_rating(self):
        repo = _FakePuzzleRepo([
            _puzzle("p1", 1200, themes=["fork"]),
            _puzzle("p2", 9999, themes=["pin"]),  # hors plage
        ])

        puzzles, strategy = resolve_random_puzzles(repo, 1000, 1600, None, limit=5)

        assert strategy == "standard"
        assert [p["puzzle_id"] for p in puzzles] == ["p1"]


class TestResolveRandomPuzzlesFallback:
    def test_empty_range_widens_by_100_and_finds_puzzle(self):
        # Rien exactement dans [1000, 1000] mais un puzzle à 1080 (dans
        # [1000-100, 1000+100] = [900, 1100]) doit être trouvé via fallback.
        repo = _FakePuzzleRepo([_puzzle("p1", 1000 + PUZZLE_FALLBACK_ELO_WINDOW - 20)])

        puzzles, strategy = resolve_random_puzzles(repo, 1000, 1000, "mateIn1", limit=1)

        assert strategy == "fallback"
        assert len(puzzles) == 1
        assert puzzles[0]["puzzle_id"] == "p1"

    def test_still_empty_after_fallback_returns_empty_list(self):
        repo = _FakePuzzleRepo([_puzzle("p1", 3000, themes=["mateIn1"])])

        puzzles, strategy = resolve_random_puzzles(repo, 1000, 1000, "mateIn1", limit=1)

        assert strategy == "fallback"
        assert puzzles == []

    def test_fallback_widens_min_and_max_symmetrically(self):
        calls = []

        class _RecordingRepo(_FakePuzzleRepo):
            def count_puzzles(self, rating_min, rating_max, theme=None):
                calls.append((rating_min, rating_max))
                return super().count_puzzles(rating_min, rating_max, theme)

        repo = _RecordingRepo([_puzzle("p1", 1700)])
        resolve_random_puzzles(repo, 1000, 1600, None, limit=1)

        assert calls == [
            (1000, 1600),
            (1000 - PUZZLE_FALLBACK_ELO_WINDOW, 1600 + PUZZLE_FALLBACK_ELO_WINDOW),
        ]

    def test_fallback_rating_min_never_goes_negative(self):
        repo = _FakePuzzleRepo([])
        # rating_min=50 - 100 serait négatif : doit être clampé à 0.
        resolve_random_puzzles(repo, 50, 60, None, limit=1)  # ne doit pas lever


class TestPuzzleQueryParams:
    def test_rejects_rating_max_below_rating_min(self):
        with pytest.raises(ValueError):
            PuzzleQueryParams(rating_min=1600, rating_max=1000)

    def test_accepts_equal_bounds(self):
        params = PuzzleQueryParams(rating_min=1200, rating_max=1200)
        assert params.rating_min == params.rating_max == 1200

    def test_theme_must_be_a_known_lichess_theme(self):
        with pytest.raises(ValueError):
            PuzzleQueryParams(theme="not_a_real_theme")

    def test_mate_in_1_theme_value(self):
        params = PuzzleQueryParams(theme=LichessTheme.MATE_IN_1)
        assert params.theme.value == "mateIn1"


class TestPuzzleResponseSchema:
    def test_builds_from_repository_row(self):
        response = PuzzleResponse(**_puzzle("p1", 1200))
        assert response.puzzle_id == "p1"
        assert response.themes == ["mateIn1"]

    def test_opening_tags_default_to_empty_list(self):
        row = _puzzle("p1", 1200)
        del row["opening_tags"]
        response = PuzzleResponse(**row)
        assert response.opening_tags == []


_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(tactics_router)
client = TestClient(_app)


def _signup_and_token(email="random-puzzles@ex.com", username="rndpuzzles") -> str:
    r = client.post(
        "/auth/signup",
        json={"email": email, "username": username, "password": "pass123"},
    )
    return r.json()["token"]


class TestRandomPuzzlesEndpoint:
    @pytest.fixture(autouse=True)
    def reset_db(self):
        db_client._reset_store()
        yield
        db_client._reset_store()

    def test_returns_503_when_no_database_configured(self):
        token = _signup_and_token()
        r = client.get(
            "/api/v1/tactics/random",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 503

    def test_rejects_rating_max_below_rating_min(self):
        token = _signup_and_token(email="badrange@ex.com", username="badrange")
        r = client.get(
            "/api/v1/tactics/random?rating_min=1600&rating_max=1000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_rejects_unknown_theme(self):
        token = _signup_and_token(email="badtheme@ex.com", username="badtheme")
        r = client.get(
            "/api/v1/tactics/random?theme=not_a_theme",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_requires_authentication(self):
        r = client.get("/api/v1/tactics/random")
        assert r.status_code == 401
