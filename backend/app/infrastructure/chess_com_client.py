"""Client HTTP asynchrone pour l'API publique Chess.com.

Passerelle I/O : aucune logique métier ici.
Toutes les méthodes lèvent ``httpx.HTTPStatusError`` si l'API répond >= 400.
"""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote

import httpx

from app.config import settings


class ChessComClient:
    """Wraps the Chess.com public API (read-only, no auth required)."""

    BASE_URL = "https://api.chess.com/pub"

    @staticmethod
    def _safe(username: str) -> str:
        """Encode le pseudo pour l'URL : aucun caractère fourni par le client
        ne peut introduire un segment de chemin (``/``, ``..``) ou une query."""
        return quote(username, safe="")

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
        url = f"{self.BASE_URL}/player/{self._safe(username)}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Archives & parties
    # ------------------------------------------------------------------

    async def get_monthly_archives(self, username: str) -> List[str]:
        """Retourne la liste des URLs d'archives mensuelles (du plus récent au plus ancien)."""
        url = f"{self.BASE_URL}/player/{self._safe(username)}/games/archives"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        archives: List[str] = data.get("archives", [])
        return list(reversed(archives))

    async def get_games_for_month(
        self, username: str, year: int, month: int
    ) -> List[Dict[str, Any]]:
        """Retourne les parties d'un mois donné (YYYY/MM)."""
        url = f"{self.BASE_URL}/player/{self._safe(username)}/games/{year:04d}/{month:02d}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("games", [])

    async def get_games_for_months(
        self, username: str, months: List[tuple]
    ) -> List[Dict[str, Any]]:
        """EPIC 24 — Parties de plusieurs mois ``(année, mois)``, concaténées.

        Un mois sans archive (404 : le joueur n'a pas joué ce mois-là) est
        silencieusement ignoré — seul cas d'erreur toléré, les autres statuts
        remontent à l'appelant comme partout ailleurs dans ce client.
        """
        games: List[Dict[str, Any]] = []
        for year, month in months:
            try:
                games.extend(await self.get_games_for_month(username, year, month))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
        return games

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
        url = f"{self.BASE_URL}/player/{self._safe(username)}/stats"
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
