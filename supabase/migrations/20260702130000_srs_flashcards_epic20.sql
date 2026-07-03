-- EPIC 20 — Bibliothèque de Mémoire Tactique : flashcards SRS (US 20.1/20.2)
-- Le Cimetière des Erreurs : chaque gaffe détectée dans une partie analysée
-- (domain.srs_flashcards.extract_blunder_flashcards) devient une flashcard
-- ici, plutôt que dans un jeu de problèmes curé (EPIC 8/10). Calendrier SM-2
-- (ease_factor/interval_days/repetitions/due_date) recalculé côté serveur à
-- chaque révision — même algorithme et mêmes colonnes que
-- `opening_repertoire` (EPIC 9) : une seule convention de répétition espacée.

CREATE TABLE IF NOT EXISTS srs_flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    game_id UUID REFERENCES games (id) ON DELETE SET NULL,
    fen TEXT NOT NULL,
    solution VARCHAR(12) NOT NULL,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 1,
    repetitions INTEGER NOT NULL DEFAULT 0,
    due_date DATE NOT NULL DEFAULT current_date,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_srs_flashcards_user
ON srs_flashcards (user_id);

CREATE INDEX IF NOT EXISTS idx_srs_flashcards_due
ON srs_flashcards (user_id, due_date);

ALTER TABLE srs_flashcards ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que ses propres flashcards
CREATE POLICY srs_flashcards_own_row ON srs_flashcards
FOR ALL
USING (user_id = auth.uid()::UUID);
