"""EPIC 11 (US 9.1/9.2) — détection de patterns d'erreur + score de fréquence."""

from app.domain.error_profile import (
    ERROR_TYPE_TO_TACTICAL_THEMES,
    ERROR_TYPES,
    RECURRING_THRESHOLD,
    detect_error_occurrences,
    is_recurring,
    update_frequency_score,
)

# PGN de référence repris de test_analyzer.py (TestExactCounters) : Nxe5 est
# une gaffe blanche vérifiée (blunders_count == 1, blunder_moves == ["f3e5"]).
# Sans horloge, ce n'est PAS une erreur de temps → hanging_piece pur.
HANGING_PIECE_PGN = "1. e4 d6 2. Nf3 e5 3. Nxe5 *"

# Même gaffe, mais avec une chute de 75 % du temps blanc sur le coup fautif
# (8:00 -> 2:00, seuil de panique = 50 %) : classée time_pressure, PAS
# hanging_piece (cf. `detect_error_occurrences` — chevauchement volontaire nul).
TIME_PRESSURE_PGN = (
    "1. e4 {[%clk 0:10:00]} d6 {[%clk 0:10:00]} "
    "2. Nf3 {[%clk 0:08:00]} e5 {[%clk 0:09:00]} "
    "3. Nxe5 {[%clk 0:02:00]} *"
)

CLEAN_PGN = """
[White "A"]
[Black "B"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
"""


def test_recurring_threshold_is_70():
    assert RECURRING_THRESHOLD == 70.0


class TestDetectErrorOccurrences:
    def test_clean_game_has_no_occurrences(self):
        occ = detect_error_occurrences(CLEAN_PGN, "white", moves=[])
        assert occ == {"hanging_piece": False, "time_pressure": False, "missed_mate": False}

    def test_missed_mate_cpl_of_one_still_counts(self):
        # `(m.get("cpl") or 0) > 0` : une perte d'1 centipion sur un mat
        # loupé compte déjà comme un oubli, pas seulement au-delà de 1.
        moves = [{"color": "white", "is_mate": True, "cpl": 1}]
        occ = detect_error_occurrences(CLEAN_PGN, "white", moves=moves)
        assert occ["missed_mate"] is True

    def test_missed_mate_detected_from_game_moves(self):
        moves = [
            {"color": "white", "is_mate": True, "cpl": 0},   # mat trouvé -> pas un oubli
            {"color": "white", "is_mate": True, "cpl": 120},  # mat manqué -> oubli
            {"color": "black", "is_mate": True, "cpl": 500},  # coup adverse, ignoré
        ]
        occ = detect_error_occurrences(CLEAN_PGN, "white", moves=moves)
        assert occ["missed_mate"] is True

    def test_missed_mate_false_when_all_mates_found(self):
        moves = [{"color": "white", "is_mate": True, "cpl": 0}]
        occ = detect_error_occurrences(CLEAN_PGN, "white", moves=moves)
        assert occ["missed_mate"] is False

    def test_missed_mate_ignores_opponent_moves(self):
        moves = [{"color": "black", "is_mate": True, "cpl": 300}]
        occ = detect_error_occurrences(CLEAN_PGN, "white", moves=moves)
        assert occ["missed_mate"] is False

    def test_result_keys_cover_all_error_types(self):
        occ = detect_error_occurrences(CLEAN_PGN, "white", moves=[])
        assert set(occ.keys()) == set(ERROR_TYPES)

    def test_hanging_piece_without_time_drop(self):
        occ = detect_error_occurrences(HANGING_PIECE_PGN, "white", moves=[])
        assert occ["hanging_piece"] is True
        assert occ["time_pressure"] is False

    def test_time_pressure_blunder_not_double_counted_as_hanging_piece(self):
        """Une gaffe sous forte chute de temps est classée time_pressure
        exclusivement — pas aussi hanging_piece (cf. docstring du module)."""
        occ = detect_error_occurrences(TIME_PRESSURE_PGN, "white", moves=[])
        assert occ["time_pressure"] is True
        assert occ["hanging_piece"] is False


class TestUpdateFrequencyScore:
    def test_occurred_pushes_score_up(self):
        new = update_frequency_score(0.0, occurred=True, alpha=0.3)
        assert new == 30.0

    def test_not_occurred_pushes_score_down(self):
        new = update_frequency_score(50.0, occurred=False, alpha=0.3)
        assert new == 35.0

    def test_score_bounded_0_100(self):
        assert update_frequency_score(95.0, occurred=True, alpha=0.5) <= 100.0
        assert update_frequency_score(5.0, occurred=False, alpha=0.5) >= 0.0

    def test_score_capped_exactly_at_100_not_101(self):
        # Mathématiquement, `new_score` ne peut dépasser 100 que si le score
        # d'entrée est déjà hors bornes (donnée corrompue) : c'est le seul
        # moyen d'exercer réellement le plafond `min(100.0, ...)`.
        assert update_frequency_score(200.0, occurred=True, alpha=0.1) == 100.0

    def test_score_rounds_to_one_decimal_not_two(self):
        new = update_frequency_score(10.0, occurred=False, alpha=1 / 3)
        assert new == round(10.0 + (1 / 3) * (0.0 - 10.0), 1)

    def test_repeated_occurrences_cross_recurring_threshold(self):
        score = 0.0
        for _ in range(4):
            score = update_frequency_score(score, occurred=True)
        assert score > RECURRING_THRESHOLD

    def test_repeated_clean_games_stay_under_threshold(self):
        score = 0.0
        for _ in range(4):
            score = update_frequency_score(score, occurred=False)
        assert score < RECURRING_THRESHOLD


class TestIsRecurring:
    def test_above_threshold_is_recurring(self):
        assert is_recurring(RECURRING_THRESHOLD + 0.1) is True

    def test_at_or_below_threshold_is_not_recurring(self):
        assert is_recurring(RECURRING_THRESHOLD) is False
        assert is_recurring(RECURRING_THRESHOLD - 10) is False


class TestErrorTypeToTacticalThemes:
    def test_every_error_type_maps_to_known_themes(self):
        from app.domain.tactics import TACTICAL_THEMES

        assert set(ERROR_TYPE_TO_TACTICAL_THEMES.keys()) == set(ERROR_TYPES)
        for themes in ERROR_TYPE_TO_TACTICAL_THEMES.values():
            assert all(t in TACTICAL_THEMES for t in themes)
