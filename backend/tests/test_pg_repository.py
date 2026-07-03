"""Tests — adaptateur Postgres & délégation db_client (EPIC 1).

Les requêtes SQL réelles nécessitent une base ; on vérifie ici le contrat sans
connexion : construction, colonnes, et le fait que db_client reste en in-memory
tant que ``DATABASE_URL`` n'est pas défini.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.infrastructure import db_client
from app.infrastructure.pg_repository import PgRepository


class TestPgRepository:
    def test_stores_dsn(self):
        repo = PgRepository("postgresql://user:pw@host/db")
        assert repo.dsn == "postgresql://user:pw@host/db"

    def test_move_columns_match_schema(self):
        assert PgRepository._MOVE_COLS == (
            "move_number", "color", "move_san", "eval_before", "eval_after",
            "score_cp", "cpl", "is_mate", "mate_in", "phase", "position_type",
            "fen", "best_move_san", "time_spent_seconds",
            "alert_severity", "alert_text", "tts_text",
        )

    def test_progress_history_methods_exist(self):
        # Verrouille le contrat US 5.1 : les deux méthodes doivent exister
        # avec cette signature, indépendamment de toute connexion réelle.
        import inspect

        create_sig = inspect.signature(PgRepository.create_progress_snapshot)
        assert list(create_sig.parameters) == ["self", "user_id", "game_id", "cadence", "elos"]

        get_sig = inspect.signature(PgRepository.get_progress_history)
        assert list(get_sig.parameters) == ["self", "user_id", "cadence"]

    def test_create_game_accepts_pgn_hash(self):
        # Verrouille le contrat US 7.2 : create_game doit accepter pgn_hash.
        import inspect

        sig = inspect.signature(PgRepository.create_game)
        assert list(sig.parameters) == [
            "self", "pgn", "user_id", "time_control", "user_color", "status", "pgn_hash",
        ]

    def test_find_game_by_pgn_hash_method_exists(self):
        import inspect

        sig = inspect.signature(PgRepository.find_game_by_pgn_hash)
        assert list(sig.parameters) == ["self", "user_id", "pgn_hash"]

    def test_tactical_attempts_methods_exist(self):
        # Verrouille le contrat US 8.4 : les deux méthodes doivent exister
        # avec cette signature, indépendamment de toute connexion réelle.
        import inspect

        record_sig = inspect.signature(PgRepository.record_tactical_attempt)
        assert list(record_sig.parameters) == [
            "self", "user_id", "problem_id", "category", "success", "time_taken",
        ]

        get_sig = inspect.signature(PgRepository.get_tactical_attempts)
        assert list(get_sig.parameters) == ["self", "user_id"]

    def test_opening_repertoire_methods_exist(self):
        # Verrouille le contrat EPIC 9 : les méthodes doivent exister avec
        # cette signature, indépendamment de toute connexion réelle.
        import inspect

        create_sig = inspect.signature(PgRepository.create_opening_line)
        assert list(create_sig.parameters) == ["self", "user_id", "name", "color", "moves"]

        get_sig = inspect.signature(PgRepository.get_opening_lines)
        assert list(get_sig.parameters) == ["self", "user_id"]

        due_sig = inspect.signature(PgRepository.get_due_opening_lines)
        assert list(due_sig.parameters) == ["self", "user_id", "today"]

        update_sig = inspect.signature(PgRepository.update_opening_line_schedule)
        assert list(update_sig.parameters) == [
            "self", "line_id", "ease_factor", "interval_days", "repetitions", "due_date",
        ]

        delete_sig = inspect.signature(PgRepository.delete_opening_line)
        assert list(delete_sig.parameters) == ["self", "line_id", "user_id"]

    def test_error_profile_methods_exist(self):
        # Verrouille le contrat EPIC 11 : les méthodes doivent exister avec
        # cette signature, indépendamment de toute connexion réelle.
        import inspect

        get_sig = inspect.signature(PgRepository.get_error_profile)
        assert list(get_sig.parameters) == ["self", "user_id", "error_type"]

        list_sig = inspect.signature(PgRepository.get_error_profiles)
        assert list(list_sig.parameters) == ["self", "user_id"]

        upsert_sig = inspect.signature(PgRepository.upsert_error_profile)
        assert list(upsert_sig.parameters) == [
            "self", "user_id", "error_type", "frequency_score", "last_observed",
        ]

    def test_tactical_sprint_methods_exist(self):
        # Verrouille le contrat EPIC 12 : les méthodes doivent exister avec
        # cette signature, indépendamment de toute connexion réelle.
        import inspect

        create_sig = inspect.signature(PgRepository.create_sprint)
        assert list(create_sig.parameters) == ["self", "user_id"]

        get_sig = inspect.signature(PgRepository.get_sprint)
        assert list(get_sig.parameters) == ["self", "sprint_id"]

        best_sig = inspect.signature(PgRepository.get_best_sprint)
        assert list(best_sig.parameters) == ["self"]

    def test_srs_flashcards_methods_exist(self):
        # Verrouille le contrat EPIC 20 : les méthodes doivent exister avec
        # cette signature, indépendamment de toute connexion réelle.
        import inspect

        create_sig = inspect.signature(PgRepository.create_flashcard)
        assert list(create_sig.parameters) == ["self", "user_id", "game_id", "fen", "solution"]

        get_sig = inspect.signature(PgRepository.get_flashcards)
        assert list(get_sig.parameters) == ["self", "user_id"]

        get_one_sig = inspect.signature(PgRepository.get_flashcard)
        assert list(get_one_sig.parameters) == ["self", "card_id"]

        due_sig = inspect.signature(PgRepository.get_due_flashcards)
        assert list(due_sig.parameters) == ["self", "user_id", "today"]

        update_sig = inspect.signature(PgRepository.update_flashcard_schedule)
        assert list(update_sig.parameters) == [
            "self", "card_id", "ease_factor", "interval_days", "repetitions", "due_date",
        ]

    def test_line_row_maps_line_name_column_to_name_key(self):
        row = {"id": "1", "line_name": "Ruy Lopez", "color": "white"}
        mapped = PgRepository._line_row(row)
        assert mapped == {"id": "1", "name": "Ruy Lopez", "color": "white"}

    def test_iso_converts_any_datetime_field(self):
        import datetime as _dt

        row = {"recorded_at": _dt.datetime(2026, 7, 1, tzinfo=_dt.timezone.utc), "cadence": "blitz"}
        converted = PgRepository._iso(row)
        assert converted["recorded_at"] == "2026-07-01T00:00:00+00:00"
        assert converted["cadence"] == "blitz"

    def test_iso_leaves_non_datetime_untouched(self):
        row = {"id": 1, "recorded_at": None}
        assert PgRepository._iso(row) == {"id": 1, "recorded_at": None}


class TestDelegation:
    def test_pg_none_without_database_url(self):
        # Par défaut aucune base → mode in-memory.
        assert settings.database_url is None
        assert db_client._pg() is None

    def test_pg_repo_built_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "database_url", "postgresql://x/y")
        db_client._pg_repo = None
        try:
            repo = db_client._pg()
            assert isinstance(repo, PgRepository)
            assert repo.dsn == "postgresql://x/y"
        finally:
            db_client._pg_repo = None
