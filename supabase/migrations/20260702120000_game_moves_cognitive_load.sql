-- EPIC 19 — Analyse de la Charge Cognitive (US 19.1/19.2)
-- Trois colonnes ajoutées à `game_moves`, calculées par
-- `domain.analysis_pipeline` :
--   * `fen`           : position AVANT le coup (sert aussi de socle aux
--                       flashcards SRS auto-générées, EPIC 20, US 20.1).
--   * `best_move_san` : meilleur coup moteur en SAN, jamais exposé au
--                       client avant tentative (même politique que le
--                       reste du produit) — alimente les flashcards.
--   * `time_spent_seconds` : temps de réflexion du joueur sur ce coup,
--                       dérivé des horloges PGN
--                       (`domain.cognitive_load.derive_time_spent`).
--                       NULL si la partie n'a pas de balises [%clk].

ALTER TABLE game_moves ADD COLUMN IF NOT EXISTS fen TEXT;
ALTER TABLE game_moves ADD COLUMN IF NOT EXISTS best_move_san VARCHAR(12);
ALTER TABLE game_moves
ADD COLUMN IF NOT EXISTS time_spent_seconds NUMERIC(8, 2);
