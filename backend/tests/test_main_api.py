"""Tests de l'API racine (app.main) — audit sécurité.

Couvre :
  - GET /health
  - Fail-fast JWT_SECRET (démarrage refusé avec le secret par défaut hors debug)
  - ChessComClient._safe : encodage du pseudo dans les URLs Chess.com.
  - EPIC 25 (US 25.4) : non-régression de la SUPPRESSION des routes mortes
    (`/analyze`, `/games/{username}`, `/srs/review`, `/srs/review/full`) —
    elles ne doivent plus jamais réapparaître (surface d'attaque publique).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.infrastructure.chess_com_client import ChessComClient

client = TestClient(main_module.app)


class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestDeadRoutesRemoved:
    """EPIC 25 (US 25.4) — les routes historiques jamais appelées par le
    frontend ont été retirées : 404 attendu, définitivement."""

    def test_analyze_removed(self):
        assert client.post("/analyze", json={"pgn": "1. e4"}).status_code == 404

    def test_games_by_username_removed(self):
        assert client.get("/games/hikaru").status_code == 404

    def test_srs_review_removed(self):
        assert client.post("/srs/review", json={}).status_code == 404
        assert client.post("/srs/review/full", json={}).status_code == 404

    def test_business_routers_still_mounted(self):
        # La purge ne doit pas avoir débranché les routers métier.
        paths = {route.path for route in main_module.app.routes}
        assert "/api/v1/games/analyze" in paths
        assert "/api/v1/games/sync" in paths
        assert "/api/v1/tactics/next" in paths
        assert "/auth/login" in paths


class TestJwtSecretFailFast:
    """Le serveur refuse de démarrer avec le JWT_SECRET par défaut hors debug."""

    _DEFAULT = "dev-secret-change-in-production"

    def test_default_secret_outside_debug_aborts_startup(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "jwt_secret", self._DEFAULT)
        monkeypatch.setattr(settings, "debug", False)
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            with TestClient(main_module.app):  # déclenche le lifespan
                pass

    def test_default_secret_in_debug_allows_startup(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "jwt_secret", self._DEFAULT)
        monkeypatch.setattr(settings, "debug", True)
        with TestClient(main_module.app) as c:
            assert c.get("/health").status_code == 200

    def test_custom_secret_allows_startup(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "jwt_secret", "un-vrai-secret-de-production")
        monkeypatch.setattr(settings, "debug", False)
        with TestClient(main_module.app) as c:
            assert c.get("/health").status_code == 200


class TestChessComClientSafeEncoding:
    """Défense en profondeur : même appelé directement, le client encode le pseudo."""

    def test_safe_passthrough_for_valid_username(self):
        assert ChessComClient._safe("Magnus_Carlsen-1") == "Magnus_Carlsen-1"

    def test_safe_encodes_path_separators(self):
        assert "/" not in ChessComClient._safe("a/b/../c")

    def test_safe_encodes_query_and_fragment(self):
        encoded = ChessComClient._safe("user?admin=1#x")
        assert "?" not in encoded and "#" not in encoded
