"""Tests unitaires — classification de cadence (EPIC 1)."""

from __future__ import annotations

from app.domain.cadence import (
    BLITZ_MIN_SECONDS,
    INCREMENT_MOVES,
    RAPID_MIN_SECONDS,
    classify_cadence,
    estimate_seconds,
    parse_increment,
)
from app.domain.models import TimeClass


class TestConstants:
    def test_thresholds(self):
        assert BLITZ_MIN_SECONDS == 180
        assert RAPID_MIN_SECONDS == 600
        assert INCREMENT_MOVES == 40


class TestEstimateSeconds:
    def test_plain_base(self):
        assert estimate_seconds("600") == 600

    def test_with_increment(self):
        assert estimate_seconds("180+2") == 180 + 40 * 2

    def test_daily(self):
        assert estimate_seconds("1/86400") == 86400

    def test_none_and_empty(self):
        assert estimate_seconds(None) is None
        assert estimate_seconds("") is None

    def test_garbage(self):
        assert estimate_seconds("abc") is None


class TestClassifyCadence:
    def test_bullet(self):
        assert classify_cadence("60") == TimeClass.BULLET
        assert classify_cadence("120+1") == TimeClass.BULLET  # 120+40=160 < 180

    def test_blitz_lower_boundary(self):
        assert classify_cadence("180") == TimeClass.BLITZ

    def test_blitz(self):
        assert classify_cadence("300") == TimeClass.BLITZ

    def test_rapid_lower_boundary(self):
        assert classify_cadence("600") == TimeClass.RAPID

    def test_rapid(self):
        assert classify_cadence("1800") == TimeClass.RAPID

    def test_daily(self):
        assert classify_cadence("1/86400") == TimeClass.DAILY

    def test_none(self):
        assert classify_cadence(None) is None
        assert classify_cadence("") is None

    def test_garbage(self):
        assert classify_cadence("xyz") is None


class TestParseIncrement:
    def test_plain_increment(self):
        assert parse_increment("180+2") == 2

    def test_double_digit_increment(self):
        assert parse_increment("600+15") == 15

    def test_no_increment_is_zero(self):
        assert parse_increment("600") == 0

    def test_none_and_empty(self):
        assert parse_increment(None) == 0
        assert parse_increment("") == 0

    def test_daily_has_no_increment(self):
        assert parse_increment("1/86400") == 0

    def test_garbage_increment_is_zero(self):
        assert parse_increment("180+abc") == 0

    def test_garbage_base_is_zero(self):
        # Le format de base est illisible ; seul l'incrément importe ici,
        # `int()` échoue quand même sur la partie droite -> repli à 0.
        assert parse_increment("abc+xyz") == 0
