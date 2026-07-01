-- EPIC 9 – Entraîneur d'Ouvertures (répertoire personnel + SRS SM-2)
-- Chaque ligne est une séquence de coups SAN validée légale avant
-- enregistrement (backend). Le calendrier SM-2 (ease_factor/interval_days/
-- repetitions/due_date) est recalculé côté serveur à chaque révision, sur
-- le même algorithme que le SRS tactique existant (domain.srs_engine).

CREATE TABLE IF NOT EXISTS opening_repertoire (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    line_name TEXT NOT NULL,
    color TEXT NOT NULL CHECK (color IN ('white', 'black')),
    moves JSONB NOT NULL,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 1,
    repetitions INTEGER NOT NULL DEFAULT 0,
    due_date DATE NOT NULL DEFAULT current_date,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_opening_repertoire_user
ON opening_repertoire (user_id);

CREATE INDEX IF NOT EXISTS idx_opening_repertoire_due
ON opening_repertoire (user_id, due_date);

ALTER TABLE opening_repertoire ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que son propre répertoire
CREATE POLICY opening_repertoire_own_row ON opening_repertoire
FOR ALL
USING (user_id = auth.uid()::UUID);
