-- EPIC 38 — Lotus Mastery Engine (Ouvertures) : arbre de répertoire
-- + progression
--
-- REMPLACE l'ancien répertoire de lignes SM-2 de l'EPIC 9 (table
-- `opening_repertoire`, migration 20260701223519) par un modèle en arbre :
-- chaque nœud est une POSITION (pas une ligne entière), la progression est
-- suivie nœud par nœud avec un score de maîtrise et un déblocage progressif
-- des enfants. `opening_repertoire` n'est PAS supprimée par cette migration
-- (pas de DROP destructif sur des données existantes) — simplement plus
-- utilisée par le code applicatif à partir de cet EPIC (cf. README §9).
--
-- `user_id` est ajouté sur `repertoire_nodes` (absent de la spec initiale)
-- pour l'isolation par utilisateur (RLS), cohérent avec le reste du
-- schéma — chaque répertoire importé (`repertoire_id`) appartient à un
-- seul joueur.

-- Arbre STATIQUE : construit une fois par l'import PGN
-- (routers/openings_trainer.py), jamais modifié par les tentatives de
-- l'utilisateur (voir user_node_progress).
CREATE TABLE IF NOT EXISTS repertoire_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repertoire_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    parent_id UUID REFERENCES repertoire_nodes (id) ON DELETE CASCADE,
    -- NULL pour un nœud racine (position de départ standard)
    move_san TEXT,
    -- position APRÈS move_san (position de départ standard si racine)
    move_fen TEXT NOT NULL,
    depth_level INTEGER NOT NULL,
    is_mainline BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_repertoire_nodes_repertoire
ON repertoire_nodes (repertoire_id);

CREATE INDEX IF NOT EXISTS idx_repertoire_nodes_parent
ON repertoire_nodes (parent_id);

CREATE INDEX IF NOT EXISTS idx_repertoire_nodes_user
ON repertoire_nodes (user_id);

ALTER TABLE repertoire_nodes ENABLE ROW LEVEL SECURITY;

CREATE POLICY repertoire_nodes_own_row ON repertoire_nodes
FOR ALL
USING (user_id = auth.uid()::UUID);

-- Progression DYNAMIQUE : une ligne par nœud DÉBLOQUÉ pour un utilisateur.
-- Absence de ligne = nœud verrouillé ("locked", jamais stocké
-- explicitement — règle métier du moteur de déblocage,
-- domain/mastery_engine.py).
CREATE TABLE IF NOT EXISTS user_node_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles (id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES repertoire_nodes (id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'learning'
    CHECK (status IN ('learning', 'review', 'mastered')),
    mastery_score INTEGER NOT NULL DEFAULT 0
    CHECK (mastery_score BETWEEN 0 AND 100),
    srs_interval INTEGER NOT NULL DEFAULT 1,
    next_review_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, node_id)
);

-- Requête de priorité du générateur de sessions
-- (routers/openings_trainer.py) : review dû -> learning -> rien. Un index
-- composite couvre les deux branches.
CREATE INDEX IF NOT EXISTS idx_user_node_progress_session
ON user_node_progress (user_id, status, next_review_date);

ALTER TABLE user_node_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_node_progress_own_row ON user_node_progress
FOR ALL
USING (user_id = auth.uid()::UUID);
