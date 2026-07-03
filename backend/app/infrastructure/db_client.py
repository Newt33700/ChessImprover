"""Database client abstraction for Chess Improver (US 7).

In development / tests: uses an in-memory dict store.
In production: configure DATABASE_URL to point at Supabase/PostgreSQL.

The interface is intentionally synchronous and dict-based so tests
need no real database and the domain layer stays decoupled.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.tactical_elo import DEFAULT_TACTICAL_ELO
from app.domain.tactics import select_nearest_problem

# ---------------------------------------------------------------------------
# In-memory store (dev / test)
# ---------------------------------------------------------------------------

_users: Dict[str, Dict[str, Any]] = {}   # keyed by user_id
_user_data: Dict[str, Dict[str, Any]] = {}  # keyed by user_id

# EPIC 1 — analyse async
_games: Dict[str, Dict[str, Any]] = {}        # keyed by game_id
_game_moves: Dict[str, List[Dict[str, Any]]] = {}  # keyed by game_id

# US 5.1 — historisation de la progression
_progress_history: List[Dict[str, Any]] = []  # append-only

# Dépôt PostgreSQL construit paresseusement si DATABASE_URL est défini.
_pg_repo: Any = None


def _pg():
    """Renvoie le dépôt Postgres si ``DATABASE_URL`` est configuré, sinon ``None``.

    L'import de ``pg_repository`` (et donc de ``psycopg``) est différé pour ne
    pas exiger la dépendance dans les environnements 100 % in-memory.
    """
    from app.config import settings

    if not settings.database_url:
        return None
    global _pg_repo
    if _pg_repo is None:  # pragma: no cover - nécessite DATABASE_URL
        from app.infrastructure.pg_repository import PgRepository

        _pg_repo = PgRepository(settings.database_url)
    return _pg_repo


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    for user in _users.values():
        if user["email"].lower() == email.lower():
            return user
    return None


def find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    for user in _users.values():
        if user["username"].lower() == username.lower():
            return user
    return None


def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return _users.get(user_id)


def update_chess_username(user_id: str, chess_username: Optional[str]) -> Optional[Dict[str, Any]]:
    """US 6.3 — Met à jour (ou délie si None/vide) le pseudo Chess.com du profil."""
    user = _users.get(user_id)
    if user is None:
        return None
    user["chess_username"] = chess_username or None
    return user


def update_settings(user_id: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """EPIC 18 (US 18.2/18.3) — Remplace les préférences de personnalisation du profil.

    Comme ``update_chess_username``, reste 100% in-memory même si
    ``DATABASE_URL`` est configuré (les tables ``profiles``/``users`` ne sont
    pas encore migrées vers Postgres, gap documenté au README §10.1).
    """
    user = _users.get(user_id)
    if user is None:
        return None
    user["settings"] = dict(settings or {})
    return user


def create_user(email: str, username: str, password_hash: str) -> Dict[str, Any]:
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "username": username,
        "password_hash": password_hash,
        "chess_username": None,
        "settings": {},
        "tactical_elo": DEFAULT_TACTICAL_ELO,
        "endgame_elo": DEFAULT_TACTICAL_ELO,
    }
    _users[user_id] = user
    _user_data[user_id] = {"games": [], "srs_cards": []}
    return user


def get_tactical_elo(user_id: str) -> int:
    """US 8.1 — Elo tactique de l'utilisateur (1000 par défaut)."""
    user = _users.get(user_id)
    if user is None:
        return DEFAULT_TACTICAL_ELO
    return user.get("tactical_elo", DEFAULT_TACTICAL_ELO)


def update_tactical_elo(user_id: str, new_elo: int) -> Optional[Dict[str, Any]]:
    user = _users.get(user_id)
    if user is None:
        return None
    user["tactical_elo"] = new_elo
    return user


def get_endgame_elo(user_id: str) -> int:
    """EPIC 10 — Elo « finales » de l'utilisateur (1000 par défaut, distinct de l'Elo tactique)."""
    user = _users.get(user_id)
    if user is None:
        return DEFAULT_TACTICAL_ELO
    return user.get("endgame_elo", DEFAULT_TACTICAL_ELO)


