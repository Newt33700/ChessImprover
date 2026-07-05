"""Tests unitaires — Analyse de la Charge Cognitive (EPIC 19, US 19.1/19.2)."""

from __future__ import annotations

from app.domain.cognitive_load import (
    DECISION_FATIGUE_RATIO,
    PRESSURE_THRESHOLD_CP,
    TOP3_CPL_THRESHOLD,
    WEAK_MOVE_CPL_THRESHOLD,
    MoveQualityBucket,
    PressureLevel,
    build_decision_fluidity_report,
    build_time_allocation_report,
    classify_pressure,
    derive_time_spent,
    is_decision_fatigue,
    move_quality_bucket,
)


def _move(phase="opening", eval_before=None, cpl=None, time_spent=None):
    return {
        "phase": phase,
        "eval_before": eval_before,
        "cpl": cpl,
        "time_spent_seconds": time_spent,
    }


class TestConstantsAndEnumValues:
    """Comparer une constante à elle-même ne détecte jamais une régression :
    valeurs littérales attendues en dur (règle métier, cf. README §5)."""

    def test_pressure_threshold_cp_is_minus_150(self):
        assert PRESSURE_THRESHOLD_CP == -150

    def test_top3_cpl_threshold_is_50(self):
        assert TOP3_CPL_THRESHOLD == 50

    def test_weak_move_cpl_threshold_is_100(self):
        assert WEAK_MOVE_CPL_THRESHOLD == 100

    def test_decision_fatigue_ratio_is_1_3(self):
        assert DECISION_FATIGUE_RATIO == 1.3

    def test_move_quality_bucket_values(self):
        assert MoveQualityBucket.TOP3.value == "top3"
        assert MoveQualityBucket.WEAK.value == "weak"


# ---------------------------------------------------------------------------
# derive_time_spent
# ---------------------------------------------------------------------------

class TestDeriveTimeSpent:
    def test_first_move_of_each_color_has_no_baseline(self):
        clocks = [600.0, 600.0]
        colors = ["white", "black"]
        assert derive_time_spent(clocks, colors) == [None, None]

    def test_simple_diff_without_increment(self):
        # blanc: 600 -> 580 (20s), noir: 600 -> 590 (10s)
        clocks = [600.0, 600.0, 580.0, 590.0]
        colors = ["white", "black", "white", "black"]
        result = derive_time_spent(clocks, colors)
        assert result == [None, None, 20.0, 10.0]

    def test_increment_is_subtracted_back_out(self):
        # blanc: 100 -> 105 (horloge remonte grâce à l'incrément de 10s) :
        # temps réel = 100 - 105 + 10 = 5s, pas une valeur négative.
        clocks = [100.0, 100.0, 105.0, 95.0]
        colors = ["white", "black", "white", "black"]
        result = derive_time_spent(clocks, colors, increment=10)
        assert result[2] == 5.0

    def test_negative_result_clamped_to_zero(self):
        # horloge blanche qui "remonte" au-delà de ce qu'explique l'incrément
        # (donnée aberrante) -> ne doit jamais renvoyer un temps négatif.
        clocks = [100.0, 100.0, 200.0]
        colors = ["white", "black", "white"]
        result = derive_time_spent(clocks, colors, increment=0)
        assert result[2] == 0.0

    def test_missing_clock_yields_none(self):
        clocks = [None, 600.0, 580.0]
        colors = ["white", "black", "white"]
        result = derive_time_spent(clocks, colors)
        assert result == [None, None, None]  # pas d'horloge de référence blanche

    def test_missing_intermediate_clock_breaks_the_chain(self):
        clocks = [600.0, 600.0, None, 590.0, 560.0]
        colors = ["white", "black", "white", "black", "white"]
        result = derive_time_spent(clocks, colors)
        # 3e coup (index 2, blanc) : horloge manquante -> None, ET n'écrase pas
        # la dernière horloge blanche connue (reste 600.0).
        assert result[2] is None
        # 5e coup (index 4, blanc) : référence = 600.0 (dernière connue) -> 40s
        assert result[4] == 40.0

    def test_empty_input(self):
        assert derive_time_spent([], []) == []


