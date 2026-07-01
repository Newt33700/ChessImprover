# User Stories – Chess Improver

## US 0 : Le Prérequis Absolu (Refonte Moteur & Stockage)

**Titre :** Remplacement de Stockfish asm.js par WASM et migration vers IndexedDB

**Description métier :**
En tant qu'application, je dois évaluer les coups avec précision (profondeur > 15) sans bloquer le navigateur, et stocker les données de manière pérenne sans saturer les 5Mo du localStorage.

**Règles de gestion & Architecture :**
- Remplacer stockfish.js v10 par Stockfish 16.1 WASM.
- Le Web Worker doit utiliser l'évaluation NNUE et renvoyer la Principal Variation (PV) sur au moins 3 demi-coups (nécessaire pour l'US 4).
- Implémenter un wrapper IndexedDB (vanilla) pour créer les tables : `games`, `srs_cards`, `openings_cache`.
- Au premier chargement, migrer silencieusement le localStorage existant vers IndexedDB.

**Exemples :**
- Le moteur ne doit plus répondre instantanément à depth 5, mais évaluer pendant au moins 500ms par coup ou jusqu'à depth 15.
- Le score de Mat (`score mate 2`) doit être converti en une valeur numérique extrême (ex: +10000 ou -10000) pour ne pas casser les calculs mathématiques futurs.

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code.
- Mutation testing obligatoire (Stryker JS pour le frontend).

**Statut :** ✅ Implémenté

---

## US 1 : Onglet Bilan des parties (Graphe d'avantage)

**Titre :** Génération du graphique de Win Probability (WP) d'une partie

**Description métier :**
En tant qu'utilisateur, je veux visualiser un graphique d'évolution de l'avantage (de 0% à 100%) tout au long de la partie pour repérer visuellement mes gaffes.

**Règles de gestion & Architecture :**
- Ne pas utiliser le cpLoss brut qui est illisible. Utiliser la formule de transformation :
  `WP = 50 + 50 * (2 / (1 + exp(-0.003682 * centipions))) - 1`
- Les Noirs gagnent = 0%, Les Blancs gagnent = 100%, Égalité = 50%.
- Utiliser l'API Canvas native ou une librairie très légère (ex: Chart.js) pour tracer la courbe en lisant le tableau `game.moves[]`.
- Rendre le graphique interactif : cliquer sur un point du graphe appelle `boardMgr.goToMove(index)`.

**Exemples :**
- Si le coup 14 donne un avantage blanc de +250 centipions, le point sur le graphe doit se situer à environ 71.5% en faveur des Blancs.
- Si le coup 15 est une gaffe (Mat en 2 pour les noirs), le graphe plonge à 0%.

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code.
- Mutation testing.

**Statut :** ✅ Implémenté

---

## US 2 : Onglet Ouvertures (Profilage W/D/L)

**Titre :** Tableau de bord des performances par ouverture jouée

**Description métier :**
En tant qu'utilisateur, je veux voir mes statistiques de victoires/nuls/défaites pour chaque ouverture afin d'optimiser mon répertoire.

**Règles de gestion & Architecture :**
- Requêter la nouvelle table IndexedDB `games`.
- Pour chaque partie, identifier le dernier coup validé par la fonction existante `_detectBookDepth()`. Prendre l'EPD (Extended Position Description) ou le nom de l'ouverture (header PGN `Opening`) comme clé primaire d'agrégation.
- Créer un tableau de statistiques croisées : Nom de l'ouverture | Jouée avec (Blanc/Noir) | Occurrences | Win % | Draw % | Loss %.
- UI : Afficher une jauge visuelle tricolore pour le ratio W/D/L.

**Exemples :**
- Le joueur a joué 15 fois la "Défense Sicilienne, Variante Najdorf" avec les Noirs. Le script agrège : 5 victoires, 2 nuls, 8 défaites. La jauge affichera 33% Vert, 13% Gris, 53% Rouge.

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code.
- Mutation testing.

**Statut :** ✅ Implémenté

---

## US 3 : Onglet Finales (Détection et Tablebases)

