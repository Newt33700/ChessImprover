-- EPIC 10 – Entraîneur de Finales Essentielles (technique de mat)
-- Réutilise le même schéma qu'EPIC 8 (tactical_problems/tactical_elo) pour
-- un thème distinct : Roi+Dame, Roi+Tour, Roi+2 Tours vs Roi seul.

CREATE TABLE IF NOT EXISTS endgame_problems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fen TEXT NOT NULL,
    solution TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty_elo INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_endgame_problems_category
ON endgame_problems (category);

CREATE INDEX IF NOT EXISTS idx_endgame_problems_difficulty
ON endgame_problems (difficulty_elo);

ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS endgame_elo INTEGER NOT NULL DEFAULT 1000;

INSERT INTO endgame_problems (fen, solution, category, difficulty_elo) VALUES
('8/8/8/8/8/8/8/k1KQ4 w - - 0 1', 'Qa4#', 'queen_mate', 700),
('7k/8/5K2/8/8/8/8/6Q1 w - - 0 1', 'Qg7#', 'queen_mate', 750),
('k7/8/K7/8/8/8/8/Q7 w - - 0 1', 'Qh8#', 'queen_mate', 700),
('8/8/8/8/8/R7/8/5K1k w - - 0 1', 'Rh3#', 'rook_mate', 850),
('k7/8/K7/8/8/8/8/2R5 w - - 0 1', 'Rc8#', 'rook_mate', 850),
('7k/8/6K1/8/8/8/8/R7 w - - 0 1', 'Ra8#', 'rook_mate', 900),
('k7/8/8/8/8/8/1R6/KR6 w - - 0 1', 'Ra2#', 'two_rooks_mate', 950),
('7k/8/8/8/8/8/6R1/KR6 w - - 0 1', 'Rh1#', 'two_rooks_mate', 1000),
('8/8/8/8/8/1R6/8/k1KR4 w - - 0 1', 'Ra3#', 'two_rooks_mate', 1000);
