"""EPIC 30 — Moteur de saisons (config statique + détection de l'évènement actif).

Module pur : parsing/sélection ne dépendent que de la liste de saisons et de
l'horodatage fourni par l'appelant (jamais de `datetime.now()` interne),
pour rester 100 % testable sans dépendre de la date réelle.

Écart assumé vs. la demande PO littérale (`backend/app/config/seasons.json`) :
`app/config.py` est déjà un **module** (pas un paquet) — y ajouter un paquet
`config/` du même nom entrerait en conflit d'import. Le catalogue vit donc
dans `app/data/seasons.json`, à côté d'où vivent déjà les données statiques
côté frontend (`frontend/assets/data/`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SEASONS_PATH = Path(__file__).resolve().parent.parent / "data" / "seasons.json"


def load_seasons(path: Path = SEASONS_PATH) -> List[Dict[str, Any]]:
    """Charge le catalogue de saisons. Fichier absent/invalide -> liste vide
    (une saison mal configurée ne doit jamais faire planter l'application)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _parse(value: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def get_active_season(seasons: List[Dict[str, Any]], now: datetime) -> Optional[Dict[str, Any]]:
    """Première saison dont la fenêtre `[start, end]` couvre `now` (UTC).

    Une entrée dont `start`/`end` est absent ou illisible est ignorée plutôt
    que de faire planter la sélection.
    """
    for season in seasons:
        start = _parse(season.get("start", ""))
        end = _parse(season.get("end", ""))
        if start is None or end is None:
            continue
        if start <= now <= end:
            return season
    return None


def seconds_remaining(season: Dict[str, Any], now: datetime) -> int:
    """Secondes avant la fin de `season` (0 si déjà terminée/invalide)."""
    end = _parse(season.get("end", ""))
    if end is None:
        return 0
    return max(0, int((end - now).total_seconds()))
