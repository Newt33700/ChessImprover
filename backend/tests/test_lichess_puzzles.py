"""Tests unitaires — parsing pur des puzzles Lichess (EPIC 34).

Aucune I/O ici : ``domain/lichess_puzzles.py`` ne fait que traduire le JSON
brut de ``GET /api/puzzle/next`` (cf. infrastructure/lichess_client.py) vers
la forme interne d'un problème tactique. Ces tests figent le format attendu
sans dépendre du réseau.
"""

from __future__ import annotations

from app.domain.lichess_puzzles import (
    LICHESS_ANGLES,
    angle_for_theme,
    parse_puzzle_payload,
    replay_pgn_to_ply,
)

PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6"


def _payload(initial_ply=4, solution=None, rating=1550, puzzle_id="abcd1", themes=None, pgn=PGN):
    return {
        "game": {"pgn": pgn},
        "puzzle": {
            "id": puzzle_id,
            "rating": rating,
            "initialPly": initial_ply,
            # `initialPly=4` = index du dernier coup déjà joué (Bb5, cf. PGN) ;
            # la position de départ du puzzle est donc après 5 demi-coups
            # (Noirs au trait) — "a7a6" y est un coup noir légal.
            "solution": solution if solution is not None else ["a7a6", "b5a4", "g8f6"],
            "themes": themes or [],
        },
    }


class TestAngleForTheme:
    def test_known_themes_map_to_lichess_angles(self):
        assert angle_for_theme("mate_in_1") == "mateIn1"
        assert angle_for_theme("mate_in_2") == "mateIn2"
        assert angle_for_theme("hanging_piece") == "hangingPiece"

    def test_none_theme_is_random_no_angle(self):
        assert angle_for_theme(None) is None

    def test_unknown_theme_returns_none(self):
        assert angle_for_theme("not-a-theme") is None

    def test_all_tactical_themes_have_an_angle(self):
        # Garde-fou : toute nouvelle catégorie interne doit avoir sa
        # correspondance Lichess explicite, jamais une omission silencieuse.
        assert set(LICHESS_ANGLES) == {"mate_in_1", "mate_in_2", "hanging_piece"}


class TestReplayPgnToPly:
    def test_replays_the_requested_number_of_plies(self):
        board = replay_pgn_to_ply(PGN, 4)
        assert board is not None
        assert board.fen() == "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"

    def test_zero_plies_returns_the_starting_position(self):
        board = replay_pgn_to_ply(PGN, 0)
        assert board.fen().startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")

    def test_more_plies_than_the_game_has_returns_none(self):
        assert replay_pgn_to_ply(PGN, 1000) is None

    def test_unreadable_pgn_returns_none_not_raise(self):
        assert replay_pgn_to_ply("this is not a pgn at all !!", 1) is None

    def test_empty_pgn_returns_none(self):
        assert replay_pgn_to_ply("", 1) is None


