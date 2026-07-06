"""Applique `supabase/migrations/*.sql` sur une base Postgres arbitraire.

Contexte (US 39 — migration Supabase → CockroachDB) : les migrations de ce
dépôt ont été rédigées pour Supabase et contiennent des `CREATE POLICY` /
`ENABLE ROW LEVEL SECURITY` reposant sur `auth.uid()`, une fonction propre à
Supabase/PostgREST. Le backend ne passe jamais par PostgREST (connexion
directe via `psycopg` avec son propre `DATABASE_URL`, filtrage par
`user_id` fait côté application) : ces politiques RLS ne sont donc jamais
appliquées à l'exécution, quelle que soit la base cible. On les retire pour
pouvoir rejouer les migrations sur n'importe quel Postgres compatible
(CockroachDB, Neon, Postgres auto-hébergé...) sans dépendre du support RLS
de ce moteur.

Même logique pour le trigger `set_updated_at` (init_auth) : la colonne
`user_data.updated_at` qu'il maintient n'est lue nulle part côté
application — on le retire plutôt que de parier sur le support des
triggers du moteur cible.

Usage ::

    python -m scripts.apply_migrations <DATABASE_URL> [--migrations-dir path]

Rejouable sans risque : les migrations utilisent `CREATE TABLE IF NOT
EXISTS` / `CREATE INDEX IF NOT EXISTS` / `ON CONFLICT DO NOTHING`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List

_RLS_ENABLE_RE = re.compile(
    r"ALTER TABLE \w+ ENABLE ROW LEVEL SECURITY;\n?"
)
_RLS_POLICY_RE = re.compile(r"CREATE POLICY.*?;\n?", re.DOTALL)
_TRIGGER_FUNCTION_RE = re.compile(
    r"CREATE OR REPLACE FUNCTION \w+\(\)\s*RETURNS TRIGGER.*?"
    r"\$\$ LANGUAGE plpgsql;\n?",
    re.DOTALL,
)
_DROP_TRIGGER_RE = re.compile(r"DROP TRIGGER IF EXISTS \w+ ON \w+;\n?")
_CREATE_TRIGGER_RE = re.compile(
    r"CREATE TRIGGER \w+.*?EXECUTE FUNCTION \w+\(\);\n?", re.DOTALL
)


def strip_unsupported_statements(sql: str) -> str:
    """Retire RLS (policies + `ENABLE ROW LEVEL SECURITY`) et triggers.

    Fonction PURE (aucune I/O) — testable sans base réelle. Voir le
    docstring du module pour la justification de chaque suppression.
    """
    sql = _RLS_POLICY_RE.sub("", sql)
    sql = _RLS_ENABLE_RE.sub("", sql)
    sql = _TRIGGER_FUNCTION_RE.sub("", sql)
    sql = _DROP_TRIGGER_RE.sub("", sql)
    sql = _CREATE_TRIGGER_RE.sub("", sql)
    return sql


def split_statements(sql: str) -> List[str]:
    """Découpe un script SQL en instructions individuelles sur `;`.

    Retire d'abord les lignes de commentaire `--` en entier, PUIS découpe
    sur `;` — dans cet ordre précisément : un commentaire en français peut
    contenir un point-virgule dans son texte (ex. « EPIC 3) ; 1000 par
    défaut... »), et découper sur `;` avant de retirer les commentaires
    couperait la ligne en deux, laissant fuiter la moitié qui ne commence
    plus par `--` comme si c'était du SQL réel.

    Suppose qu'aucun bloc dollar-quoté (`$$...$$`) ne subsiste — c'est le
    cas après `strip_unsupported_statements`, seul appelant prévu.
    """
    lines = [
        line for line in sql.splitlines() if not line.strip().startswith("--")
    ]
    without_comments = "\n".join(lines)
    statements = []
    for raw in without_comments.split(";"):
        statement = raw.strip()
        if statement:
            statements.append(statement)
    return statements


def _default_migrations_dir() -> str:  # pragma: no cover - trivial
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "supabase" / "migrations")


def prepare_migration_files(
    migrations_dir: str,
) -> List[Path]:  # pragma: no cover - I/O réel
    """Liste les fichiers `.sql` de `migrations_dir`, triés par nom.

    Le nom de fichier commence par un horodatage (`YYYYMMDDHHMMSS_...`) :
    le tri lexicographique restitue l'ordre chronologique d'application.
    """
    return sorted(Path(migrations_dir).glob("*.sql"))


def apply_migrations(
    dsn: str, migrations_dir: str
) -> int:  # pragma: no cover - nécessite une base réelle
    """Applique chaque migration de `migrations_dir` sur `dsn`, dans l'ordre.

    Une transaction par fichier. Retourne le nombre de fichiers appliqués.
    """
    import psycopg

    files = prepare_migration_files(migrations_dir)
    with psycopg.connect(dsn) as conn:
        for path in files:
            raw = path.read_text(encoding="utf-8")
            sql = strip_unsupported_statements(raw)
            with conn.cursor() as cur:
                for statement in split_statements(sql):
                    cur.execute(statement)
            conn.commit()
    return len(files)


def main() -> None:  # pragma: no cover - point d'entrée CLI
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database_url", help="DSN Postgres de la base cible")
    parser.add_argument(
        "--migrations-dir",
        default=_default_migrations_dir(),
        help="Dossier des fichiers .sql (défaut : supabase/migrations)",
    )
    args = parser.parse_args()

    count = apply_migrations(args.database_url, args.migrations_dir)
    print(f"apply_migrations: {count} fichier(s) appliqué(s).")


if __name__ == "__main__":  # pragma: no cover
    main()
