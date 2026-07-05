"""Tests — règles pures de la synchronisation à la connexion (EPIC 23)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain import game_sync


class TestContratPo:
    def test_fetch_last_games_is_10(self):
        # Décision PO (EPIC 23) : ratisser les 10 dernières parties.
        assert game_sync.FETCH_LAST_GAMES == 10

    def test_max_analyses_per_sync_is_5(self):
        # Décision PO (EPIC 23) : plafond de 5 nouvelles analyses par sync.
        assert game_sync.MAX_ANALYSES_PER_SYNC == 5

    def test_stale_processing_minutes_is_10(self):
        assert game_sync.STALE_PROCESSING_MINUTES == 10


class TestDetectUserColor:
    def test_black_side_match(self):
        raw = {"white": {"username": "Autre"}, "black": {"username": "FabDek"}}
        assert game_sync.detect_user_color(raw, "fabdek") == "black"

    def test_white_side_match(self):
        raw = {"white": {"username": "fabdek"}, "black": {"username": "Autre"}}
        assert game_sync.detect_user_color(raw, "FabDek") == "white"

    def test_username_absent_defaults_to_white(self):
        raw = {"white": {"username": "a"}, "black": {"username": "b"}}
        assert game_sync.detect_user_color(raw, "fabdek") == "white"

    def test_missing_sides_default_to_white(self):
        assert game_sync.detect_user_color({}, "fabdek") == "white"

    def test_empty_username_defaults_to_white(self):
        raw = {"black": {"username": ""}}
        assert game_sync.detect_user_color(raw, "") == "white"

    def test_none_username_does_not_match_any_default_placeholder(self):
        # `(chess_username or "").lower()` : un pseudo absent (None) doit
        # rester une chaîne vide, jamais une valeur par défaut qui pourrait
        # accidentellement matcher un pseudo réel.
        raw = {"black": {"username": "xxxx"}}
        assert game_sync.detect_user_color(raw, None) == "white"

    def test_missing_black_username_does_not_match_any_default_placeholder(self):
        # Même chose côté `black` : un dictionnaire sans "username" doit
        # rester une chaîne vide, jamais un défaut qui matcherait le pseudo.
        raw = {"black": {}}
        assert game_sync.detect_user_color(raw, "xxxx") == "white"


class TestExtractSyncCandidates:
    def test_keeps_only_games_with_pgn(self):
        raw = [
            {"pgn": "1. e4 e5", "time_control": "180"},
            {"time_control": "60"},  # pas de PGN
            {"pgn": None},  # PGN nul
            {"pgn": 42},  # PGN non-chaîne
        ]
        candidates = game_sync.extract_sync_candidates(raw, "fabdek")
        assert len(candidates) == 1
        assert candidates[0]["pgn"] == "1. e4 e5"

    def test_preserves_input_order(self):
        raw = [{"pgn": "a"}, {"pgn": "b"}, {"pgn": "c"}]
        candidates = game_sync.extract_sync_candidates(raw, "fabdek")
        assert [c["pgn"] for c in candidates] == ["a", "b", "c"]

    def test_maps_color_and_time_control(self):
        raw = [
            {
                "pgn": "1. d4",
                "time_control": "600",
                "black": {"username": "fabdek"},
            }
        ]
        c = game_sync.extract_sync_candidates(raw, "fabdek")[0]
        assert c["user_color"] == "black"
        assert c["time_control"] == "600"

    def test_missing_time_control_is_none(self):
        c = game_sync.extract_sync_candidates([{"pgn": "1. d4"}], "x")[0]
        assert c["time_control"] is None

    def test_empty_or_none_input(self):
        assert game_sync.extract_sync_candidates([], "x") == []
        assert game_sync.extract_sync_candidates(None, "x") == []


class TestIsStaleProcessing:
    def _game(self, **overrides):
        base = {
            "status": "processing",
            "pgn": "1. e4",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }
        base.update(overrides)
        return base

    def test_old_processing_game_is_stale(self):
        assert game_sync.is_stale_processing(self._game()) is True

    def test_recent_processing_game_is_not_stale(self):
        recent = datetime.now(timezone.utc).isoformat()
        assert game_sync.is_stale_processing(self._game(created_at=recent)) is False

    def test_completed_game_is_never_stale(self):
        assert game_sync.is_stale_processing(self._game(status="completed")) is False

    def test_missing_pgn_is_never_stale(self):
        assert game_sync.is_stale_processing(self._game(pgn=None)) is False

    def test_unreadable_created_at_is_not_stale(self):
        # Prudence : sans horodatage lisible, ne pas risquer une double analyse.
        assert game_sync.is_stale_processing(self._game(created_at="n/a")) is False
        assert game_sync.is_stale_processing(self._game(created_at=None)) is False

    def test_datetime_created_at_supported(self):
        old = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert game_sync.is_stale_processing(self._game(created_at=old)) is True

    def test_naive_datetime_treated_as_utc(self):
        naive_old = datetime.utcnow() - timedelta(minutes=30)
        assert game_sync.is_stale_processing(self._game(created_at=naive_old)) is True

    def test_threshold_boundary(self):
        now = datetime.now(timezone.utc)
        at_threshold = now - timedelta(minutes=game_sync.STALE_PROCESSING_MINUTES)
        game = self._game(created_at=at_threshold.isoformat())
        assert game_sync.is_stale_processing(game, now=now) is True
        just_under = now - timedelta(minutes=game_sync.STALE_PROCESSING_MINUTES - 1)
        game = self._game(created_at=just_under.isoformat())
        assert game_sync.is_stale_processing(game, now=now) is False
