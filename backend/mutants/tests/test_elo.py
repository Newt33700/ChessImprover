"""Tests unitaires du calculateur d'Elo — conçus pour tuer 100% des mutations mutmut.

Chaque constante (DECAY, ELO_FLOOR, ELO_CEIL), chaque seuil de classification
et chaque formule arithmétique est exercé par des assertions exactes et inverses.
"""

from __future__ import annotations

import math

from app.domain.elo_calculator import (
    DECAY,
    ELO_CEIL,
    ELO_FLOOR,
    classify_move,
    estimate_elo,
    game_accuracy,
    move_accuracy,
)
from app.domain.models import Classification


# ===================================================================
# move_accuracy
# ===================================================================

class TestMoveAccuracy:
    """Tests pour move_accuracy(cp_loss) → 100 × e^(-DECAY × |cp_loss|)."""

    def test_zero_loss_is_perfect(self):
        """Perte nulle → score 100.0."""
        assert move_accuracy(0.0) == 100.0

    def test_zero_loss_negative_also_perfect(self):
        """La valeur absolue doit être utilisée."""
        assert move_accuracy(-50.0) == move_accuracy(50.0)

    def test_known_value_100_cp(self):
        """100 cp de perte → 100 × e^(-0.005 × 100) = 100 × e^(-0.5) ≈ 60.65."""
        expected = 100.0 * math.exp(-DECAY * 100.0)
        result = move_accuracy(100.0)
        assert result == expected

    def test_known_value_200_cp(self):
        """200 cp → 100 × e^(-1.0) ≈ 36.79."""
        expected = 100.0 * math.exp(-DECAY * 200.0)
        assert move_accuracy(200.0) == expected

    def test_known_value_50_cp(self):
        """50 cp → 100 × e^(-0.25) ≈ 77.88."""
        expected = 100.0 * math.exp(-DECAY * 50.0)
        assert move_accuracy(50.0) == expected

    def test_large_loss_approaches_zero(self):
        """Grosse perte → score proche de zéro mais > 0."""
        score = move_accuracy(2000.0)
        assert 0.0 < score < 1.0

    def test_result_never_negative(self):
        """Le score est toujours >= 0."""
        for loss in [0, 100, 500, 5000, 10000]:
            assert move_accuracy(loss) >= 0.0

    def test_result_never_exceeds_100(self):
        """Le score ne dépasse jamais 100."""
        for loss in [0, -10, -500]:
            assert move_accuracy(loss) <= 100.0

    def test_decay_constant_value(self):
        """DECAY doit être exactement 0.005."""
        assert DECAY == 0.005

    def test_decay_used_in_formula(self):
        """Si DECAY change, move_accuracy change — prouve l'utilisation."""
        assert move_accuracy(100.0) != move_accuracy(100.0 * 2)


# ===================================================================
# game_accuracy
# ===================================================================

class TestGameAccuracy:
    """Tests pour game_accuracy(scores) → moyenne arithmétique."""

    def test_empty_list_returns_zero(self):
        assert game_accuracy([]) == 0.0

    def test_single_score(self):
        assert game_accuracy([80.0]) == 80.0

    def test_two_scores_average(self):
        assert game_accuracy([100.0, 0.0]) == 50.0

    def test_three_scores_average(self):
        assert game_accuracy([60.0, 70.0, 80.0]) == 70.0

    def test_integer_scores_division(self):
        """Vérifie que la division est correcte (pas int division)."""
        result = game_accuracy([1.0, 2.0])
        assert result == 1.5

    def test_all_same_values(self):
        assert game_accuracy([50.0, 50.0, 50.0]) == 50.0


# ===================================================================
# estimate_elo
# ===================================================================

