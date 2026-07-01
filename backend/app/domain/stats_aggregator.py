"""Agrégation des statistiques avancées — `GET /api/v1/stats/summary` (US 4.1).

Construit, à partir des parties analysées et de leurs coups persistés, le résumé
consommé tel quel par le frontend (« zéro calcul client ») : matrice cadence ×
catégorie d'Elo virtuel, tendance ACPL, répartition des gaffes, taux de
conversion / résilience en finale, et bloc tactiques.

Module PUR.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.cadence import classify_cadence
from app.domain.models import Phase, TimeClass
from app.domain.move_class import (
    TacticOutcome,
    strategic_elo,
    tactic_outcome,
    tactical_elo,
    tactical_success_ratio,
)
from app.domain.virtual_elo import acpl_to_elo

# Cadences affichées dans la matrice (lignes).
MATRIX_CADENCES: List[TimeClass] = [TimeClass.BULLET, TimeClass.BLITZ, TimeClass.RAPID]

#: Elo par défaut quand une catégorie/cadence n'a aucune donnée.
DEFAULT_ELO: int = 1200

#: Seuils de qualification d'un coup pour la tendance et le taux de gaffes.
BLUNDER_CPL: int = 200
MISSED_CPL: int = 100

#: Seuils d'avantage/désavantage à l'entrée de finale (centipions).
ADVANTAGE_CP: int = 150


def _avg(values: List[int]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def user_outcome(result: Optional[str], user_color: str) -> Optional[str]:
    """Issue de la partie pour le joueur analysé : ``win`` / ``loss`` / ``draw``."""
    if result == "1-0":
        return "win" if user_color == "white" else "loss"
    if result == "0-1":
        return "win" if user_color == "black" else "loss"
    if result == "1/2-1/2":
        return "draw"
    return None


def _user_moves(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    color = entry["game"].get("user_color", "white")
    return [m for m in entry["moves"] if m.get("color") == color]


def _endgame_entry_eval(moves: List[Dict[str, Any]]) -> Optional[int]:
    """Éval (point de vue joueur) de son premier coup en finale, ou ``None``."""
    for m in moves:
        if m.get("phase") == Phase.ENDGAME.value and m.get("eval_before") is not None:
            return m["eval_before"]
    return None


def category_elos(moves: List[Dict[str, Any]], tc: TimeClass) -> Dict[str, int]:
    """Elos virtuels par catégorie (ouvertures/tactique/stratégie/finales).

    Fonction partagée : utilisée par la matrice ``build_summary`` (US 4.1) et
    par le snapshot de progression ``progress_history.build_snapshot`` (US 5.1)
    pour garantir un calcul d'Elo virtuel identique partout.

    Parameters
    ----------
    moves : list[dict]
        Coups du joueur uniquement (déjà filtrés par couleur).
    tc : TimeClass
        Cadence, pour le bonus du mapping US 3.1.
    """
    opening_cpls = [m["cpl"] for m in moves if m.get("phase") == Phase.OPENING.value and m.get("cpl") is not None]
    endgame_cpls = [m["cpl"] for m in moves if m.get("phase") == Phase.ENDGAME.value and m.get("cpl") is not None]
    strat_cpls = [m["cpl"] for m in moves if m.get("position_type") == "strategic" and m.get("cpl") is not None]
    tac_outcomes = [
        tactic_outcome(m["cpl"])
        for m in moves
        if m.get("position_type") == "tactical" and m.get("cpl") is not None
    ]

    op_acpl = _avg(opening_cpls)
    eg_acpl = _avg(endgame_cpls)
    return {
        "openings": acpl_to_elo(op_acpl, tc) if op_acpl is not None else DEFAULT_ELO,
        "endgames": acpl_to_elo(eg_acpl, tc) if eg_acpl is not None else DEFAULT_ELO,
        "strategy": strategic_elo(strat_cpls, tc) or DEFAULT_ELO,
        "tactics": tactical_elo(tactical_success_ratio(tac_outcomes)) or DEFAULT_ELO,
    }


def build_summary(
    entries: List[Dict[str, Any]],
    ratings: Optional[Dict[str, int]] = None,
    period: str = "30d",
) -> Dict[str, Any]:
    """Construit le résumé agrégé.

    Parameters
    ----------
    entries : list[dict]
        Liste de ``{"game": game_dict, "moves": [move_dict, ...]}``.
    ratings : dict, optional
        Classement réel par cadence (``{"bullet": 1500, ...}``) ; sinon dérivé.
    period : str
        Période demandée (échographie, renvoyée telle quelle).
    """
    ratings = ratings or {}
    by_cadence: Dict[str, List[Dict[str, Any]]] = {tc.value: [] for tc in MATRIX_CADENCES}
    for entry in entries:
        tc = classify_cadence(entry["game"].get("time_control"))
        if tc in MATRIX_CADENCES:
            by_cadence[tc.value].append(entry)

    rows: Dict[str, Dict[str, int]] = {}
    for tc in MATRIX_CADENCES:
        key = tc.value
        moves: List[Dict[str, Any]] = []
        for entry in by_cadence[key]:
            moves.extend(_user_moves(entry))
        cats = category_elos(moves, tc)
        current = ratings.get(key)
        if current is None:
            current = round(sum(cats.values()) / len(cats)) if cats else DEFAULT_ELO
        rows[key] = {"current": int(current), **{k: int(v) for k, v in cats.items()}}

    return {
        "period": period,
        "hasData": bool(entries),
        "totalGames": len(entries),
        "rows": rows,
        "acplTrend": _acpl_trend(entries),
        "gaffeRate": _gaffe_rate(entries),
        "finales": _finales(entries),
        "tactics": _tactics_block(rows),
    }


def _acpl_trend(entries: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """Nombre de gaffes / coups manqués du joueur par partie (chronologique)."""
    ordered = sorted(entries, key=lambda e: e["game"].get("created_at", ""))
    labels, blunders, missed = [], [], []
    for idx, entry in enumerate(ordered, start=1):
        moves = _user_moves(entry)
        b = sum(1 for m in moves if (m.get("cpl") or 0) >= BLUNDER_CPL)
        mi = sum(1 for m in moves if MISSED_CPL <= (m.get("cpl") or 0) < BLUNDER_CPL)
        labels.append(f"G{idx}")
        blunders.append(b)
        missed.append(mi)
    return {"labels": labels, "blunders": blunders, "missed": missed}


def _gaffe_rate(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Répartition des gaffes (cpl ≥ 200) par phase, en pourcentage du total."""
    counts = {Phase.OPENING.value: 0, Phase.MIDDLEGAME.value: 0, Phase.ENDGAME.value: 0}
    for entry in entries:
        for m in _user_moves(entry):
            if (m.get("cpl") or 0) >= BLUNDER_CPL and m.get("phase") in counts:
                counts[m["phase"]] += 1
    total = sum(counts.values())
    if total == 0:
        return {"opening": 0.0, "middlegame": 0.0, "endgame": 0.0}
    return {
        "opening": round(100 * counts[Phase.OPENING.value] / total, 1),
        "middlegame": round(100 * counts[Phase.MIDDLEGAME.value] / total, 1),
        "endgame": round(100 * counts[Phase.ENDGAME.value] / total, 1),
    }


