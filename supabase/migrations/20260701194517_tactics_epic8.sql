-- EPIC 8 – US 8.1 : Moteur de sélection adaptative (Elo tactique)
-- Jeu de problèmes tactiques curés côté serveur (distinct du mode
-- Exercice/SRS existant, qui rejoue les propres gaffes du joueur).

CREATE TABLE IF NOT EXISTS tactical_problems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fen TEXT NOT NULL,
    solution TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty_elo INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tactical_problems_category
ON tactical_problems (category);

CREATE INDEX IF NOT EXISTS idx_tactical_problems_difficulty
ON tactical_problems (difficulty_elo);

-- Elo tactique du joueur (distinct de l'Elo virtuel Stats Avancées,
-- EPIC 3) ; 1000 par défaut tant qu'aucune tentative n'a été faite.
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS tactical_elo INTEGER NOT NULL DEFAULT 1000;

-- Seed MVP : 15 problèmes vérifiés programmatiquement (python-chess :
-- coup légal + mat effectif pour mate_in_1/mate_in_2, capture non
-- défendue pour hanging_piece). À remplacer/enrichir plus tard par un
-- import de dataset externe (cf. §10 README).
INSERT INTO tactical_problems (fen, solution, category, difficulty_elo)
VALUES
('6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1', 'Ra8#', 'mate_in_1', 650),
('7k/6pp/8/8/8/8/8/R6K w - - 0 1', 'Ra8#', 'mate_in_1', 650),
('k7/8/1K6/8/8/8/8/7R w - - 0 1', 'Rh8#', 'mate_in_1', 700),
('3r2k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1', 'Rd1#', 'mate_in_1', 750),
('6k1/4Rppp/8/8/8/8/6PP/6K1 w - - 0 1', 'Re8#', 'mate_in_1', 700),
('k1K5/8/8/8/8/8/8/6R1 w - - 0 1', 'Ra1#', 'mate_in_1', 800),
('4k3/8/8/3q4/8/8/3R4/4K3 w - - 0 1', 'Rxd5', 'hanging_piece', 900),
('4k3/8/8/4q3/8/8/4R3/4K3 w - - 0 1', 'Rxe5+', 'hanging_piece', 950),
('4k3/8/2n5/8/8/8/2R5/4K3 w - - 0 1', 'Rxc6', 'hanging_piece', 850),
('4k3/8/8/8/4n3/8/4Q3/4K3 w - - 0 1', 'Qxe4+', 'hanging_piece', 1000),
('8/8/8/8/8/8/8/k1KQ4 w - - 0 1', 'Qd4+', 'mate_in_2', 1250),
('8/8/8/8/8/8/8/k1K1Q3 w - - 0 1', 'Qe5+', 'mate_in_2', 1300),
('8/8/8/8/8/8/8/k1K1Q3 w - - 0 1', 'Qc3+', 'mate_in_2', 1300),
('8/8/8/8/8/8/8/k1K2Q2 w - - 0 1', 'Qf6+', 'mate_in_2', 1350),
('8/8/8/8/8/8/8/k1K2Q2 w - - 0 1', 'Kc2+', 'mate_in_2', 1400);
