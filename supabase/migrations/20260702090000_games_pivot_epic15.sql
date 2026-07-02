-- EPIC 15 (US 15.1/15.2) — Réparation de Partie (Game-Salvage)
-- Index (0-based, ligne principale) du premier coup DU JOUEUR où l'évaluation
-- s'effondre (cf. `game_salvage.find_defeat_pivot`), pour reconstruire la
-- position exacte à ce « pivot de défaite » en mode Sandbox.

ALTER TABLE games
ADD COLUMN IF NOT EXISTS pivot_move_index INT;
