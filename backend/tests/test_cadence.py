"""Tests unitaires — classification de cadence (EPIC 1)."""

from __future__ import annotations

from app.domain.cadence import (
    BLITZ_MIN_SECONDS,
    INCREMENT_MOVES,
    RAPID_MIN_SECONDS,
    classify_cadence,
    estimate_seconds,
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
