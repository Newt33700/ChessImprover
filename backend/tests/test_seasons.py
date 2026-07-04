"""Tests unitaires — Moteur de saisons (EPIC 30)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.seasons import get_active_season, load_seasons, seconds_remaining

SEASON = {
    "id": "halloween",
    "name": "Halloween Chess",
    "start": "2026-10-15T00:00:00+00:00",
    "end": "2026-11-05T23:59:59+00:00",
    "banner_message": "🎃 Événement Halloween",
    "cosmetic_piece_theme": "cyber-tactics",
    "cosmetic_board_theme": "cyber",
}


class TestLoadSeasons:
    def test_loads_real_catalog_as_a_list(self):
        assert isinstance(load_seasons(), list)

    def test_missing_file_returns_empty_list(self, tmp_path):
        assert load_seasons(tmp_path / "does-not-exist.json") == []

    def test_invalid_json_returns_empty_list(self, tmp_path):
        bad = tmp_path / "seasons.json"
        bad.write_text("not json at all")
        assert load_seasons(bad) == []

    def test_non_list_json_returns_empty_list(self, tmp_path):
        bad = tmp_path / "seasons.json"
        bad.write_text('{"not": "a list"}')
        assert load_seasons(bad) == []


class TestGetActiveSeason:
    def test_within_window_is_active(self):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        assert get_active_season([SEASON], now) == SEASON

    def test_before_window_is_inactive(self):
        now = datetime(2026, 9, 1, tzinfo=timezone.utc)
        assert get_active_season([SEASON], now) is None

    def test_after_window_is_inactive(self):
        now = datetime(2026, 12, 1, tzinfo=timezone.utc)
        assert get_active_season([SEASON], now) is None

    def test_exact_start_boundary_is_active(self):
        now = datetime.fromisoformat(SEASON["start"])
        assert get_active_season([SEASON], now) == SEASON

    def test_exact_end_boundary_is_active(self):
        now = datetime.fromisoformat(SEASON["end"])
        assert get_active_season([SEASON], now) == SEASON

    def test_empty_catalog_is_inactive(self):
        assert get_active_season([], datetime.now(timezone.utc)) is None

    def test_malformed_entry_ignored_not_crashing(self):
        malformed = {"id": "broken", "start": "not-a-date", "end": "also-not-a-date"}
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        assert get_active_season([malformed, SEASON], now) == SEASON

    def test_missing_start_or_end_ignored(self):
        incomplete = {"id": "incomplete", "end": "2026-12-31T00:00:00+00:00"}
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        assert get_active_season([incomplete, SEASON], now) == SEASON

    def test_first_matching_season_wins(self):
        overlapping = {**SEASON, "id": "other"}
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        assert get_active_season([SEASON, overlapping], now)["id"] == "halloween"


class TestSecondsRemaining:
    def test_positive_before_end(self):
        now = datetime(2026, 11, 5, 23, 59, 0, tzinfo=timezone.utc)
        assert seconds_remaining(SEASON, now) == 59

    def test_zero_after_end(self):
        now = datetime(2026, 12, 1, tzinfo=timezone.utc)
        assert seconds_remaining(SEASON, now) == 0

    def test_zero_on_malformed_end(self):
        malformed = {**SEASON, "end": "not-a-date"}
        assert seconds_remaining(malformed, datetime.now(timezone.utc)) == 0
