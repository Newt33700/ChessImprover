"""Synchronisation automatique des parties Chess.com à la connexion (EPIC 23).

À la connexion, le frontend appelle ``POST /api/v1/games/sync`` : le backend
récupère les dernières parties Chess.com de l'utilisateur (pseudo lié au
profil, US 6.3), écarte celles déjà connues (hash PGN, US 7.2) et enfile les
nouvelles dans le pipeline d'analyse asynchrone existant (``run_analysis``) —
qui met déjà à jour tous les KPI en cascade : snapshot de progression
(US 5.1), profil d'erreurs (EPIC 11), flashcards SRS (EPIC 20), pivot de
défaite (EPIC 15).

Module PUR : aucune I/O — la route (``routers/games.py``) orchestre le client
Chess.com et la persistance ; ici, uniquement les règles de sélection.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

#: Nombre de parties récentes ratissées à chaque sync (décision PO, EPIC 23).
FETCH_LAST_GAMES = 10

#: Plafond de NOUVELLES analyses lancées par sync : depth 14 × ~40 coups est
#: CPU-lourd sur une petite instance Render — les parties au-delà du plafond
#: sont différées à la prochaine connexion (le hash PGN les retrouvera).
MAX_ANALYSES_PER_SYNC = 5

#: Une partie restée en ``processing`` plus longtemps que ce seuil est
#: considérée orpheline (instance endormie/redémarrée en plein travail sur
#: Render) et re-enfilée à la prochaine sync. Le seuil évite de re-lancer une
#: analyse encore réellement en cours (double insertion des coups).
STALE_PROCESSING_MINUTES = 10


def detect_user_color(raw_game: Dict[str, Any], chess_username: str) -> str:
    """Couleur jouée par l'utilisateur dans une partie brute Chess.com.

    Comparaison insensible à la casse (l'API renvoie la casse d'affichage du
    pseudo, pas celle saisie par l'utilisateur). Défaut ``"white"`` si le
    pseudo n'apparaît d'aucun côté — même convention que le reste du produit.
    """
    username = (chess_username or "").lower()
    black = ((raw_game.get("black") or {}).get("username") or "").lower()
    if username and black == username:
        return "black"
    return "white"


def extract_sync_candidates(
    raw_games: List[Dict[str, Any]], chess_username: str
) -> List[Dict[str, Any]]:
    """Transforme les parties brutes Chess.com en candidats à l'analyse.

    Ne garde que les parties avec un PGN exploitable et produit le triplet
    attendu par ``run_analysis`` : ``{pgn, user_color, time_control}``.
    L'ordre d'entrée (de la plus récente à la plus ancienne) est préservé,
    pour que le plafond ``MAX_ANALYSES_PER_SYNC`` privilégie le récent.
    """
    candidates: List[Dict[str, Any]] = []
    for raw in raw_games or []:
        pgn = raw.get("pgn")
        if not pgn or not isinstance(pgn, str):
            continue
        candidates.append(
            {
                "pgn": pgn,
                "user_color": detect_user_color(raw, chess_username),
                "time_control": raw.get("time_control") or None,
            }
        )
    return candidates


def _parse_created_at(value: Any) -> Optional[datetime]:
    """``created_at`` peut être un ``datetime`` (Postgres) ou une chaîne ISO
    (store in-memory / sérialisation) ; toute valeur illisible vaut ``None``."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def is_stale_processing(
    game: Dict[str, Any],
    now: Optional[datetime] = None,
    threshold_minutes: int = STALE_PROCESSING_MINUTES,
) -> bool:
    """Vrai si la partie est bloquée en ``processing`` depuis trop longtemps.

    Sans ``created_at`` lisible, la partie n'est PAS considérée orpheline
    (on préfère différer un re-enfilage que dupliquer une analyse en cours).
    Le PGN doit être présent : sans lui, rien à re-analyser.
    """
    if game.get("status") != "processing" or not game.get("pgn"):
        return False
    created_at = _parse_created_at(game.get("created_at"))
    if created_at is None:
        return False
    reference = now or datetime.now(timezone.utc)
    return reference - created_at >= timedelta(minutes=threshold_minutes)