# ---------------------------------------------------------------------------
# US 19.1 — pression & répartition par phase
# ---------------------------------------------------------------------------

class TestClassifyPressure:
    def test_none_is_unknown(self):
        assert classify_pressure(None) is None

    def test_at_threshold_is_under_pressure(self):
        assert classify_pressure(PRESSURE_THRESHOLD_CP) is PressureLevel.UNDER_PRESSURE

    def test_just_above_threshold_is_equality(self):
        assert classify_pressure(PRESSURE_THRESHOLD_CP + 1) is PressureLevel.EQUALITY

    def test_large_advantage_is_equality_bucket(self):
        # Le camp gagnant n'est jamais "sous pression" par construction.
        assert classify_pressure(500) is PressureLevel.EQUALITY

    def test_large_disadvantage_is_under_pressure(self):
        assert classify_pressure(-900) is PressureLevel.UNDER_PRESSURE


class TestBuildTimeAllocationReport:
    def test_empty_moves_yields_zeroed_report(self):
        report = build_time_allocation_report([])
        assert report["sample_size"] == 0
        for phase_stats in report["by_phase"].values():
            assert phase_stats["avg_seconds"] is None
            assert phase_stats["total_seconds"] == 0.0
            assert phase_stats["count"] == 0
            assert phase_stats["share_pct"] == 0.0

    def test_avg_and_total_seconds_round_to_one_decimal(self):
        moves = [
            _move(phase="opening", time_spent=1.0),
            _move(phase="opening", time_spent=1.0),
            _move(phase="opening", time_spent=2.0),
        ]
        report = build_time_allocation_report(moves)
        assert report["by_phase"]["opening"]["avg_seconds"] == round(4 / 3, 1)

    def test_total_seconds_rounds_to_one_decimal_not_two(self):
        moves = [_move(phase="opening", time_spent=1.0), _move(phase="opening", time_spent=1.11)]
        report = build_time_allocation_report(moves)
        assert report["by_phase"]["opening"]["total_seconds"] == round(2.11, 1)

    def test_share_pct_rounds_to_one_decimal(self):
        moves = [
            _move(phase="opening", time_spent=1.0),
            _move(phase="middlegame", time_spent=1.0),
            _move(phase="endgame", time_spent=1.0),
        ]
        report = build_time_allocation_report(moves)
        assert report["by_phase"]["opening"]["share_pct"] == round(100 / 3, 1)

    def test_share_pct_computed_even_below_one_second_total(self):
        # `total_seconds > 0` (pas `> 1`) : un total inférieur à 1s doit quand
        # même produire un share_pct calculé, pas le repli à 0.0.
        moves = [_move(phase="opening", time_spent=0.5)]
        report = build_time_allocation_report(moves)
        assert report["by_phase"]["opening"]["share_pct"] == 100.0

    def test_all_three_phases_always_present(self):
        report = build_time_allocation_report([])
        assert set(report["by_phase"].keys()) == {"opening", "middlegame", "endgame"}
        assert set(report["by_pressure"].keys()) == {"under_pressure", "equality"}

    def test_ignores_moves_without_known_time(self):
        moves = [_move(phase="opening", time_spent=None)]
        report = build_time_allocation_report(moves)
        assert report["sample_size"] == 0

    def test_opening_time_dominance_detected(self):
        """Cas d'usage central de la valeur métier : le joueur passe l'essentiel
        de son temps en ouverture faute de préparation -> share_pct élevé."""
        moves = [
            _move(phase="opening", time_spent=40.0),
            _move(phase="opening", time_spent=40.0),
            _move(phase="middlegame", time_spent=10.0),
            _move(phase="endgame", time_spent=10.0),
        ]
        report = build_time_allocation_report(moves)
        assert report["by_phase"]["opening"]["share_pct"] == 80.0
        assert report["by_phase"]["opening"]["avg_seconds"] == 40.0
        assert report["by_phase"]["opening"]["count"] == 2

    def test_pressure_bucketing(self):
        moves = [
            _move(eval_before=-300, time_spent=90.0),  # sous pression
            _move(eval_before=50, time_spent=10.0),    # équilibre
            _move(eval_before=None, time_spent=999.0),  # pression inconnue -> exclu du bucket
        ]
        report = build_time_allocation_report(moves)
        assert report["by_pressure"]["under_pressure"]["avg_seconds"] == 90.0
        assert report["by_pressure"]["equality"]["avg_seconds"] == 10.0
        # le coup sans éval compte quand même dans l'échantillon global/phase
        assert report["sample_size"] == 3


