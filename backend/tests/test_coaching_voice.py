"""EPIC 14 (US 14.1/14.2) — Coach Vocal : alertes contextuelles par coup."""

from __future__ import annotations

import chess

from app.domain.coaching_voice import attach_move_alert, build_move_alert

# Dame blanche en d4, attaquée par la tour noire en d8 (colonne libre) et non
# défendue par aucune pièce blanche : gaffe de pièce non protégée classique.
HANGING_QUEEN_FEN = "3rk3/8/8/8/3Q4/8/8/4K3 w - - 0 1"

# Position "calme" (Ruy Lopez) : aucune pièce en prise après Bb5.
QUIET_BOARD = chess.Board()
for _san in ("e4", "e5", "Nf3", "Nc6", "Bb5"):
    QUIET_BOARD.push_san(_san)


class TestBuildMoveAlert:
    def test_no_alert_without_cpl(self):
        board = chess.Board(HANGING_QUEEN_FEN)
        assert build_move_alert(board, chess.WHITE, None, "Qd4") is None

    def test_no_alert_for_good_move(self):
        # cpl=10 -> score ~95.1 -> classification "brilliant", pas d'alerte.
        assert build_move_alert(QUIET_BOARD, chess.WHITE, 10, "Bb5") is None

    def test_mistake_without_hanging_piece_uses_generic_message(self):
        # cpl=150 -> score ~47.2 -> classification "mistake".
        alert = build_move_alert(QUIET_BOARD, chess.WHITE, 150, "Bb5")
        assert alert is not None
        assert alert["severity"] == "mistake"
        assert "Bb5" in alert["alert_text"]
        assert alert["tts_text"]

    def test_blunder_with_hanging_queen_names_the_piece_and_square(self):
        board = chess.Board(HANGING_QUEEN_FEN)
        # cpl=400 -> score ~13.5 -> classification "blunder".
        alert = build_move_alert(board, chess.WHITE, 400, "Qd4")
        assert alert is not None
        assert alert["severity"] == "blunder"
        assert "dame" in alert["alert_text"].lower()
        assert "d4" in alert["alert_text"]
        assert "dame" in alert["tts_text"].lower()

    def test_blunder_without_hanging_piece_uses_generic_message(self):
        alert = build_move_alert(QUIET_BOARD, chess.WHITE, 400, "Bb5")
        assert alert is not None
        assert alert["severity"] == "blunder"
        assert "gaffe" in alert["alert_text"].lower()

    def test_hanging_piece_of_opponent_color_is_ignored(self):
        # La pièce en prise est blanche ; si mover_color est noir, l'alerte
        # de gaffe reste générique (on n'attribue pas la pièce ADVERSE au joueur).
        board = chess.Board(HANGING_QUEEN_FEN)
        alert = build_move_alert(board, chess.BLACK, 400, "Rd4")
        assert alert is not None
        assert "dame" not in alert["alert_text"].lower()


class TestAttachMoveAlert:
    def test_adds_no_keys_when_no_alert(self):
        record = {"cpl": 10, "move_san": "Bb5"}
        attach_move_alert(record, QUIET_BOARD, chess.WHITE)
        assert "alert_severity" not in record
        assert "alert_text" not in record
        assert "tts_text" not in record

    def test_adds_keys_when_alert_triggered(self):
        board = chess.Board(HANGING_QUEEN_FEN)
        record = {"cpl": 400, "move_san": "Qd4"}
        attach_move_alert(record, board, chess.WHITE)
        assert record["alert_severity"] == "blunder"
        assert "d4" in record["alert_text"]
        assert record["tts_text"]
