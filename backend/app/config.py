"""Configuration générale de l'application Chess Improver."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Chess Improver"
    app_version: str = "0.1.0"
    debug: bool = False

    # Identifiant HTTP envoyé à Chess.com (politique de leur API)
    user_agent: str = "ChessImprover/0.1 (contact: chess-improver@example.com)"

    # CORS — séparées par des virgules dans .env
    allowed_origins: List[str] = ["http://localhost:8080", "http://127.0.0.1:8080"]

    # Auth JWT (US 7)
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expiry_days: int = 30

    # Database (Supabase/PostgreSQL — laisser vide pour mode in-memory)
    database_url: Optional[str] = None

    # Moteur d'analyse (EPIC 2) — binaire Stockfish natif optionnel sur Render.
    # Laisser vide pour utiliser les évaluations fournies par le client (navigateur).
    stockfish_path: Optional[str] = None
    engine_depth: int = 14

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