# ---------------------------------------------------------------------------
# US 19.2 — fluidité de décision
# ---------------------------------------------------------------------------

class TestMoveQualityBucket:
    def test_none_cpl_is_unclassified(self):
        assert move_quality_bucket(None) is None

    def test_zero_cpl_is_top3(self):
        assert move_quality_bucket(0) is MoveQualityBucket.TOP3

    def test_at_top3_threshold_is_top3(self):
        assert move_quality_bucket(TOP3_CPL_THRESHOLD) is MoveQualityBucket.TOP3

    def test_just_above_top3_threshold_is_unclassified(self):
        assert move_quality_bucket(TOP3_CPL_THRESHOLD + 1) is None

    def test_just_below_weak_threshold_is_unclassified(self):
        assert move_quality_bucket(WEAK_MOVE_CPL_THRESHOLD - 1) is None

    def test_at_weak_threshold_is_weak(self):
        assert move_quality_bucket(WEAK_MOVE_CPL_THRESHOLD) is MoveQualityBucket.WEAK

    def test_large_cpl_is_weak(self):
        assert move_quality_bucket(400) is MoveQualityBucket.WEAK


class TestIsDecisionFatigue:
    def test_missing_values_never_flag(self):
        assert is_decision_fatigue(None, 200.0) is False
        assert is_decision_fatigue(10.0, None) is False
        assert is_decision_fatigue(None, None) is False

    def test_zero_top3_reference_never_flags(self):
        assert is_decision_fatigue(0.0, 100.0) is False

    def test_below_ratio_is_not_fatigue(self):
        assert is_decision_fatigue(10.0, 10.0 * DECISION_FATIGUE_RATIO) is False

    def test_above_ratio_is_fatigue(self):
        assert is_decision_fatigue(10.0, 10.0 * DECISION_FATIGUE_RATIO + 0.1) is True

    def test_spec_example_three_minutes_on_a_losing_move(self):
        # Coups Top 3 joués vite (5s), mais 3 minutes sur un coup perdant.
        assert is_decision_fatigue(5.0, 180.0) is True

    def test_reference_of_one_second_still_evaluates_ratio(self):
        # `top3_avg_seconds <= 0` : seule une référence nulle/négative doit
        # court-circuiter le calcul, pas une référence de 1s exactement.
        assert is_decision_fatigue(1.0, 1000.0) is True


class TestBuildDecisionFluidityReport:
    def test_empty_moves(self):
        report = build_decision_fluidity_report([])
        assert report["top3"]["avg_seconds"] is None
        assert report["weak"]["avg_seconds"] is None
        assert report["decision_fatigue"] is False

    def test_fluid_player_not_flagged(self):
        moves = [
            _move(cpl=0, time_spent=3.0),
            _move(cpl=10, time_spent=4.0),
            _move(cpl=300, time_spent=4.2),
        ]
        report = build_decision_fluidity_report(moves)
        assert report["decision_fatigue"] is False
        assert report["top3"]["avg_seconds"] == 3.5
        assert report["weak"]["avg_seconds"] == 4.2

    def test_decision_fatigue_flagged(self):
        moves = [
            _move(cpl=0, time_spent=5.0),
            _move(cpl=350, time_spent=180.0),
        ]
        report = build_decision_fluidity_report(moves)
        assert report["decision_fatigue"] is True
        assert report["weak"]["count"] == 1

    def test_ignores_midzone_moves(self):
        moves = [_move(cpl=75, time_spent=999.0)]  # zone intermédiaire non classée
        report = build_decision_fluidity_report(moves)
        assert report["top3"]["count"] == 0
        assert report["weak"]["count"] == 0
