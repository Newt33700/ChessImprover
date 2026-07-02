-- EPIC 14 (US 14.1/14.2) — Coach Vocal : alerte contextuelle par coup
-- Chaque coup évalué par un moteur peut porter une alerte de gravité
-- (blunder/mistake), un texte d'affichage et sa variante lue à voix haute
-- (synthèse vocale Web Speech API, 100% côté navigateur).

ALTER TABLE game_moves
ADD COLUMN IF NOT EXISTS alert_severity VARCHAR(12),
ADD COLUMN IF NOT EXISTS alert_text TEXT,
ADD COLUMN IF NOT EXISTS tts_text TEXT;
