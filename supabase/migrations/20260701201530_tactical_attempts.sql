-- US 8.4 – Persistance et historique des tentatives tactiques
-- Chaque coup soumis à POST /api/v1/tactics/attempt est enregistré, afin
-- de calculer le taux de réussite par catégorie.

CREATE TABLE IF NOT EXISTS tactical_attempts (
    attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES tactical_problems (id)
    ON DELETE CASCADE,
    success BOOLEAN NOT NULL,
    time_taken NUMERIC NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tactical_attempts_user
ON tactical_attempts (user_id);

CREATE INDEX IF NOT EXISTS idx_tactical_attempts_problem
ON tactical_attempts (problem_id);

ALTER TABLE tactical_attempts ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que ses propres tentatives
CREATE POLICY tactical_attempts_own_row ON tactical_attempts
FOR ALL
USING (user_id = auth.uid()::UUID);
