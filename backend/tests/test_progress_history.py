"""Tests unitaires — historisation de la progression (US 5.1)."""

from __future__ import annotations

import datetime as _dt

from app.domain.progress_history import build_snapshot, filter_history_by_days


def _move(color, phase, cpl=None, position_type="neutral"):
    return {"color": color, "phase": phase, "cpl": cpl, "position_type": position_type}


# ===================================================================
# build_snapshot
# ===================================================================

class TestBuildSnapshot:
    def test_unknown_cadence_returns_none(self):
        moves = [_move("white", "opening", 10)]
        assert build_snapshot(moves, time_control=None) is None
        assert build_snapshot(moves, time_control="not-a-cadence") is None

    def test_known_cadence_returns_record(self):
        moves = [_move("white", "opening", 10)]
        record = build_snapshot(moves, time_control="300", user_color="white")
        assert record is not None
        assert record["cadence"] == "blitz"
        assert set(record.keys()) == {"user_id", "game_id", "cadence", "elos"}
        assert set(record["elos"].keys()) == {"openings", "tactics", "strategy", "endgames"}

    def test_filters_by_user_color(self):
        # Coups noirs à perte massive ne doivent PAS dégrader l'Elo blanc.
        moves = [
            _move("white", "opening", 0),
            _move("black", "opening", 400),
        ]
        white_record = build_snapshot(moves, time_control="300", user_color="white")
        black_record = build_snapshot(moves, time_control="300", user_color="black")
        assert white_record["elos"]["openings"] > black_record["elos"]["openings"]

    def test_passes_through_ids(self):
        record = build_snapshot(
            [_move("white", "opening", 10)],
            time_control="60",
            game_id="game-1",
            user_id="user-1",
        )
        assert record["game_id"] == "game-1"
        assert record["user_id"] == "user-1"
        assert record["cadence"] == "bullet"

    def test_empty_moves_uses_default_elo(self):
        record = build_snapshot([], time_control="600")
        assert record["cadence"] == "rapid"
        # Aucune donnée par catégorie → DEFAULT_ELO partout (comportement
        # partagé avec stats_aggregator.category_elos).
        assert record["elos"]["openings"] == record["elos"]["endgames"] == 1200


# ===================================================================
# filter_history_by_days
# ===================================================================

_NOW = _dt.datetime(2026, 7, 1, 12, 0, tzinfo=_dt.timezone.utc)


def _row(days_ago, **overrides):
    recorded = (_NOW - _dt.timedelta(days=days_ago)).isoformat()
    row = {"recorded_at": recorded, "elo_openings": 1500}
    row.update(overrides)
    return row


class TestFilterHistoryByDays:
    def test_empty_history(self):
        assert filter_history_by_days([], days=30, now=_NOW) == []

    def test_keeps_within_window(self):
        rows = [_row(5), _row(15), _row(45)]
        result = filter_history_by_days(rows, days=30, now=_NOW)
        assert len(result) == 2

    def test_exact_boundary_included(self):
        rows = [_row(30)]
        result = filter_history_by_days(rows, days=30, now=_NOW)
        assert len(result) == 1

    def test_just_outside_boundary_excluded(self):
        rows = [_row(30, recorded_at=(_NOW - _dt.timedelta(days=30, seconds=1)).isoformat())]
        result = filter_history_by_days(rows, days=30, now=_NOW)
        assert result == []

    def test_zero_or_negative_days_returns_empty(self):
        rows = [_row(0)]
        assert filter_history_by_days(rows, days=0, now=_NOW) == []
        assert filter_history_by_days(rows, days=-5, now=_NOW) == []

    def test_missing_recorded_at_excluded(self):
        rows = [{"elo_openings": 1500}]
        assert filter_history_by_days(rows, days=30, now=_NOW) == []

    def test_malformed_date_excluded(self):
        rows = [_row(5, recorded_at="not-a-date")]
        assert filter_history_by_days(rows, days=30, now=_NOW) == []

    def test_naive_iso_treated_as_utc(self):
        # Défensif : une date sans fuseau (donnée legacy/corrompue) est
        # supposée UTC plutôt que de faire planter la comparaison aware/naive.
        naive = (_NOW - _dt.timedelta(days=2)).replace(tzinfo=None).isoformat()
        rows = [_row(2, recorded_at=naive)]
        assert len(filter_history_by_days(rows, days=30, now=_NOW)) == 1

    def test_z_suffix_parsed(self):
        recorded = (_NOW - _dt.timedelta(days=2)).isoformat().replace("+00:00", "Z")
        rows = [_row(2, recorded_at=recorded)]
        assert len(filter_history_by_days(rows, days=30, now=_NOW)) == 1

    def test_default_now_used_when_not_provided(self):
        # Sans `now` explicite, la fonction utilise l'heure réelle : une ligne
        # d'il y a 1 jour doit systématiquement rester dans une fenêtre de 30j.
        rows = [_row(1)]
        assert len(filter_history_by_days(rows, days=30)) == 1
