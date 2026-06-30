"""Tests unitaires — mapping ACPL → Elo virtuel (US 3.1)."""

from __future__ import annotations

from app.domain.models import TimeClass
from app.domain.virtual_elo import (
    ACPL_ELO_ANCHORS,
    CADENCE_BONUS,
    ELO_CEIL,
    ELO_FLOOR,
    FINAL_CEIL,
    FINAL_FLOOR,
    acpl_to_elo,
    acpl_to_elo_base,
    cadence_bonus,
)


# ===================================================================
# Constantes
# ===================================================================

class TestConstants:
    def test_anchors_table(self):
        assert ACPL_ELO_ANCHORS == [
            (10.0, 2800),
            (20.0, 2400),
            (35.0, 1900),
            (50.0, 1500),
            (75.0, 1100),
            (110.0, 600),
        ]

    def test_base_bounds(self):
        assert ELO_CEIL == 2800
        assert ELO_FLOOR == 600

    def test_final_bounds(self):
        assert FINAL_FLOOR == 600
        assert FINAL_CEIL == 3000


# ===================================================================
# acpl_to_elo_base — ancres exactes
# ===================================================================

class TestAnchors:
    def test_each_anchor_exact(self):
        for acpl, elo in ACPL_ELO_ANCHORS:
            assert acpl_to_elo_base(acpl) == elo

    def test_below_first_anchor_is_ceil(self):
        assert acpl_to_elo_base(0) == 2800
        assert acpl_to_elo_base(5) == 2800
        assert acpl_to_elo_base(10) == 2800

    def test_above_last_anchor_is_floor(self):
        assert acpl_to_elo_base(110) == 600
        assert acpl_to_elo_base(200) == 600


# ===================================================================
# acpl_to_elo_base — interpolation
# ===================================================================

class TestInterpolation:
    def test_midpoint_10_20(self):
        # 15 → 2800 + 0.5×(2400−2800) = 2600
        assert acpl_to_elo_base(15) == 2600

    def test_acpl_40(self):
        # 40 entre (35,1900) et (50,1500) : 1900 + (5/15)×(−400) ≈ 1767
        assert acpl_to_elo_base(40) == 1767

    def test_monotonic_decreasing(self):
        prev = acpl_to_elo_base(0)
        for acpl in range(1, 130):
            current = acpl_to_elo_base(float(acpl))
            assert current <= prev
            prev = current


# ===================================================================
# cadence_bonus
# ===================================================================

class TestCadenceBonus:
    def test_values(self):
        assert cadence_bonus(TimeClass.BULLET) == 200
        assert cadence_bonus(TimeClass.BLITZ) == 100
        assert cadence_bonus(TimeClass.RAPID) == 0
        assert cadence_bonus(TimeClass.DAILY) == 0

    def test_none_is_zero(self):
        assert cadence_bonus(None) == 0

    def test_bonus_table_matches(self):
        assert CADENCE_BONUS[TimeClass.BULLET] == 200
        assert CADENCE_BONUS[TimeClass.BLITZ] == 100


# ===================================================================
# acpl_to_elo — final
# ===================================================================

class TestAcplToElo:
    def test_no_cadence_equals_base(self):
        assert acpl_to_elo(40) == acpl_to_elo_base(40)

    def test_bullet_bonus_example(self):
        # ACPL 40 en Bullet : 1767 + 200 = 1967
        assert acpl_to_elo(40, TimeClass.BULLET) == 1967

    def test_blitz_bonus(self):
        assert acpl_to_elo(40, TimeClass.BLITZ) == 1867

    def test_final_ceil_clamp(self):
        # base 2800 + 200 = 3000 → plafond
        assert acpl_to_elo(8, TimeClass.BULLET) == 3000

    def test_final_floor(self):
        assert acpl_to_elo(110, None) == 600
        assert acpl_to_elo(200, TimeClass.DAILY) == 600
