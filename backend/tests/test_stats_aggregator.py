"""Tests unitaires — agrégateur de statistiques (EPIC 1 / US 4.1)."""

from __future__ import annotations

from app.domain.stats_aggregator import (
    DEFAULT_ELO,
    build_summary,
    user_outcome,
)


def _move(phase, cpl, color="white", position_type="neutral", eval_before=None, san="e4"):
    return {
        "move_san": san, "color": color, "phase": phase, "cpl": cpl,
        "position_type": position_type, "eval_before": eval_before,
    }


def _entry(time_control="300", user_color="white", result="1-0", moves=None, created_at="2026-01-01"):
    return {
        "game": {"time_control": time_control, "user_color": user_color, "result": result, "created_at": created_at},
        "moves": moves or [],
    }


# ── user_outcome ──────────────────────────────────────────────────

class TestUserOutcome:
    def test_white_win(self):
        assert user_outcome("1-0", "white") == "win"
        assert user_outcome("1-0", "black") == "loss"

    def test_black_win(self):
        assert user_outcome("0-1", "black") == "win"

    def test_draw(self):
        assert user_outcome("1/2-1/2", "white") == "draw"

    def test_unknown(self):
        assert user_outcome(None, "white") is None


# ── build_summary : structure & valeurs ───────────────────────────

class TestBuildSummary:
    def test_empty_defaults(self):
        s = build_summary([], period="7d")
        assert s["period"] == "7d"
        assert s["hasData"] is False
        assert s["totalGames"] == 0
        assert set(s["rows"]) == {"bullet", "blitz", "rapid"}
        assert s["rows"]["blitz"]["current"] == DEFAULT_ELO
        assert s["gaffeRate"] == {"opening": 0.0, "middlegame": 0.0, "endgame": 0.0}
        assert s["finales"] == {"conversion": 0.0, "resilience": 0.0}

    def test_has_data_flag(self):
        s = build_summary([_entry(moves=[_move("opening", 10)])])
        assert s["hasData"] is True
        assert s["totalGames"] == 1

    def test_category_elos(self):
        moves = [
            _move("opening", 10),            # ACPL 10 → 2800
            _move("endgame", 110),           # ACPL 110 → 600
            _move("middlegame", 50, position_type="strategic"),  # strat 50 → 1500 +100 blitz
            _move("middlegame", 0, position_type="tactical"),    # tactique réussie → 3000
        ]
        s = build_summary([_entry(time_control="300", moves=moves)])
        row = s["rows"]["blitz"]
        # Le bonus de cadence (US 3.1) s'applique à toutes les catégories (+100 blitz).
        assert row["openings"] == 2900  # base 2800 + 100
        assert row["endgames"] == 700   # base 600 + 100
        assert row["strategy"] == 1600  # base 1500 + 100
        assert row["tactics"] == 3000   # ratio de réussite 1.0 (pas de bonus cadence)
        assert row["current"] == round((2900 + 700 + 1600 + 3000) / 4)

    def test_ratings_override_current(self):
        s = build_summary([_entry(moves=[_move("opening", 10)])], ratings={"blitz": 1234})
        assert s["rows"]["blitz"]["current"] == 1234

    def test_only_user_color_moves_count(self):
        moves = [_move("opening", 0, color="white"), _move("opening", 400, color="black")]
        s = build_summary([_entry(user_color="white", moves=moves)])
        # seuls les coups blancs comptent → ACPL 0 → base 2800 + bonus blitz 100
        assert s["rows"]["blitz"]["openings"] == 2900


# ── gaffeRate ─────────────────────────────────────────────────────

class TestGaffeRate:
    def test_distribution(self):
        moves = [
            _move("opening", 250),     # gaffe
            _move("middlegame", 300),  # gaffe
            _move("middlegame", 200),  # gaffe (seuil exact)
            _move("endgame", 50),      # pas une gaffe
        ]
        s = build_summary([_entry(moves=moves)])
        gr = s["gaffeRate"]
        assert gr["opening"] == round(100 / 3, 1)
        assert gr["middlegame"] == round(200 / 3, 1)
        assert gr["endgame"] == 0.0


# ── finales ───────────────────────────────────────────────────────

class TestFinales:
    def test_conversion(self):
        moves = [_move("endgame", 10, eval_before=200)]  # avantage ≥ +150
        s = build_summary([_entry(result="1-0", user_color="white", moves=moves)])
        assert s["finales"]["conversion"] == 100.0

    def test_resilience(self):
        moves = [_move("endgame", 10, eval_before=-200)]  # position perdante
        s = build_summary([_entry(result="1/2-1/2", user_color="white", moves=moves)])
        assert s["finales"]["resilience"] == 100.0

    def test_lost_advantage_low_conversion(self):
        moves = [_move("endgame", 10, eval_before=200)]
        s = build_summary([_entry(result="0-1", user_color="white", moves=moves)])
        assert s["finales"]["conversion"] == 0.0


# ── acplTrend ─────────────────────────────────────────────────────

class TestAcplTrend:
    def test_counts_per_game(self):
        g1 = _entry(created_at="2026-01-01", moves=[_move("opening", 250), _move("middlegame", 150)])
        g2 = _entry(created_at="2026-01-02", moves=[_move("opening", 50)])
        s = build_summary([g2, g1])  # ordre inversé → doit être trié par date
        assert s["acplTrend"]["labels"] == ["G1", "G2"]
        assert s["acplTrend"]["blunders"] == [1, 0]  # G1 a 1 gaffe, G2 0
        assert s["acplTrend"]["missed"] == [1, 0]    # G1 a 1 coup manqué
