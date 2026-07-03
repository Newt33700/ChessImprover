"""Tests unitaires — store flashcards SRS (EPIC 20, US 20.1/20.2)."""

from __future__ import annotations

import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestCreateFlashcard:
    def test_returns_card_with_default_srs_schedule(self):
        card = db_client.create_flashcard("u1", "game-1", "8/8/8/8/8/8/8/k1KQ4 w - - 0 1", "Qd4+")
        assert card["fen"] == "8/8/8/8/8/8/8/k1KQ4 w - - 0 1"
        assert card["solution"] == "Qd4+"
        assert card["game_id"] == "game-1"
        assert card["ease_factor"] == 2.5
        assert card["interval_days"] == 1
        assert card["repetitions"] == 0
        assert "due_date" in card and "id" in card

    def test_game_id_can_be_none(self):
        card = db_client.create_flashcard("u1", None, "fen", "Qd4+")
        assert card["game_id"] is None


class TestGetFlashcards:
    def test_returns_only_own_cards(self):
        db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        db_client.create_flashcard("u2", "g2", "fenB", "Rxd5")
        cards_u1 = db_client.get_flashcards("u1")
        assert len(cards_u1) == 1
        assert cards_u1[0]["fen"] == "fenA"

    def test_unknown_user_has_empty_cemetery(self):
        assert db_client.get_flashcards("does-not-exist") == []


class TestGetFlashcard:
    def test_returns_known_card(self):
        card = db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        assert db_client.get_flashcard(card["id"])["fen"] == "fenA"

    def test_unknown_id_returns_none(self):
        assert db_client.get_flashcard("missing") is None


class TestGetDueFlashcards:
    def test_new_card_is_due_today(self):
        card = db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        due = db_client.get_due_flashcards("u1", card["due_date"])
        assert [c["id"] for c in due] == [card["id"]]

    def test_card_due_in_the_future_is_excluded(self):
        card = db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        db_client.update_flashcard_schedule(card["id"], 2.6, 6, 2, "2099-01-01")
        assert db_client.get_due_flashcards("u1", "2026-07-01") == []

    def test_only_returns_own_cards(self):
        card1 = db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        db_client.create_flashcard("u2", "g2", "fenB", "Rxd5")
        due = db_client.get_due_flashcards("u1", card1["due_date"])
        assert len(due) == 1


class TestUpdateFlashcardSchedule:
    def test_persists_new_schedule(self):
        card = db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        updated = db_client.update_flashcard_schedule(card["id"], 2.6, 6, 1, "2026-07-08")
        assert updated["ease_factor"] == 2.6
        assert updated["interval_days"] == 6
        assert updated["repetitions"] == 1
        assert updated["due_date"] == "2026-07-08"

    def test_unknown_card_returns_none(self):
        assert db_client.update_flashcard_schedule("missing", 2.6, 6, 1, "2026-07-08") is None


class TestResetStore:
    def test_reset_store_clears_flashcards(self):
        db_client.create_flashcard("u1", "g1", "fenA", "Qd4+")
        db_client._reset_store()
        assert db_client.get_flashcards("u1") == []
