"""Client HTTP asynchrone pour l'API publique Chess.com.

Passerelle I/O : aucune logique métier ici.
Toutes les méthodes lèvent ``httpx.HTTPStatusError`` si l'API répond >= 400.
"""

from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.config import settings


class ChessComClient:
    """Wraps the Chess.com public API (read-only, no auth required)."""

    BASE_URL = "https://api.chess.com/pub"

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client or httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent},
            timeout=10.0,
        )

    # ------------------------------------------------------------------
    # Player
    # ------------------------------------------------------------------

    async def get_player(self, username: str) -> Dict[str, Any]:
        """Retourne le profil d'un joueur."""
        url = f"{self.BASE_URL}/player/{username}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Archives & parties
    # ------------------------------------------------------------------

    async def get_monthly_archives(self, username: str) -> List[str]:
        """Retourne la liste des URLs d'archives mensuelles (du plus récent au plus ancien)."""
        url = f"{self.BASE_URL}/player/{username}/games/archives"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        archives: List[str] = data.get("archives", [])
        return list(reversed(archives))

    async def get_games_for_month(
        self, username: str, year: int, month: int
    ) -> List[Dict[str, Any]]:
        """Retourne les parties d'un mois donné (YYYY/MM)."""
        url = f"{self.BASE_URL}/player/{username}/games/{year:04d}/{month:02d}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("games", [])

    async def get_latest_games(
        self, username: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retourne les ``limit`` dernières parties du joueur (toutes cadences)."""
        archives = await self.get_monthly_archives(username)
        games: List[Dict[str, Any]] = []
        for archive_url in archives:
            if len(games) >= limit:
                break
            resp = await self._client.get(archive_url)
            resp.raise_for_status()
            month_games: List[Dict[str, Any]] = resp.json().get("games", [])
            games.extend(reversed(month_games))
        return games[:limit]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_player_stats(self, username: str) -> Dict[str, Any]:
        """Retourne les statistiques de rating du joueur."""
        url = f"{self.BASE_URL}/player/{username}/stats"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Ferme la session HTTP sous-jacente."""
        await self._client.aclose()

    async def __aenter__(self) -> "ChessComClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