def update_endgame_elo(user_id: str, new_elo: int) -> Optional[Dict[str, Any]]:
    user = _users.get(user_id)
    if user is None:
        return None
    user["endgame_elo"] = new_elo
    return user


def get_user_data(user_id: str) -> Dict[str, Any]:
    return _user_data.get(user_id, {"games": [], "srs_cards": []})


def upsert_user_data(user_id: str, games: List[Any], srs_cards: List[Any]) -> Dict[str, Any]:
    """Client Wins: merge by game_id/card_id, client data overwrites server data."""
    existing = _user_data.get(user_id, {"games": [], "srs_cards": []})

    # Index existing data by id
    games_map: Dict[str, Any] = {g["game_id"]: g for g in existing["games"] if "game_id" in g}
    cards_map: Dict[str, Any] = {c["id"]: c for c in existing["srs_cards"] if "id" in c}

    # Client wins: overwrite with client data
    for g in games:
        if "game_id" in g:
            games_map[g["game_id"]] = g
    for c in srs_cards:
        if "id" in c:
            cards_map[c["id"]] = c

    merged = {
        "games": sorted(games_map.values(), key=lambda x: x.get("date", ""), reverse=True),
        "srs_cards": list(cards_map.values()),
    }
    _user_data[user_id] = merged
    return merged


# ---------------------------------------------------------------------------
# Games & game_moves (EPIC 1)
# ---------------------------------------------------------------------------

