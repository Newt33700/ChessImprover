"""Tests — courbe d'Elo Chess.com par cadence (EPIC 24, domaine pur)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain import elo_curve

NOW = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)


def _raw(end_time, rating=1200, cadence="blitz", white="fabdek", black="adv"):
    return {
        "time_class": cadence,
        "end_time": end_time,
        "white": {"username": white, "rating": rating if white == "fabdek" else 999},
        "black": {"username": black, "rating": rating if black == "fabdek" else 999},
    }


def _ts(days_ago: int, hour: int = 12) -> int:
    return int((NOW - timedelta(days=days_ago)).replace(hour=hour).timestamp())


class TestMonthsCovering:
    def test_window_within_single_month(self):
        now = datetime(2026, 7, 20, tzinfo=timezone.utc)
        assert elo_curve.months_covering(now, 7) == [(2026, 7)]

    def test_window_spanning_two_months(self):
        assert elo_curve.months_covering(NOW, 7) == [(2026, 6), (2026, 7)]

    def test_90_days_spans_four_months(self):
        assert elo_curve.months_covering(NOW, 90) == [
            (2026, 4),
            (2026, 5),
            (2026, 6),
            (2026, 7),
        ]

    def test_year_boundary(self):
        now = datetime(2026, 1, 10, tzinfo=timezone.utc)
        assert elo_curve.months_covering(now, 30) == [(2025, 12), (2026, 1)]

    def test_days_floor_at_one(self):
        assert elo_curve.months_covering(NOW, 0) == [(2026, 7)]


class TestBuildEloCurve:
    def test_one_point_per_played_day_last_rating_wins(self):
        games = [
            _raw(_ts(1, hour=9), rating=1200),
            _raw(_ts(1, hour=21), rating=1215),  # dernière du jour → retenue
            _raw(_ts(3), rating=1180),
        ]
        points = elo_curve.build_elo_curve(games, "fabdek", "blitz", 7, now=NOW)
        assert [p["rating"] for p in points] == [1180, 1215]  # ordre chronologique

    def test_filters_by_cadence(self):
        games = [
            _raw(_ts(1), rating=1200, cadence="blitz"),
            _raw(_ts(1), rating=800, cadence="bullet"),
        ]
        points = elo_curve.build_elo_curve(games, "fabdek", "bullet", 7, now=NOW)
        assert [p["rating"] for p in points] == [800]

    def test_filters_by_window(self):
        games = [
            _raw(_ts(2), rating=1200),
            _raw(_ts(40), rating=1100),  # hors fenêtre 7 jours
        ]
        points = elo_curve.build_elo_curve(games, "fabdek", "blitz", 7, now=NOW)
        assert [p["rating"] for p in points] == [1200]

    def test_rating_read_from_black_side_case_insensitive(self):
        games = [_raw(_ts(1), rating=1350, white="adv", black="fabdek")]
        points = elo_curve.build_elo_curve(games, "FabDek", "blitz", 7, now=NOW)
        assert points[0]["rating"] == 1350

    def test_ignores_games_without_usable_data(self):
        games = [
            {"time_class": "blitz"},  # sans end_time
            {"time_class": "blitz", "end_time": "hier"},  # end_time non numérique
            _raw(_ts(1), white="autre", black="adv"),  # joueur absent
            {
                "time_class": "blitz",
                "end_time": _ts(1),
                "white": {"username": "fabdek", "rating": None},
            },  # rating absent
        ]
        assert elo_curve.build_elo_curve(games, "fabdek", "blitz", 7, now=NOW) == []

    def test_empty_input(self):
        assert elo_curve.build_elo_curve([], "fabdek", "blitz", 30, now=NOW) == []
        assert elo_curve.build_elo_curve(None, "fabdek", "blitz", 30, now=NOW) == []

    def test_dates_are_iso_and_sorted(self):
        games = [_raw(_ts(5), rating=1100), _raw(_ts(2), rating=1150)]
        points = elo_curve.build_elo_curve(games, "fabdek", "blitz", 30, now=NOW)
        assert points == [
            {"date": "2026-06-28", "rating": 1100},
            {"date": "2026-07-01", "rating": 1150},
        ]
