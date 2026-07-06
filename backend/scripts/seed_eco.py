"""ETL — référentiel ECO dans `eco_reference` (EPIC 38 — Lotus Mastery Engine).

Parse les TSV locaux `frontend/assets/data/openings/{a,b,c,d,e}.tsv`
(colonnes ``eco``, ``name``, ``pgn`` séparées par tabulation — déjà
rapatriés localement depuis raw.githubusercontent.com, EPIC 13) et les
insère dans `eco_reference` (``eco_code``, ``name``, ``moves_sequence``).

Usage ::

    python -m scripts.seed_eco [chemin/vers/openings/]

Sans argument, cherche `../frontend/assets/data/openings/` relatif à la
racine du dépôt (mise en page standard de ce projet). ``DATABASE_URL`` doit
être configuré (même variable que le reste du backend).
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List

logger = logging.getLogger(__name__)

BATCH_SIZE = 5_000

#: Fichiers du référentiel ECO (volumes A à E, nomenclature standard).
ECO_TSV_FILENAMES = ("a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv")

_INSERT_SQL = """
    INSERT INTO eco_reference (eco_code, opening_name, moves_sequence)
    VALUES (%s, %s, %s)
    ON CONFLICT (moves_sequence) DO NOTHING
"""


def parse_eco_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Traduit une ligne brute du TSV ECO vers la forme `eco_reference`.

    Fonction PURE (aucune I/O) — testable sans fichier ni base réelle.
    ``opening_name`` (pas ``name``) : évite un mot-clé SQL non réservé comme
    identifiant de colonne, même convention que ``line_name`` sur l'ex-table
    ``opening_repertoire`` (EPIC 9).
    """
    return {
        "eco_code": row["eco"],
        "opening_name": row["name"],
        "moves_sequence": row["pgn"],
    }


def _row_to_params(entry: Dict[str, Any]) -> tuple:
    return (entry["eco_code"], entry["opening_name"], entry["moves_sequence"])


def iter_eco_rows(openings_dir: str) -> Iterator[Dict[str, Any]]:  # pragma: no cover - I/O réel
    """Parse les 5 TSV (a.tsv…e.tsv) présents dans ``openings_dir``, en flux."""
    base = Path(openings_dir)
    for filename in ECO_TSV_FILENAMES:
        path = base / filename
        if not path.exists():
            logger.warning("seed_eco: fichier manquant, ignoré : %s", path)
            continue
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                yield parse_eco_row(row)


def seed(openings_dir: str, dsn: str, batch_size: int = BATCH_SIZE) -> int:  # pragma: no cover - I/O réel
    """Ingère les TSV de ``openings_dir`` dans `eco_reference` par lots.
    Retourne le nombre total de lignes lues (``ON CONFLICT DO NOTHING``
    ignore les doublons d'un ré-import — ré-exécutable sans risque)."""
    import psycopg

    total = 0
    batch: List[tuple] = []
    with psycopg.connect(dsn) as conn:
        conn.prepare_threshold = None  # compat pooler Supabase (mode transaction)
        with conn.cursor() as cur:
            for entry in iter_eco_rows(openings_dir):
                batch.append(_row_to_params(entry))
                total += 1
                if len(batch) >= batch_size:
                    cur.executemany(_INSERT_SQL, batch)
                    conn.commit()
                    batch.clear()
            if batch:
                cur.executemany(_INSERT_SQL, batch)
                conn.commit()
    logger.info("seed_eco: terminé — %d lignes traitées", total)
    return total


def _default_openings_dir() -> str:  # pragma: no cover - trivial
    # backend/scripts/seed_eco.py -> repo_root/frontend/assets/data/openings
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "frontend" / "assets" / "data" / "openings")


def main() -> None:  # pragma: no cover - point d'entrée CLI
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 2:
        print("Usage: python -m scripts.seed_eco [<dossier openings/>]")
        raise SystemExit(1)
    openings_dir = sys.argv[1] if len(sys.argv) == 2 else _default_openings_dir()

    from app.config import settings

    if not settings.database_url:
        print("DATABASE_URL non configuré.")
        raise SystemExit(1)

    seed(openings_dir, settings.database_url)


if __name__ == "__main__":  # pragma: no cover
    main()
