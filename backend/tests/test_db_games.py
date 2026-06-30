"""Tests unitaires — store games / game_moves (EPIC 1)."""

from __future__ import annotations

import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestGames:
    def test_create_game_defaults(self):
        g = db_client.create_game(pgn="1. e4 e5", user_id="u1", time_control="600")
        assert g["status"] == "processing"
        assert g["user_color"] == "white"
        assert g["pgn"] == "1. e4 e5"
        assert g["time_control"] == "600"
        assert "created_at" in g and g["created_at"]

    def test_get_game(self):
        g = db_client.create_game(pgn="x")
        assert db_client.get_game(g["id"]) == g
        assert db_client.get_game("missing") is None

    def test_get_games_for_user(self):
        db_client.create_game(pgn="a", user_id="u1")
        db_client.create_game(pgn="b", user_id="u2")
        assert len(db_client.get_games_for_user("u1")) == 1

    def test_update_game(self):
        g = db_client.create_game(pgn="x")
        db_client.update_game(g["id"], status="completed", result="1-0")
        updated = db_client.get_game(g["id"])
        assert updated["status"] == "completed"
        assert updated["result"] == "1-0"

    def test_update_missing_returns_none(self):
        assert db_client.update_game("nope", status="failed") is None

    def test_completed_games_filter(self):
        g1 = db_client.create_game(pgn="a", user_id="u1")
        db_client.create_game(pgn="b", user_id="u1")  # reste processing
        db_client.update_game(g1["id"], status="completed")
        assert len(db_client.get_completed_games("u1")) == 1
        assert len(db_client.get_completed_games()) == 1


class TestGameMoves:
    def test_bulk_insert_and_get(self):
        g = db_client.create_game(pgn="x")
        n = db_client.bulk_insert_moves(g["id"], [{"move_san": "e4"}, {"move_san": "e5"}])
        assert n == 2
        assert len(db_client.get_moves_for_game(g["id"])) == 2

    def test_clear_moves(self):
        g = db_client.create_game(pgn="x")
        db_client.bulk_insert_moves(g["id"], [{"move_san": "e4"}])
        db_client.clear_moves(g["id"])
        assert db_client.get_moves_for_game(g["id"]) == []

    def test_moves_for_unknown_game(self):
        assert db_client.get_moves_for_game("missing") == []
