"""Client HTTP asynchrone pour l'API publique Puzzle de Lichess (EPIC 34).

Passerelle I/O : aucune logique métier ici (cf. ``domain/lichess_puzzles.py``
pour le parsing). Mirroir de ``ChessComClient`` — mêmes conventions.
Toutes les méthodes lèvent ``httpx.HTTPStatusError``/``httpx.HTTPError`` si
l'API répond en erreur ou est injoignable ; l'appelant (``routers/tactics.py``)
retombe alors sur le seed local, sans jamais laisser planter la route.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings


class LichessClient:
    """Wraps the public Lichess Puzzle API (read-only, no auth required)."""

    BASE_URL = "https://lichess.org/api"

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client or httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=10.0,
        )

    async def get_next_puzzle(self, angle: Optional[str] = None) -> Dict[str, Any]:
        """Retourne un puzzle (JSON brut) — ``angle`` filtre par thème
        (ex. ``mateIn2``), omis pour un puzzle toutes catégories confondues."""
        params = {"angle": angle} if angle else {}
        resp = await self._client.get(f"{self.BASE_URL}/puzzle/next", params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        """Ferme la session HTTP sous-jacente."""
        await self._client.aclose()

    async def __aenter__(self) -> "LichessClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