class TestParsePuzzlePayload:
    def test_parses_a_well_formed_payload(self):
        parsed = parse_puzzle_payload(_payload(), category="mate_in_2")
        assert parsed is not None
        assert parsed["category"] == "mate_in_2"
        assert parsed["difficulty_elo"] == 1550
        assert parsed["lichess_id"] == "abcd1"
        # EPIC 34 hotfix : `solution` est la séquence COMPLÈTE à résoudre —
        # aucun élément n'est auto-joué (cf. payload réel de production).
        assert parsed["solution"] == ["a7a6", "b5a4", "g8f6"]
        assert parsed["fen"] == "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"

    def test_category_defaults_to_aleatoire_when_none_requested(self):
        parsed = parse_puzzle_payload(_payload(), category=None)
        assert parsed["category"] == "aleatoire"

    def test_missing_game_key_returns_none(self):
        payload = _payload()
        del payload["game"]
        assert parse_puzzle_payload(payload, category="mate_in_1") is None

    def test_missing_puzzle_key_returns_none(self):
        payload = _payload()
        del payload["puzzle"]
        assert parse_puzzle_payload(payload, category="mate_in_1") is None

    def test_missing_solution_field_returns_none(self):
        payload = _payload()
        del payload["puzzle"]["solution"]
        assert parse_puzzle_payload(payload, category="mate_in_1") is None

    def test_empty_solution_list_returns_none(self):
        assert parse_puzzle_payload(_payload(solution=[]), category="mate_in_1") is None

    def test_single_move_solution_is_valid(self):
        # EPIC 34 hotfix : un puzzle à un seul coup (ex. mat en 1) est
        # parfaitement valide — rien n'est plus "auto-joué" avant de résoudre.
        parsed = parse_puzzle_payload(_payload(solution=["a7a6"]), category="mate_in_1")
        assert parsed is not None
        assert parsed["solution"] == ["a7a6"]

    def test_non_integer_rating_returns_none(self):
        payload = _payload()
        payload["puzzle"]["rating"] = "not-a-number"
        assert parse_puzzle_payload(payload, category="mate_in_1") is None

    def test_unreadable_pgn_returns_none(self):
        assert parse_puzzle_payload(_payload(pgn="garbage"), category="mate_in_1") is None

    def test_illegal_first_move_returns_none(self):
        # "a1a1" n'est pas un coup légal (case de départ = case d'arrivée).
        assert parse_puzzle_payload(_payload(solution=["a1a1", "e7e5"]), category="mate_in_1") is None

    def test_already_played_move_is_illegal_at_the_real_position(self):
        # "e7e5" a déjà été joué dans le PGN (2ᵉ demi-coup) : la case e7 est
        # vide à la vraie position de départ du puzzle (après 5 demi-coups).
        assert parse_puzzle_payload(_payload(solution=["e7e5"]), category="mate_in_1") is None

    def test_malformed_first_move_token_returns_none(self):
        assert parse_puzzle_payload(_payload(solution=["not-a-move", "e7e5"]), category="mate_in_1") is None

    def test_completely_unexpected_shape_returns_none(self):
        assert parse_puzzle_payload({"unexpected": "shape"}, category="mate_in_1") is None

    def test_none_payload_fields_return_none(self):
        assert parse_puzzle_payload({"game": None, "puzzle": None}, category="mate_in_1") is None

    def test_real_production_payload_regression(self):
        # EPIC 34 hotfix — payload RÉEL capturé en production (04/07) qui
        # révélait le bug initialPly/off-by-one : доit désormais se parser
        # correctement (Noirs jouent Bxe2, Blancs Rxe2 forcé, Noirs Bxc1).
        payload = {
            "game": {
                "pgn": (
                    "d4 c5 d5 e5 c4 d6 e4 Be7 Nf3 Nf6 Nc3 O-O Bd3 h6 O-O Nh7 "
                    "Ne1 f5 f4 fxe4 Bxe4 Nd7 fxe5 Rxf1+ Kxf1 Nxe5 b3 Bg4 Qc2 "
                    "Qf8+ Kg1 Nf6 Bb2 a6 Nd3 Nxe4 Nxe4 Nxd3 Qxd3 Qd8 Qg3 h5 "
                    "h3 Bh4 Qxd6 Qxd6 Nxd6 Bd7 Nxb7 Rc8 Nd6 Rf8 Rf1 Rxf1+ "
                    "Kxf1 Be7 Ne4 Bf5 Ng3 Bd3+ Ke1 h4 Ne2 Bg5 Kd1 Kf7 Ba3 "
                    "Be3 Bc1"
                ),
            },
            "puzzle": {
                "id": "pmR1P", "rating": 1386, "initialPly": 68,
                "solution": ["d3e2", "d1e2", "e3c1"],
                "themes": ["advantage", "short", "endgame"],
            },
        }
        parsed = parse_puzzle_payload(payload, category=None)
        assert parsed is not None
        assert parsed["solution"] == ["d3e2", "d1e2", "e3c1"]
        assert parsed["difficulty_elo"] == 1386
        assert parsed["lichess_id"] == "pmR1P"
