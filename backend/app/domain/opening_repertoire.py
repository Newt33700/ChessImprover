"""Lotus Mastery Engine — arbre de répertoire depuis un PGN (EPIC 38, US 38.1).

REMPLACE l'ancien module EPIC 9 (répertoire de lignes + SRS SM-2 sur des
lignes entières, ``validate_move_sequence``/``infer_quality``) : le nouveau
modèle est un **arbre de positions** (une ligne PGN peut contenir des
variations, chacune devenant une branche), avec une progression par nœud
gérée séparément (``domain.mastery_engine``), pas par ligne.

Module PUR (aucune I/O, aucun accès base) : ``parse_pgn_tree`` traduit un
texte PGN en une liste plate de nœuds prête pour l'insertion
(``routers/openings_trainer.py`` assigne les UUID réels et gère les FK).

Décision de modélisation (spec ambiguë sur ce point précis) : pas de nœud
racine « position de départ, aucun coup » — un tel nœud n'aurait rien à
faire pratiquer (``move_san`` vide) et bloquerait le générateur de sessions
dès l'import. Les nœuds de plus haut niveau (``parent_index=None``,
``depth_level=1``) sont directement les premiers coups possibles depuis la
position initiale (échiquier standard, FEN bien connue) — ce sont eux, au
pluriel s'il y a plusieurs variations dès le 1ᵉʳ coup, que la règle de
déblocage de l'Étape 12 appelle « le nœud racine ».
"""

from __future__ import annotations

import io
from typing import List, Optional, TypedDict

import chess
import chess.pgn


class RepertoireNodeData(TypedDict):
    """Un nœud de l'arbre, avant assignation d'un UUID réel.

    ``parent_index`` référence un index dans la liste retournée par
    ``parse_pgn_tree`` (``None`` pour un nœud racine, cf. docstring du
    module) — traduit en UUID par l'appelant au moment de l'insertion, dans
    l'ordre (parent toujours inséré avant ses enfants, l'arbre étant
    construit en profondeur).
    """

    parent_index: Optional[int]
    move_san: str
    move_fen: str
    depth_level: int
    is_mainline: bool


def parse_pgn_tree(pgn_text: str) -> List[RepertoireNodeData]:
    """Reconstruit l'arbre complet (ligne principale + variations) d'un PGN.

    Liste vide si le PGN est illisible, ne contient aucune partie, ou aucun
    coup — jamais d'exception (donnée potentiellement fournie par
    l'utilisateur, jamais une confiance aveugle). ``is_mainline`` : vrai
    uniquement le long du premier enfant de chaque nœud (convention PGN
    standard — la première variation est la ligne principale, les
    suivantes des alternatives).
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []
    if game is None:
        return []

    nodes: List[RepertoireNodeData] = []

    def _walk(game_node: chess.pgn.GameNode, parent_index: Optional[int], board: chess.Board,
              depth: int, parent_is_mainline: bool) -> None:
        for i, variation in enumerate(game_node.variations):
            move = variation.move
            if move not in board.legal_moves:
                continue  # PGN corrompu/incohérent : on ignore la branche, pas de crash
            san = board.san(move)
            child_board = board.copy()
            child_board.push(move)
            child_is_mainline = parent_is_mainline and i == 0
            nodes.append({
                "parent_index": parent_index,
                "move_san": san,
                "move_fen": child_board.fen(),
                "depth_level": depth + 1,
                "is_mainline": child_is_mainline,
            })
            _walk(variation, len(nodes) - 1, child_board, depth + 1, child_is_mainline)

    _walk(game, None, game.board(), 0, True)
    return nodes