def _finales(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Taux de conversion (avantage ≥ +1.50) et de résilience (≤ −1.50)."""
    adv_games = won_adv = 0
    losing_games = saved = 0
    for entry in entries:
        moves = _user_moves(entry)
        entry_eval = _endgame_entry_eval(moves)
        if entry_eval is None:
            continue
        outcome = user_outcome(entry["game"].get("result"), entry["game"].get("user_color", "white"))
        if entry_eval >= ADVANTAGE_CP:
            adv_games += 1
            if outcome == "win":
                won_adv += 1
        elif entry_eval <= -ADVANTAGE_CP:
            losing_games += 1
            if outcome in ("draw", "win"):
                saved += 1
    conversion = round(100 * won_adv / adv_games, 1) if adv_games else 0.0
    resilience = round(100 * saved / losing_games, 1) if losing_games else 0.0
    return {"conversion": conversion, "resilience": resilience}


def _tactics_block(rows: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Bloc tactiques : rating dérivé de l'Elo tactique moyen (SRS hors périmètre)."""
    tactic_elos = [r["tactics"] for r in rows.values() if "tactics" in r]
    rating = round(sum(tactic_elos) / len(tactic_elos)) if tactic_elos else DEFAULT_ELO
    return {"rating": rating, "toReview": 0, "solved": 0, "streak": 0}
