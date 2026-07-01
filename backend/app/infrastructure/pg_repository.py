"""Dépôt PostgreSQL/Supabase pour les parties analysées (EPIC 1).

Implémente les mêmes opérations que le store in-memory de ``db_client`` pour les
tables ``games`` et ``game_moves``, activé lorsque ``DATABASE_URL`` est défini.
Utilise ``psycopg`` (v3) avec des requêtes paramétrées.

Importé **paresseusement** par ``db_client`` (uniquement si une base est
configurée) afin que les environnements sans base — ni ``psycopg`` — restent
fonctionnels. Une connexion par appel est ouverte : simple et correct ; un pool
constituerait une optimisation de production.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PgRepository:
    """Accès aux tables ``games`` / ``game_moves`` via PostgreSQL."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    # -- Connexion -----------------------------------------------------------

    def _connect(self):  # pragma: no cover - nécessite une base réelle
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(self.dsn, row_factory=dict_row)
        # Compat pooler Supabase en mode "transaction" (port 6543) : les
        # prepared statements de psycopg3 y sont incompatibles.
        conn.prepare_threshold = None
        return conn

    @staticmethod
    def _iso(row: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        created = row.get("created_at")
        if created is not None and hasattr(created, "isoformat"):
            row["created_at"] = created.isoformat()
        return row

    # -- games ---------------------------------------------------------------

    def create_game(
        self,
        pgn: str,
        user_id: Optional[str] = None,
        time_control: Optional[str] = None,
        user_color: str = "white",
        status: str = "processing",
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO games (user_id, pgn, time_control, user_color, status) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, pgn, time_control, user_color, status))
            row = cur.fetchone()
            conn.commit()
        return self._iso(dict(row))

    def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM games WHERE id = %s::uuid", (game_id,))
            row = cur.fetchone()
        return self._iso(dict(row)) if row else None

    def get_games_for_user(self, user_id: Optional[str]) -> List[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM games WHERE user_id = %s::uuid", (user_id,))
            return [self._iso(dict(r)) for r in cur.fetchall()]

    def update_game(self, game_id: str, **fields: Any) -> Optional[Dict[str, Any]]:  # pragma: no cover
        if not fields:
            return self.get_game(game_id)
        cols = ", ".join(f"{k} = %s" for k in fields)
        params = list(fields.values()) + [game_id]
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"UPDATE games SET {cols} WHERE id = %s::uuid RETURNING *", params)
            row = cur.fetchone()
            conn.commit()
        return self._iso(dict(row)) if row else None

    def get_completed_games(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:  # pragma: no cover
        # NB : on évite un paramètre "IS NULL" non typé (IndeterminateDatatype
        # avec psycopg3) en branchant la requête sur la présence de user_id, et
        # on caste explicitement en ::uuid pour la colonne UUID de Postgres.
        if user_id is None:
            sql, params = "SELECT * FROM games WHERE status = 'completed'", ()
        else:
            sql = "SELECT * FROM games WHERE status = 'completed' AND user_id = %s::uuid"
            params = (user_id,)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return [self._iso(dict(r)) for r in cur.fetchall()]

    # -- game_moves ----------------------------------------------------------

    _MOVE_COLS = (
        "move_number", "color", "move_san", "eval_before", "eval_after",
        "score_cp", "cpl", "is_mate", "mate_in", "phase", "position_type",
    )

    def bulk_insert_moves(self, game_id: str, moves: List[Dict[str, Any]]) -> int:  # pragma: no cover
        if not moves:
            return 0
        cols = "game_id, " + ", ".join(self._MOVE_COLS)
        placeholders = "(" + ", ".join(["%s"] * (len(self._MOVE_COLS) + 1)) + ")"
        rows = [
            [game_id] + [m.get(c) for c in self._MOVE_COLS] for m in moves
        ]
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(f"INSERT INTO game_moves ({cols}) VALUES {placeholders}", rows)
            conn.commit()
        return len(moves)

    def get_moves_for_game(self, game_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM game_moves WHERE game_id = %s::uuid ORDER BY id", (game_id,))
            return [dict(r) for r in cur.fetchall()]

    def clear_moves(self, game_id: str) -> None:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM game_moves WHERE game_id = %s::uuid", (game_id,))
            conn.commit()
