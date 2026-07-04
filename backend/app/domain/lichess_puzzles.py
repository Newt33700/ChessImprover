"""Puzzles Lichess (EPIC 34) — parsing pur de la réponse de l'API Puzzle.

Le pool statique de problèmes tactiques (``db_client._TACTICAL_PROBLEMS_SEED``)
ne compte que 5-6 positions par catégorie : avec un Elo tactique qui bouge peu
d'une session à l'autre, ``select_nearest_problem`` retombe presque toujours
sur le même unique problème le plus proche — d'où le « toujours le même
exercice » signalé par les utilisateurs. L'API Puzzle Lichess (des millions de
positions, déjà vérifiées, filtrables par thème) devient la source PRIMAIRE ;
le seed local reste un repli si Lichess est injoignable (même politique que
Chess.com, cf. ``routers/games.py``).

Module PUR : aucune I/O ici (``infrastructure/lichess_client.py`` s'en charge) —
uniquement la traduction du JSON brut de ``GET /api/puzzle/next`` vers la forme
interne d'un problème tactique.

Format de la réponse Lichess (vérifié sur une vraie réponse en production,
cf. hotfix diagnostic 04/07 — la documentation seule ne suffisait pas) ::

    {
      "game": {"pgn": "e4 e5 Nf3 ... Ba3 Bc1"},
      "puzzle": {
        "id": "abcd1", "rating": 1550, "initialPly": 68,
        "solution": ["d3e2", "d1e2", "e3c1"],  # UCI
        "themes": ["middlegame", "mateIn2"]
      }
    }

``initialPly`` est l'index **0-based du dernier coup déjà joué** dans
``game.pgn`` (pas « la position avant le coup qui amène le puzzle » comme le
laisse penser une lecture rapide de la doc publique) — la position de départ
du puzzle s'obtient donc en rejouant ``initialPly + 1`` demi-coups. À cette
position, ``solution`` est la séquence **complète** que le solveur doit
jouer (son propre coup, la réplique adverse forcée, son coup suivant, …) —
aucun élément de ``solution`` n'est un coup à auto-jouer avant de commencer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import chess
import chess.pgn
import io

#: theme_id interne -> "angle" Lichess (paramètre de /api/puzzle/next).
#: ``None`` (thème "Aléatoire" côté UI) omet le paramètre — Lichess sert
#: alors un puzzle toutes catégories confondues.
LICHESS_ANGLES: Dict[str, str] = {
    "mate_in_1": "mateIn1",
    "mate_in_2": "mateIn2",
    "hanging_piece": "hangingPiece",
}


def angle_for_theme(theme_id: Optional[str]) -> Optional[str]:
    """``theme_id`` interne -> paramètre ``angle`` Lichess, ``None`` si
    aléatoire ou thème sans correspondance connue."""
    if theme_id is None:
        return None
    return LICHESS_ANGLES.get(theme_id)


def replay_pgn_to_ply(pgn_text: str, ply: int) -> Optional[chess.Board]:
    """Rejoue les ``ply`` premiers demi-coups d'un PGN et retourne le plateau.

    ``None`` si le PGN est illisible ou compte moins de ``ply`` coups —
    jamais d'exception : c'est une donnée externe (Lichess).
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return None
    if game is None:
        return None
    board = game.board()
    node = game
    for _ in range(ply):
        node = node.next()
        if node is None:
            return None
        board.push(node.move)
    return board


def parse_puzzle_payload(payload: Dict[str, Any], category: Optional[str]) -> Optional[Dict[str, Any]]:
    """Traduit la réponse brute de ``GET /api/puzzle/next`` en un problème
    tactique interne, prêt pour ``db_client.add_lichess_tactical_problem``.

    Retourne ``None`` (jamais d'exception) si la forme est inattendue —
    l'appelant retombe alors sur le seed local, comme pour toute panne
    réseau (même politique de résilience que le reste de l'app).

    ``category`` est celle DEMANDÉE par l'appelant (le thème filtré côté
    route) plutôt que déduite des ``themes`` Lichess (une liste ouverte,
    pas garantie de correspondre à notre vocabulaire à 3 valeurs) — plus
    robuste et cohérent avec le filtre ``theme_id`` déjà en place.
    """
    try:
        game = payload["game"]
        puzzle = payload["puzzle"]
        pgn_text = game["pgn"]
        initial_ply = int(puzzle["initialPly"])
        solution: List[str] = list(puzzle["solution"])
        rating = int(puzzle["rating"])
        puzzle_id = puzzle["id"]
    except (KeyError, TypeError, ValueError):
        return None
    if not solution:
        return None

    # +1 : `initialPly` est l'index 0-based du DERNIER coup déjà joué dans
    # le PGN, pas le nombre de coups à rejouer (cf. docstring du module).
    board = replay_pgn_to_ply(pgn_text, initial_ply + 1)
    if board is None:
        return None

    try:
        first_move = chess.Move.from_uci(solution[0])
    except ValueError:
        return None
    if first_move not in board.legal_moves:
        return None

    return {
        "fen": board.fen(),
        "solution": solution,
        "category": category or "aleatoire",
        "difficulty_elo": rating,
        "lichess_id": puzzle_id,
    }
