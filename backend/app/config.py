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

    # CORS — surchargeable via ALLOWED_ORIGINS (liste séparée par des virgules).
    allowed_origins: List[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://chess-improver-nu.vercel.app",
    ]

    # Auth JWT (US 7)
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expiry_days: int = 30

    # Database (Supabase/PostgreSQL — laisser vide pour mode in-memory)
    database_url: Optional[str] = None

    # Moteur d'analyse (EPIC 2) — binaire Stockfish natif optionnel sur Render.
    # Laisser vide pour utiliser les évaluations fournies par le client (navigateur).
    stockfish_path: Optional[str] = None
    engine_depth: int = 14

    # EPIC 34 — Coach Tactique : désactive l'appel réseau à l'API Puzzle
    # Lichess (source primaire de /tactics/next) pour ne servir que le seed
    # local déterministe. Utilisé par les tests E2E Playwright, dont les
    # scénarios pilotent un stub `Chess.move()` sur des FEN fixes du seed —
    # un vrai puzzle Lichess (FEN/Elo arbitraires) les casserait, ce qui
    # n'arrive qu'en CI où le réseau sortant est autorisé.
    disable_lichess_puzzles: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Accepte `ALLOWED_ORIGINS` en liste séparée par des virgules.

            Pydantic v1 exigerait sinon du JSON pour un champ `List[str]`, ce
            qui ferait planter le démarrage si l'on met simplement
            `ALLOWED_ORIGINS=https://a,https://b`.
            """
            if field_name == "allowed_origins":
                return [origin.strip() for origin in raw_val.split(",") if origin.strip()]
            return cls.json_loads(raw_val)  # comportement par défaut


settings = Settings()
