"""Analyse Comportementale — détection de patterns d'erreur + profil (EPIC 11, US 9.1/9.2).

Identifie, à la fin de chaque partie analysée, si l'utilisateur a commis
chacun des trois types d'erreur suivis, puis met à jour un score de
fréquence par moyenne mobile exponentielle (même principe de mise à jour
incrémentale et pure que l'Elo tactique `domain.tactical_elo` ou le
calendrier SM-2 `domain.srs_engine` : pas de scan de tout l'historique à
chaque partie).

Module PUR : aucune I/O, aucune dépendance à la base de données.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.domain.analyzer import analyze_pgn as analyze_geometric

#: Types d'erreur suivis (US 9.1). Les valeurs `hanging_piece`/`mate_in_1`/
#: `mate_in_2` correspondent volontairement aux `TACTICAL_THEMES` existants
#: (`domain.tactics`) pour brancher l'entraînement personnalisé (US 9.2)
#: sans table de correspondance supplémentaire.
ERROR_TYPES: Tuple[str, ...] = ("hanging_piece", "time_pressure", "missed_mate")

#: Poids de la mise à jour EMA (0 < alpha <= 1) : plus alpha est élevé, plus
#: la dernière partie pèse par rapport à l'historique. 0.3 fait converger un
#: schéma d'erreur répété (4 parties consécutives) au-delà du seuil "récurrent".
FREQUENCY_EMA_ALPHA: float = 0.3

#: Score de fréquence (0-100) au-delà duquel une erreur est un "Problème
#: récurrent" (règle métier explicite de la demande initiale).
RECURRING_THRESHOLD: float = 70.0

#: Thème(s) tactique(s) le(s) plus pertinent(s) pour l'entraînement ciblé
#: d'un type d'erreur (US 9.2, `GET /tactics/custom?focus=`).
#: `time_pressure` pointe vers `hanging_piece` : dans `detect_error_occurrences`
#: ci-dessous, une gaffe sous pression de temps est TOUJOURS un cas particulier
#: de pièce non défendue (cf. `domain.analyzer` : la zeitnot n'est comptée que
#: sur des coups déjà classés blunder) — le thème d'entraînement pertinent est
#: donc le même.
ERROR_TYPE_TO_TACTICAL_THEMES: Dict[str, Tuple[str, ...]] = {
    "hanging_piece": ("hanging_piece",),
    "time_pressure": ("hanging_piece",),
    "missed_mate": ("mate_in_1", "mate_in_2"),
}


def detect_error_occurrences(
    pgn: str, user_color: str, moves: List[Dict[str, Any]]
) -> Dict[str, bool]:
    """Détecte, pour UNE partie, si chaque type d'erreur est survenu ≥ 1 fois.

    - ``hanging_piece``/``time_pressure`` : réutilise le moteur géométrique
      déjà existant (`domain.analyzer.analyze_pgn`) plutôt que de dupliquer
      la détection de pièce non défendue depuis `game_moves`, qui ne stocke
      pas l'état de l'échiquier nécessaire à ce calcul.
    - ``missed_mate`` : dérivé de `game_moves` (US 1.2) — un coup joué PAR
      l'utilisateur pour lequel le meilleur coup menait à un mat forcé
      (``is_mate=True``) mais dont le coup réellement joué n'était pas ce
      mat (``cpl > 0``, donc `eval_after` moteur ≠ `eval_before` optimal).
    """
    color_code = "w" if user_color == "white" else "b"
    geo = analyze_geometric(pgn, color_code)

    hanging_only = set(geo.blunder_moves) - set(geo.time_panic_moves)
    missed_mate = any(
        m.get("color") == user_color and m.get("is_mate") and (m.get("cpl") or 0) > 0
        for m in moves
    )
    return {
        "hanging_piece": bool(hanging_only),
        "time_pressure": geo.time_panic_count > 0,
        "missed_mate": missed_mate,
    }


def update_frequency_score(
    old_score: float, occurred: bool, alpha: float = FREQUENCY_EMA_ALPHA
) -> float:
    """Moyenne mobile exponentielle du score de fréquence (0-100).

    ``occurred`` pousse le score vers 100 (erreur commise cette partie) ou
    vers 0 (partie propre sur ce plan) ; le score converge vers la fréquence
    récente d'apparition sans jamais recalculer tout l'historique.
    """
    target = 100.0 if occurred else 0.0
    new_score = old_score + alpha * (target - old_score)
    return round(max(0.0, min(100.0, new_score)), 1)


def is_recurring(frequency_score: float) -> bool:
    """Vrai si le score de fréquence dépasse le seuil "Problème récurrent"."""
    return frequency_score > RECURRING_THRESHOLD
