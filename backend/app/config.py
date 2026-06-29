"""Configuration générale de l'application Chess Improver."""

from __future__ import annotations

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Chess Improver"
    app_version: str = "0.1.0"
    debug: bool = False

    # Identifiant HTTP envoyé à Chess.com (politique de leur API)
    user_agent: str = "ChessImprover/0.1 (contact: chess-improver@example.com)"

    # CORS — séparées par des virgules dans .env
    allowed_origins: list[str] = ["http://localhost:8080", "http://127.0.0.1:8080"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