**Titre :** Évaluation de la technique de conversion en finale

**Description métier :**
En tant qu'utilisateur, je veux savoir si je gâche des positions de finales théoriquement gagnantes ou nulles.

**Règles de gestion & Architecture :**
- Créer une fonction `detectEndgamePhase(fen)` : Déclenchement si le matériel total (hors Rois et Pions) est <= 13 points (ex: 1 Tour (5) + 1 Fou (3) + 1 Cavalier (3) = 11).
- Isoler la précision (Accuracy) moyenne uniquement sur les coups joués après ce déclencheur.
- Intégration Syzygy : Si le nombre total de pièces sur l'échiquier est <= 7, faire un call asynchrone à `http://tablebase.lichess.ovh/standard?fen={FEN}`.
- Si l'évaluation passe de Win à Draw/Loss à cause d'un coup du joueur, taguer ce coup comme "Gaffe de Finale".

**Exemples :**
- Il ne reste que R+T contre R. Le joueur a les Blancs. L'API Syzygy dit "Win". Le joueur joue un coup, la FEN suivante envoyée à l'API dit "Draw" (pat). L'US comptabilise un échec de conversion.

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code. Mock obligatoire de l'API Lichess pour les tests.
- Mutation testing.

**Statut :** ✅ Implémenté

---

## US 4 : Onglet Puzzle (Câblage auto du SRS SM-2)

**Titre :** Génération et résolution de puzzles issus des gaffes personnelles

**Description métier :**
En tant qu'utilisateur, je veux que l'application génère automatiquement des exercices de répétition espacée (SRS) quand je fais une gaffe, pour m'entraîner à trouver le bon coup.

**Règles de gestion & Architecture :**
- Dans `_onMoveAccuracy()`, intercepter les coups tagués `blunder`.
- Appeler `SRS.createCard()` (actuellement orphelin dans le code) avec : la fen précédant la gaffe, et la séquence de la Principal Variation (PV) de Stockfish comme solution attendue.
- Dans le mode Exercice : Si l'utilisateur joue le premier coup de la PV, faire jouer la réponse forcée de l'adversaire (deuxième coup de la PV) par l'échiquier, puis attendre le troisième coup du joueur.
- Calcul de qualité : Si le joueur trouve la ligne complète : quality = 5. S'il joue un autre coup mais que l'évaluation reste positive : quality = 3. S'il se trompe : quality = 1.

**Exemples :**
- Le joueur rate une fourchette au coup 22. Le système sauvegarde la position au coup 21. Dans l'onglet Puzzle, le joueur doit jouer le mouvement de Cavalier optimal. S'il réussit, la carte passe à un intervalle de 6 jours (SM-2).

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code. Test spécifique sur l'algorithme d'espacement SM-2.
- Mutation testing.

**Statut :** ✅ Implémenté

---

## US 5 : Onglet Statistiques (Correction mathématique et tendances)

**Titre :** Suivi analytique de la progression Elo et précision

**Description métier :**
En tant qu'utilisateur, je veux suivre ma progression sur 7, 30 et 90 jours avec des formules d'évaluation fiables.

**Règles de gestion & Architecture :**
- Refonte de l'estimation Elo existante (EloEngine) : La formule linéaire `(acc * 10) + (eloOpp * 0.3)` est fausse. Implémenter une formule logistique qui tient compte de la Win Probability moyenne et bride les valeurs extrêmes sans écraser les performances parfaites.
- Requêter la base IndexedDB pour sortir les datas chronologiquement.
- Générer un double graphique (Line chart) : Courbe 1 = Elo estimé. Courbe 2 = Précision moyenne (Accuracy %).
- Appliquer un lissage (Moyenne mobile sur les 5 dernières parties) pour éviter les graphiques illisibles en dents de scie.

**Exemples :**
- Le joueur sélectionne "30 derniers jours". L'UI trace 20 points (ses 20 parties du mois), montrant une tendance de précision passant de 65% à 72%, et un Elo estimé passant de 1050 à 1180.

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code.
- Mutation testing.

