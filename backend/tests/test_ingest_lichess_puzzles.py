"""Tests unitaires — mapping pur CSV Lichess -> `lichess_puzzles` (EPIC 37, US 37.1).

Aucune I/O ici (comme `test_lichess_puzzles.py` pour le parsing API) :
`parse_puzzle_row` traduit une ligne déjà décodée par `csv.DictReader`, sans
dépendre du fichier `.csv.zst` réel ni d'une connexion Postgres.
"""

from __future__ import annotations

import pytest

from scripts.ingest_lichess_puzzles import DEFAULT_PUZZLE_DUMP_URL, is_url, parse_puzzle_row


def _row(**overrides) -> dict:
    row = {
        "PuzzleId": "00sHx",
        "FEN": "q3k1nr/1pp1nQpp/3p4/1P2p3/4P3/B1PP1b2/B5PP/5K1R b k - 0 17",
        "Moves": "e8d7 a2e6 d7d8 f7f8",
        "Rating": "1760",
        "RatingDeviation": "80",
        "Popularity": "83",
        "NbPlays": "72",
        "Themes": "mate mateIn2 middlegame short",
        "GameUrl": "https://lichess.org/787zsVup/black#34",
        "OpeningTags": "Italian_Game Italian_Game_Classical_Variation",
    }
    row.update(overrides)
    return row


class TestParsePuzzleRow:
    def test_maps_scalar_fields(self):
        puzzle = parse_puzzle_row(_row())
        assert puzzle["puzzle_id"] == "00sHx"
        assert puzzle["fen"].startswith("q3k1nr")
        assert puzzle["moves"] == "e8d7 a2e6 d7d8 f7f8"
        assert puzzle["rating"] == 1760
        assert puzzle["rating_deviation"] == 80
        assert puzzle["popularity"] == 83
        assert puzzle["nb_plays"] == 72

    def test_splits_space_separated_themes_into_list(self):
        puzzle = parse_puzzle_row(_row())
        assert puzzle["themes"] == ["mate", "mateIn2", "middlegame", "short"]

    def test_splits_space_separated_opening_tags_into_list(self):
        puzzle = parse_puzzle_row(_row())
        assert puzzle["opening_tags"] == [
            "Italian_Game", "Italian_Game_Classical_Variation",
        ]

    def test_empty_themes_field_becomes_empty_list(self):
        puzzle = parse_puzzle_row(_row(Themes=""))
        assert puzzle["themes"] == []

    def test_empty_opening_tags_field_becomes_empty_list(self):
        puzzle = parse_puzzle_row(_row(OpeningTags=""))
        assert puzzle["opening_tags"] == []

    def test_empty_game_url_becomes_none(self):
        puzzle = parse_puzzle_row(_row(GameUrl=""))
        assert puzzle["game_url"] is None

    def test_numeric_fields_are_cast_to_int(self):
        puzzle = parse_puzzle_row(_row())
        assert all(
            isinstance(puzzle[key], int)
            for key in ("rating", "rating_deviation", "popularity", "nb_plays")
        )

    def test_missing_rating_field_raises_type_error(self):
        # csv.DictReader met `None` (restval) sur les clés absentes d'une
        # ligne trop courte -- vu en production sur le dump réel (EPIC 39,
        # ~1,81M/6M lignes) ; iter_puzzle_rows attrape cette exception pour
        # ignorer la ligne plutôt que de faire échouer tout l'import.
        with pytest.raises(TypeError):
            parse_puzzle_row(_row(Rating=None))


class TestIsUrl:
    def test_https_dump_url_is_a_url(self):
        assert is_url(DEFAULT_PUZZLE_DUMP_URL) is True

    def test_http_url_is_a_url(self):
        assert is_url("http://example.com/dump.csv.zst") is True

    def test_local_path_is_not_a_url(self):
        assert is_url("lichess_db_puzzle.csv.zst") is False

    def test_absolute_local_path_is_not_a_url(self):
        assert is_url("/data/lichess_db_puzzle.csv.zst") is False
