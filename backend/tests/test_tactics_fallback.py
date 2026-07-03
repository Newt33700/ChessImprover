"""Tests — Fallback anti-« Impossible de charger un problème » (EPIC 22, US 22.2).

Le bug bloquant en production : ``DATABASE_URL`` configuré mais dépôt Postgres
incomplet (méthodes tactiques jamais migrées, cf. README §10.6) ou table vide
→ la route ``GET /api/v1/tactics/next`` crashait en 500/404 et figeait
l'interface. Ces tests vérifient que le backend retombe TOUJOURS sur le set
de problèmes par défaut in-memory au lieu de renvoyer une erreur.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.endgames import router as endgames_router
from app.routers.tactics import router as tactics_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(tactics_router)
_app.include_router(endgames_router)
client = TestClient(_app)


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _signup_and_token(email="alice@ex.com", username="alice") -> str:
    r = client.post(
        "/auth/signup",
        json={"email": email, "username": username, "password": "pass123"},
    )
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class _UserAwareRepo:
    """Socle commun des doublures : depuis EPIC 25, les comptes sont délégués
    à Postgres — les fakes relaient donc les lectures utilisateur vers le
    store in-memory (où le signup des tests a créé le compte), et simulent
    une table `profiles` aux Elos non initialisés (None → défaut 1000)."""

    def find_user_by_id(self, user_id):
        return db_client._users.get(user_id)

    def get_user_elo(self, user_id, column):
        return None  # ligne sans Elo → db_client retombe sur le défaut 1000

    def update_user_elo(self, user_id, column, new_elo):
        return db_client._users.get(user_id)


class _BrokenRepo(_UserAwareRepo):
    """Simule un dépôt Postgres partiel : les méthodes *problèmes tactiques*
    sont indisponibles (AttributeError au premier appel — scénario historique
    du gap §10.6, fermé par EPIC 25 mais que le fallback doit continuer de
    couvrir), tandis que l'historique des tentatives fonctionne."""

    def __init__(self):
        self._attempts = []

    def record_tactical_attempt(
        self, user_id, problem_id, category, success, time_taken
    ):
        from datetime import datetime, timezone

        attempt = {
            "user_id": user_id,
            "problem_id": problem_id,
            "category": category,
            "success": success,
            "time_taken": time_taken,
            "created_at": datetime.now(timezone.utc),
        }
        self._attempts.append(attempt)
        return attempt

    def get_tactical_attempts(self, user_id):
        return [a for a in self._attempts if a["user_id"] == user_id]


class _EmptyRepo(_UserAwareRepo):
    """Simule un dépôt Postgres joignable mais dont la table est vide."""

    def get_tactical_problem(self, problem_id):
        return None

    def get_next_tactical_problem(self, tactical_elo, category=None):
        return None


class TestDbClientFallback:
    def test_broken_repo_falls_back_to_seed(self, monkeypatch):
        monkeypatch.setattr(db_client, "_pg", lambda: _BrokenRepo())
        problem = db_client.get_next_tactical_problem(1000)
        assert problem is not None
        assert problem["category"] in {"mate_in_1", "mate_in_2", "hanging_piece"}

    def test_empty_repo_falls_back_to_seed(self, monkeypatch):
        monkeypatch.setattr(db_client, "_pg", lambda: _EmptyRepo())
        problem = db_client.get_next_tactical_problem(1000, category="mate_in_1")
        assert problem is not None
        assert problem["category"] == "mate_in_1"

    def test_get_tactical_problem_falls_back_to_seed(self, monkeypatch):
        monkeypatch.setattr(db_client, "_pg", lambda: _BrokenRepo())
        seed_id = next(iter(db_client._tactical_problems))
        problem = db_client.get_tactical_problem(seed_id)
        assert problem is not None
        assert problem["id"] == seed_id

    def test_custom_training_falls_back_to_seed(self, monkeypatch):
        monkeypatch.setattr(db_client, "_pg", lambda: _BrokenRepo())
        problem = db_client.get_next_tactical_problem_for_categories(
            1000, ["mate_in_1", "mate_in_2"]
        )
        assert problem is not None
        assert problem["category"] in {"mate_in_1", "mate_in_2"}

    def test_empty_category_pool_widens_to_all_categories(self):
        # Filtre qui vide le pool → élargissement plutôt que None/404.
        problem = db_client.get_next_tactical_problem_for_categories(
            1000, ["categorie_inexistante"]
        )
        assert problem is not None

    def test_endgame_empty_category_pool_widens(self, monkeypatch):
        # Un seed amputé d'une catégorie ne doit jamais produire None.
        only_queen = {
            pid: p
            for pid, p in db_client._endgame_problems.items()
            if p["category"] == "queen_mate"
        }
        monkeypatch.setattr(db_client, "_endgame_problems", only_queen)
        problem = db_client.get_next_endgame_problem(900, category="rook_mate")
        assert problem is not None


class TestApiNeverFreezesUi:
    """La route /next répond 200 même avec un dépôt Postgres cassé/vide."""

    def test_tactics_next_returns_200_with_broken_repo(self, monkeypatch):
        token = _signup_and_token()
        monkeypatch.setattr(db_client, "_pg", lambda: _BrokenRepo())
        r = client.get("/api/v1/tactics/next", headers=_auth(token))
        assert r.status_code == 200
        assert set(r.json()) == {"id", "fen", "category", "difficulty_elo"}

    def test_tactics_next_returns_200_with_empty_repo(self, monkeypatch):
        token = _signup_and_token()
        monkeypatch.setattr(db_client, "_pg", lambda: _EmptyRepo())
        r = client.get(
            "/api/v1/tactics/next",
            params={"theme_id": "mate_in_2"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["category"] == "mate_in_2"

    def test_attempt_validates_against_seed_with_broken_repo(self, monkeypatch):
        token = _signup_and_token()
        repo = _BrokenRepo()
        monkeypatch.setattr(db_client, "_pg", lambda: repo)
        r = client.get("/api/v1/tactics/next", headers=_auth(token))
        pid = r.json()["id"]
        r2 = client.post(
            "/api/v1/tactics/attempt",
            json={"problem_id": pid, "move": "a3"},
            headers=_auth(token),
        )
        assert r2.status_code == 200
        assert "success" in r2.json()

    def test_custom_next_returns_200_with_broken_repo(self, monkeypatch):
        token = _signup_and_token()
        monkeypatch.setattr(db_client, "_pg", lambda: _BrokenRepo())
        r = client.get(
            "/api/v1/tactics/custom",
            params={"focus": "missed_mate"},
            headers=_auth(token),
        )
        assert r.status_code == 200

    def test_endgames_next_always_returns_200(self):
        token = _signup_and_token()
        r = client.get("/api/v1/endgames/next", headers=_auth(token))
        assert r.status_code == 200
