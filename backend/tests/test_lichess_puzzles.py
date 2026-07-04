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
            "solution": solution if solution is not None else ["f1b5", "a7a6", "b5a4", "g8f6"],
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
        # solution[0] ("f1b5") est auto-joué pour atteindre le FEN retourné ;
        # solution restante = ce que le solveur doit trouver.
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

    def test_solution_with_only_the_setup_move_returns_none(self):
        # Rien à résoudre après le coup auto-joué : donnée inexploitable.
        assert parse_puzzle_payload(_payload(solution=["f1b5"]), category="mate_in_1") is None

    def test_non_integer_rating_returns_none(self):
        payload = _payload()
        payload["puzzle"]["rating"] = "not-a-number"
        assert parse_puzzle_payload(payload, category="mate_in_1") is None

    def test_unreadable_pgn_returns_none(self):
        assert parse_puzzle_payload(_payload(pgn="garbage"), category="mate_in_1") is None

    def test_illegal_setup_move_returns_none(self):
        assert parse_puzzle_payload(_payload(solution=["a1a1", "e7e5"]), category="mate_in_1") is None

    def test_malformed_setup_move_token_returns_none(self):
        assert parse_puzzle_payload(_payload(solution=["not-a-move", "e7e5"]), category="mate_in_1") is None

    def test_completely_unexpected_shape_returns_none(self):
        assert parse_puzzle_payload({"unexpected": "shape"}, category="mate_in_1") is None

    def test_none_payload_fields_return_none(self):
        assert parse_puzzle_payload({"game": None, "puzzle": None}, category="mate_in_1") is None
