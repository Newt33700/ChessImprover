-- US 7 – Auth & Cloud Persistence
-- Migration initiale : profils utilisateurs + données synchronisées

-- Profils utilisateurs

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ── Données utilisateur (parties + cartes SRS) ───────────────────────────────

CREATE TABLE IF NOT EXISTS user_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    games JSONB NOT NULL DEFAULT '[]',
    srs_cards JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id)
);

-- Index pour la recherche rapide par user_id
CREATE INDEX IF NOT EXISTS idx_user_data_user_id ON user_data (user_id);

-- Row Level Security

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_data ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que son propre profil
CREATE POLICY profiles_own_row ON profiles
FOR ALL
USING (id = auth.uid()::UUID);

-- Chaque utilisateur ne voit que ses propres données
CREATE POLICY user_data_own_row ON user_data
FOR ALL
USING (user_id = auth.uid()::UUID);

-- ── Trigger updated_at ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_user_data_updated_at ON user_data;
CREATE TRIGGER trg_user_data_updated_at
BEFORE UPDATE ON user_data
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
