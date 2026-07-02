-- EPIC 11 — Analyse Comportementale (US 9.1/9.2) : profil d'erreurs récurrentes
-- Un score de fréquence (0-100, moyenne mobile exponentielle mise à jour côté
-- backend après chaque partie analysée) par type d'erreur suivi. Un score
-- > 70 marque l'erreur comme "Problème récurrent" (domain.error_profile),
-- calculé à la lecture — non stocké, pour ne pas dupliquer un état dérivé.
-- error_type en TEXT + CHECK plutôt qu'un type ENUM Postgres natif, par
-- cohérence avec le reste du schéma (`games.status`,
-- `opening_repertoire.color`, `game_moves.phase`/`position_type`).

CREATE TABLE IF NOT EXISTS user_error_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    error_type TEXT NOT NULL
    CHECK (error_type IN ('hanging_piece', 'time_pressure', 'missed_mate')),
    frequency_score NUMERIC(5, 1) NOT NULL DEFAULT 0,
    last_observed TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, error_type)
);

CREATE INDEX IF NOT EXISTS idx_user_error_profiles_user
ON user_error_profiles (user_id);

ALTER TABLE user_error_profiles ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que son propre profil d'erreurs
CREATE POLICY user_error_profiles_own_row ON user_error_profiles
FOR ALL
USING (user_id = auth.uid()::UUID);
