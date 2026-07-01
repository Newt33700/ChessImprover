-- US 7.2 – Hashage PGN et prévention du recalcul
-- Un même PGN déjà soumis par un utilisateur ne doit pas relancer une
-- analyse Stockfish coûteuse. L'unicité est scopée par utilisateur (et non
-- globale) : deux utilisateurs différents peuvent légitimement soumettre le
-- même texte PGN (ex. une partie célèbre partagée).

ALTER TABLE games ADD COLUMN IF NOT EXISTS pgn_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_games_user_pgn_hash
ON games (user_id, pgn_hash)
WHERE pgn_hash IS NOT NULL;
