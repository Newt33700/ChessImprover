"""Tests unitaires — store répertoire d'ouvertures (EPIC 9, US 9.1/9.2)."""

from __future__ import annotations

import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


class TestCreateOpeningLine:
    def test_returns_line_with_default_srs_schedule(self):
        line = db_client.create_opening_line("u1", "Ruy Lopez", "white", ["e4", "e5", "Nf3", "Nc6", "Bb5"])
        assert line["name"] == "Ruy Lopez"
        assert line["color"] == "white"
        assert line["moves"] == ["e4", "e5", "Nf3", "Nc6", "Bb5"]
        assert line["ease_factor"] == 2.5
        assert line["interval_days"] == 1
        assert line["repetitions"] == 0
        assert "due_date" in line and "id" in line


class TestGetOpeningLines:
    def test_returns_only_own_lines(self):
        db_client.create_opening_line("u1", "A", "white", ["e4"])
        db_client.create_opening_line("u2", "B", "black", ["d4"])
        lines_u1 = db_client.get_opening_lines("u1")
        assert len(lines_u1) == 1
        assert lines_u1[0]["name"] == "A"

    def test_unknown_user_has_empty_repertoire(self):
        assert db_client.get_opening_lines("does-not-exist") == []


class TestGetOpeningLine:
    def test_returns_known_line(self):
        line = db_client.create_opening_line("u1", "A", "white", ["e4"])
        assert db_client.get_opening_line(line["id"])["name"] == "A"

    def test_unknown_id_returns_none(self):
        assert db_client.get_opening_line("missing") is None


class TestGetDueOpeningLines:
    def test_new_line_is_due_today(self):
        line = db_client.create_opening_line("u1", "A", "white", ["e4"])
        due = db_client.get_due_opening_lines("u1", line["due_date"])
        assert [line_["id"] for line_ in due] == [line["id"]]

    def test_line_due_in_the_future_is_excluded(self):
        line = db_client.create_opening_line("u1", "A", "white", ["e4"])
        db_client.update_opening_line_schedule(line["id"], 2.6, 6, 2, "2099-01-01")
        assert db_client.get_due_opening_lines("u1", "2026-07-01") == []

    def test_only_returns_own_lines(self):
        line1 = db_client.create_opening_line("u1", "A", "white", ["e4"])
        db_client.create_opening_line("u2", "B", "black", ["d4"])
        due = db_client.get_due_opening_lines("u1", line1["due_date"])
        assert len(due) == 1


class TestUpdateOpeningLineSchedule:
    def test_persists_new_schedule(self):
        line = db_client.create_opening_line("u1", "A", "white", ["e4"])
        updated = db_client.update_opening_line_schedule(line["id"], 2.6, 6, 1, "2026-07-08")
        assert updated["ease_factor"] == 2.6
        assert updated["interval_days"] == 6
        assert updated["repetitions"] == 1
        assert updated["due_date"] == "2026-07-08"

    def test_unknown_line_returns_none(self):
        assert db_client.update_opening_line_schedule("missing", 2.6, 6, 1, "2026-07-08") is None


class TestDeleteOpeningLine:
    def test_owner_can_delete(self):
        line = db_client.create_opening_line("u1", "A", "white", ["e4"])
        assert db_client.delete_opening_line(line["id"], "u1") is True
        assert db_client.get_opening_line(line["id"]) is None

    def test_non_owner_cannot_delete(self):
        line = db_client.create_opening_line("u1", "A", "white", ["e4"])
        assert db_client.delete_opening_line(line["id"], "u2") is False
        assert db_client.get_opening_line(line["id"]) is not None

    def test_unknown_line_returns_false(self):
        assert db_client.delete_opening_line("missing", "u1") is False

    def test_reset_store_clears_lines(self):
        db_client.create_opening_line("u1", "A", "white", ["e4"])
        db_client._reset_store()
        assert db_client.get_opening_lines("u1") == []
