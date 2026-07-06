"""Tests unitaires — mapping pur TSV ECO -> `eco_reference` (EPIC 38, US 38.1).

Aucune I/O ici (comme `test_ingest_lichess_puzzles.py`) : `parse_eco_row`
traduit une ligne déjà décodée par `csv.DictReader`, sans dépendre des
fichiers `.tsv` réels ni d'une connexion Postgres.
"""

from __future__ import annotations

from scripts.seed_eco import ECO_TSV_FILENAMES, parse_eco_row


def _row(**overrides) -> dict:
    row = {
        "eco": "A00",
        "name": "Amar Opening: Paris Gambit",
        "pgn": "1. Nh3 d5 2. g3 e5 3. f4",
    }
    row.update(overrides)
    return row


class TestParseEcoRow:
    def test_maps_eco_code(self):
        assert parse_eco_row(_row())["eco_code"] == "A00"

    def test_maps_name_to_opening_name(self):
        assert parse_eco_row(_row())["opening_name"] == "Amar Opening: Paris Gambit"

    def test_maps_pgn_to_moves_sequence(self):
        assert parse_eco_row(_row())["moves_sequence"] == "1. Nh3 d5 2. g3 e5 3. f4"

    def test_returns_exactly_three_fields(self):
        assert set(parse_eco_row(_row())) == {"eco_code", "opening_name", "moves_sequence"}


class TestEcoTsvFilenames:
    def test_covers_the_five_eco_volumes(self):
        assert ECO_TSV_FILENAMES == ("a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv")