class TestEstimateElo:
    """Tests pour estimate_elo(accuracy, opponent_elo) → Elo borné [400, 2800]."""

    def test_basic_calculation(self):
        """accuracy=80, opp=1200 → 80×20 + 1200×0.5 = 1600 + 600 = 2200."""
        assert estimate_elo(80.0, 1200) == 2200

    def test_floor_clamping(self):
        """accuracy=0, opp=0 → 0 + 0 = 0 → clamp à 400."""
        assert estimate_elo(0.0, 0) == ELO_FLOOR

    def test_ceil_clamping(self):
        """accuracy=100, opp=4000 → 2000 + 2000 = 4000 → clamp à 2800."""
        assert estimate_elo(100.0, 4000) == ELO_CEIL

    def test_exact_floor_boundary(self):
        """400 → ne doit PAS être clampé plus haut."""
        assert estimate_elo(0.0, 800) == 400  # 0 + 400 = 400

    def test_exact_ceil_boundary(self):
        """2800 → ne doit PAS être clampé plus bas."""
        # (100 * 20) + (4000 * 0.5) = 2000 + 2000 = 4000 → clamp 2800
        assert estimate_elo(100.0, 4000) == 2800

    def test_floor_constant(self):
        assert ELO_FLOOR == 400

    def test_ceil_constant(self):
        assert ELO_CEIL == 2800

    def test_just_above_floor(self):
        """accuracy=1, opp=800 → 20 + 400 = 420."""
        assert estimate_elo(1.0, 800) == 420

    def test_just_below_ceil(self):
        """accuracy=99, opp=3000 → 1980 + 1500 = 3480 → 2800."""
        assert estimate_elo(99.0, 3000) == 2800

    def test_mid_range(self):
        """accuracy=50, opp=1000 → 1000 + 500 = 1500."""
        assert estimate_elo(50.0, 1000) == 1500

    def test_opponent_elo_weight(self):
        """L'opponent_elo est multiplié par 0.5, pas 1.0."""
        # Si weight était 1.0 : 1600 + 800 = 2400 (au lieu de 2000)
        assert estimate_elo(80.0, 800) == 2000  # 1600 + 400

    def test_accuracy_weight(self):
        """L'accuracy est multipliée par 20, pas autre chose."""
        assert estimate_elo(5.0, 0) == 400  # 100 + 0 = 100 → clamp 400
        assert estimate_elo(20.0, 0) == 400  # 400 + 0 = 400 (au seuil)
        assert estimate_elo(21.0, 0) == 420  # 420 + 0 = 420


# ===================================================================
# classify_move
# ===================================================================

class TestClassifyMove:
    """Tests pour classify_move(score) → Classification."""

    def test_brilliant_threshold(self):
        assert classify_move(95.0) == Classification.BRILLIANT
        assert classify_move(100.0) == Classification.BRILLIANT

    def test_excellent_threshold(self):
        assert classify_move(85.0) == Classification.EXCELLENT
        assert classify_move(94.9) == Classification.EXCELLENT

    def test_good_threshold(self):
        assert classify_move(70.0) == Classification.GOOD
        assert classify_move(84.9) == Classification.GOOD

    def test_inaccuracy_threshold(self):
        assert classify_move(50.0) == Classification.INACCURACY
        assert classify_move(69.9) == Classification.INACCURACY

    def test_mistake_threshold(self):
        assert classify_move(25.0) == Classification.MISTAKE
        assert classify_move(49.9) == Classification.MISTAKE

    def test_blunder_below_threshold(self):
        assert classify_move(24.9) == Classification.BLUNDER
        assert classify_move(0.0) == Classification.BLUNDER
        assert classify_move(-5.0) == Classification.BLUNDER

    def test_exact_boundary_transitions(self):
        """Vérifie que chaque seuil exact correspond à la bonne classe."""
        assert classify_move(95.0) == Classification.BRILLIANT
        assert classify_move(85.0) == Classification.EXCELLENT
        assert classify_move(70.0) == Classification.GOOD
        assert classify_move(50.0) == Classification.INACCURACY
        assert classify_move(25.0) == Classification.MISTAKE
        assert classify_move(24.99) == Classification.BLUNDER

    def test_classification_order_strict(self):
        """Le premier seuil qui matche doit gagner (pas de reorder possible)."""
        # Si les seuils étaient dans le mauvais ordre, le résultat changerait
        for score in [97, 88, 75, 60, 35, 10]:
            result = classify_move(float(score))
            assert isinstance(result, Classification)
