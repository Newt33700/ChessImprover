"""EPIC 29 (US 29.1) — XP / Niveau authoritatifs côté serveur.

Module pur (aucun accès base de données ici — voir `infrastructure.db_client`
pour la persistance). Formule identique au système historique côté client
(`app.js:XPSystem`, `XP_PER_LEVEL(n) = n × 100`) pour ne jamais désynchroniser
l'affichage entre une session anonyme (localStorage) et une session connectée
(Postgres) qui utiliseraient une formule différente.
"""

from __future__ import annotations

from typing import Any, Dict

#: Gain accordé à la complétion d'une analyse de partie (`routers.games.run_analysis`).
XP_PER_ANALYSIS = 50

#: Gain accordé à la résolution d'un problème (tactique, finale, sprint, flashcard, ouverture).
XP_PER_PROBLEM_SOLVED = 15


def xp_required_for_level(level: int) -> int:
    """XP nécessaires pour passer du niveau ``level`` au niveau ``level + 1``."""
    return level * 100


def apply_xp_gain(current_xp: int, current_level: int, amount: int) -> Dict[str, Any]:
    """Ajoute ``amount`` XP et fait monter de niveau autant de fois que nécessaire.

    Renvoie ``{"xp": ..., "level": ..., "leveled_up": bool}``. ``xp`` reste
    toujours strictement inférieur au seuil du niveau courant (comme le
    système client historique) — ce n'est pas un total cumulé depuis toujours.
    """
    xp = max(0, current_xp) + max(0, amount)
    level = max(1, current_level)
    leveled_up = False
    while xp >= xp_required_for_level(level):
        xp -= xp_required_for_level(level)
        level += 1
        leveled_up = True
    return {"xp": xp, "level": level, "leveled_up": leveled_up}
