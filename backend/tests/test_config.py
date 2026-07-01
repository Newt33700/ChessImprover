"""Tests — configuration (parsing CORS)."""

from __future__ import annotations

from app.config import Settings


class TestAllowedOrigins:
    def test_comma_separated_env(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.vercel.app, https://b.com ,")
        s = Settings()
        assert s.allowed_origins == ["https://a.vercel.app", "https://b.com"]

    def test_default_origins(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        s = Settings()
        assert "http://localhost:8080" in s.allowed_origins
