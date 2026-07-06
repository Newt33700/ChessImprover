"""ETL — ingestion du dump public Lichess dans `lichess_puzzles` (EPIC 37, US 37.1).

Le dump officiel (https://database.lichess.org/#puzzles, ``lichess_db_puzzle.csv.zst``)
est un CSV compressé Zstandard de plusieurs millions de lignes :

    PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags

``Themes``/``OpeningTags`` sont des chaînes de tags séparés par des espaces
(ex. ``"advantage endgame short"``) — mappées ici vers des ``TEXT[]`` Postgres.

Contraintes (spec EPIC 37) : pas de pandas (empreinte mémoire trop lourde pour
un fichier de plusieurs Go décompressé), lecture par chunks via
``zstandard.ZstdDecompressor.stream_reader`` + ``csv.DictReader``, insertion
par lots de 10 000 lignes (``ON CONFLICT DO NOTHING`` — ré-exécutable sans
dupliquer).

Usage (fichier local déjà téléchargé, OU URL — téléchargée en flux, jamais
matérialisée sur disque) ::

    python -m scripts.ingest_lichess_puzzles lichess_db_puzzle.csv.zst
    python -m scripts.ingest_lichess_puzzles https://database.lichess.org/lichess_db_puzzle.csv.zst
    python -m scripts.ingest_lichess_puzzles   # sans argument : DEFAULT_PUZZLE_DUMP_URL

``DATABASE_URL`` doit être configuré (même variable que le reste du backend).
Ce script est prévu pour tourner depuis un environnement qui a *à la fois*
l'accès réseau sortant vers Lichess et les identifiants de la base cible —
typiquement un job ponctuel sur l'infrastructure de production (Render/CI),
pas nécessairement la même machine que celle où le code est édité.
"""

from __future__ import annotations

import csv
import io
import logging
import sys
import urllib.request
from typing import Any, Dict, Iterator, List

logger = logging.getLogger(__name__)

BATCH_SIZE = 10_000

#: Dump officiel — cf. https://database.lichess.org/#puzzles
DEFAULT_PUZZLE_DUMP_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"

_INSERT_SQL = """
    INSERT INTO lichess_puzzles (
        puzzle_id, fen, moves, rating, rating_deviation,
        popularity, nb_plays, themes, game_url, opening_tags
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (puzzle_id) DO NOTHING
"""


def parse_puzzle_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Traduit une ligne brute du CSV Lichess vers la forme `lichess_puzzles`.

    Fonction PURE (aucune I/O) — testable sans fichier ni base réelle, comme
    ``domain.lichess_puzzles.parse_puzzle_payload``.
    """
    return {
        "puzzle_id": row["PuzzleId"],
        "fen": row["FEN"],
        "moves": row["Moves"],
        "rating": int(row["Rating"]),
        "rating_deviation": int(row["RatingDeviation"]),
        "popularity": int(row["Popularity"]),
        "nb_plays": int(row["NbPlays"]),
        "themes": row["Themes"].split() if row["Themes"] else [],
        "game_url": row["GameUrl"] or None,
        "opening_tags": row["OpeningTags"].split() if row["OpeningTags"] else [],
    }


def _row_to_params(puzzle: Dict[str, Any]) -> tuple:
    return (
        puzzle["puzzle_id"], puzzle["fen"], puzzle["moves"], puzzle["rating"],
        puzzle["rating_deviation"], puzzle["popularity"], puzzle["nb_plays"],
        puzzle["themes"], puzzle["game_url"], puzzle["opening_tags"],
    )


def is_url(source: str) -> bool:
    """Fonction PURE — distingue un chemin local d'une URL HTTP(S), sans I/O."""
    return source.startswith("http://") or source.startswith("https://")


def _open_binary_stream(source: str):  # pragma: no cover - I/O réel
    """Fichier local OU flux HTTP — dans les deux cas un objet supportant
    ``.read(n)``, ce que ``zstandard`` exige de son ``stream_reader``.
    ``urllib.request.urlopen`` diffuse la réponse par morceaux (pas de
    téléchargement préalable sur disque, cohérent avec la contrainte
    mémoire de l'EPIC 37 — un dump complet fait plusieurs Go décompressé)."""
    if is_url(source):
        return urllib.request.urlopen(source)  # noqa: S310 - source figée (dump officiel Lichess)
    return open(source, "rb")


def iter_puzzle_rows(csv_zst_source: str) -> Iterator[Dict[str, Any]]:  # pragma: no cover - I/O réel
    """Décompresse et parse le dump Lichess en flux, sans jamais matérialiser
    le fichier entier en mémoire (chunks Zstandard -> lignes CSV).
    ``csv_zst_source`` : chemin local OU URL HTTP(S) (cf. ``is_url``)."""
    import zstandard

    with _open_binary_stream(csv_zst_source) as compressed:
        dctx = zstandard.ZstdDecompressor()
        with dctx.stream_reader(compressed) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8")
            for row in csv.DictReader(text_stream):
                yield parse_puzzle_row(row)


def ingest(csv_zst_source: str, dsn: str, batch_size: int = BATCH_SIZE) -> int:  # pragma: no cover - I/O réel
    """Ingère ``csv_zst_source`` (chemin local ou URL) dans `lichess_puzzles`
    par lots de ``batch_size`` lignes. Retourne le nombre total de lignes lues
    (pas nécessairement toutes insérées : ``ON CONFLICT DO NOTHING`` ignore
    les doublons d'un ré-import)."""
    import psycopg

    total = 0
    batch: List[tuple] = []
    with psycopg.connect(dsn) as conn:
        conn.prepare_threshold = None  # compat pooler Supabase (mode transaction)
        with conn.cursor() as cur:
            for puzzle in iter_puzzle_rows(csv_zst_source):
                batch.append(_row_to_params(puzzle))
                total += 1
                if len(batch) >= batch_size:
                    cur.executemany(_INSERT_SQL, batch)
                    conn.commit()
                    logger.info("ingest_lichess_puzzles: %d lignes traitées", total)
                    batch.clear()
            if batch:
                cur.executemany(_INSERT_SQL, batch)
                conn.commit()
    logger.info("ingest_lichess_puzzles: terminé — %d lignes traitées", total)
    return total


def main() -> None:  # pragma: no cover - point d'entrée CLI
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 2:
        print("Usage: python -m scripts.ingest_lichess_puzzles [<fichier.csv.zst>|<url>]")
        raise SystemExit(1)
    source = sys.argv[1] if len(sys.argv) == 2 else DEFAULT_PUZZLE_DUMP_URL

    from app.config import settings

    if not settings.database_url:
        print("DATABASE_URL non configuré.")
        raise SystemExit(1)

    ingest(source, settings.database_url)


if __name__ == "__main__":  # pragma: no cover
    main()
