-- EPIC 29 (US 29.1) — XP/Niveau authoritatifs côté serveur.
-- Formule identique au système client historique (`XP_PER_LEVEL(n) = n × 100`,
-- `app.js:XPSystem`) — voir `app/domain/gamification.py`.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS xp INT NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS level INT NOT NULL DEFAULT 1;
