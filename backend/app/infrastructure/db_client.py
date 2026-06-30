"""Database client abstraction for Chess Improver (US 7).

In development / tests: uses an in-memory dict store.
In production: configure DATABASE_URL to point at Supabase/PostgreSQL.

The interface is intentionally synchronous and dict-based so tests
need no real database and the domain layer stays decoupled.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# In-memory store (dev / test)
# ---------------------------------------------------------------------------

_users: Dict[str, Dict[str, Any]] = {}   # keyed by user_id
_user_data: Dict[str, Dict[str, Any]] = {}  # keyed by user_id

# EPIC 1 — analyse async
_games: Dict[str, Dict[str, Any]] = {}        # keyed by game_id
_game_moves: Dict[str, List[Dict[str, Any]]] = {}  # keyed by game_id


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    for user in _users.values():
        if user["email"].lower() == email.lower():
            return user
    return None


def find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    for user in _users.values():
        if user["username"].lower() == username.lower():
            return user
    return None


def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return _users.get(user_id)


def create_user(email: str, username: str, password_hash: str) -> Dict[str, Any]:
    user_id = str(uuid.uuid4())
    user = {"id": user_id, "email": email, "username": username, "password_hash": password_hash}
    _users[user_id] = user
    _user_data[user_id] = {"games": [], "srs_cards": []}
    return user


def get_user_data(user_id: str) -> Dict[str, Any]:
    return _user_data.get(user_id, {"games": [], "srs_cards": []})


def upsert_user_data(user_id: str, games: List[Any], srs_cards: List[Any]) -> Dict[str, Any]:
    """Client Wins: merge by game_id/card_id, client data overwrites server data."""
    existing = _user_data.get(user_id, {"games": [], "srs_cards": []})

    # Index existing data by id
    games_map: Dict[str, Any] = {g["game_id"]: g for g in existing["games"] if "game_id" in g}
    cards_map: Dict[str, Any] = {c["id"]: c for c in existing["srs_cards"] if "id" in c}

    # Client wins: overwrite with client data
    for g in games:
        if "game_id" in g:
            games_map[g["game_id"]] = g
    for c in srs_cards:
        if "id" in c:
            cards_map[c["id"]] = c

    merged = {
        "games": sorted(games_map.values(), key=lambda x: x.get("date", ""), reverse=True),
        "srs_cards": list(cards_map.values()),
    }
    _user_data[user_id] = merged
    return merged


# ---------------------------------------------------------------------------
# Games & game_moves (EPIC 1)
# ---------------------------------------------------------------------------

def create_game(
    pgn: str,
    user_id: Optional[str] = None,
    time_control: Optional[str] = None,
    user_color: str = "white",
    status: str = "processing",
) -> Dict[str, Any]:
    """Crée une ligne `games` au statut initial et renvoie l'enregistrement."""
    import datetime as _dt

    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "user_id": user_id,
        "pgn": pgn,
        "time_control": time_control,
        "user_color": user_color,
        "result": None,
        "status": status,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    _games[game_id] = game
    _game_moves[game_id] = []
    return game


def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    return _games.get(game_id)


def get_games_for_user(user_id: Optional[str]) -> List[Dict[str, Any]]:
    return [g for g in _games.values() if g.get("user_id") == user_id]


def update_game(game_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    """Met à jour des champs arbitraires d'une partie (ex. status, result)."""
    game = _games.get(game_id)
    if game is None:
        return None
    game.update(fields)
    return game


def bulk_insert_moves(game_id: str, moves: List[Dict[str, Any]]) -> int:
    """Insère en bloc les métriques par coup d'une partie. Renvoie le nombre inséré."""
    if game_id not in _game_moves:
        _game_moves[game_id] = []
    _game_moves[game_id].extend(moves)
    return len(moves)


def get_moves_for_game(game_id: str) -> List[Dict[str, Any]]:
    return list(_game_moves.get(game_id, []))


def clear_moves(game_id: str) -> None:
    """Purge les coups d'une partie (avant réanalyse)."""
    _game_moves[game_id] = []


def get_completed_games(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Parties analysées (status=completed), filtrées par utilisateur si fourni."""
    games = [g for g in _games.values() if g.get("status") == "completed"]
    if user_id is not None:
        games = [g for g in games if g.get("user_id") == user_id]
    return games


def _reset_store() -> None:
    """Reset in-memory store between tests."""
    _users.clear()
    _user_data.clear()
    _games.clear()
    _game_moves.clear()
