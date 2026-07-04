"""Tests d'intégration — EPIC 30 : GET /api/v1/seasons/active."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.seasons import router as seasons_router

_app = FastAPI()
_app.include_router(seasons_router)
client = TestClient(_app)


class TestActiveSeasonEndpoint:
    def test_public_no_auth_required(self):
        r = client.get("/api/v1/seasons/active")
        assert r.status_code == 200

    def test_response_shape_when_no_season_active(self, monkeypatch):
        monkeypatch.setattr("app.routers.seasons.load_seasons", lambda: [])
        r = client.get("/api/v1/seasons/active")
        body = r.json()
        assert body["active"] is False
        assert body["season"] is None
        assert body["seconds_remaining"] == 0

    def test_response_shape_when_season_active(self, monkeypatch):
        season = {
            "id": "halloween",
            "name": "Halloween Chess",
            "start": "2026-01-01T00:00:00+00:00",
            "end": "2099-01-01T00:00:00+00:00",
            "banner_message": "🎃 Boo!",
            "cosmetic_piece_theme": "cyber-tactics",
            "cosmetic_board_theme": "cyber",
        }
        monkeypatch.setattr("app.routers.seasons.load_seasons", lambda: [season])
        r = client.get("/api/v1/seasons/active")
        body = r.json()
        assert body["active"] is True
        assert body["season"]["id"] == "halloween"
        assert body["season"]["banner_message"] == "🎃 Boo!"
        assert body["seconds_remaining"] > 0

    def test_never_leaks_start_field_to_client(self, monkeypatch):
        # SeasonPublic n'expose pas `start` — non nécessaire côté client.
        season = {
            "id": "x", "name": "X",
            "start": "2026-01-01T00:00:00+00:00", "end": "2099-01-01T00:00:00+00:00",
            "banner_message": "hi",
        }
        monkeypatch.setattr("app.routers.seasons.load_seasons", lambda: [season])
        r = client.get("/api/v1/seasons/active")
        assert "start" not in r.json()["season"]