**Statut :** ✅ Implémenté

---

## US 6 : Onglet Coach Perso (Agent Synthétique Local)

**Titre :** Génération d'un plan d'action d'entraînement dynamique

**Description métier :**
En tant qu'utilisateur, je veux que l'application croise toutes mes statistiques pour me donner un conseil d'entraînement unique et précis.

**Règles de gestion & Architecture :**
- Pas d'API externe (Full Offline). Créer une classe `PersonalCoach` basée sur un arbre de décision (Decision Tree) pur JavaScript.
- Le script analyse le JSON consolidé des US précédentes : (Taux de gaffes, pire ouverture W/D/L, accuracy en finale).
- Générer un string de diagnostic et un bouton HTML d'action liant vers le mode d'entraînement pertinent.

**Exemples :**
- Condition vérifiée : BlunderRate > 20% dans les 15 premiers coups.
  Output UI : "Tu perds trop vite tes parties à cause d'erreurs tactiques précoces." → [Bouton : Réviser mes ouvertures]
- Condition vérifiée : L'ouverture "Caro-Kann" a un winrate < 30% sur +10 parties.
  Output UI : "La Caro-Kann te coûte des points. Revois tes lignes."

**Exigences de Qualité :**
- Couverture par des TUs d'au moins 80% du nouveau code. Tests de tous les embranchements de l'arbre de décision.
- Mutation testing.

**Statut :** ✅ Implémenté

---

## US 7 : Authentification, Profil & Persistance Cloud

**Titre :** Création de compte, connexion JWT et synchronisation des données vers Supabase

**Description métier :**
En tant qu'utilisateur, je veux créer un compte et retrouver mes parties, mes cartes SRS et mes statistiques sur n'importe quel appareil.

**Règles de gestion & Architecture :**
- **Backend FastAPI** : endpoints `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`, `POST /sync`.
- **Mots de passe** : hashés via bcrypt (facteur de coût 12).
- **Tokens JWT** : HS256, expiration 30 jours. Stockés en localStorage côté client.
- **Base de données** : Supabase/PostgreSQL avec tables `profiles` et `user_data` (JSONB). Row Level Security activée.
- **Stratégie de synchronisation** : "Client Wins" — les données du client écrasent le serveur en cas de conflit sur un même `game_id` ou `card_id`.
- **Frontend** : module `auth.js` avec `signup()`, `login()`, `logout()`, `autoConnect()`, `syncData()`.

**Exemples :**
- Un utilisateur s'inscrit → token JWT reçu → stocké en `localStorage["ci_jwt"]`.
- Au rechargement, `autoConnect()` valide le token via `GET /auth/me` et restaure la session.
- `POST /sync` avec 5 parties → serveur les stocke et retourne la liste complète fusionnée.

**Schéma SQL (Supabase) :**
```sql
profiles   : id UUID, email TEXT UNIQUE, username TEXT UNIQUE, password_hash TEXT, created_at
user_data  : id UUID, user_id UUID FK→profiles, games JSONB, srs_cards JSONB, updated_at
```

**Exigences de Qualité :**
- Tests pytest couvrant : hash/verify, JWT create/decode, signup, login, me, sync (24 TUs).
- Mutation testing via mutmut sur `backend/app/domain/auth.py`.

**Statut :** ✅ Implémenté

---

## CI/CD 1 : Pipeline Frontend (Vercel)

**Titre :** Déploiement automatique du frontend sur Vercel via GitHub Actions

**Description métier :**
En tant qu'équipe, nous voulons que chaque push sur `main` affectant `frontend/**` déploie automatiquement l'application sur Vercel, après validation des tests.

