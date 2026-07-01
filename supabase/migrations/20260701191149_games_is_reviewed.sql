-- US 7.3 – Table de correspondance "Partie-Étude"
-- Marque une partie comme déjà étudiée, pour une distinction visuelle dans
-- le dashboard (coche verte) et éviter de la re-parcourir inutilement.

ALTER TABLE games
ADD COLUMN IF NOT EXISTS is_reviewed BOOLEAN NOT NULL DEFAULT false;
