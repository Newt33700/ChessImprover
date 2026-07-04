"""Tests unitaires — pipeline d'analyse (EPIC 1, US 1.2)."""

from __future__ import annotations

import io

import chess
import chess.pgn

from app.domain.analysis_pipeline import (
    _extract_opening,
    analyze_pgn,
    build_client_engine,
    compute_pgn_hash,
)

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


class TestComputePgnHash:
    def test_deterministic_for_same_pgn(self):
        assert compute_pgn_hash(PGN) == compute_pgn_hash(PGN)

    def test_different_for_different_pgn(self):
        assert compute_pgn_hash(PGN) != compute_pgn_hash(PGN + " ")

    def test_is_sha256_hex_digest(self):
        h = compute_pgn_hash(PGN)
        assert len(h) == 64
        int(h, 16)  # lève ValueError si ce n'est pas de l'hexadécimal


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

    def test_invalid_pgn_has_no_eco(self):
        out = analyze_pgn("not a pgn")
        assert out["eco"] is None
        assert out["opening_name"] is None


class TestExtractOpening:
    def test_eco_and_opening_headers(self):
        eco, name = _extract_opening({"ECO": "C50", "Opening": "Italian Game"})
        assert eco == "C50"
        assert name == "Italian Game"

    def test_derives_name_from_eco_url(self):
        eco, name = _extract_opening({
            "ECO": "C50",
            "ECOUrl": "https://www.chess.com/openings/Italian-Game-Giuoco-Piano",
        })
        assert eco == "C50"
        assert name == "Italian Game Giuoco Piano"

    def test_opening_header_takes_precedence_over_eco_url(self):
        eco, name = _extract_opening({
            "Opening": "Ruy Lopez",
            "ECOUrl": "https://www.chess.com/openings/Italian-Game",
        })
        assert name == "Ruy Lopez"

    def test_no_headers(self):
        assert _extract_opening(None) == (None, None)
        assert _extract_opening({}) == (None, None)

    def test_eco_without_name_source(self):
        eco, name = _extract_opening({"ECO": "C50"})
        assert eco == "C50"
        assert name is None

    def test_trailing_slash_in_eco_url(self):
        eco, name = _extract_opening({"ECOUrl": "https://www.chess.com/openings/Italian-Game/"})
        assert name == "Italian Game"

    def test_analyze_pgn_extracts_eco_from_full_pgn(self):
        # Un tag PGN par ligne (format standard réellement produit par Chess.com) ;
        # des tags accolés sur une seule ligne sont mal supportés par python-chess.
        pgn = (
            '[Event "x"]\n[Result "1-0"]\n[ECO "C50"]\n'
            '[ECOUrl "https://www.chess.com/openings/Italian-Game"]\n\n'
            "1. e4 e5 2. Nf3 Nc6 3. Bc4 1-0"
        )
        out = analyze_pgn(pgn)
        assert out["eco"] == "C50"
        assert out["opening_name"] == "Italian Game"


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


# ---------------------------------------------------------------------------
# EPIC 19/20 : fen / best_move_san / time_spent_seconds
# ---------------------------------------------------------------------------

CLOCK_PGN = (
    '[Event "x"][Result "*"][TimeControl "600+0"]\n\n'
    "1. e4 {[%clk 0:10:00]} e5 {[%clk 0:10:00]} "
    "2. Nf3 {[%clk 0:09:40]} Nc6 {[%clk 0:09:50]} *"
)


class TestFenAndBestMoveSan:
    def test_fen_present_without_engine(self):
        out = analyze_pgn(PGN)
        assert out["moves"][0]["fen"] == chess.Board().fen()
        assert out["moves"][0]["best_move_san"] is None

    def test_best_move_san_from_engine(self):
        engine = build_client_engine(_evals_for(PGN, played=40, best_delta=0))
        out = analyze_pgn(PGN, engine)
        # best_delta=0 -> le meilleur coup ("0000" = null move) reste inconnu
        # en SAN (coup nul), donc None : on vérifie plutôt un cas où le
        # meilleur coup EST un coup réel.
        assert "best_move_san" in out["moves"][0]

    def test_best_move_san_resolves_real_move(self):
        game = chess.pgn.read_game(io.StringIO(PGN))
        board = game.board()
        first_move = next(iter(game.mainline_moves()))
        evals = {board.fen(): [[first_move.uci(), 40]]}
        out = analyze_pgn(PGN, build_client_engine(evals))
        assert out["moves"][0]["best_move_san"] == board.san(first_move)


class TestTimeSpentSeconds:
    def test_no_clocks_yields_none(self):
        out = analyze_pgn(PGN)
        assert all(m["time_spent_seconds"] is None for m in out["moves"])

    def test_first_move_per_color_is_none(self):
        out = analyze_pgn(CLOCK_PGN)
        assert out["moves"][0]["time_spent_seconds"] is None  # e4 (blanc, 1er)
        assert out["moves"][1]["time_spent_seconds"] is None  # e5 (noir, 1er)

    def test_subsequent_move_time_computed(self):
        out = analyze_pgn(CLOCK_PGN)
        # Nf3 : 10:00 -> 9:40 = 20s (pas d'incrément, TimeControl "600+0")
        assert out["moves"][2]["time_spent_seconds"] == 20.0
        # Nc6 : 10:00 -> 9:50 = 10s
        assert out["moves"][3]["time_spent_seconds"] == 10.0

    def test_explicit_time_control_overrides_header(self):
        out = analyze_pgn(CLOCK_PGN, time_control="600+5")
        # incrément 5s retranché : 20s de chute d'horloge + 5s d'incrément = 25s réels
        assert out["moves"][2]["time_spent_seconds"] == 25.0


class TestOnProgressCallback:
    """EPIC 28 (US 28.1) — progression coup-par-coup pour le Smart Loader."""

    def test_called_once_per_move(self):
        calls = []
        analyze_pgn(PGN, on_progress=lambda current, total: calls.append((current, total)))
        assert len(calls) == 6  # PGN = 6 demi-coups (e4 e5 Nf3 Nc6 Bb5 a6)

    def test_current_increments_from_one_to_total(self):
        calls = []
        analyze_pgn(PGN, on_progress=lambda current, total: calls.append((current, total)))
        assert [c for c, _ in calls] == [1, 2, 3, 4, 5, 6]
        assert all(total == 6 for _, total in calls)

    def test_last_call_current_equals_total(self):
        calls = []
        analyze_pgn(PGN, on_progress=lambda current, total: calls.append((current, total)))
        last_current, last_total = calls[-1]
        assert last_current == last_total

    def test_no_callback_by_default_does_not_raise(self):
        # Comportement par défaut inchangé (aucun appelant existant ne casse).
        out = analyze_pgn(PGN)
        assert len(out["moves"]) == 6

    def test_empty_pgn_never_calls_callback(self):
        calls = []
        analyze_pgn("not a pgn", on_progress=lambda current, total: calls.append((current, total)))
        assert calls == []
