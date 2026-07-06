-- EPIC 37 – Moteur de Puzzles (catalogue Lichess local)
-- Catalogue de référence en lecture seule, ingéré depuis le dump public
-- Lichess (backend/scripts/ingest_lichess_puzzles.py) — contrairement à
-- `tactical_problems` (EPIC 8), aucune ligne n'appartient à un utilisateur :
-- pas de RLS nécessaire, la table n'est lue que côté serveur.

CREATE TABLE IF NOT EXISTS lichess_puzzles (
    puzzle_id VARCHAR(50) PRIMARY KEY,
    fen TEXT NOT NULL,
    moves TEXT NOT NULL,
    rating INTEGER NOT NULL,
    rating_deviation INTEGER NOT NULL,
    popularity INTEGER NOT NULL,
    nb_plays INTEGER NOT NULL,
    themes TEXT [] NOT NULL DEFAULT '{}',
    game_url TEXT,
    opening_tags TEXT [] NOT NULL DEFAULT '{}'
);

-- Sélection par plage d'Elo (US 37.1 : recherche standard + fallback ±100).
CREATE INDEX IF NOT EXISTS idx_lichess_puzzles_rating
ON lichess_puzzles (rating);

-- Filtrage par thème via l'opérateur `@>` (ex. themes @> ARRAY['mateIn2']).
CREATE INDEX IF NOT EXISTS idx_lichess_puzzles_themes
ON lichess_puzzles USING gin (themes);
