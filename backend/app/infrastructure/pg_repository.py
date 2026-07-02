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
        """Convertit tout champ de type date/heure (ex. ``created_at``,
        ``recorded_at``) en chaîne ISO 8601, pour une sérialisation JSON directe.
        """
        for key, value in row.items():
            if value is not None and hasattr(value, "isoformat"):
                row[key] = value.isoformat()
        return row

    # -- games ---------------------------------------------------------------

    def create_game(
        self,
        pgn: str,
        user_id: Optional[str] = None,
        time_control: Optional[str] = None,
        user_color: str = "white",
        status: str = "processing",
        pgn_hash: Optional[str] = None,
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO games (user_id, pgn, time_control, user_color, status, pgn_hash) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, pgn, time_control, user_color, status, pgn_hash))
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

    def find_game_by_pgn_hash(
        self, user_id: Optional[str], pgn_hash: str
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = "SELECT * FROM games WHERE user_id = %s::uuid AND pgn_hash = %s"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, pgn_hash))
            row = cur.fetchone()
        return self._iso(dict(row)) if row else None

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
        # EPIC 14 (US 14.1/14.2) : alerte vocale contextuelle, optionnelle.
        "alert_severity", "alert_text", "tts_text",
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

    # -- user_progress_history (US 5.1) --------------------------------------

    def create_progress_snapshot(
        self,
        user_id: Optional[str],
        game_id: Optional[str],
        cadence: str,
        elos: Dict[str, int],
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO user_progress_history "
            "(user_id, game_id, cadence, elo_openings, elo_tactics, "
            "elo_strategy, elo_endgames) "
            "VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s) RETURNING *"
        )
        params = (
            user_id, game_id, cadence,
            elos["openings"], elos["tactics"], elos["strategy"], elos["endgames"],
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            conn.commit()
        return self._iso(dict(row))

    def get_progress_history(
        self, user_id: Optional[str], cadence: str
    ) -> List[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        # Même précaution que get_completed_games : pas de paramètre "IS NULL"
        # non typé, cast ::uuid explicite sur la colonne UUID.
        if user_id is None:
            sql = "SELECT * FROM user_progress_history WHERE cadence = %s ORDER BY recorded_at ASC"
            params: tuple = (cadence,)
        else:
            sql = (
                "SELECT * FROM user_progress_history "
                "WHERE cadence = %s AND user_id = %s::uuid ORDER BY recorded_at ASC"
            )
            params = (cadence, user_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return [self._iso(dict(r)) for r in cur.fetchall()]

    # -- tactical_attempts (US 8.4) -------------------------------------------

    def record_tactical_attempt(
        self,
        user_id: str,
        problem_id: str,
        category: str,
        success: bool,
        time_taken: float,
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO tactical_attempts "
            "(user_id, problem_id, success, time_taken) "
            "VALUES (%s::uuid, %s::uuid, %s, %s) RETURNING *"
        )
        params = (user_id, problem_id, success, time_taken)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            row = dict(cur.fetchone())
            conn.commit()
        row["category"] = category
        return self._iso(row)

    def get_tactical_attempts(self, user_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
        sql = (
            "SELECT a.*, p.category FROM tactical_attempts a "
            "JOIN tactical_problems p ON p.id = a.problem_id "
            "WHERE a.user_id = %s::uuid ORDER BY a.created_at ASC"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return [self._iso(dict(r)) for r in cur.fetchall()]

    # -- opening_repertoire (EPIC 9) -------------------------------------------

    @staticmethod
    def _line_row(row: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(row)
        row["name"] = row.pop("line_name")
        return row

    def create_opening_line(
        self, user_id: str, name: str, color: str, moves: List[str]
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        from psycopg.types.json import Json

        sql = (
            "INSERT INTO opening_repertoire (user_id, line_name, color, moves) "
            "VALUES (%s::uuid, %s, %s, %s) RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, name, color, Json(moves)))
            row = dict(cur.fetchone())
            conn.commit()
        return self._iso(self._line_row(row))

    def get_opening_lines(self, user_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
        sql = "SELECT * FROM opening_repertoire WHERE user_id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return [self._iso(self._line_row(r)) for r in cur.fetchall()]

    def get_opening_line(self, line_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        sql = "SELECT * FROM opening_repertoire WHERE id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (line_id,))
            row = cur.fetchone()
            return self._iso(self._line_row(dict(row))) if row else None

    def get_due_opening_lines(
        self, user_id: str, today: str
    ) -> List[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "SELECT * FROM opening_repertoire "
            "WHERE user_id = %s::uuid AND due_date <= %s::date"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, today))
            return [self._iso(self._line_row(r)) for r in cur.fetchall()]

    def update_opening_line_schedule(
        self, line_id: str, ease_factor: float, interval_days: int, repetitions: int, due_date: str
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "UPDATE opening_repertoire SET ease_factor = %s, interval_days = %s, "
            "repetitions = %s, due_date = %s::date WHERE id = %s::uuid RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (ease_factor, interval_days, repetitions, due_date, line_id))
            row = cur.fetchone()
            conn.commit()
            return self._iso(self._line_row(dict(row))) if row else None

    def delete_opening_line(self, line_id: str, user_id: str) -> bool:  # pragma: no cover
        sql = "DELETE FROM opening_repertoire WHERE id = %s::uuid AND user_id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (line_id, user_id))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted

    # -- EPIC 11 : profils d'erreur comportementale (US 9.1/9.2) -------------

    def get_error_profile(
        self, user_id: str, error_type: str
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "SELECT * FROM user_error_profiles "
            "WHERE user_id = %s::uuid AND error_type = %s"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, error_type))
            row = cur.fetchone()
            return self._iso(dict(row)) if row else None

    def get_error_profiles(self, user_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
        sql = "SELECT * FROM user_error_profiles WHERE user_id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return [self._iso(dict(r)) for r in cur.fetchall()]

    def upsert_error_profile(
        self, user_id: str, error_type: str, frequency_score: float, last_observed: str
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO user_error_profiles (user_id, error_type, frequency_score, last_observed) "
            "VALUES (%s::uuid, %s, %s, %s::timestamptz) "
            "ON CONFLICT (user_id, error_type) "
            "DO UPDATE SET frequency_score = EXCLUDED.frequency_score, "
            "last_observed = EXCLUDED.last_observed "
            "RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, error_type, frequency_score, last_observed))
            row = dict(cur.fetchone())
            conn.commit()
        return self._iso(row)

    # -- EPIC 12 : mode Tactical Sprint (US 11.1/11.2) ------------------------

    def create_sprint(self, user_id: str) -> Dict[str, Any]:  # pragma: no cover
        sql = "INSERT INTO tactical_sprints (user_id) VALUES (%s::uuid) RETURNING *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = dict(cur.fetchone())
            conn.commit()
        return self._iso(row)

    def get_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        sql = "SELECT * FROM tactical_sprints WHERE id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (sprint_id,))
            row = cur.fetchone()
            return self._iso(dict(row)) if row else None

    def update_sprint(
        self, sprint_id: str, **fields: Any
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        from psycopg.types.json import Json

        columns = list(fields.keys())
        values = [Json(v) if k == "moves" else v for k, v in fields.items()]
        set_clause = ", ".join(f"{c} = %s" for c in columns)
        sql = f"UPDATE tactical_sprints SET {set_clause} WHERE id = %s::uuid RETURNING *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (*values, sprint_id))
            row = cur.fetchone()
            conn.commit()
            return self._iso(dict(row)) if row else None

    def get_best_sprint(self) -> Optional[Dict[str, Any]]:  # pragma: no cover
        sql = (
            "SELECT * FROM tactical_sprints WHERE finished_at IS NOT NULL "
            "ORDER BY score DESC LIMIT 1"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            return self._iso(dict(row)) if row else None
