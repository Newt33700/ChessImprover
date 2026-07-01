-- US 6.2 – Création automatique du profil : colonne de liaison Chess.com
-- Distincte du "username" (pseudo de connexion à l'app) : chess_username
-- permet de mémoriser le pseudo Chess.com de l'utilisateur, modifiable
-- indépendamment (US 6.3), sans jamais entrer en conflit avec le username.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS chess_username TEXT;
