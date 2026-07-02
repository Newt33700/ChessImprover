"""Le Cimetière des Erreurs — flashcards SRS auto-générées depuis les gaffes
(EPIC 20, US 20.1).

Chaque gaffe détectée dans une partie analysée (perte >= ``BLUNDER_CPL_THRESHOLD``)
devient une flashcard dans le moteur SRS **déjà existant** (``domain.srs_engine``,
algorithme SM-2 réutilisé une 3ᵉ fois après le SRS tactique JS et le répertoire
d'ouvertures d'EPIC 9) — aucun nouvel algorithme de répétition espacée : seule
la SOURCE des cartes change (auto-générée depuis les erreurs passées du joueur,
plutôt que piochée dans un jeu de problèmes curé comme EPIC 8/10).

Module PUR : consomme des enregistrements ``game_moves`` déjà persistés
(nécessite que ``domain.analysis_pipeline`` ait renseigné ``fen``/``best_move_san``,
donc qu'un moteur d'évaluation ait été disponible pour l'analyse).
"""

from __future__ import annotations

from typing import Any, Dict, List

#: Perte (cp) à partir de laquelle un coup est une « gaffe » digne d'une
#: flashcard — même seuil que ``stats_aggregator.BLUNDER_CPL`` (cohérence de
#: ce qui compte comme « gaffe » dans tout le produit).
BLUNDER_CPL_THRESHOLD: int = 200

#: Calendrier SM-2 initial d'une flashcard fraîchement générée — identique à
#: ``domain.opening_repertoire``/``domain.srs_engine.create_card`` (ef=2.5,
#: interval=1 jour) : une seule convention de démarrage SM-2 dans tout le produit.
DEFAULT_EASE_FACTOR: float = 2.5
DEFAULT_INTERVAL_DAYS: int = 1


def extract_blunder_flashcards(own_moves: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extrait les flashcards candidates depuis les gaffes d'une partie analysée.

    Parameters
    ----------
    own_moves : list[dict]
        Enregistrements ``game_moves`` du joueur uniquement (même convention
        de pré-filtrage par couleur que ``domain.cognitive_load`` : la
        responsabilité de ne garder que les coups du joueur analysé revient
        à l'appelant, une partie pouvant être jouée Blancs ou Noirs).

    Returns
    -------
    list[dict]
        ``[{"fen": ..., "solution": ...}, ...]`` — une entrée par gaffe
        exploitable : perte >= seuil, FEN et meilleur coup connus (nécessite
        un moteur d'évaluation lors de l'analyse), et solution différente du
        coup réellement joué (garde-fou défensif : par construction une perte
        >= 200cp implique déjà un coup joué différent du meilleur).
    """
    cards: List[Dict[str, str]] = []
    for m in own_moves:
        cpl = m.get("cpl")
        if cpl is None or cpl < BLUNDER_CPL_THRESHOLD:
            continue

        fen = m.get("fen")
        best = m.get("best_move_san")
        if not fen or not best or best == m.get("move_san"):
            continue

        cards.append({"fen": fen, "solution": best})
    return cards
