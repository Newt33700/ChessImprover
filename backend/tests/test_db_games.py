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

    def test_create_game_stores_pgn_hash(self):
        g = db_client.create_game(pgn="x", user_id="u1", pgn_hash="abc123")
        assert g["pgn_hash"] == "abc123"

    def test_create_game_pgn_hash_defaults_to_none(self):
        g = db_client.create_game(pgn="x", user_id="u1")
        assert g["pgn_hash"] is None

    def test_find_game_by_pgn_hash_found(self):
        g = db_client.create_game(pgn="x", user_id="u1", pgn_hash="abc123")
        found = db_client.find_game_by_pgn_hash("u1", "abc123")
        assert found["id"] == g["id"]

    def test_find_game_by_pgn_hash_not_found(self):
        db_client.create_game(pgn="x", user_id="u1", pgn_hash="abc123")
        assert db_client.find_game_by_pgn_hash("u1", "does-not-exist") is None

    def test_find_game_by_pgn_hash_scoped_per_user(self):
        # Deux utilisateurs différents peuvent soumettre le même PGN (même hash)
        # sans collision : l'unicité est scopée par utilisateur.
        db_client.create_game(pgn="x", user_id="u1", pgn_hash="abc123")
        assert db_client.find_game_by_pgn_hash("u2", "abc123") is None

    def test_update_game(self):
        g = db_client.create_game(pgn="x")
        db_client.update_game(g["id"], status="completed", result="1-0")
        updated = db_client.get_game(g["id"])
        assert updated["status"] == "completed"
        assert updated["result"] == "1-0"

    def test_update_missing_returns_none(self):
        assert db_client.update_game("nope", status="failed") is None

    def test_update_game_rejects_unknown_field(self):
        # Liste blanche de colonnes : empêche toute injection via un nom de
        # champ interpolé dans la requête SQL (PgRepository.update_game).
        g = db_client.create_game(pgn="x")
        with pytest.raises(ValueError):
            db_client.update_game(g["id"], **{"status = 'x' WHERE 1=1; --": "pwned"})

    def test_update_game_rejects_field_outside_whitelist(self):
        g = db_client.create_game(pgn="x")
        with pytest.raises(ValueError):
            db_client.update_game(g["id"], user_id="autre-utilisateur")

    def test_create_game_starts_progress_at_zero(self):
        # EPIC 28 (US 28.1) : progression coup-par-coup pour le Smart Loader.
        g = db_client.create_game(pgn="x")
        assert g["progress_current"] == 0
        assert g["progress_total"] == 0

    def test_update_game_accepts_progress_fields(self):
        g = db_client.create_game(pgn="x")
        db_client.update_game(g["id"], progress_current=3, progress_total=10)
        updated = db_client.get_game(g["id"])
        assert updated["progress_current"] == 3
        assert updated["progress_total"] == 10

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


class TestProgressHistory:
    _ELOS = {"openings": 2800, "tactics": 3000, "strategy": 1600, "endgames": 700}

    def test_create_snapshot_fields(self):
        record = db_client.create_progress_snapshot("u1", "g1", "blitz", self._ELOS)
        assert record["user_id"] == "u1"
        assert record["game_id"] == "g1"
        assert record["cadence"] == "blitz"
        assert record["elo_openings"] == 2800
        assert record["elo_tactics"] == 3000
        assert "recorded_at" in record and record["recorded_at"]

    def test_get_history_filters_by_cadence(self):
        db_client.create_progress_snapshot("u1", "g1", "blitz", self._ELOS)
        db_client.create_progress_snapshot("u1", "g2", "bullet", self._ELOS)
        assert len(db_client.get_progress_history("u1", "blitz")) == 1
        assert len(db_client.get_progress_history("u1", "bullet")) == 1

    def test_get_history_filters_by_user(self):
        db_client.create_progress_snapshot("u1", "g1", "blitz", self._ELOS)
        db_client.create_progress_snapshot("u2", "g2", "blitz", self._ELOS)
        assert len(db_client.get_progress_history("u1", "blitz")) == 1
        assert len(db_client.get_progress_history(None, "blitz")) == 2

    def test_get_history_sorted_chronologically(self):
        first = db_client.create_progress_snapshot("u1", "g1", "blitz", self._ELOS)
        second = db_client.create_progress_snapshot("u1", "g2", "blitz", self._ELOS)
        history = db_client.get_progress_history("u1", "blitz")
        assert [h["game_id"] for h in history] == [first["game_id"], second["game_id"]]

    def test_get_history_empty(self):
        assert db_client.get_progress_history("u1", "blitz") == []
