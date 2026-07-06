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

    # Listes blanches de colonnes : les noms de colonnes ne peuvent pas être
    # passés en paramètres SQL, ils sont interpolés dans la requête — seule une
    # liste fermée empêche toute injection via un nom de champ. Doit rester
    # alignée avec GAME_UPDATABLE_FIELDS / SPRINT_UPDATABLE_FIELDS (db_client).
    _GAME_COLS = frozenset(
        {
            "status", "result", "eco", "opening_name", "pivot_move_index", "is_reviewed",
            # EPIC 28 (US 28.1) : progression coup-par-coup (Smart Loader).
            "progress_current", "progress_total",
        }
    )
    _SPRINT_COLS = frozenset(
        {"score", "problems_solved_count", "moves", "started_at", "finished_at", "duration_seconds"}
    )

    @staticmethod
    def _check_cols(fields: Dict[str, Any], allowed: frozenset) -> None:
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Colonnes non modifiables : {sorted(unknown)}")

    def update_game(self, game_id: str, **fields: Any) -> Optional[Dict[str, Any]]:  # pragma: no cover
        if not fields:
            return self.get_game(game_id)
        self._check_cols(fields, self._GAME_COLS)
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
        "fen", "best_move_san", "time_spent_seconds",
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

    def get_sprints_for_user(self, user_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
        """EPIC 29 (US 29.2) — Sprints de l'utilisateur (quête quotidienne)."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM tactical_sprints WHERE user_id = %s::uuid", (user_id,))
            return [self._iso(dict(r)) for r in cur.fetchall()]

    def update_sprint(
        self, sprint_id: str, **fields: Any
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        from psycopg.types.json import Json

        self._check_cols(fields, self._SPRINT_COLS)
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

    # -- EPIC 20 : flashcards SRS auto-générées (US 20.1/20.2) ----------------

    def create_flashcard(
        self, user_id: str, game_id: Optional[str], fen: str, solution: str
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO srs_flashcards (user_id, game_id, fen, solution) "
            "VALUES (%s::uuid, %s::uuid, %s, %s) RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, game_id, fen, solution))
            row = cur.fetchone()
            conn.commit()
        return self._iso(dict(row))

    def get_flashcards(self, user_id: str) -> List[Dict[str, Any]]:  # pragma: no cover
        sql = "SELECT * FROM srs_flashcards WHERE user_id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return [self._iso(dict(r)) for r in cur.fetchall()]

    def get_flashcard(self, card_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        sql = "SELECT * FROM srs_flashcards WHERE id = %s::uuid"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (card_id,))
            row = cur.fetchone()
            return self._iso(dict(row)) if row else None

    def get_due_flashcards(
        self, user_id: str, today: str
    ) -> List[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "SELECT * FROM srs_flashcards "
            "WHERE user_id = %s::uuid AND due_date <= %s::date"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, today))
            return [self._iso(dict(r)) for r in cur.fetchall()]

    def update_flashcard_schedule(
        self, card_id: str, ease_factor: float, interval_days: int, repetitions: int, due_date: str
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "UPDATE srs_flashcards SET ease_factor = %s, interval_days = %s, "
            "repetitions = %s, due_date = %s::date WHERE id = %s::uuid RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (ease_factor, interval_days, repetitions, due_date, card_id))
            row = cur.fetchone()
            conn.commit()
            return self._iso(dict(row)) if row else None

    # -- EPIC 25 : profils utilisateurs & user_data (US 7, gap §10.1 fermé) ----
    #
    # Les comptes vivaient jusqu'ici en mémoire (perdus à chaque redéploiement
    # Render). Ces méthodes branchent enfin les tables `profiles`/`user_data`
    # de la migration initiale (init_auth.sql) — mêmes structures de dict que
    # le store in-memory de db_client, pour une délégation transparente.

    @staticmethod
    def _user_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:  # pragma: no cover
        """Normalise une ligne `profiles` vers le dict user du produit :
        UUID → str, settings JSONB absent → {}, dates → ISO."""
        if row is None:
            return None
        user = dict(row)
        user["id"] = str(user["id"])
        user["settings"] = user.get("settings") or {}
        return PgRepository._iso(user)

    def create_user(
        self, email: str, username: str, password_hash: str
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        sql = (
            "INSERT INTO profiles (email, username, password_hash) "
            "VALUES (%s, %s, %s) RETURNING *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (email, username, password_hash))
            row = dict(cur.fetchone())
            conn.commit()
        return self._user_row(row)

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM profiles WHERE LOWER(email) = LOWER(%s)", (email,))
            row = cur.fetchone()
        return self._user_row(dict(row) if row else None)

    def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM profiles WHERE LOWER(username) = LOWER(%s)", (username,))
            row = cur.fetchone()
        return self._user_row(dict(row) if row else None)

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM profiles WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        return self._user_row(dict(row) if row else None)

    def update_chess_username(
        self, user_id: str, chess_username: Optional[str]
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = "UPDATE profiles SET chess_username = %s WHERE id = %s::uuid RETURNING *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (chess_username or None, user_id))
            row = cur.fetchone()
            conn.commit()
        return self._user_row(dict(row) if row else None)

    def update_settings(
        self, user_id: str, settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        import json

        sql = "UPDATE profiles SET settings = %s::jsonb WHERE id = %s::uuid RETURNING *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (json.dumps(dict(settings or {})), user_id))
            row = cur.fetchone()
            conn.commit()
        return self._user_row(dict(row) if row else None)

    def get_user_elo(self, user_id: str, column: str) -> Optional[int]:  # pragma: no cover
        """Elo tactique ou finales du profil. ``column`` est validé contre une
        liste blanche (nom de colonne non paramétrable en SQL)."""
        if column not in ("tactical_elo", "endgame_elo"):
            raise ValueError(f"Colonne d'Elo inconnue : {column!r}")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {column} FROM profiles WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        return row[column] if row else None

    def update_user_elo(
        self, user_id: str, column: str, new_elo: int
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        if column not in ("tactical_elo", "endgame_elo"):
            raise ValueError(f"Colonne d'Elo inconnue : {column!r}")
        sql = f"UPDATE profiles SET {column} = %s WHERE id = %s::uuid RETURNING *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (new_elo, user_id))
            row = cur.fetchone()
            conn.commit()
        return self._user_row(dict(row) if row else None)

    def get_user_xp(self, user_id: str) -> Optional[Dict[str, int]]:  # pragma: no cover
        """EPIC 29 (US 29.1) : XP/niveau authoritatifs du profil."""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT xp, level FROM profiles WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        return {"xp": row["xp"], "level": row["level"]} if row else None

    def update_user_xp(
        self, user_id: str, xp: int, level: int
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        sql = "UPDATE profiles SET xp = %s, level = %s WHERE id = %s::uuid RETURNING *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (xp, level, user_id))
            row = cur.fetchone()
            conn.commit()
        return self._user_row(dict(row) if row else None)

    def get_user_data(self, user_id: str) -> Dict[str, Any]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT games, srs_cards FROM user_data WHERE user_id = %s::uuid", (user_id,)
            )
            row = cur.fetchone()
        if row is None:
            return {"games": [], "srs_cards": []}
        return {"games": row["games"] or [], "srs_cards": row["srs_cards"] or []}

    def save_user_data(
        self, user_id: str, games: List[Any], srs_cards: List[Any]
    ) -> Dict[str, Any]:  # pragma: no cover - nécessite une base réelle
        """Écrit l'état FUSIONNÉ (la fusion « client wins » est faite par
        db_client._merge_user_data, partagée avec le store in-memory)."""
        import json

        sql = (
            "INSERT INTO user_data (user_id, games, srs_cards) "
            "VALUES (%s::uuid, %s::jsonb, %s::jsonb) "
            "ON CONFLICT (user_id) DO UPDATE "
            "SET games = EXCLUDED.games, srs_cards = EXCLUDED.srs_cards "
            "RETURNING games, srs_cards"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, json.dumps(games), json.dumps(srs_cards)))
            row = dict(cur.fetchone())
            conn.commit()
        return {"games": row["games"] or [], "srs_cards": row["srs_cards"] or []}

    # -- EPIC 25 : problèmes tactiques (gap US 8.1 / §10.6 fermé) --------------

    def get_tactical_problem(self, problem_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM tactical_problems WHERE id = %s::uuid", (problem_id,))
            row = cur.fetchone()
        if row is None:
            return None
        row = dict(row)
        row["id"] = str(row["id"])
        return self._iso(row)

    def get_next_tactical_problem(
        self, tactical_elo: int, category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        """Problème le plus proche de l'Elo demandé (US 8.1) — tirage aléatoire
        parmi les équidistants, comme `domain.tactics.select_nearest_problem`."""
        if category is not None:
            sql = (
                "SELECT * FROM tactical_problems WHERE category = %s "
                "ORDER BY ABS(difficulty_elo - %s), random() LIMIT 1"
            )
            params = (category, tactical_elo)
        else:
            sql = (
                "SELECT * FROM tactical_problems "
                "ORDER BY ABS(difficulty_elo - %s), random() LIMIT 1"
            )
            params = (tactical_elo,)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        if row is None:
            return None
        row = dict(row)
        row["id"] = str(row["id"])
        return self._iso(row)

    # -- lichess_puzzles (EPIC 37 — Moteur de Puzzles) -----------------------
    #
    # `lichess_puzzles` compte des millions de lignes (dump complet ingéré) :
    # contrairement à `tactical_problems` ci-dessus, `ORDER BY random()` y
    # forcerait un tri complet de la table à chaque appel — interdit par la
    # spec. La sélection aléatoire se fait donc en deux requêtes bornées par
    # index (`idx_lichess_puzzles_rating` / GIN `idx_lichess_puzzles_themes`) :
    # un COUNT filtré, puis un SELECT ... LIMIT/OFFSET à un décalage tiré côté
    # Python (cf. `domain.lichess_puzzles.resolve_random_puzzles`).

    @staticmethod
    def _puzzle_filter_sql(theme: Optional[str]) -> "tuple[str, tuple]":
        """Clause ``WHERE`` commune à ``count_puzzles``/``get_random_puzzles``."""
        if theme is not None:
            return "WHERE rating BETWEEN %s AND %s AND themes @> ARRAY[%s]", (theme,)
        return "WHERE rating BETWEEN %s AND %s", ()

    def count_puzzles(
        self, rating_min: int, rating_max: int, theme: Optional[str] = None
    ) -> int:  # pragma: no cover - nécessite une base réelle
        where_sql, extra_params = self._puzzle_filter_sql(theme)
        sql = f"SELECT COUNT(*) AS count FROM lichess_puzzles {where_sql}"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (rating_min, rating_max) + extra_params)
            row = cur.fetchone()
        return int(row["count"])

    def get_random_puzzles(
        self,
        rating_min: int,
        rating_max: int,
        theme: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:  # pragma: no cover - nécessite une base réelle
        """``limit`` lignes à partir de ``offset`` (déjà tiré aléatoirement par
        l'appelant) — jamais de tri sur la table entière."""
        where_sql, extra_params = self._puzzle_filter_sql(theme)
        sql = (
            f"SELECT * FROM lichess_puzzles {where_sql} "
            "ORDER BY puzzle_id LIMIT %s OFFSET %s"
        )
        params = (rating_min, rating_max) + extra_params + (limit, offset)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
