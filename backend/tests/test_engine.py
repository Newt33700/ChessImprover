"""Tests unitaires — abstraction du moteur (EPIC 2, infrastructure)."""

from __future__ import annotations

import pytest

from app.infrastructure.engine import (
    ENGINE_DEPTH,
    MATE_SCORE,
    ClientProvidedEngine,
    EngineProvider,
    MoveScore,
    NativeStockfishEngine,
    PositionEval,
)


# ===================================================================
# Constantes
# ===================================================================

def test_engine_depth_is_14():
    assert ENGINE_DEPTH == 14


def test_mate_score_positive():
    assert MATE_SCORE > 0


# ===================================================================
# PositionEval
# ===================================================================

class TestPositionEval:
    def test_best_returns_first_line(self):
        pos = PositionEval("fen", [MoveScore("e2e4", 30), MoveScore("d2d4", 20)])
        assert pos.best.move_uci == "e2e4"

    def test_best_empty_is_none(self):
        assert PositionEval("fen", []).best is None

    def test_score_of_known_move(self):
        pos = PositionEval("fen", [MoveScore("e2e4", 30), MoveScore("d2d4", 20)])
        assert pos.score_of("d2d4") == 20

    def test_score_of_unknown_move(self):
        pos = PositionEval("fen", [MoveScore("e2e4", 30)])
        assert pos.score_of("a2a3") is None


# ===================================================================
# ClientProvidedEngine
# ===================================================================

class TestClientProvidedEngine:
    def _pos(self):
        return PositionEval("FEN1", [MoveScore("e2e4", 30), MoveScore("d2d4", 20), MoveScore("c2c4", 10)])

    def test_default_depth(self):
        assert ClientProvidedEngine().depth == ENGINE_DEPTH

    def test_satisfies_protocol(self):
        assert isinstance(ClientProvidedEngine(), EngineProvider)

    def test_analyse_returns_stored(self):
        engine = ClientProvidedEngine({"FEN1": self._pos()})
        assert engine.analyse("FEN1").best.move_uci == "e2e4"

    def test_analyse_missing_raises_keyerror(self):
        with pytest.raises(KeyError):
            ClientProvidedEngine().analyse("UNKNOWN")

    def test_add_then_analyse(self):
        engine = ClientProvidedEngine()
        engine.add(self._pos())
        assert engine.analyse("FEN1").fen == "FEN1"

    def test_multipv_truncates(self):
        engine = ClientProvidedEngine({"FEN1": self._pos()})
        result = engine.analyse("FEN1", multipv=2)
        assert len(result.lines) == 2

    def test_multipv_larger_than_available(self):
        engine = ClientProvidedEngine({"FEN1": self._pos()})
        result = engine.analyse("FEN1", multipv=10)
        assert len(result.lines) == 3


# ===================================================================
# NativeStockfishEngine (sans binaire)
# ===================================================================

class TestNativeStockfishEngine:
    def test_stores_config(self):
        engine = NativeStockfishEngine("/usr/bin/stockfish", depth=20)
        assert engine.binary_path == "/usr/bin/stockfish"
        assert engine.depth == 20

    def test_default_depth(self):
        assert NativeStockfishEngine(None).depth == ENGINE_DEPTH
