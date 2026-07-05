"""Tests unitaires — agrégateur de statistiques (EPIC 1 / US 4.1)."""

from __future__ import annotations

from app.domain.stats_aggregator import (
    ADVANTAGE_CP,
    BLUNDER_CPL,
    DEFAULT_ELO,
    MISSED_CPL,
    TOP_OPENINGS_LIMIT,
    _tactical_success_ratio_all,
    build_summary,
    top_openings,
    user_outcome,
)


def _move(phase, cpl, color="white", position_type="neutral", eval_before=None, san="e4"):
    return {
        "move_san": san, "color": color, "phase": phase, "cpl": cpl,
        "position_type": position_type, "eval_before": eval_before,
    }


def _entry(
    time_control="300", user_color="white", result="1-0", moves=None, created_at="2026-01-01",
    eco=None, opening_name=None,
):
    return {
        "game": {
            "time_control": time_control, "user_color": user_color, "result": result,
            "created_at": created_at, "eco": eco, "opening_name": opening_name,
        },
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

    def test_white_loses_as_black_wins(self):
        assert user_outcome("0-1", "white") == "loss"


# ── Constantes de seuil (règles métier, cf. README §5) ─────────────

class TestThresholdConstants:
    """Verrouille la valeur exacte des seuils : comparer une constante à
    elle-même (`== DEFAULT_ELO`) ne détecte jamais une régression, il faut
    la valeur littérale attendue en dur."""

    def test_default_elo_is_1200(self):
        assert DEFAULT_ELO == 1200

    def test_top_openings_limit_is_3(self):
        assert TOP_OPENINGS_LIMIT == 3

    def test_blunder_cpl_is_200(self):
        assert BLUNDER_CPL == 200

    def test_missed_cpl_is_100(self):
        assert MISSED_CPL == 100

    def test_advantage_cp_is_150(self):
        assert ADVANTAGE_CP == 150


# ── build_summary : structure & valeurs ───────────────────────────

class TestBuildSummary:
    def test_default_period_is_30d(self):
        s = build_summary([])
        assert s["period"] == "30d"

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

    def test_missing_user_color_defaults_to_white(self):
        moves = [_move("opening", 0, color="white"), _move("opening", 400, color="black")]
        entry = _entry(moves=moves)
        del entry["game"]["user_color"]
        s = build_summary([entry])
        assert s["rows"]["blitz"]["openings"] == 2900

    def test_user_color_black_actually_read_not_ignored(self):
        # Distinct du test ci-dessus : prouve que la clé `"user_color"` est
        # bien lue (pas seulement que la valeur par défaut marche).
        moves = [_move("opening", 0, color="white"), _move("opening", 400, color="black")]
        s = build_summary([_entry(user_color="black", moves=moves)])
        # côté noir uniquement → ACPL 400 → base ~100 + bonus blitz 100
        assert s["rows"]["blitz"]["openings"] != 2900


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

    def test_blunder_exact_threshold_not_double_counted_as_missed(self):
        moves = [_move("opening", BLUNDER_CPL)]
        s = build_summary([_entry(moves=moves)])
        assert s["gaffeRate"]["opening"] == 100.0
        assert s["acplTrend"]["missed"] == [0]

    def test_two_blunders_same_phase_both_counted(self):
        # Détecte un mutant `-=`/comptage erroné : deux gaffes dans la même
        # phase doivent porter le total à 2, pas rester à 1 (ou devenir négatif).
        moves = [_move("opening", 300), _move("opening", 300), _move("middlegame", 10)]
        s = build_summary([_entry(moves=moves)])
        assert s["gaffeRate"]["opening"] == 100.0
        assert s["gaffeRate"]["middlegame"] == 0.0

    def test_endgame_percentage_uses_division_not_multiplication(self):
        moves = [_move("opening", 300), _move("endgame", 300)]
        s = build_summary([_entry(moves=moves)])
        assert s["gaffeRate"]["endgame"] == 50.0

    def test_endgame_percentage_rounds_to_one_decimal(self):
        moves = [_move("opening", 300), _move("middlegame", 300), _move("endgame", 300)]
        s = build_summary([_entry(moves=moves)])
        assert s["gaffeRate"]["endgame"] == round(100 / 3, 1)


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

    def test_no_endgame_eval_does_not_stop_later_games(self):
        # `entry_eval is None` doit passer à la partie suivante (continue),
        # jamais interrompre le calcul (break) — sinon toute partie SANS
        # finale placée avant une partie AVEC finale masquerait cette dernière.
        no_endgame = _entry(moves=[_move("opening", 10)])
        with_endgame = _entry(result="1-0", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
        s = build_summary([no_endgame, with_endgame])
        assert s["finales"]["conversion"] == 100.0

    def test_conversion_counts_every_advantage_game_not_just_first(self):
        won = _entry(result="1-0", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
        lost = _entry(result="0-1", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
        s = build_summary([won, lost])
        assert s["finales"]["conversion"] == 50.0

    def test_resilience_counts_every_losing_game_not_just_first(self):
        saved = _entry(result="1/2-1/2", user_color="white", moves=[_move("endgame", 10, eval_before=-200)])
        not_saved = _entry(result="0-1", user_color="white", moves=[_move("endgame", 10, eval_before=-200)])
        s = build_summary([saved, not_saved])
        assert s["finales"]["resilience"] == 50.0

    def test_resilience_loss_outcome_not_saved(self):
        moves = [_move("endgame", 10, eval_before=-200)]
        s = build_summary([_entry(result="0-1", user_color="white", moves=moves)])
        assert s["finales"]["resilience"] == 0.0

    def test_advantage_boundary_exact_threshold_counts(self):
        moves = [_move("endgame", 10, eval_before=ADVANTAGE_CP)]
        s = build_summary([_entry(result="1-0", user_color="white", moves=moves)])
        assert s["finales"]["conversion"] == 100.0

    def test_losing_boundary_exact_negative_threshold_counts(self):
        moves = [_move("endgame", 10, eval_before=-ADVANTAGE_CP)]
        s = build_summary([_entry(result="1/2-1/2", user_color="white", moves=moves)])
        assert s["finales"]["resilience"] == 100.0

    def test_eval_between_thresholds_counts_as_neither(self):
        # Ni avantage ni désavantage : ne doit alimenter ni conversion ni résilience.
        moves = [_move("endgame", 10, eval_before=0)]
        s = build_summary([_entry(result="1-0", user_color="white", moves=moves)])
        assert s["finales"] == {"conversion": 0.0, "resilience": 0.0}

    def test_conversion_accumulates_across_multiple_wins(self):
        # `won_adv += 1` doit s'accumuler ; un mutant `won_adv = 1` resterait
        # bloqué à 1 même avec deux victoires en position avantageuse.
        g1 = _entry(result="1-0", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
        g2 = _entry(result="1-0", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
        s = build_summary([g1, g2])
        assert s["finales"]["conversion"] == 100.0

    def test_resilience_accumulates_across_multiple_saves(self):
        g1 = _entry(result="1/2-1/2", user_color="white", moves=[_move("endgame", 10, eval_before=-200)])
        g2 = _entry(result="1/2-1/2", user_color="white", moves=[_move("endgame", 10, eval_before=-200)])
        s = build_summary([g1, g2])
        assert s["finales"]["resilience"] == 100.0

    def test_resilience_win_outcome_also_counts_as_saved(self):
        # `outcome in ("draw", "win")` : une victoire depuis une position
        # perdante à un instant T (comeback) compte aussi comme "sauvée".
        moves = [_move("endgame", 10, eval_before=-200)]
        s = build_summary([_entry(result="1-0", user_color="white", moves=moves)])
        assert s["finales"]["resilience"] == 100.0

    def test_missing_user_color_defaults_to_white(self):
        moves = [_move("endgame", 10, eval_before=200)]
        entry = _entry(result="1-0", moves=moves)
        del entry["game"]["user_color"]
        s = build_summary([entry])
        assert s["finales"]["conversion"] == 100.0

    def test_user_color_black_actually_read_in_finales(self):
        # Distinct du test ci-dessus : la partie est gagnée par les Blancs
        # (résultat "1-0") mais l'utilisateur est déclaré Noir → "loss", pas "win".
        moves = [_move("endgame", 10, eval_before=200, color="black")]
        s = build_summary([_entry(result="1-0", user_color="black", moves=moves)])
        assert s["finales"]["conversion"] == 0.0

    def test_resilience_precision_two_decimals_needed(self):
        saved = _entry(result="1/2-1/2", user_color="white", moves=[_move("endgame", 10, eval_before=-200)])
        others = [
            _entry(result="0-1", user_color="white", moves=[_move("endgame", 10, eval_before=-200)])
            for _ in range(2)
        ]
        s = build_summary([saved, *others])
        assert s["finales"]["resilience"] == round(100 / 3, 1)

    def test_endgame_eval_requires_both_phase_and_value(self):
        # `phase == ENDGAME and eval_before is not None` : un coup de finale
        # sans éval doit être ignoré (pas retourné comme "l'éval de finale"),
        # la boucle doit continuer jusqu'au prochain coup qui, lui, en a une.
        moves = [_move("endgame", 5, eval_before=None), _move("endgame", 10, eval_before=200)]
        s = build_summary([_entry(result="1-0", user_color="white", moves=moves)])
        assert s["finales"]["conversion"] == 100.0

    def test_conversion_precision_two_decimals_needed(self):
        won = _entry(result="1-0", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
        others = [
            _entry(result="0-1", user_color="white", moves=[_move("endgame", 10, eval_before=200)])
            for _ in range(2)
        ]
        s = build_summary([won, *others])
        assert s["finales"]["conversion"] == round(100 / 3, 1)


# ── acplTrend ─────────────────────────────────────────────────────

class TestAcplTrend:
    def test_counts_per_game(self):
        g1 = _entry(created_at="2026-01-01", moves=[_move("opening", 250), _move("middlegame", 150)])
        g2 = _entry(created_at="2026-01-02", moves=[_move("opening", 50)])
        s = build_summary([g2, g1])  # ordre inversé → doit être trié par date
        assert s["acplTrend"]["labels"] == ["G1", "G2"]
        assert s["acplTrend"]["blunders"] == [1, 0]  # G1 a 1 gaffe, G2 0
        assert s["acplTrend"]["missed"] == [1, 0]    # G1 a 1 coup manqué

    def test_missing_created_at_sorts_first(self):
        # Clé de tri par défaut "" (chaîne vide) : une partie sans date connue
        # doit être classée avant toute date ISO réelle. Distingué via le
        # nombre de gaffes (pas seulement les labels, toujours G1/G2 dans
        # l'ordre quel que soit le tri) : la partie non datée a 1 gaffe, la
        # partie datée n'en a aucune — l'ordre du tableau `blunders` révèle
        # laquelle est passée en premier.
        g_dated = _entry(created_at="2026-01-01", moves=[_move("opening", 10)])
        g_undated = _entry(moves=[_move("opening", 300)])
        del g_undated["game"]["created_at"]
        s = build_summary([g_dated, g_undated])
        assert s["acplTrend"]["blunders"] == [1, 0]

    def test_blunder_boundary_exact_threshold_counts(self):
        moves = [_move("opening", BLUNDER_CPL)]  # exactement au seuil → gaffe (>=)
        s = build_summary([_entry(moves=moves)])
        assert s["acplTrend"]["blunders"] == [1]

    def test_missed_boundary_exact_lower_threshold_counts(self):
        moves = [_move("opening", MISSED_CPL)]  # exactement 100 → coup manqué (<=)
        s = build_summary([_entry(moves=moves)])
        assert s["acplTrend"]["missed"] == [1]

    def test_missed_boundary_just_below_blunder_still_missed(self):
        moves = [_move("opening", BLUNDER_CPL - 1)]  # 199 → coup manqué, pas gaffe
        s = build_summary([_entry(moves=moves)])
        assert s["acplTrend"]["missed"] == [1]
        assert s["acplTrend"]["blunders"] == [0]


# ── tactics.successRatio (US 4.2) ──────────────────────────────────

class TestTacticsSuccessRatio:
    def test_no_tactical_positions_defaults_zero(self):
        s = build_summary([_entry(moves=[_move("opening", 10)])])
        assert s["tactics"]["successRatio"] == 0.0

    def test_all_successes_is_100(self):
        moves = [_move("middlegame", 0, position_type="tactical")]
        s = build_summary([_entry(moves=moves)])
        assert s["tactics"]["successRatio"] == 100.0

    def test_all_missed_is_zero(self):
        moves = [_move("middlegame", 200, position_type="tactical")]
        s = build_summary([_entry(moves=moves)])
        assert s["tactics"]["successRatio"] == 0.0

    def test_mixed_ratio(self):
        moves = [
            _move("middlegame", 0, position_type="tactical"),    # succès
            _move("middlegame", 200, position_type="tactical"),  # loupée
        ]
        s = build_summary([_entry(moves=moves)])
        assert s["tactics"]["successRatio"] == 50.0

    def test_pools_across_games(self):
        g1 = _entry(moves=[_move("middlegame", 0, position_type="tactical")])
        g2 = _entry(moves=[_move("middlegame", 200, position_type="tactical")])
        s = build_summary([g1, g2])
        assert s["tactics"]["successRatio"] == 50.0

    def test_only_user_color_counted(self):
        moves = [
            _move("middlegame", 0, color="white", position_type="tactical"),
            _move("middlegame", 200, color="black", position_type="tactical"),
        ]
        s = build_summary([_entry(user_color="white", moves=moves)])
        assert s["tactics"]["successRatio"] == 100.0

    def test_non_tactical_move_with_cpl_not_counted(self):
        # `position_type == "tactical" AND cpl is not None` : un coup non
        # tactique mais avec un cpl renseigné ne doit jamais être compté
        # (sinon successRatio ne resterait pas à 0 faute de position tactique).
        moves = [_move("middlegame", 100, position_type="strategic")]
        s = build_summary([_entry(moves=moves)])
        assert s["tactics"]["successRatio"] == 0.0

    def test_ratio_precision_two_decimals_needed(self):
        moves = [
            _move("middlegame", 0, position_type="tactical"),
            _move("middlegame", 0, position_type="tactical"),
            _move("middlegame", 200, position_type="tactical"),
        ]
        s = build_summary([_entry(moves=moves)])
        assert s["tactics"]["successRatio"] == round(100 * 2 / 3, 1)


class TestTacticalSuccessRatioAll:
    """Teste directement `_tactical_success_ratio_all` (le AND phase/cpl de
    `and`/`or` n'est pas observable via successRatio seul, cf. ci-dessus :
    un coup non tactique exclu ou inclus à tort donne parfois le même 0.0
    affiché — mais pas le même None/valeur retourné par la fonction pure)."""

    def test_no_tactical_position_returns_none(self):
        entries = [_entry(moves=[_move("middlegame", 100, position_type="strategic")])]
        assert _tactical_success_ratio_all(entries) is None

    def test_non_tactical_move_with_cpl_excluded(self):
        entries = [_entry(moves=[
            _move("middlegame", 0, position_type="tactical"),
            _move("middlegame", 100, position_type="strategic"),
        ])]
        # Si le coup stratégique (cpl non None) était compté à tort, le ratio
        # ne serait plus 100 % (2 positions dont 1 loupée au lieu d'1/1 réussie).
        assert _tactical_success_ratio_all(entries) == 1.0


# ── tactics.rating (moyenne des Elos tactiques par cadence) ───────

class TestTacticsRating:
    def test_rating_defaults_when_no_data(self):
        s = build_summary([])
        assert s["tactics"]["rating"] == DEFAULT_ELO

    def test_rating_averages_across_cadence_rows(self):
        # Une seule cadence (blitz) alimentée avec un Elo tactique de 3000 ;
        # bullet/rapid restent au DEFAULT_ELO (1200) → moyenne des 3 lignes.
        moves = [_move("middlegame", 0, position_type="tactical")]
        s = build_summary([_entry(time_control="300", moves=moves)])
        expected = round((1200 + 1200 + 3000) / 3)
        assert s["tactics"]["rating"] == expected

    def test_tactics_block_full_shape(self):
        s = build_summary([])
        assert s["tactics"] == {
            "rating": DEFAULT_ELO, "toReview": 0, "solved": 0, "streak": 0, "successRatio": 0.0,
        }


# ── top_openings (US 4.2) ───────────────────────────────────────────

class TestTopOpenings:
    def test_empty_without_eco(self):
        s = build_summary([_entry(moves=[_move("opening", 10)])])  # pas d'ECO
        assert s["topOpenings"] == []

    def test_single_opening(self):
        moves = [_move("opening", 10)]
        s = build_summary([_entry(eco="C50", opening_name="Italian Game", moves=moves)])
        assert s["topOpenings"] == [{"name": "Italian Game", "elo": 2800, "games": 1}]

    def test_falls_back_to_eco_code_without_name(self):
        s = build_summary([_entry(eco="C50", opening_name=None, moves=[_move("opening", 10)])])
        assert s["topOpenings"][0]["name"] == "C50"

    def test_ranked_by_games_played_desc(self):
        entries = (
            [_entry(eco="C50", opening_name="Italian", moves=[_move("opening", 10)])] * 1
            + [_entry(eco="B01", opening_name="Scandi", moves=[_move("opening", 10)])] * 3
        )
        result = top_openings(entries)
        assert result[0]["name"] == "Scandi"
        assert result[0]["games"] == 3
        assert result[1]["name"] == "Italian"
        assert result[1]["games"] == 1

    def test_respects_limit(self):
        entries = [
            _entry(eco=str(i), opening_name=f"Opening{i}", moves=[_move("opening", 10)])
            for i in range(TOP_OPENINGS_LIMIT + 2)
        ]
        assert len(top_openings(entries)) == TOP_OPENINGS_LIMIT

    def test_no_cadence_bonus_applied(self):
        # ACPL 10 → base 2800 ; PAS de +100 bonus blitz (mélange de cadences).
        s = build_summary([_entry(time_control="300", eco="C50", moves=[_move("opening", 10)])])
        assert s["topOpenings"][0]["elo"] == 2800

    def test_pools_opening_moves_across_games_same_eco(self):
        g1 = _entry(eco="C50", moves=[_move("opening", 0)])
        g2 = _entry(eco="C50", moves=[_move("opening", 20)])
        result = top_openings([g1, g2])
        assert result[0]["games"] == 2
        # ACPL moyen = 10 → 2800 (comme test_single_opening)
        assert result[0]["elo"] == 2800

    def test_default_elo_without_opening_phase_moves(self):
        s = build_summary([_entry(eco="C50", moves=[_move("middlegame", 10)])])
        assert s["topOpenings"][0]["elo"] == DEFAULT_ELO

    def test_entries_without_eco_do_not_stop_later_ones(self):
        # `if not eco: continue` doit passer à la partie suivante, jamais
        # interrompre la boucle (break) — sinon toute partie sans ECO placée
        # avant une partie avec ECO masquerait cette dernière.
        no_eco = _entry(moves=[_move("opening", 10)])
        with_eco = _entry(eco="C50", opening_name="Italian Game", moves=[_move("opening", 10)])
        result = top_openings([no_eco, with_eco])
        assert result == [{"name": "Italian Game", "elo": 2800, "games": 1}]
