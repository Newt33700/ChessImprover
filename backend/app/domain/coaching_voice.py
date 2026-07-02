"""Coach Vocal — Shadow Coaching (EPIC 14, US 14.1 / US 14.2).

Génère, pour un coup déjà évalué par le moteur (``analysis_pipeline``), un
texte d'alerte contextuel et sa variante « à lire à voix haute » (US 14.2,
synthèse vocale côté frontend via l'API Web Speech du navigateur — aucun
appel réseau, conformément à la contrainte « Zero External Assets » de
l'EPIC 13).

Réutilise volontairement l'infrastructure existante plutôt que d'inventer de
nouveaux seuils :
- la classification de précision (``brilliant``..``blunder``) vient de
  ``elo_calculator`` (mêmes seuils que le reste du produit) ;
- la détection « pièce non défendue » vient de ``analyzer.is_piece_hanging``
  (déjà utilisée par EPIC 11 pour le profil comportemental), pour produire un
  message contextuel précis (« ta Dame est en prise ») plutôt qu'un simple
  label de gravité.

Module PUR : aucune I/O, aucun appel moteur — opère sur un ``chess.Board``
déjà connu de l'appelant (``analysis_pipeline``, qui a déjà la position).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import chess

from app.domain.analyzer import PIECE_VALUES, is_piece_hanging
from app.domain.elo_calculator import classify_move, move_accuracy
from app.domain.models import Classification

#: Noms français des pièces, pour un message contextuel lisible.
_PIECE_NAMES_FR: Dict[int, str] = {
    chess.PAWN: "ton pion",
    chess.KNIGHT: "ton cavalier",
    chess.BISHOP: "ton fou",
    chess.ROOK: "ta tour",
    chess.QUEEN: "ta dame",
    chess.KING: "ton roi",
}

#: Seules les classifications ci-dessous déclenchent une alerte vocale (US
#: 14.1) — un coup "good"/"excellent"/"brilliant" ne mérite aucune coupure de
#: concentration du joueur.
_ALERT_SEVERITY: Dict[Classification, str] = {
    Classification.BLUNDER: "blunder",
    Classification.MISTAKE: "mistake",
}


def _find_hanging_piece_square(
    board_after: chess.Board, mover_color: bool
) -> Optional[chess.Square]:
    """Cherche la pièce la plus précieuse du camp ``mover_color`` en prise et
    non défendue sur ``board_after`` (position résultant du coup joué).

    Renvoie la case de la pièce la plus précieuse exposée (priorité à la
    Dame plutôt qu'à un pion), ou ``None`` si rien n'est en prise.
    """
    best_square: Optional[chess.Square] = None
    best_value = -1
    for square, piece in board_after.piece_map().items():
        if piece.color != mover_color:
            continue
        if not is_piece_hanging(board_after, square, mover_color):
            continue
        value = PIECE_VALUES.get(piece.piece_type, 0)
        if value > best_value:
            best_value = value
            best_square = square
    return best_square


def build_move_alert(
    board_after: chess.Board,
    mover_color: bool,
    cpl: Optional[int],
    move_san: str,
) -> Optional[Dict[str, str]]:
    """Construit l'alerte vocale d'un coup, ou ``None`` si le coup ne mérite
    aucune alerte (précision "good" ou mieux, ou coup non évalué par moteur).

    Parameters
    ----------
    board_after : chess.Board
        Position APRÈS que le coup a été joué (nécessaire pour détecter une
        pièce laissée en prise).
    mover_color : bool
        Couleur du joueur qui a joué le coup (``chess.WHITE``/``chess.BLACK``).
    cpl : int | None
        Perte en centipions du coup (``None`` si non évalué par un moteur).
    move_san : str
        Notation SAN du coup joué, pour un message lisible.

    Returns
    -------
    dict | None
        ``{"severity", "alert_text", "tts_text"}`` si le coup déclenche une
        alerte, sinon ``None``.
    """
    if cpl is None:
        return None
    classification = classify_move(move_accuracy(cpl))
    severity = _ALERT_SEVERITY.get(classification)
    if severity is None:
        return None

    hanging_square = _find_hanging_piece_square(board_after, mover_color)
    if hanging_square is not None:
        piece = board_after.piece_at(hanging_square)
        piece_name = _PIECE_NAMES_FR.get(piece.piece_type, "une pièce") if piece else "une pièce"
        square_name = chess.square_name(hanging_square)
        alert_text = f"Attention, {move_san} expose {piece_name} en {square_name} !"
        tts_text = f"Attention, ce coup expose {piece_name}."
    elif severity == "blunder":
        alert_text = f"Gaffe ! {move_san} perd un avantage important."
        tts_text = "Attention, c'est une gaffe importante."
    else:
        alert_text = f"{move_san} n'était pas le meilleur coup."
        tts_text = "Ce coup n'était pas optimal, il y avait mieux."

    return {"severity": severity, "alert_text": alert_text, "tts_text": tts_text}


def attach_move_alert(record: Dict[str, Any], board_after: chess.Board, mover_color: bool) -> None:
    """Enrichit en place un enregistrement ``game_moves`` avec l'alerte vocale
    (``alert_severity``/``alert_text``/``tts_text``), si applicable.

    No-op silencieux si le coup ne déclenche aucune alerte (les 3 clés ne sont
    alors pas ajoutées) — cohérent avec le reste du schéma ``game_moves``, où
    les champs non pertinents restent absents/``None``.
    """
    alert = build_move_alert(board_after, mover_color, record.get("cpl"), record.get("move_san", ""))
    if alert is None:
        return
    record["alert_severity"] = alert["severity"]
    record["alert_text"] = alert["alert_text"]
    record["tts_text"] = alert["tts_text"]
