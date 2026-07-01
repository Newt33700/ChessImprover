"""Pipeline d'analyse d'une partie — orchestration du « worker » (EPIC 1).

Transforme un PGN en une liste de métriques par coup (US 1.2) en combinant :
segmentation des phases (US 2.1), perte de centipions (US 2.2) et classification
tactique/stratégique (US 3.2). La source des évaluations est abstraite via
``EngineProvider`` ; sans moteur, seules les phases et les coups sont produits.

Module PUR (hormis l'appel au moteur injecté) : testable avec un moteur stub.
"""

from __future__ import annotations

import io as _io
from typing import Any, Dict, List, Optional

import chess
import chess.pgn

from app.domain.acpl import centipawn_loss
from app.domain.move_class import classify_position
from app.domain.phases import segment_phases
from app.infrastructure.engine import (
    ClientProvidedEngine,
    EngineProvider,
    MoveScore,
    PositionEval,
)


def build_client_engine(evals: Dict[str, List[List[Any]]]) -> ClientProvidedEngine:
    """Construit un moteur depuis des évaluations client ``{fen: [[uci, cp, mate?, in?]]}``."""
    positions: Dict[str, PositionEval] = {}
    for fen, lines in (evals or {}).items():
        scores: List[MoveScore] = []
        for line in lines:
            uci = line[0]
            cp = int(line[1])
            is_mate = bool(line[2]) if len(line) > 2 else False
            mate_in = int(line[3]) if len(line) > 3 and line[3] is not None else None
            scores.append(MoveScore(move_uci=uci, score_cp=cp, is_mate=is_mate, mate_in=mate_in))
        positions[fen] = PositionEval(fen=fen, lines=scores)
    return ClientProvidedEngine(positions)


def _blank_record(board: chess.Board, move: chess.Move, phase) -> Dict[str, Any]:
    return {
        "move_number": board.fullmove_number,
        "color": "white" if board.turn == chess.WHITE else "black",
        "move_san": board.san(move),
        "eval_before": None,
        "eval_after": None,
        "score_cp": None,
        "cpl": None,
        "is_mate": False,
        "mate_in": None,
        "phase": phase.value,
        "position_type": "neutral",
    }


def _enrich_with_engine(
    record: Dict[str, Any], engine: EngineProvider, fen: str, move: chess.Move
) -> None:
    """Complète un enregistrement avec les évaluations moteur (best, joué, type)."""
    try:
        pos = engine.analyse(fen, multipv=3)
    except Exception:
        return
    best = pos.best
    if best is None:
        return
    record["eval_before"] = best.score_cp
    record["is_mate"] = best.is_mate
    record["mate_in"] = best.mate_in
    record["position_type"] = classify_position([ln.score_cp for ln in pos.lines]).value

    played_cp = pos.score_of(move.uci())
    if played_cp is not None:
        record["eval_after"] = played_cp
        record["score_cp"] = played_cp
        record["cpl"] = centipawn_loss(best.score_cp, played_cp)


def _extract_opening(headers: Any) -> tuple:
    """Extrait ``(eco, opening_name)`` des en-têtes PGN (US 4.2 — top 3 ouvertures).

    Chess.com exporte systématiquement ``ECO`` (ex. ``"C50"``) et ``ECOUrl``
    (ex. ``".../openings/Italian-Game"``) ; on dérive le nom lisible du dernier
    segment de l'URL faute d'en-tête ``Opening`` standard. Renvoie
    ``(None, None)`` si les en-têtes ne portent aucune de ces informations
    (PGN non issu de Chess.com, ou collé manuellement).
    """
    if not headers:
        return None, None
    eco = headers.get("ECO") or None
    name = headers.get("Opening") or None
    if not name:
        eco_url = headers.get("ECOUrl")
        if eco_url:
            slug = eco_url.rstrip("/").rsplit("/", 1)[-1]
            name = slug.replace("-", " ") if slug else None
    return eco, name


def analyze_pgn(pgn: str, engine: Optional[EngineProvider] = None) -> Dict[str, Any]:
    """Analyse un PGN et renvoie ``{"result", "eco", "opening_name", "moves": [...]}``.

    Chaque ``record`` de ``moves`` suit le schéma ``game_moves`` (US 1.2). Sans
    moteur, les évaluations restent ``None`` mais les phases et coups sont
    produits. ``eco``/``opening_name`` sont ``None`` si absents du PGN.
    """
    empty = {"result": None, "eco": None, "opening_name": None, "moves": []}
    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return empty
    if game is None:
        return empty

    board = game.board()
    moves = list(game.mainline_moves())
    phases = segment_phases(board, moves)
    result = game.headers.get("Result") if game.headers else None
    if result == "*":
        result = None
    eco, opening_name = _extract_opening(game.headers)

    records: List[Dict[str, Any]] = []
    cursor = board.copy(stack=False)
    for i, move in enumerate(moves):
        fen = cursor.fen()
        record = _blank_record(cursor, move, phases[i])
        if engine is not None:
            _enrich_with_engine(record, engine, fen, move)
        records.append(record)
        cursor.push(move)

    return {"result": result, "eco": eco, "opening_name": opening_name, "moves": records}