**Règles de gestion :**
- Déclencheur : push ou PR sur `main`, filtre `frontend/**`.
- Job `test-frontend` : `npm ci` + `npm test -- --coverage` (seuils 80%).
- Job `deploy-frontend` (main seulement) : `vercel deploy --prod` via VERCEL_TOKEN.
- Secrets requis : `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.

**Statut :** ✅ Implémenté (`.github/workflows/deploy-frontend.yml`)

---

## CI/CD 2 : Pipeline Backend (Render)

**Titre :** Déploiement automatique du backend FastAPI sur Render via GitHub Actions

**Description métier :**
En tant qu'équipe, nous voulons que chaque push sur `main` affectant `backend/**` déploie automatiquement l'API sur Render, après validation des tests.

**Règles de gestion :**
- Déclencheur : push ou PR sur `main`, filtre `backend/**`.
- Job `test-backend` : `pip install -r requirements.txt` + `pytest tests/ -v`.
- Job `deploy-backend` (main seulement) : `curl -X POST $RENDER_DEPLOY_HOOK`.
- Secrets requis : `RENDER_DEPLOY_HOOK`, `JWT_SECRET`.

**Statut :** ✅ Implémenté (`.github/workflows/deploy-backend.yml`)

---

## CI/CD 3 : Pipeline Database (Supabase)

**Titre :** Application automatique des migrations SQL sur Supabase via GitHub Actions

**Description métier :**
En tant qu'équipe, nous voulons que chaque modification de `supabase/migrations/**` pousse automatiquement la migration vers Supabase en production.

**Règles de gestion :**
- Déclencheur : push ou PR sur `main`, filtre `supabase/migrations/**`.
- Job `lint-migrations` : `sqlfluff lint` avec dialecte `postgres`.
- Job `push-migrations` (main seulement) : `supabase db push` via CLI.
- Secrets requis : `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, `SUPABASE_PROJECT_ID`.

**Statut :** ✅ Implémenté (`.github/workflows/deploy-database.yml`)

---

# EPIC : Statistiques Avancées (type Chess.com Premium)

> Fonctionnalité multi-US. Architecture : Frontend (Vercel) · Backend (Render/Python) · BDD (Supabase/Postgres).
> Le cœur algorithmique (EPIC 2 & 3) est implémenté en premier : modules Python purs, testés à fond, indépendants de l'infrastructure. EPIC 1 (ingestion async + schéma Supabase) et EPIC 4 (matrice UI mobile) restent à faire.

## US 2.1 : Segmentation automatique des phases de jeu

**Description :** diviser une partie en Ouverture / Milieu de jeu / Finale pour isoler les performances par phase.

**Règles de gestion :**
- Ouverture : du coup 1 jusqu'à la sortie du livre d'ouvertures (détecteur injectable `in_book`), limite dure au coup 15 (30 demi-coups).
- Finale (matériel cumulé des deux camps, Rois exclus, Pion=1/Cavalier=3/Fou=3/Tour=5/Dame=9) :
  - aucune Dame ET matériel total ≤ 16 points, **OU**
  - Dames présentes mais ≤ 1 pièce lourde/mineure par camp en plus de la Dame.
  - Une fois déclenchée, la finale est verrouillée (latch).
- Milieu de jeu : entre la fin de l'ouverture et le début de la finale.

**Statut :** ✅ Implémenté (`backend/app/domain/phases.py`, `tests/test_phases.py`)

## US 2.2 : Calcul de la perte de centipions (ACPL) calibrée

**Description :** évaluer chaque coup (Stockfish profondeur 14) et calculer la perte de centipions, agrégée en ACPL par phase.

**Règles de gestion :**
- `CPL = Eval_meilleurCoup − Eval_coupJoué` (point de vue du camp au trait), plancher 0.
- Plafonnement des gaffes : CPL plafonné à 400 centipions.
- ACPL = moyenne des CPL, calculée séparément par phase.
- Source des évaluations abstraite derrière `EngineProvider` : implémentation « évals fournies par le client » active ; implémentation « Stockfish natif Render » branchable.

**Statut :** ✅ Implémenté (`backend/app/domain/acpl.py`, `backend/app/infrastructure/engine.py`, `tests/test_acpl.py`, `tests/test_engine.py`)

## US 3.1 : Mapping ACPL → Classement Elo virtuel

**Description :** transformer l'ACPL en Elo virtuel compréhensible (« vous avez joué la finale comme un 2100 »).

**Règles de gestion :**
- Échelle empirique interpolée linéairement : ACPL ≤10→2800, 20→2400, 35→1900, 50→1500, 75→1100, ≥110→600.
- Bonus de cadence : Bullet +200, Blitz +100, Rapide/Daily +0 (à ACPL égal).
- Bornes finales [600, 3000].

**Statut :** ✅ Implémenté (`backend/app/domain/virtual_elo.py`, `tests/test_virtual_elo.py`)

## US 3.2 : Isolation Tactique vs Stratégie

**Description :** classer chaque position en « Tactique » ou « Stratégie » et en déduire des Elo virtuels distincts.

**Règles de gestion :**
- Tactique : 2ᵉ meilleur coup perd > 150 cp vs le meilleur. Meilleur coup joué → réussie ; perte > 100 cp → loupée. Elo tactique proportionnel au ratio de réussite (mapping linéaire 600→3000).
- Stratégie : top 3 coups séparés de < 40 cp (position calme). Elo stratégie = ACPL exclusif des positions calmes mappé via US 3.1.

**Statut :** ✅ Implémenté (`backend/app/domain/move_class.py`, `tests/test_move_class.py`)

## US 4.1 : Tableau matriciel global des Statistiques Avancées

**Description :** matrice cadence × catégorie d'Elo virtuel, mobile-optimized, zéro calcul client.

**Règles de gestion :**
- Lignes Bullet/Blitz/Rapide × colonnes Classement/Ouvertures/Tactique/Stratégie/Finales.
- Cellule = Elo virtuel ; couleur désaturée verte si > classement actuel, orange/rouge si inférieur (intensité selon l'écart, seuil fort à 150).
- Le frontend appelle `GET /api/v1/stats/summary?period=` (zéro calcul client) ; fallback sur données de démo tant que l'EPIC 1 n'est pas branché.

**Statut :** ✅ Implémenté bout en bout — frontend (`frontend/js/advanced_stats.js`, vue plein écran `#advstats-col`) + backend (`GET /api/v1/stats/summary`, EPIC 1).

## US 4.2 : Vues détaillées par catégorie (Deep Dive mobile)

**Description :** détail par catégorie adapté au mobile (gauge Héros + deltas par phase + métriques Finales/Tactiques/Ouvertures).

**Règles de gestion :**
- Onglets de cadence + carte « Héros » (niveau estimé + gauge) + liste « Détail par phase » (Elo + delta coloré vs classement).
- Finales : tuiles Taux de conversion (avantage ≥ +1.50) et Taux de résilience (position perdante ≤ −1.50).
- Tactiques : carte rating de puzzles (à réviser / résolus / série) **+ mini-indicateur circulaire du taux de réussite tactique** (`summary.tactics.successRatio`, agrégé sur toutes les parties analysées, sans bucketing par cadence).
- Ouvertures : **top 3 des ouvertures les plus jouées** par code ECO (`summary.topOpenings`), triées par nombre de parties décroissant, avec l'Elo virtuel « Ouvertures » associé (ACPL des coups d'ouverture du groupe, **sans bonus de cadence** — un groupe ECO peut mélanger plusieurs cadences). L'ECO/nom d'ouverture sont extraits des en-têtes PGN Chess.com (`ECO`/`ECOUrl`) par le worker d'analyse ; les parties sans ECO (PGN non issu de Chess.com) sont exclues du classement.

**Statut :** ✅ Implémenté bout en bout, DoD complète :
- Migration `20260701164500_games_eco.sql` (colonnes `eco`/`opening_name` sur `games`).
- `backend/app/domain/analysis_pipeline.py` (`_extract_opening`), `backend/app/domain/stats_aggregator.py` (`top_openings`, `_tactical_success_ratio_all`).
- `frontend/js/advanced_stats.js` (`tacticSuccessGaugeHtml`, SVG circulaire pur).
- Tests : extensions `test_analysis_pipeline.py`, `test_stats_aggregator.py`, `advanced_stats.test.js`.

## US 1.1 : Soumission asynchrone de PGN

**Description :** envoyer un PGN au serveur qui crée une ligne `games` et délègue l'analyse à un worker async (évite les timeouts Render).

**Règles de gestion :**
- `POST /api/v1/games/analyze` accepte un `pgn` ou une liste `game_ids`.
- Crée la ligne `games` au statut `processing`, répond immédiatement en `202` + UUID.
- Tâche de fond (`BackgroundTasks` FastAPI) lance le parsing + l'analyse.

**Statut :** ✅ Implémenté (`backend/app/routers/games.py`, `supabase/migrations/20260701000000_advanced_stats.sql`, `tests/test_games_api.py`). Mode in-memory en dev/test ; connexion Supabase réelle à brancher (cf. §10.1).

## US 1.2 : Persistance des métriques par coup

**Description :** stocker l'évaluation de chaque coup dans `game_moves` pour recalculer les stats sans réanalyser.

**Règles de gestion :**
- Table `game_moves` liée à `games` : `move_number`, `color`, `move_san`, `eval_before`, `eval_after`, `score_cp`, `cpl`, `is_mate`, `mate_in`, `phase`, `position_type`.
- Insertion groupée (bulk) en fin d'analyse, puis `games.status = 'completed'`.

**Statut :** ✅ Implémenté (`backend/app/domain/analysis_pipeline.py`, `infrastructure/db_client.py`, `tests/test_analysis_pipeline.py`, `tests/test_db_games.py`).

## Endpoint d'agrégation `GET /api/v1/stats/summary` (US 4.1)

**Statut :** ✅ Implémenté (`backend/app/domain/stats_aggregator.py`, `tests/test_stats_aggregator.py`) — alimente la matrice/le deep-dive du frontend ; le frontend bascule du mock au réel en pointant `window.STATS_API_BASE`.

---

## US 5.1 : Historisation et Visualisation de la Progression (Courbes)

**En tant qu'** utilisateur de Chessimprover
**Je veux** que le système enregistre un instantané de mes performances Elo virtuelles après chaque analyse de partie
**Afin de** visualiser un graphique d'évolution de mon niveau sur les 30 derniers jours.

**Critères d'Acceptation (DoD) :**
- Une ligne est enregistrée automatiquement dans `user_progress_history` (`user_id`, `game_id`, `cadence`, `elo_openings`, `elo_tactics`, `elo_strategy`, `elo_endgames`, `recorded_at`) après chaque analyse réussie dont la cadence est reconnue.
- `GET /api/v1/stats/history?cadence=blitz&days=30` renvoie l'historique chronologique (ascendant) filtré aux `days` derniers jours.
- Frontend : courbe Chart.js (4 séries Ouvertures/Tactique/Stratégie/Finales) dans la carte PROGRESSION de la vue Stats Avancées, avec 4 chips à cocher pour masquer/afficher une série sans reconstruire le graphe.
- UX mobile : le graphe est dans un conteneur `overflow-x: auto` dont la largeur minimale grandit avec le nombre de points, pour rester lisible en scrollant horizontalement sur petit écran.

**Règles de gestion :**
- Un snapshot n'est enregistré **que si la cadence est reconnue** (`classify_cadence` non `None`) — sinon aucune ligne n'est créée (évite de polluer une courbe avec une cadence indéterminée).
- Les Elo par catégorie du snapshot réutilisent **exactement** `stats_aggregator.category_elos` (même calcul que la matrice US 4.1), pour que le dernier point de la courbe corresponde à la ligne courante de la matrice.
- Le filtrage temporel (`days`) est fait en Python (`progress_history.filter_history_by_days`), pas en SQL, pour un comportement identique en in-memory et en Postgres. `days ≤ 0` renvoie une liste vide.
- Un échec d'enregistrement du snapshot n'entraîne **jamais** l'échec de l'analyse (garde-fou séparé dans le worker) ; un échec d'accès à l'historique dégrade en `history: []` (200) plutôt qu'un 500.

**Statut :** ✅ Implémenté :
- Backend : `supabase/migrations/20260701120000_progress_history.sql`, `backend/app/domain/progress_history.py`, `backend/app/infrastructure/db_client.py` + `pg_repository.py` (méthodes `create_progress_snapshot`/`get_progress_history`), `backend/app/routers/games.py` (`GET /api/v1/stats/history`, snapshot auto dans `run_analysis`).
- Frontend : `frontend/js/api_client.js` (`getStatsHistory`), `frontend/js/advanced_stats.js` (`fetchHistory`, `buildProgressDatasets`, `renderProgressChart`, `toggleProgressSeries`), carte PROGRESSION dans `index.html`.
- Tests : `test_progress_history.py`, extensions `test_db_games.py`/`test_pg_repository.py`/`test_games_api.py`, `advanced_stats.test.js`/`api_client.test.js`.

---

## EPIC 6 : Gestion d'Identité et Personnalisation (Auth & Profil)

**Objectif :** garantir l'isolation des données par utilisateur et permettre la synchronisation avec l'écosystème Chess.com.

> **Note d'architecture :** l'app dispose déjà d'un système d'authentification JWT maison (US 7 : `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`, tokens HMAC-SHA256, table `profiles`), déployé en production. Les US ci-dessous sont adaptées à cette architecture existante plutôt qu'à un remplacement par le service Auth natif de Supabase (`supabase.auth.signUp`/`auth.users`/`auth.uid()`), ce qui casserait l'auth déjà livrée. Concrètement : « l'utilisateur authentifié » = le `sub` du JWT maison décodé par la dépendance FastAPI `_current_user`, et « déclencheur à la création du compte » = le code de `POST /auth/signup` (pas un trigger Postgres sur `auth.users`, table qui n'existe pas dans ce schéma).

### US 6.1 : Inscription et Authentification Sécurisée

**Description :** en tant qu'utilisateur, je veux créer un compte et me connecter de façon sécurisée, avec un retour clair en cas d'erreur (email invalide, mot de passe trop court).

**Critères d'Acceptation (DoD) :**
- Inscription (`Auth.signup`) et connexion (`Auth.login`) via les endpoints JWT maison existants ; succès → fermeture de la modale et accès au tableau de bord.
- Le format de l'email est validé (rejet si absence de `@`/domaine), pas seulement sa longueur minimale.
- Les erreurs (email invalide, mot de passe trop court, identifiants incorrects) sont affichées de façon lisible dans l'UI, y compris pour les erreurs de validation Pydantic (422, qui renvoient une liste de détails et non une simple chaîne).

**Statut :** ✅ Implémenté — `backend/app/domain/models.py` (`UserCreate._validate_email_format`, regex `_EMAIL_RE`), `frontend/js/auth.js` (`_extractErrorMessage`, gère `detail` chaîne ou liste Pydantic 422). Tests : `backend/tests/test_auth.py` (`test_signup_invalid_email_format_returns_422`, `test_signup_invalid_email_error_mentions_email`, `test_signup_password_too_short_returns_422`), `frontend/tests/auth.test.js` (nouveau fichier, 7 tests).

### US 6.2 : Création automatique du Profil Utilisateur

**Description :** à la création d'un compte, un profil doit être créé automatiquement, sans étape manuelle supplémentaire.

**Critères d'Acceptation (DoD) :**
- Équivalent du « trigger » : `POST /auth/signup` crée atomiquement la ligne `profiles` (`id`, `email`, `username`, `password_hash`, `created_at`) — déjà le cas dans `db_client.create_user`/`pg_repository`.
- Ajouter une colonne `chess_username` (nullable) sur `profiles`, distincte du `username` de connexion.

**Statut :** ✅ Implémenté — migration `supabase/migrations/20260701172219_profiles_chess_username.sql` (`ALTER TABLE profiles ADD COLUMN IF NOT EXISTS chess_username TEXT`), `db_client.create_user` initialise `chess_username: None`, `UserProfile` (modèle Pydantic) et les réponses `/auth/signup`/`/auth/login`/`/auth/me` exposent le champ. Pas encore modifiable via API (cf. US 6.3, qui ajoutera l'endpoint d'écriture + la validation de format + l'UI profil). Tests : `test_signup_response_includes_chess_username_field`, `test_signup_stores_chess_username_none_in_db`, `test_me_includes_chess_username_field` dans `backend/tests/test_auth.py`.

### US 6.3 : Liaison au compte Chess.com

**Description :** en tant qu'utilisateur, je veux enregistrer mon pseudo Chess.com sur mon profil (au lieu d'un simple champ local perdu si je change de navigateur), pour que le tableau de bord précharge automatiquement mes parties.

**Critères d'Acceptation (DoD) :**
- Page/section profil permettant de lire et modifier `chess_username`.
- Validation basique du format (pseudo Chess.com : caractères alphanumériques/`_`/`-`, longueur raisonnable).
- `PATCH /auth/me` (ou équivalent) restreint à l'utilisateur courant (identifié via le JWT) — un utilisateur ne peut modifier que son propre `chess_username`.
- Le champ `signup-chess-username` actuellement stocké uniquement en `localStorage` (`frontend/js/app.js`) est migré vers ce nouveau champ persistant côté serveur.

**Statut :** 🔜 Backlog.

### US 6.4 : Isolation des données par user_id

**Description :** garantir qu'un utilisateur ne peut jamais lire ou écrire les données d'un autre utilisateur, y compris en cas de manipulation du payload côté client.

**Critères d'Acceptation (DoD) :**
- Les routes `games`/`stats` dérivent `user_id` du JWT (dépendance FastAPI `Depends`) et **non** d'un champ `user_id` fourni par le client dans le body/query — faille actuelle : `POST /api/v1/games/analyze` et `GET /api/v1/stats/summary` acceptent aujourd'hui un `user_id` arbitraire non authentifié.
- Toutes les requêtes SQL sur `games`/`game_moves`/`user_progress_history` restent filtrées par ce `user_id` authentifié (déjà le cas au niveau SQL dans `pg_repository.py`, la faille est en amont au niveau des routes).

**Statut :** 🔜 Backlog.

---

## EPIC 7 : Gestion du Cycle de Vie des Analyses (Persistance & Cache)

**Objectif :** offrir une UX instantanée après une première analyse et garantir que chaque utilisateur ne voit que ses propres données.

### US 7.1 : Récupération des parties par utilisateur

**Description :** au chargement du tableau de bord, l'utilisateur retrouve la liste de ses parties déjà analysées, sans tout ré-analyser.

**Critères d'Acceptation (DoD) :**
- `GET /api/v1/games` (nouveau) filtré côté SQL par l'utilisateur authentifié (JWT), réutilisant `get_games_for_user`.
- Le frontend appelle cet endpoint au chargement du dashboard, avec un état de chargement (loader).

**Statut :** 🔜 Backlog.

### US 7.2 : Hashage PGN et prévention du recalcul

**Description :** éviter de ré-analyser (coûteux en CPU/Stockfish) un PGN déjà soumis.

**Critères d'Acceptation (DoD) :**
- Hash SHA-256 du PGN calculé avant analyse (`hashlib`).
- Colonne `pgn_hash` sur `games` (index unique).
- Avant analyse : `SELECT * FROM games WHERE pgn_hash = %s AND user_id = %s` ; si trouvé → renvoyer la partie existante sans relancer Stockfish, sinon analyser normalement (US 2.1/1.1).

**Statut :** 🔜 Backlog.

### US 7.3 : Table de correspondance « Partie-Étude »

**Description :** permettre de marquer une partie comme « déjà étudiée » pour la distinguer visuellement des parties encore à revoir.

**Critères d'Acceptation (DoD) :**
- Colonne `is_reviewed` (boolean, défaut `false`) sur `games`.
- `PATCH /api/v1/games/{game_id}/status` pour basculer l'état (restreint à l'utilisateur propriétaire).
- Distinction visuelle (coche verte) dans le dashboard pour les parties `is_reviewed = true`.

**Statut :** 🔜 Backlog.
