-- EPIC 12 — Mode "Tactical Sprint" (Social & Compétitif, US 11.1/11.2)
-- Chrono anti-triche géré côté serveur (started_at/now(), pas un temps
-- déclaré par le client). `moves` stocke la séquence de coups résolus
-- (JSONB, [{problem_id, move, elapsed_ms}]) pour le replay "Ghost" du
-- meilleur sprint (US 11.2) — un simple GET/polling suffit côté frontend,
-- pas de WebSocket (cf. recommandation PO).
-- Lecture publique (leaderboard/Ghost = compétitif entre utilisateurs) mais
-- écriture restreinte au propriétaire, à l'inverse des autres tables du
-- schéma qui sont privées de bout en bout.

CREATE TABLE IF NOT EXISTS tactical_sprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    score INTEGER NOT NULL DEFAULT 0,
    problems_solved_count INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    moves JSONB NOT NULL DEFAULT '[]'::JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tactical_sprints_user
ON tactical_sprints (user_id);

CREATE INDEX IF NOT EXISTS idx_tactical_sprints_score
ON tactical_sprints (score DESC);

ALTER TABLE tactical_sprints ENABLE ROW LEVEL SECURITY;

-- Lecture publique : le mode Ghost (US 11.2) doit pouvoir rejouer le
-- meilleur sprint, quel que soit son auteur.
CREATE POLICY tactical_sprints_read_all ON tactical_sprints
FOR SELECT
USING (true);

-- Écriture restreinte au propriétaire du sprint.
CREATE POLICY tactical_sprints_insert_own ON tactical_sprints
FOR INSERT
WITH CHECK (user_id = auth.uid()::UUID);

CREATE POLICY tactical_sprints_update_own ON tactical_sprints
FOR UPDATE
USING (user_id = auth.uid()::UUID);
