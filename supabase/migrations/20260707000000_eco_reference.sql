-- EPIC 38 — Lotus Mastery Engine (Ouvertures) : référentiel ECO
-- Peuplé par `backend/scripts/seed_eco.py` depuis les TSV locaux
-- (frontend/assets/data/openings/a.tsv…e.tsv, ex-raw.githubusercontent.com,
-- déjà rapatriés localement EPIC 13). Table de référence en lecture seule
-- (pas de RLS — aucune ligne n'appartient à un utilisateur).

CREATE TABLE IF NOT EXISTS eco_reference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eco_code VARCHAR(10) NOT NULL,
    -- "opening_name", pas "name" (mot-clé SQL non réservé mais déconseillé
    -- comme identifiant — même convention que line_name sur l'ex-table
    -- opening_repertoire, EPIC 9).
    opening_name TEXT NOT NULL,
    moves_sequence TEXT NOT NULL
);

-- Unicité sur la séquence de coups (identité d'une ligne d'ouverture) —
-- déduplique un ré-import du même TSV.
CREATE UNIQUE INDEX IF NOT EXISTS idx_eco_reference_moves_sequence
ON eco_reference (moves_sequence);

CREATE INDEX IF NOT EXISTS idx_eco_reference_eco_code
ON eco_reference (eco_code);
