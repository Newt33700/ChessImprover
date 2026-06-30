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


def _reset_store() -> None:
    """Reset in-memory store between tests."""
    _users.clear()
    _user_data.clear()
