-- EPIC 18 (US 18.2/18.3) — Personnalisation Visuelle (Theme & Board)
-- Préférences arbitraires de personnalisation (thème des pièces, couleurs du
-- plateau…), stockées en JSONB pour rester extensible sans nouvelle migration
-- à chaque nouveau réglage (sons, animations, taille d'échiquier…).

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}'::JSONB;
