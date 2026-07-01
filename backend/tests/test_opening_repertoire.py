"""Tests unitaires — validation + SRS du répertoire d'ouvertures (EPIC 9, US 9.1/9.2)."""

from __future__ import annotations

from app.domain.opening_repertoire import infer_quality, validate_move_sequence


class TestValidateMoveSequence:
    def test_valid_ruy_lopez_line_is_accepted(self):
        assert validate_move_sequence(["e4", "e5", "Nf3", "Nc6", "Bb5"]) is True

    def test_empty_sequence_is_rejected(self):
        assert validate_move_sequence([]) is False

    def test_illegal_move_in_the_middle_is_rejected(self):
        assert validate_move_sequence(["e4", "e5", "Bxh7"]) is False

    def test_garbage_input_is_rejected_not_raised(self):
        assert validate_move_sequence(["e4", "not a move"]) is False

    def test_single_legal_move_is_accepted(self):
        assert validate_move_sequence(["d4"]) is True


class TestInferQuality:
    def test_no_mistakes_is_perfect_recall(self):
        assert infer_quality(0) == 5

    def test_one_mistake_is_middling_recall(self):
        assert infer_quality(1) == 3

    def test_two_or_more_mistakes_is_failed_recall(self):
        assert infer_quality(2) == 1
        assert infer_quality(5) == 1
