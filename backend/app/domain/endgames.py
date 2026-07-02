"""Entraîneur de Finales Essentielles (EPIC 10, fonctionnalité bonus).

Ne redéfinit **aucune** logique de validation/sélection : `is_correct_move`
et `select_nearest_problem` (`domain/tactics.py`) sont des fonctions pures
déjà génériques (elles opèrent sur des dicts `fen`/`solution`/`difficulty_elo`
sans rien de spécifique aux puzzles tactiques) et sont réutilisées telles
quelles par `routers/endgames.py`, de même que `domain/tactical_elo.update_elo`.
"""

from __future__ import annotations

#: Catégories de technique de mat essentielle couvertes par le seed.
ENDGAME_THEMES = ("queen_mate", "rook_mate", "two_rooks_mate")
