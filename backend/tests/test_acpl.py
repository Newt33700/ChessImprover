"""Tests unitaires — CPL & ACPL par phase (US 2.2)."""

from __future__ import annotations

from app.domain.acpl import (
    CPL_CAP,
    PhasedMove,
    acpl_by_phase,
    average_cpl,
    centipawn_loss,
    overall_acpl,
)
from app.domain.models import Phase


# ===================================================================
# Constante
# ===================================================================

def test_cpl_cap_is_400():
    assert CPL_CAP == 400


# ===================================================================
# centipawn_loss
# ===================================================================

class TestCentipawnLoss:
    def test_best_move_zero_loss(self):
        assert centipawn_loss(100, 100) == 0

    def test_simple_loss(self):
        assert centipawn_loss(200, 50) == 150

    def test_negative_loss_floored_to_zero(self):
        # Coup joué « meilleur » que le meilleur → pas de gain, plancher 0
        assert centipawn_loss(50, 200) == 0

    def test_cap_applied(self):
        assert centipawn_loss(1000, 0) == CPL_CAP

    def test_cap_exact_boundary(self):
        assert centipawn_loss(400, 0) == 400

    def test_just_above_cap(self):
        assert centipawn_loss(401, 0) == 400

    def test_just_below_cap(self):
        assert centipawn_loss(399, 0) == 399

    def test_uses_difference_not_absolute(self):
        # Le signe compte : best - played, pas |best| - |played|
        assert centipawn_loss(-100, -250) == 150


# ===================================================================
# average_cpl
# ===================================================================

class TestAverageCpl:
    def test_empty_is_none(self):
        assert average_cpl([]) is None

    def test_single(self):
        assert average_cpl([42]) == 42.0

    def test_mean(self):
        assert average_cpl([10, 20, 30]) == 20.0

    def test_division_is_float(self):
        assert average_cpl([1, 2]) == 1.5


# ===================================================================
# acpl_by_phase
# ===================================================================

class TestAcplByPhase:
    def test_all_phases_present(self):
        result = acpl_by_phase([])
        assert set(result.keys()) == {Phase.OPENING, Phase.MIDDLEGAME, Phase.ENDGAME}

    def test_empty_phase_is_none(self):
        result = acpl_by_phase([PhasedMove(Phase.OPENING, 10)])
        assert result[Phase.OPENING] == 10.0
        assert result[Phase.MIDDLEGAME] is None
        assert result[Phase.ENDGAME] is None

    def test_separate_averages(self):
        moves = [
            PhasedMove(Phase.OPENING, 10),
            PhasedMove(Phase.OPENING, 30),
            PhasedMove(Phase.MIDDLEGAME, 100),
            PhasedMove(Phase.ENDGAME, 0),
            PhasedMove(Phase.ENDGAME, 50),
        ]
        result = acpl_by_phase(moves)
        assert result[Phase.OPENING] == 20.0
        assert result[Phase.MIDDLEGAME] == 100.0
        assert result[Phase.ENDGAME] == 25.0


# ===================================================================
# overall_acpl
# ===================================================================

class TestOverallAcpl:
    def test_empty_is_none(self):
        assert overall_acpl([]) is None

    def test_mixes_all_phases(self):
        moves = [
            PhasedMove(Phase.OPENING, 10),
            PhasedMove(Phase.ENDGAME, 30),
        ]
        assert overall_acpl(moves) == 20.0
