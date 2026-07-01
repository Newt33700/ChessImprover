-- US 4.2 (reste) — Top 3 ouvertures par code ECO
-- Ajoute l'ECO/nom d'ouverture (headers PGN Chess.com) sur `games`, renseignés
-- par le worker d'analyse une fois la partie parsée.

ALTER TABLE games ADD COLUMN IF NOT EXISTS eco VARCHAR(10);
ALTER TABLE games ADD COLUMN IF NOT EXISTS opening_name TEXT;

CREATE INDEX IF NOT EXISTS idx_games_eco ON games (eco);
