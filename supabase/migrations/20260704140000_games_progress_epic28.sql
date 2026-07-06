-- EPIC 28 (US 28.1) — Progression coup-par-coup de l'analyse asynchrone.
-- Alimentées par `analysis_pipeline.analyze_pgn` (callback `on_progress`)
-- pendant le déroulement de l'analyse Stockfish en tâche de fond, pour que
-- le frontend puisse afficher « Coup X sur Y » (Smart Loader) au lieu d'un
-- simple statut binaire processing/completed.
ALTER TABLE games
ADD COLUMN IF NOT EXISTS progress_current INT NOT NULL DEFAULT 0;
ALTER TABLE games
ADD COLUMN IF NOT EXISTS progress_total INT NOT NULL DEFAULT 0;
