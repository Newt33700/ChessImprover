"""Tests unitaires — pipeline d'analyse (EPIC 1, US 1.2)."""

from __future__ import annotations

import io

import chess
import chess.pgn

from app.domain.analysis_pipeline import analyze_pgn, build_client_engine

PGN = '[Event "x"][Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0'


def _evals_for(pgn, played=50, best_delta=0, extra_line=None):
    """Construit un dict d'évals client {fen: [[uci, cp], ...]} pour chaque coup joué."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    evals = {}
    for move in game.mainline_moves():
        fen = board.fen()
        lines = [["0000", played + best_delta], [move.uci(), played]]
        if extra_line is not None:
            lines.append(["1111", played - extra_line])
        evals[fen] = lines
        board.push(move)
    return evals


class TestWithoutEngine:
    def test_records_have_phase_and_san(self):
        out = analyze_pgn(PGN)
        assert out["result"] == "1-0"
        assert len(out["moves"]) == 6
        first = out["moves"][0]
        assert first["move_san"] == "e4"
        assert first["color"] == "white"
        assert first["phase"] == "opening"
        assert first["cpl"] is None  # pas de moteur → pas d'éval

    def test_invalid_pgn(self):
        assert analyze_pgn("not a pgn")["moves"] == []

    def test_star_result_normalized(self):
        out = analyze_pgn('[Result "*"]\n\n1. e4 *')
        assert out["result"] is None


class TestWithEngine:
    def test_cpl_zero_when_best_played(self):
        engine = build_client_engine(_evals_for(PGN, played=40, best_delta=0))
        out = analyze_pgn(PGN, engine)
        assert all(m["cpl"] == 0 for m in out["moves"])
        assert out["moves"][0]["eval_before"] == 40
        assert out["moves"][0]["score_cp"] == 40

    def test_cpl_reflects_delta_capped(self):
        engine = build_client_engine(_evals_for(PGN, played=10, best_delta=500))
        out = analyze_pgn(PGN, engine)
        # best - played = 500 → plafonné à 400
        assert all(m["cpl"] == 400 for m in out["moves"])

    def test_tactical_position_detected(self):
        # écart best→2e = 200 > 150 → tactical
        engine = build_client_engine(_evals_for(PGN, played=10, best_delta=200))
        out = analyze_pgn(PGN, engine)
        assert out["moves"][0]["position_type"] == "tactical"

    def test_strategic_position_detected(self):
        # 3 lignes resserrées (<40) → strategic
        engine = build_client_engine(_evals_for(PGN, played=50, best_delta=10, extra_line=20))
        out = analyze_pgn(PGN, engine)
        assert out["moves"][0]["position_type"] == "strategic"


class TestBuildClientEngine:
    def test_parses_mate_fields(self):
        engine = build_client_engine({"FEN": [["e2e4", 100000, True, 3]]})
        pos = engine.analyse("FEN")
        assert pos.best.is_mate is True
        assert pos.best.mate_in == 3
