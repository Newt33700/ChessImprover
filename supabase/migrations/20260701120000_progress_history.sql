-- US 5.1 — Historisation et Visualisation de la Progression
-- Snapshot des Elo virtuels après chaque analyse, pour tracer une courbe
-- d'évolution par cadence sur les N derniers jours.

CREATE TABLE IF NOT EXISTS user_progress_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES profiles (id) ON DELETE CASCADE,
    game_id UUID REFERENCES games (id) ON DELETE SET NULL,
    -- bullet | blitz | rapid | daily
    cadence VARCHAR(10) NOT NULL,
    elo_openings INT NOT NULL,
    elo_tactics INT NOT NULL,
    elo_strategy INT NOT NULL,
    elo_endgames INT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_progress_history_user_cadence
ON user_progress_history (user_id, cadence, recorded_at);

-- Row Level Security

ALTER TABLE user_progress_history ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que ses propres snapshots.
CREATE POLICY user_progress_history_own_row ON user_progress_history
FOR ALL
USING (user_id = auth.uid()::UUID);
