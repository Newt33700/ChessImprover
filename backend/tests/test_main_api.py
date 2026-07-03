"""Tests de l'API racine (app.main) — audit sécurité.

Couvre :
  - GET /health
  - GET /games/{username} : validation du pseudo (injection d'URL), mapping
    des erreurs amont sans fuite de détails internes (str(exc)).
  - ChessComClient._safe : encodage du pseudo dans les URLs Chess.com.
"""

from __future__ import annotations

from typing import Any, Dict, List

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.infrastructure.chess_com_client import ChessComClient

client = TestClient(main_module.app)


class _StubChessComClient:
    """Doublure du client Chess.com : renvoie des parties ou lève une erreur."""

    def __init__(self, games: List[Dict[str, Any]] | None = None, exc: Exception | None = None):
        self._games = games or []
        self._exc = exc

    async def get_latest_games(self, username: str, limit: int = 10):
        if self._exc is not None:
            raise self._exc
        return self._games[:limit]


@pytest.fixture
def stub_client(monkeypatch):
    def _install(stub: _StubChessComClient) -> None:
        monkeypatch.setattr(main_module, "chess_com_client", stub)
    return _install


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.chess.com/pub/player/x/games/archives")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("boom interne", request=request, response=response)


class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestGetGamesValidation:
    """Le pseudo est borné à ``[A-Za-z0-9_-]{1,50}`` avant tout appel réseau."""

    def test_valid_username_returns_games(self, stub_client):
        stub_client(_StubChessComClient(games=[{"url": "g1"}, {"url": "g2"}]))
        r = client.get("/games/Magnus_Carlsen-1")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_limit_is_applied(self, stub_client):
        stub_client(_StubChessComClient(games=[{"url": f"g{i}"} for i in range(10)]))
        r = client.get("/games/hikaru", params={"limit": 3})
        assert r.status_code == 200
        assert len(r.json()) == 3

    @pytest.mark.parametrize(
        "username",
        [
            "a/b",            # segment de chemin supplémentaire
            "..",             # traversée
            "user name",      # espace
            "a" * 51,         # trop long
            "p%2Fq",          # encodage détourné
            "<script>",       # balise
        ],
    )
    def test_invalid_username_rejected_without_network_call(self, username, stub_client):
        called = []

        class _Spy(_StubChessComClient):
            async def get_latest_games(self, username: str, limit: int = 10):
                called.append(username)
                return []

        stub_client(_Spy())
        r = client.get(f"/games/{username}")
        assert r.status_code in (404, 422)
        assert called == []

    def test_limit_out_of_bounds_rejected(self, stub_client):
        stub_client(_StubChessComClient())
        assert client.get("/games/hikaru", params={"limit": 0}).status_code == 422
        assert client.get("/games/hikaru", params={"limit": 51}).status_code == 422


class TestGetGamesErrorMapping:
    """Les erreurs amont ne fuient jamais leur message interne au client."""

    def test_upstream_404_maps_to_404(self, stub_client):
        stub_client(_StubChessComClient(exc=_http_status_error(404)))
        r = client.get("/games/inconnu")
        assert r.status_code == 404
        assert "introuvable" in r.json()["detail"]

    def test_upstream_500_maps_to_502_without_leaking_details(self, stub_client):
        stub_client(_StubChessComClient(exc=_http_status_error(500)))
        r = client.get("/games/hikaru")
        assert r.status_code == 502
        assert "boom interne" not in r.json()["detail"]

    def test_network_error_maps_to_502_without_leaking_details(self, stub_client):
        stub_client(_StubChessComClient(exc=RuntimeError("dsn=postgres://secret@host")))
        r = client.get("/games/hikaru")
        assert r.status_code == 502
        assert "secret" not in r.json()["detail"]

    def test_client_not_ready_returns_503(self, monkeypatch):
        monkeypatch.setattr(main_module, "chess_com_client", None)
        r = client.get("/games/hikaru")
        assert r.status_code == 503


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
