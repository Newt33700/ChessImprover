"""EPIC 29 (US 29.2) — Quêtes quotidiennes, sans état.

Décision d'architecture assumée : plutôt qu'une table `daily_quests` mutable
(qu'il faudrait peupler/purger chaque jour pour chaque utilisateur), les 3
quêtes du jour sont **dérivées** d'un hash déterministe `(date, user_id)` —
même joueur, même jour → mêmes quêtes, sans jamais rien persister. La
progression est calculée à la volée depuis des données déjà existantes
(parties analysées, tentatives tactiques, sprints) : zéro nouvelle table de
suivi. Limite assumée : la récompense en XP affichée (`xp_reward`) est
indicative — l'attribuer automatiquement à la complétion nécessiterait de
mémoriser qu'elle a déjà été payée ce jour (sans quoi rejouer l'appel la
recréditerait à l'infini), ce qui réintroduirait l'état qu'on cherche
justement à éviter ici. Non traité dans cette itération.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List

#: Catalogue des quêtes possibles. `metric` désigne le compteur (calculé côté
#: routeur depuis les données existantes) contre lequel `target` est comparé.
QUEST_POOL: List[Dict[str, Any]] = [
    {"id": "analyze_1", "label": "Analyser une partie", "metric": "games_analyzed", "target": 1, "xp_reward": 20},
    {"id": "analyze_2", "label": "Analyser 2 parties", "metric": "games_analyzed", "target": 2, "xp_reward": 35},
    {"id": "tactics_3", "label": "Résoudre 3 problèmes tactiques", "metric": "tactics_solved", "target": 3, "xp_reward": 30},
    {"id": "tactics_5", "label": "Résoudre 5 problèmes tactiques", "metric": "tactics_solved", "target": 5, "xp_reward": 45},
    {"id": "sprint_1", "label": "Terminer un Tactical Sprint", "metric": "sprints_finished", "target": 1, "xp_reward": 25},
]

DAILY_QUEST_COUNT = 3


def select_daily_quests(
    date_str: str, user_id: str, pool: List[Dict[str, Any]] = QUEST_POOL, n: int = DAILY_QUEST_COUNT
) -> List[Dict[str, Any]]:
    """Sélectionne ``n`` quêtes déterministes pour ``(date_str, user_id)``.

    Même date + même utilisateur → toujours les mêmes quêtes (rejouer
    l'appel ne « re-tire » jamais) ; deux utilisateurs ou deux jours
    différents obtiennent des combinaisons différentes.
    """
    seed = hashlib.sha256(f"{date_str}:{user_id}".encode("utf-8")).hexdigest()
    rng = random.Random(seed)
    n = min(n, len(pool))
    return rng.sample(pool, n)


def compute_quest_progress(quest: Dict[str, Any], counts: Dict[str, int]) -> Dict[str, Any]:
    """Fusionne une définition de quête avec la progression réelle du jour."""
    progress = min(counts.get(quest["metric"], 0), quest["target"])
    return {**quest, "progress": progress, "completed": progress >= quest["target"]}
