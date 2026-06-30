-- EPIC 1 — Ingestion async & persistance des métriques d'analyse
-- US 1.1 : table `games` (statut d'analyse asynchrone)
-- US 1.2 : table `game_moves` (métriques par coup, bulk insert)

-- ── Parties soumises à l'analyse ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS games (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID        REFERENCES profiles(id) ON DELETE CASCADE,
  pgn           TEXT        NOT NULL,
  time_control  VARCHAR(32),
  user_color    VARCHAR(5)  NOT NULL DEFAULT 'white',
  result        VARCHAR(8),
  status        VARCHAR(16) NOT NULL DEFAULT 'processing',  -- processing | completed | failed
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_games_user_id ON games (user_id);
CREATE INDEX IF NOT EXISTS idx_games_status  ON games (status);

-- ── Métriques par coup ────────────────────────────────────────────────────────
-- Colonnes du DoD (score_cp, is_mate, mate_in, phase) + eval_before/eval_after
-- (texte de l'US) + cpl/position_type (nécessaires aux agrégations US 3.x).

CREATE TABLE IF NOT EXISTS game_moves (
  id            BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  game_id       UUID        NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  move_number   INT         NOT NULL,
  color         VARCHAR(5)  NOT NULL,           -- white | black
  move_san      VARCHAR(12) NOT NULL,
  eval_before   INT,                            -- cp, point de vue du camp au trait
  eval_after    INT,                            -- cp, point de vue du camp au trait
  score_cp      INT,                            -- éval réalisée (cp)
  cpl           INT,                            -- centipawn loss plafonné (0..400)
  is_mate       BOOLEAN     NOT NULL DEFAULT false,
  mate_in       INT,
  phase         VARCHAR(12) NOT NULL,           -- opening | middlegame | endgame
  position_type VARCHAR(12) NOT NULL DEFAULT 'neutral'  -- tactical | strategic | neutral
);

CREATE INDEX IF NOT EXISTS idx_game_moves_game_id ON game_moves (game_id);

-- ── Row Level Security ────────────────────────────────────────────────────────

ALTER TABLE games      ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_moves ENABLE ROW LEVEL SECURITY;

-- Chaque utilisateur ne voit que ses propres parties.
CREATE POLICY "games_own_row" ON games
  FOR ALL
  USING (user_id = auth.uid()::UUID);

-- Les coups suivent l'accès à la partie parente.
CREATE POLICY "game_moves_own_row" ON game_moves
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM games g
      WHERE g.id = game_moves.game_id
        AND g.user_id = auth.uid()::UUID
    )
  );
