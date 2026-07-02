"""Tests unitaires — Le Cimetière des Erreurs (EPIC 20, US 20.1)."""

from __future__ import annotations

from app.domain.srs_flashcards import (
    BLUNDER_CPL_THRESHOLD,
    DEFAULT_EASE_FACTOR,
    DEFAULT_INTERVAL_DAYS,
    extract_blunder_flashcards,
)


def _move(cpl=None, fen="fen1", best_move_san="Qxe5", move_san="Nc3"):
    return {"cpl": cpl, "fen": fen, "best_move_san": best_move_san, "move_san": move_san}


class TestConstants:
    def test_defaults_match_sm2_convention(self):
        # Même point de départ que domain.srs_engine.create_card /
        # domain.opening_repertoire — une seule convention SM-2 dans le produit.
        assert DEFAULT_EASE_FACTOR == 2.5
        assert DEFAULT_INTERVAL_DAYS == 1


class TestExtractBlunderFlashcards:
    def test_empty_moves(self):
        assert extract_blunder_flashcards([]) == []

    def test_below_threshold_ignored(self):
        moves = [_move(cpl=BLUNDER_CPL_THRESHOLD - 1)]
        assert extract_blunder_flashcards(moves) == []

    def test_at_threshold_included(self):
        moves = [_move(cpl=BLUNDER_CPL_THRESHOLD)]
        cards = extract_blunder_flashcards(moves)
        assert cards == [{"fen": "fen1", "solution": "Qxe5"}]

    def test_none_cpl_ignored(self):
        moves = [_move(cpl=None)]
        assert extract_blunder_flashcards(moves) == []

    def test_missing_fen_ignored(self):
        moves = [_move(cpl=300, fen=None)]
        assert extract_blunder_flashcards(moves) == []

    def test_missing_best_move_ignored(self):
        moves = [_move(cpl=300, best_move_san=None)]
        assert extract_blunder_flashcards(moves) == []

    def test_best_move_equal_to_played_ignored(self):
        # Garde-fou défensif : ne devrait jamais arriver en pratique (une
        # perte >= seuil implique un coup joué différent du meilleur), mais
        # on ne veut jamais générer une flashcard dont la solution == l'énoncé.
        moves = [_move(cpl=300, best_move_san="Nc3", move_san="Nc3")]
        assert extract_blunder_flashcards(moves) == []

    def test_multiple_blunders_yield_multiple_cards(self):
        moves = [
            _move(cpl=200, fen="fenA", best_move_san="Qxe5"),
            _move(cpl=50, fen="fenB", best_move_san="Rxd5"),  # sous le seuil
            _move(cpl=400, fen="fenC", best_move_san="Bxf7+"),
        ]
        cards = extract_blunder_flashcards(moves)
        assert cards == [
            {"fen": "fenA", "solution": "Qxe5"},
            {"fen": "fenC", "solution": "Bxf7+"},
        ]
