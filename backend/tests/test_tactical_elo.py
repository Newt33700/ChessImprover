"""Tests unitaires — Elo tactique (US 8.1, EPIC 8)."""

from __future__ import annotations

from app.domain.tactical_elo import (
    DEFAULT_TACTICAL_ELO,
    ELO_STEP,
    MIN_TACTICAL_ELO,
    update_elo,
)


class TestUpdateElo:
    def test_success_adds_15(self):
        assert update_elo(1000, True) == 1015

    def test_failure_subtracts_15(self):
        assert update_elo(1000, False) == 985

    def test_step_constant_is_15(self):
        assert ELO_STEP == 15

    def test_default_elo_is_1000(self):
        assert DEFAULT_TACTICAL_ELO == 1000

    def test_floor_prevents_going_below_minimum(self):
        assert update_elo(105, False) == MIN_TACTICAL_ELO

    def test_floor_exact_boundary(self):
        assert update_elo(MIN_TACTICAL_ELO + ELO_STEP, False) == MIN_TACTICAL_ELO

    def test_success_has_no_ceiling(self):
        assert update_elo(3000, True) == 3015