def create_game(
    pgn: str,
    user_id: Optional[str] = None,
    time_control: Optional[str] = None,
    user_color: str = "white",
    status: str = "processing",
    pgn_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Crée une ligne `games` au statut initial et renvoie l'enregistrement."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.create_game(pgn, user_id, time_control, user_color, status, pgn_hash)

    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "user_id": user_id,
        "pgn": pgn,
        "time_control": time_control,
        "user_color": user_color,
        "result": None,
        "status": status,
        "pgn_hash": pgn_hash,
        "is_reviewed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _games[game_id] = game
    _game_moves[game_id] = []
    return game


def find_game_by_pgn_hash(user_id: Optional[str], pgn_hash: str) -> Optional[Dict[str, Any]]:
    """US 7.2 — Retrouve une partie déjà soumise par cet utilisateur pour ce PGN."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.find_game_by_pgn_hash(user_id, pgn_hash)
    for game in _games.values():
        if game.get("user_id") == user_id and game.get("pgn_hash") == pgn_hash:
            return game
    return None


def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_game(game_id)
    return _games.get(game_id)


def get_games_for_user(user_id: Optional[str]) -> List[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_games_for_user(user_id)
    return [g for g in _games.values() if g.get("user_id") == user_id]


# Colonnes modifiables de `games` : tout nom de champ hors de cette liste est
# rejeté AVANT de descendre vers la couche SQL (les noms de colonnes ne sont
# pas paramétrables dans une requête — seule une liste blanche protège
# l'interpolation faite par PgRepository.update_game).
GAME_UPDATABLE_FIELDS = frozenset(
    {"status", "result", "eco", "opening_name", "pivot_move_index", "is_reviewed"}
)

# Idem pour `tactical_sprints` (PgRepository.update_sprint).
SPRINT_UPDATABLE_FIELDS = frozenset(
    {"score", "problems_solved_count", "moves", "started_at", "finished_at", "duration_seconds"}
)


def _check_fields(fields: Dict[str, Any], allowed: frozenset) -> None:
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Champs non modifiables : {sorted(unknown)}")


def update_game(game_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    """Met à jour des champs d'une partie (liste blanche : ``GAME_UPDATABLE_FIELDS``)."""
    _check_fields(fields, GAME_UPDATABLE_FIELDS)
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.update_game(game_id, **fields)
    game = _games.get(game_id)
    if game is None:
        return None
    game.update(fields)
    return game


def bulk_insert_moves(game_id: str, moves: List[Dict[str, Any]]) -> int:
    """Insère en bloc les métriques par coup d'une partie. Renvoie le nombre inséré."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.bulk_insert_moves(game_id, moves)
    if game_id not in _game_moves:
        _game_moves[game_id] = []
    _game_moves[game_id].extend(moves)
    return len(moves)


def get_moves_for_game(game_id: str) -> List[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_moves_for_game(game_id)
    return list(_game_moves.get(game_id, []))


def clear_moves(game_id: str) -> None:
    """Purge les coups d'une partie (avant réanalyse)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        repo.clear_moves(game_id)
        return
    _game_moves[game_id] = []


def get_completed_games(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Parties analysées (status=completed), filtrées par utilisateur si fourni."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_completed_games(user_id)
    games = [g for g in _games.values() if g.get("status") == "completed"]
    if user_id is not None:
        games = [g for g in games if g.get("user_id") == user_id]
    return games


# ---------------------------------------------------------------------------
# Historisation de la progression (US 5.1)
# ---------------------------------------------------------------------------

def create_progress_snapshot(
    user_id: Optional[str],
    game_id: Optional[str],
    cadence: str,
    elos: Dict[str, int],
) -> Dict[str, Any]:
    """Enregistre un snapshot d'Elo virtuel après une analyse réussie."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.create_progress_snapshot(user_id, game_id, cadence, elos)

    record = {
        "id": len(_progress_history) + 1,
        "user_id": user_id,
        "game_id": game_id,
        "cadence": cadence,
        "elo_openings": elos["openings"],
        "elo_tactics": elos["tactics"],
        "elo_strategy": elos["strategy"],
        "elo_endgames": elos["endgames"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _progress_history.append(record)
    return record


def get_progress_history(user_id: Optional[str], cadence: str) -> List[Dict[str, Any]]:
    """Historique des snapshots d'une cadence, trié chronologiquement (asc)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_progress_history(user_id, cadence)

    rows = [
        r for r in _progress_history
        if r["cadence"] == cadence and (user_id is None or r["user_id"] == user_id)
    ]
    return sorted(rows, key=lambda r: r["recorded_at"])


# ---------------------------------------------------------------------------
# Problèmes tactiques (US 8.1, EPIC 8) — jeu de données de référence, non
# réinitialisé par _reset_store() (ce n'est pas une donnée utilisateur).
# Mêmes 15 problèmes que le seed SQL (migration games_epic8), vérifiés par
# python-chess (voir tests/test_db_tactics.py).
# ---------------------------------------------------------------------------

_TACTICAL_PROBLEMS_SEED = [
    {"fen": "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1", "solution": "Ra8#", "category": "mate_in_1", "difficulty_elo": 650},
    {"fen": "7k/6pp/8/8/8/8/8/R6K w - - 0 1", "solution": "Ra8#", "category": "mate_in_1", "difficulty_elo": 650},
    {"fen": "k7/8/1K6/8/8/8/8/7R w - - 0 1", "solution": "Rh8#", "category": "mate_in_1", "difficulty_elo": 700},
    {"fen": "3r2k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1", "solution": "Rd1#", "category": "mate_in_1", "difficulty_elo": 750},
    {"fen": "6k1/4Rppp/8/8/8/8/6PP/6K1 w - - 0 1", "solution": "Re8#", "category": "mate_in_1", "difficulty_elo": 700},
    {"fen": "k1K5/8/8/8/8/8/8/6R1 w - - 0 1", "solution": "Ra1#", "category": "mate_in_1", "difficulty_elo": 800},
    {"fen": "4k3/8/8/3q4/8/8/3R4/4K3 w - - 0 1", "solution": "Rxd5", "category": "hanging_piece", "difficulty_elo": 900},
    {"fen": "4k3/8/8/4q3/8/8/4R3/4K3 w - - 0 1", "solution": "Rxe5+", "category": "hanging_piece", "difficulty_elo": 950},
    {"fen": "4k3/8/2n5/8/8/8/2R5/4K3 w - - 0 1", "solution": "Rxc6", "category": "hanging_piece", "difficulty_elo": 850},
    {"fen": "4k3/8/8/8/4n3/8/4Q3/4K3 w - - 0 1", "solution": "Qxe4+", "category": "hanging_piece", "difficulty_elo": 1000},
    {"fen": "8/8/8/8/8/8/8/k1KQ4 w - - 0 1", "solution": "Qd4+", "category": "mate_in_2", "difficulty_elo": 1250},
    {"fen": "8/8/8/8/8/8/8/k1K1Q3 w - - 0 1", "solution": "Qe5+", "category": "mate_in_2", "difficulty_elo": 1300},
    {"fen": "8/8/8/8/8/8/8/k1K1Q3 w - - 0 1", "solution": "Qc3+", "category": "mate_in_2", "difficulty_elo": 1300},
    {"fen": "8/8/8/8/8/8/8/k1K2Q2 w - - 0 1", "solution": "Qf6+", "category": "mate_in_2", "difficulty_elo": 1350},
    {"fen": "8/8/8/8/8/8/8/k1K2Q2 w - - 0 1", "solution": "Kc2+", "category": "mate_in_2", "difficulty_elo": 1400},
]

_tactical_problems: Dict[str, Dict[str, Any]] = {}
for _seed in _TACTICAL_PROBLEMS_SEED:
    _pid = str(uuid.uuid4())
    _tactical_problems[_pid] = {"id": _pid, **_seed}
del _seed, _pid


def get_tactical_problem(problem_id: str) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:
        # EPIC 22 (US 22.2) : le dépôt Postgres peut être incomplet (méthode
        # jamais migrée, cf. README §10.6) ou la table vide — on retombe sur
        # le seed in-memory plutôt que de faire crasher la route en 500.
        try:
            problem = repo.get_tactical_problem(problem_id)
        except Exception:  # pragma: no cover - dépend de l'état du déploiement
            problem = None
        if problem is not None:  # pragma: no cover - nécessite DATABASE_URL
            return problem
    return _tactical_problems.get(problem_id)


def get_next_tactical_problem(
    tactical_elo: int, category: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """US 8.1 — Problème le plus proche de l'Elo tactique du joueur.

    ``category`` (US 8.2) filtre le jeu de problèmes avant sélection ;
    ``None`` (par défaut) considère toutes les catégories.

    EPIC 22 (US 22.2) — Fallback anti-« Impossible de charger » : si le dépôt
    Postgres échoue (méthode non migrée, table vide, erreur SQL), on sert le
    set de problèmes par défaut in-memory ; et si le filtre de catégorie vide
    le pool, on élargit à toutes les catégories plutôt que de renvoyer None
    (donc 404 côté route, qui figeait l'interface).
    """
    repo = _pg()
    if repo is not None:
        try:
            problem = repo.get_next_tactical_problem(tactical_elo, category)
        except Exception:  # pragma: no cover - dépend de l'état du déploiement
            problem = None
        if problem is not None:  # pragma: no cover - nécessite DATABASE_URL
            return problem
    pool = list(_tactical_problems.values())
    if category is not None:
        filtered = [p for p in pool if p["category"] == category]
        pool = filtered or pool  # élargissement : jamais de pool vide
    return select_nearest_problem(pool, tactical_elo)


# ---------------------------------------------------------------------------
# EPIC 10 — Entraîneur de Finales Essentielles (fonctionnalité bonus)
#
# Même structure que le seed tactique ci-dessus, thème distinct (technique de
# mat Roi+Dame/Roi+Tour/Roi+2 Tours). Volontairement 100 % in-memory, sans
# tentative de délégation Postgres : évite de reproduire le piège de
# US 8.1 (tactical_problems délègue à des méthodes PgRepository jamais
# écrites, cf. §10.6 du README) pour une table qui n'est de toute façon
# testée qu'en local dans cet environnement.
# ---------------------------------------------------------------------------

_ENDGAME_PROBLEMS_SEED = [
    {"fen": "8/8/8/8/8/8/8/k1KQ4 w - - 0 1", "solution": "Qa4#", "category": "queen_mate", "difficulty_elo": 700},
    {"fen": "7k/8/5K2/8/8/8/8/6Q1 w - - 0 1", "solution": "Qg7#", "category": "queen_mate", "difficulty_elo": 750},
    {"fen": "k7/8/K7/8/8/8/8/Q7 w - - 0 1", "solution": "Qh8#", "category": "queen_mate", "difficulty_elo": 700},
    {"fen": "8/8/8/8/8/R7/8/5K1k w - - 0 1", "solution": "Rh3#", "category": "rook_mate", "difficulty_elo": 850},
    {"fen": "k7/8/K7/8/8/8/8/2R5 w - - 0 1", "solution": "Rc8#", "category": "rook_mate", "difficulty_elo": 850},
    {"fen": "7k/8/6K1/8/8/8/8/R7 w - - 0 1", "solution": "Ra8#", "category": "rook_mate", "difficulty_elo": 900},
    {"fen": "k7/8/8/8/8/8/1R6/KR6 w - - 0 1", "solution": "Ra2#", "category": "two_rooks_mate", "difficulty_elo": 950},
    {"fen": "7k/8/8/8/8/8/6R1/KR6 w - - 0 1", "solution": "Rh1#", "category": "two_rooks_mate", "difficulty_elo": 1000},
    {"fen": "8/8/8/8/8/1R6/8/k1KR4 w - - 0 1", "solution": "Ra3#", "category": "two_rooks_mate", "difficulty_elo": 1000},
]

_endgame_problems: Dict[str, Dict[str, Any]] = {}
for _seed in _ENDGAME_PROBLEMS_SEED:
    _pid = str(uuid.uuid4())
    _endgame_problems[_pid] = {"id": _pid, **_seed}
del _seed, _pid


def get_endgame_problem(problem_id: str) -> Optional[Dict[str, Any]]:
    return _endgame_problems.get(problem_id)


def get_next_endgame_problem(
    endgame_elo: int, category: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """EPIC 10 — Position la plus proche de l'Elo « finales » du joueur.

    Réutilise directement `select_nearest_problem` (US 8.1) — même logique
    de sélection adaptative, aucune duplication. Comme pour les tactiques
    (US 22.2), un filtre de catégorie qui vide le pool est élargi à toutes
    les catégories plutôt que de renvoyer None (404 → interface figée).
    """
    pool = list(_endgame_problems.values())
    if category is not None:
        filtered = [p for p in pool if p["category"] == category]
        pool = filtered or pool
    return select_nearest_problem(pool, endgame_elo)


# US 8.4 — historique des tentatives, append-only
_tactical_attempts: List[Dict[str, Any]] = []


def record_tactical_attempt(
    user_id: str,
    problem_id: str,
    category: str,
    success: bool,
    time_taken: float,
) -> Dict[str, Any]:
    """Enregistre une tentative résolue (US 8.4), pour le calcul du taux de
    réussite par catégorie et de la série en cours (streak)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.record_tactical_attempt(user_id, problem_id, category, success, time_taken)
    attempt = {
        "attempt_id": str(uuid.uuid4()),
        "user_id": user_id,
        "problem_id": problem_id,
        "category": category,
        "success": success,
        "time_taken": time_taken,
        "created_at": datetime.now(timezone.utc),
    }
    _tactical_attempts.append(attempt)
    return attempt


def get_tactical_attempts(user_id: str) -> List[Dict[str, Any]]:
    """Historique des tentatives d'un utilisateur (US 8.4), du plus ancien au plus récent."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_tactical_attempts(user_id)
    return [a for a in _tactical_attempts if a["user_id"] == user_id]


# EPIC 9 — répertoire d'ouvertures (US 9.1/9.2)
_opening_lines: Dict[str, Dict[str, Any]] = {}  # keyed by line id


def create_opening_line(user_id: str, name: str, color: str, moves: List[str]) -> Dict[str, Any]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.create_opening_line(user_id, name, color, moves)
    from app.domain.opening_repertoire import DEFAULT_EASE_FACTOR, DEFAULT_INTERVAL_DAYS

    line_id = str(uuid.uuid4())
    line = {
        "id": line_id,
        "user_id": user_id,
        "name": name,
        "color": color,
        "moves": list(moves),
        "ease_factor": DEFAULT_EASE_FACTOR,
        "interval_days": DEFAULT_INTERVAL_DAYS,
        "repetitions": 0,
        "due_date": datetime.now(timezone.utc).date().isoformat(),
    }
    _opening_lines[line_id] = line
    return line


def get_opening_lines(user_id: str) -> List[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_opening_lines(user_id)
    return [line for line in _opening_lines.values() if line["user_id"] == user_id]


def get_due_opening_lines(user_id: str, today: str) -> List[Dict[str, Any]]:
    """Lignes dont l'échéance de révision (US 9.2) est arrivée ou dépassée."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_due_opening_lines(user_id, today)
    return [
        line for line in _opening_lines.values()
        if line["user_id"] == user_id and line["due_date"] <= today
    ]


def get_opening_line(line_id: str) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_opening_line(line_id)
    return _opening_lines.get(line_id)


def update_opening_line_schedule(
    line_id: str, ease_factor: float, interval_days: int, repetitions: int, due_date: str
) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.update_opening_line_schedule(
            line_id, ease_factor, interval_days, repetitions, due_date
        )
    line = _opening_lines.get(line_id)
    if line is None:
        return None
    line["ease_factor"] = ease_factor
    line["interval_days"] = interval_days
    line["repetitions"] = repetitions
    line["due_date"] = due_date
    return line


def delete_opening_line(line_id: str, user_id: str) -> bool:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.delete_opening_line(line_id, user_id)
    line = _opening_lines.get(line_id)
    if line is None or line["user_id"] != user_id:
        return False
    del _opening_lines[line_id]
    return True


# ---------------------------------------------------------------------------
# EPIC 11 — Profils d'erreur comportementale (US 9.1/9.2)
# ---------------------------------------------------------------------------

_error_profiles: Dict[str, Dict[str, Dict[str, Any]]] = {}  # user_id -> error_type -> profile


def get_error_profile(user_id: str, error_type: str) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_error_profile(user_id, error_type)
    return _error_profiles.get(user_id, {}).get(error_type)


def get_error_profiles(user_id: str) -> List[Dict[str, Any]]:
    """Tous les profils d'erreur de l'utilisateur (un par type observé au moins une fois)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_error_profiles(user_id)
    return list(_error_profiles.get(user_id, {}).values())


def upsert_error_profile(
    user_id: str, error_type: str, frequency_score: float, last_observed: str
) -> Dict[str, Any]:
    """Crée ou met à jour le score de fréquence d'un type d'erreur (1 ligne par
    couple user_id/error_type, cf. contrainte UNIQUE de la migration)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.upsert_error_profile(user_id, error_type, frequency_score, last_observed)
    profile = {
        "user_id": user_id,
        "error_type": error_type,
        "frequency_score": frequency_score,
        "last_observed": last_observed,
    }
    _error_profiles.setdefault(user_id, {})[error_type] = profile
    return profile


def get_next_tactical_problem_for_categories(
    tactical_elo: int, categories: List[str]
) -> Optional[Dict[str, Any]]:
    """EPIC 11 — variante multi-catégories de `get_next_tactical_problem`.

    Sert l'entraînement personnalisé (US 9.2) quand un type d'erreur pointe
    vers plusieurs thèmes tactiques (ex. `missed_mate` -> mate_in_1 +
    mate_in_2). Réutilise directement `select_nearest_problem` (US 8.1),
    aucune duplication de la logique de sélection adaptative.

    EPIC 22 (US 22.2) : même fallback anti-404 que `get_next_tactical_problem`
    — un dépôt Postgres défaillant ou vide retombe sur le seed in-memory, et
    un pool vide est élargi à toutes les catégories.
    """
    repo = _pg()
    if repo is not None:
        pool = []
        try:
            for cat in categories:
                problem = repo.get_next_tactical_problem(tactical_elo, cat)
                if problem is not None:
                    pool.append(problem)
        except Exception:  # pragma: no cover - dépend de l'état du déploiement
            pool = []
        if pool:  # pragma: no cover - nécessite DATABASE_URL, cf. gap §10.6
            return select_nearest_problem(pool, tactical_elo)
    pool = [p for p in _tactical_problems.values() if p["category"] in categories]
    if not pool:
        pool = list(_tactical_problems.values())  # élargissement (US 22.2)
    return select_nearest_problem(pool, tactical_elo)


# ---------------------------------------------------------------------------
# EPIC 12 — Mode "Tactical Sprint" (US 11.1/11.2)
# ---------------------------------------------------------------------------

_tactical_sprints: Dict[str, Dict[str, Any]] = {}  # keyed by sprint_id


def create_sprint(user_id: str) -> Dict[str, Any]:
    """Démarre un sprint — `started_at` fixé côté serveur (chrono anti-triche)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.create_sprint(user_id)
    sprint_id = str(uuid.uuid4())
    sprint = {
        "id": sprint_id,
        "user_id": user_id,
        "score": 0,
        "problems_solved_count": 0,
        "duration_seconds": 0,
        "moves": [],
        "started_at": datetime.now(timezone.utc),
        "finished_at": None,
    }
    _tactical_sprints[sprint_id] = sprint
    return sprint


def get_sprint(sprint_id: str) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_sprint(sprint_id)
    return _tactical_sprints.get(sprint_id)


def update_sprint(sprint_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    _check_fields(fields, SPRINT_UPDATABLE_FIELDS)
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.update_sprint(sprint_id, **fields)
    sprint = _tactical_sprints.get(sprint_id)
    if sprint is None:
        return None
    sprint.update(fields)
    return sprint


def get_best_sprint() -> Optional[Dict[str, Any]]:
    """Meilleur sprint **terminé**, toutes utilisateurs confondus (mode Ghost, US 11.2)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_best_sprint()
    finished = [s for s in _tactical_sprints.values() if s.get("finished_at") is not None]
    if not finished:
        return None
    return max(finished, key=lambda s: s["score"])



# ---------------------------------------------------------------------------
# EPIC 20 — Flashcards SRS auto-générées (US 20.1/20.2)
# ---------------------------------------------------------------------------

_srs_flashcards: Dict[str, Dict[str, Any]] = {}  # keyed by card id


def create_flashcard(user_id: str, game_id: Optional[str], fen: str, solution: str) -> Dict[str, Any]:
    """Crée une flashcard au calendrier SM-2 initial (US 20.1)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.create_flashcard(user_id, game_id, fen, solution)
    from app.domain.srs_flashcards import DEFAULT_EASE_FACTOR, DEFAULT_INTERVAL_DAYS

    card_id = str(uuid.uuid4())
    card = {
        "id": card_id,
        "user_id": user_id,
        "game_id": game_id,
        "fen": fen,
        "solution": solution,
        "ease_factor": DEFAULT_EASE_FACTOR,
        "interval_days": DEFAULT_INTERVAL_DAYS,
        "repetitions": 0,
        "due_date": datetime.now(timezone.utc).date().isoformat(),
    }
    _srs_flashcards[card_id] = card
    return card


def get_flashcards(user_id: str) -> List[Dict[str, Any]]:
    """Toutes les flashcards de l'utilisateur (le « Cimetière des Erreurs »)."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_flashcards(user_id)
    return [c for c in _srs_flashcards.values() if c["user_id"] == user_id]


def get_flashcard(card_id: str) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_flashcard(card_id)
    return _srs_flashcards.get(card_id)


def get_due_flashcards(user_id: str, today: str) -> List[Dict[str, Any]]:
    """Flashcards dont l'échéance de révision (US 20.2, Recall Training) est atteinte."""
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.get_due_flashcards(user_id, today)
    return [
        c for c in _srs_flashcards.values()
        if c["user_id"] == user_id and c["due_date"] <= today
    ]


def update_flashcard_schedule(
    card_id: str, ease_factor: float, interval_days: int, repetitions: int, due_date: str
) -> Optional[Dict[str, Any]]:
    repo = _pg()
    if repo is not None:  # pragma: no cover - nécessite DATABASE_URL
        return repo.update_flashcard_schedule(card_id, ease_factor, interval_days, repetitions, due_date)
    card = _srs_flashcards.get(card_id)
    if card is None:
        return None
    card["ease_factor"] = ease_factor
    card["interval_days"] = interval_days
    card["repetitions"] = repetitions
    card["due_date"] = due_date
    return card


def _reset_store() -> None:
    """Reset in-memory store between tests."""
    _users.clear()
    _user_data.clear()
    _games.clear()
    _game_moves.clear()
    _progress_history.clear()
    _tactical_attempts.clear()
    _opening_lines.clear()
    _error_profiles.clear()
    _tactical_sprints.clear()
    _srs_flashcards.clear()
