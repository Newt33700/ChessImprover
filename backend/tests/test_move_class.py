"""Tests unitaires — tactique vs stratégie (US 3.2)."""

from __future__ import annotations

from app.domain.models import TimeClass
from app.domain.move_class import (
    STRATEGIC_SPREAD,
    TACTICAL_GAP,
    TACTICAL_MISS_THRESHOLD,
    PositionType,
    TacticOutcome,
    classify_position,
    strategic_elo,
    tactic_outcome,
    tactical_elo,
    tactical_success_ratio,
)


# ===================================================================
# Constantes
# ===================================================================

class TestConstants:
    def test_thresholds(self):
        assert TACTICAL_GAP == 150
        assert TACTICAL_MISS_THRESHOLD == 100
        assert STRATEGIC_SPREAD == 40


# ===================================================================
# Valeurs .value des enums (persistées telles quelles dans game_moves,
# comparées comme chaînes brutes ailleurs — ex. stats_aggregator.py — donc
# leur valeur exacte est une règle métier, pas un détail d'implémentation).
# ===================================================================

class TestEnumValues:
    def test_position_type_values(self):
        assert PositionType.TACTICAL.value == "tactical"
        assert PositionType.STRATEGIC.value == "strategic"
        assert PositionType.NEUTRAL.value == "neutral"

    def test_tactic_outcome_values(self):
        assert TacticOutcome.SUCCESS.value == "success"
        assert TacticOutcome.MISSED.value == "missed"
        assert TacticOutcome.PARTIAL.value == "partial"


# ===================================================================
# classify_position
# ===================================================================

class TestClassifyPosition:
    def test_tactical_clear(self):
        assert classify_position([300, 100, 90]) == PositionType.TACTICAL

    def test_tactical_just_above_gap(self):
        # 300 − 149 = 151 > 150
        assert classify_position([300, 149, 0]) == PositionType.TACTICAL

    def test_not_tactical_at_exact_gap(self):
        # 300 − 150 = 150, pas > 150 ; top3 non resserré → NEUTRAL
        assert classify_position([300, 150, 150]) == PositionType.NEUTRAL

    def test_strategic_clear(self):
        # écart best→3e = 30 < 40, et pas tactique
        assert classify_position([50, 40, 20]) == PositionType.STRATEGIC

    def test_strategic_just_below_spread(self):
        # 50 − 11 = 39 < 40
        assert classify_position([50, 30, 11]) == PositionType.STRATEGIC

    def test_not_strategic_at_exact_spread(self):
        # 50 − 10 = 40, pas < 40
        assert classify_position([50, 30, 10]) == PositionType.NEUTRAL

    def test_tactical_takes_precedence(self):
        # Gros écart 2e coup → tactique, même si autre structure
        assert classify_position([400, 100, 95]) == PositionType.TACTICAL

    def test_two_lines_cannot_be_strategic(self):
        assert classify_position([50, 40]) == PositionType.NEUTRAL

    def test_two_lines_can_be_tactical(self):
        # `len(line_scores) >= 2` : deux lignes suffisent pour la détection
        # tactique (contrairement au cas stratégique qui en exige 3).
        assert classify_position([300, 100]) == PositionType.TACTICAL

    def test_single_line_neutral(self):
        assert classify_position([100]) == PositionType.NEUTRAL

    def test_empty_neutral(self):
        assert classify_position([]) == PositionType.NEUTRAL


# ===================================================================
# tactic_outcome
# ===================================================================

class TestTacticOutcome:
    def test_best_move_success(self):
        assert tactic_outcome(0) == TacticOutcome.SUCCESS

    def test_negative_cpl_success(self):
        assert tactic_outcome(-5) == TacticOutcome.SUCCESS

    def test_missed_above_threshold(self):
        assert tactic_outcome(101) == TacticOutcome.MISSED

    def test_partial_at_threshold(self):
        # 100 n'est pas > 100 → partiel
        assert tactic_outcome(100) == TacticOutcome.PARTIAL

    def test_partial_between(self):
        assert tactic_outcome(50) == TacticOutcome.PARTIAL

    def test_cpl_one_is_partial_not_success(self):
        # `played_cpl <= 0` : seul un coup parfait (0 ou négatif) est un
        # succès ; une perte d'1 centipion est déjà un partiel.
        assert tactic_outcome(1) == TacticOutcome.PARTIAL


# ===================================================================
# tactical_success_ratio
# ===================================================================

class TestSuccessRatio:
    def test_empty_is_none(self):
        assert tactical_success_ratio([]) is None

    def test_half(self):
        ratio = tactical_success_ratio([TacticOutcome.SUCCESS, TacticOutcome.MISSED])
        assert ratio == 0.5

    def test_all_success(self):
        assert tactical_success_ratio([TacticOutcome.SUCCESS] * 3) == 1.0

    def test_all_missed(self):
        assert tactical_success_ratio([TacticOutcome.MISSED] * 2) == 0.0

    def test_partial_counts_in_denominator(self):
        ratio = tactical_success_ratio([TacticOutcome.SUCCESS, TacticOutcome.PARTIAL])
        assert ratio == 0.5


# ===================================================================
# tactical_elo
# ===================================================================

class TestTacticalElo:
    def test_none_ratio_is_none(self):
        assert tactical_elo(None) is None

    def test_zero_ratio_floor(self):
        assert tactical_elo(0.0) == 600

    def test_full_ratio_ceil(self):
        assert tactical_elo(1.0) == 3000

    def test_half_ratio(self):
        # 600 + 0.5 × (3000 − 600) = 1800
        assert tactical_elo(0.5) == 1800

    def test_ratio_clamped(self):
        assert tactical_elo(1.5) == 3000
        assert tactical_elo(-0.5) == 600


# ===================================================================
# strategic_elo
# ===================================================================

class TestStrategicElo:
    def test_empty_is_none(self):
        assert strategic_elo([]) is None

    def test_uses_acpl_mapping(self):
        # ACPL moyen 10 → 2800 (sans cadence)
        assert strategic_elo([10, 10]) == 2800

    def test_with_cadence_bonus(self):
        # ACPL 10 → 2800, +200 Bullet → 3000 (plafond)
        assert strategic_elo([10], TimeClass.BULLET) == 3000

    def test_mid_acpl(self):
        assert strategic_elo([50]) == 1500
