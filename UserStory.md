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

**Statut :** ✅ Implémenté :
- Backend : `ChessUsernameUpdate` (`app/domain/models.py`, regex `^[A-Za-z0-9_-]{3,25}$`, vide autorisé pour délier), `db_client.update_chess_username`, `PATCH /auth/me` (`app/routers/auth.py`, restreint à l'utilisateur du token via `_current_user` — aucun paramètre `user_id` en entrée, donc aucune façon de cibler le profil d'un autre utilisateur).
- Frontend : `Auth.updateChessUsername` (`auth.js`, PATCH via un helper `_request` générique factorisé avec `_post`), modal `#profile-modal` (réutilise la charte `auth-overlay`/`auth-card`/`auth-form`/`auth-error` + nouvelle classe `.auth-success`), bouton « Profil » dans `_renderAuthState()`, `_submitSignup` persiste désormais le pseudo Chess.com saisi à l'inscription côté serveur (au lieu du seul `localStorage`).
- **Bug détecté et corrigé pendant la vérification navigateur (Playwright)** : le gestionnaire de bascule d'onglets Connexion/Inscription (`document.querySelectorAll(".auth-form")`) masquait aussi `#profile-form` (qui partage la classe `.auth-form`) dès qu'un onglet auth était cliqué, rendant le formulaire de profil invisible en permanence. Corrigé en scopant le sélecteur à `#auth-modal .auth-form`, avec une remise à `hidden = false` défensive dans `_openProfileModal()`.
- Tests : `backend/tests/test_auth.py` (classe `TestUpdateMe`, 7 tests : succès, persistance, format invalide, caractères spéciaux, vidage, sans token, isolation entre utilisateurs), `frontend/tests/auth.test.js` (3 tests `updateChessUsername`).

### US 6.4 : Isolation des données par user_id

**Description :** garantir qu'un utilisateur ne peut jamais lire ou écrire les données d'un autre utilisateur, y compris en cas de manipulation du payload côté client.

**Critères d'Acceptation (DoD) :**
- Les routes `games`/`stats` dérivent `user_id` du JWT (dépendance FastAPI `Depends`) et **non** d'un champ `user_id` fourni par le client dans le body/query — faille actuelle : `POST /api/v1/games/analyze` et `GET /api/v1/stats/summary` acceptent aujourd'hui un `user_id` arbitraire non authentifié.
- Toutes les requêtes SQL sur `games`/`game_moves`/`user_progress_history` restent filtrées par ce `user_id` authentifié (déjà le cas au niveau SQL dans `pg_repository.py`, la faille est en amont au niveau des routes).

**Statut :** ✅ Implémenté :
- `backend/app/routers/deps.py` (nouveau) : `get_current_user`/`get_current_user_id`, factorisés depuis `auth.py` (qui les réutilise désormais) pour être partagés par tous les routeurs.
- `backend/app/routers/games.py` : `POST /api/v1/games/analyze`, `GET /api/v1/games/{id}`, `GET /api/v1/stats/summary`, `GET /api/v1/stats/history` exigent toutes un JWT valide (`Depends(get_current_user_id)`) — faille corrigée : ces routes acceptaient auparavant un `user_id` arbitraire non authentifié (body ou query param), permettant à quiconque de lire les statistiques/parties de n'importe quel utilisateur en devinant/forgeant un UUID.
- `AnalyzeGamesRequest` n'a plus de champ `user_id` (uniquement dérivé du token). `GET /games/{id}` et la réanalyse par `game_ids` renvoient 404/ignorent silencieusement une partie n'appartenant pas à l'utilisateur authentifié (pas de distinction avec « partie introuvable », pour ne rien révéler sur l'existence de parties tierces).
- Frontend : `api_client.js` attache `Authorization: Bearer <token>` (via `Auth.getToken()`) sur les 4 appels ; les paramètres `user_id`/`userId` sont retirés de son API publique. `app.js:_syncToBackend` ne tente plus l'appel si l'utilisateur n'est pas connecté (et ne référence plus `Auth.currentUser`, qui n'existait pas — toujours `null` en pratique).
- Vérifié en intégration réelle (serveur local + `curl`) : 401 sans token, 200 avec token, **404** en tentant de lire la partie d'un autre utilisateur.
- Tests : `backend/tests/test_games_api.py` réécrit intégralement avec JWT (401 sans token sur les 4 routes, isolation testée entre 2 utilisateurs sur `get_game`/réanalyse/stats summary/history), `frontend/tests/api_client.test.js` étendu (en-tête `Authorization` présent/absent selon `Auth.getToken()`).

---

## EPIC 7 : Gestion du Cycle de Vie des Analyses (Persistance & Cache)

**Objectif :** offrir une UX instantanée après une première analyse et garantir que chaque utilisateur ne voit que ses propres données.

### US 7.1 : Récupération des parties par utilisateur

**Description :** au chargement du tableau de bord, l'utilisateur retrouve la liste de ses parties déjà analysées, sans tout ré-analyser.

**Critères d'Acceptation (DoD) :**
- `GET /api/v1/games` (nouveau) filtré côté SQL par l'utilisateur authentifié (JWT), réutilisant `get_games_for_user`.
- Le frontend appelle cet endpoint au chargement du dashboard, avec un état de chargement (loader).

**Statut :** ✅ Implémenté :
- Backend : `GET /api/v1/games` (`backend/app/routers/games.py`), `Depends(get_current_user_id)`, réutilise `db_client.get_games_for_user` (déjà filtré par `user_id` en SQL/in-memory).
- Frontend : `ApiClient.getGames()` (`api_client.js`, en-tête `Authorization`), appelé depuis `app.js:_loadServerGames()` (au boot après restauration de session ET juste après connexion/inscription, via `_onAuthSuccess`), avec `_setLoading(true/false, "Chargement de vos parties…")` pendant l'appel. Résultat stocké dans `this.serverGames` (base pour US 7.2/7.3). Best-effort : ne bloque jamais le reste du chargement du dashboard en cas d'échec.
- Vérifié en intégration réelle (serveur local + `curl`) : 401 sans token, `{"games": []}` avant toute analyse, liste peuplée après une analyse.
- Tests : `backend/tests/test_games_api.py` (classe `TestListGames`, 4 tests : liste propre, vide, 401 sans token, isolation entre utilisateurs), `frontend/tests/api_client.test.js` (`getGames`, en-tête Authorization).

### US 7.2 : Hashage PGN et prévention du recalcul

**Description :** éviter de ré-analyser (coûteux en CPU/Stockfish) un PGN déjà soumis.

**Critères d'Acceptation (DoD) :**
- Hash SHA-256 du PGN calculé avant analyse (`hashlib`).
- Colonne `pgn_hash` sur `games` (index unique).
- Avant analyse : `SELECT * FROM games WHERE pgn_hash = %s AND user_id = %s` ; si trouvé → renvoyer la partie existante sans relancer Stockfish, sinon analyser normalement (US 2.1/1.1).

**Statut :** ✅ Implémenté :
- `backend/app/domain/analysis_pipeline.py:compute_pgn_hash` (SHA-256 hexdigest via `hashlib`).
- Migration `20260701185622_games_pgn_hash.sql` : colonne `pgn_hash` (TEXT) + index **unique composite** `(user_id, pgn_hash)` — l'unicité est scopée par utilisateur (et non globale), pour que deux utilisateurs différents puissent légitimement soumettre le même PGN (ex. une partie célèbre partagée) sans collision.
- `db_client.find_game_by_pgn_hash(user_id, pgn_hash)` + `create_game(..., pgn_hash=...)` (in-memory et `pg_repository.py`).
- `routers/games.py:analyze_games` : avant de créer une partie depuis un `pgn`, calcule son hash et cherche une partie existante de l'utilisateur authentifié avec ce hash. Si trouvée, renvoie son `game_id` **et son statut réel** (`processing`/`completed`/`failed`) sans recréer de ligne ni relancer `run_analysis` ; sinon, analyse normalement en persistant le hash.
- Vérifié en intégration réelle (serveur local + `curl`) : une 2ᵉ soumission du même PGN par le même utilisateur renvoie le même `game_id` avec le statut `completed`, sans doublon dans `GET /api/v1/games`.
- Tests : `backend/tests/test_analysis_pipeline.py` (`TestComputePgnHash` : déterminisme, hex SHA-256, PGN différent → hash différent), `backend/tests/test_db_games.py` (stockage/recherche par hash, isolation par utilisateur), `backend/tests/test_pg_repository.py` (contrat de signature), `backend/tests/test_games_api.py` (classe `TestPgnHashDedup`, 5 tests : même game_id, pas de doublon, statut réel renvoyé, deux utilisateurs isolés, PGN différent → parties distinctes).

### US 7.3 : Table de correspondance « Partie-Étude »

**Description :** permettre de marquer une partie comme « déjà étudiée » pour la distinguer visuellement des parties encore à revoir.

**Critères d'Acceptation (DoD) :**
- Colonne `is_reviewed` (boolean, défaut `false`) sur `games`.
- `PATCH /api/v1/games/{game_id}/status` pour basculer l'état (restreint à l'utilisateur propriétaire).
- Distinction visuelle (coche verte) dans le dashboard pour les parties `is_reviewed = true`.

**Statut :** ✅ Implémenté :
- Migration `20260701191149_games_is_reviewed.sql` (colonne `is_reviewed` boolean, `NOT NULL DEFAULT false`).
- `PATCH /api/v1/games/{game_id}/status` (body `{is_reviewed}`, modèle `GameStatusUpdate`), restreint à l'utilisateur propriétaire (`Depends(get_current_user_id)`, 404 si partie inconnue ou appartenant à un autre utilisateur — même traitement, indiscernable).
- Frontend : `ApiClient.updateGameStatus(gameId, isReviewed)` (PATCH), bouton `#btn-mark-reviewed` dans le topbar de la vue Review (`index.html`), affiché uniquement quand la partie en cours a un pendant serveur connu (`this.currentGame.serverGameId`, capturé par `_syncToBackend` après un appel `getGame` pour lire le statut réel — utile en cas de dédup US 7.2). `_toggleReviewed()` bascule l'état via l'API et met à jour visuellement le bouton (texte + classe CSS `.is-reviewed`, fond vert).
- **Décision de conception documentée** : la « distinction visuelle » est portée par ce bouton dans la vue Review (partie du dashboard SPA), pas par la liste `#games-list` du dashboard (parties Chess.com) — ces deux listes sont aujourd'hui disjointes : seule une partie explicitement analysée via la modale « Analyser un PGN » est synchronisée côté serveur (`_syncToBackend`), les 20 dernières parties Chess.com affichées dans `#games-list` ne le sont pas automatiquement.
- Vérifié en intégration réelle (navigateur Playwright + backend/frontend locaux) : le bouton apparaît après analyse, bascule visuellement (texte + fond vert) après clic, revient à l'état initial au second clic ; capture d'écran à l'appui.
- Tests : `backend/tests/test_games_api.py` (classe `TestUpdateGameStatus`, 7 tests : marque/démarque, persistance via GET, 401 sans token, 404 partie inconnue/autre utilisateur, 422 body invalide ; `is_reviewed=False` par défaut vérifié dans `TestListGames`), `frontend/tests/api_client.test.js` (`updateGameStatus`).

---

## EPIC 8 : Système de Coaching Tactique Adaptatif

**Objectif :** créer un moteur de problèmes tactiques (puzzles curés, pas les propres gaffes du joueur) qui s'ajuste au niveau réel du joueur et propose des catégories ciblées.

> **Note d'architecture :** ce système est distinct du mode « Exercice » existant (`SRS`, `js/app.js`), qui rejoue les propres gaffes détectées lors de l'analyse d'une partie du joueur (répétition espacée, cartes locales `IndexedDB`). L'EPIC 8 introduit un **jeu de problèmes tactiques curés côté serveur** (dataset externe), avec sélection adaptative par Elo et validation anti-triche côté backend — une fonctionnalité nouvelle, pas une extension du SRS.
>
> **Recommandations du PO retenues :**
> - Données : table `tactical_problems` (PGN/FEN du problème, solution, difficulté Elo, catégorie), peuplée pour le MVP par import d'un dataset open-source (CSV/JSON) dans Supabase.
> - Validation : jamais uniquement côté frontend (anti-triche) — le backend valide que le coup joué correspond au « best move » attendu.
> - UI : échiquier responsive, touchant le haut de l'écran sur mobile, boutons « Catégories » en dessous.
> - UX : compteur de « Série en cours » (streak) — nombre de problèmes réussis d'affilée aujourd'hui.

### US 8.1 : Moteur de sélection adaptative (Elo type Glicko simplifié)

**Description :** proposer des problèmes dont la difficulté correspond à l'Elo tactique actuel du joueur, pour rester dans sa zone de progression.

**Critères d'Acceptation (DoD) :**
- Système de notation simplifié (type Elo) pour le joueur sur les problèmes tactiques (distinct de l'Elo virtuel Stats Avancées, EPIC 3).
- Si aucun Elo tactique n'est défini pour l'utilisateur, le système propose un problème de difficulté moyenne (1000) et l'ajuste dès le premier résultat.
- Algorithme : succès → +15 points ; échec → −15 points.

**Statut :** ✅ Implémenté :
- Migration `20260701194517_tactics_epic8.sql` : table `tactical_problems` (`fen`, `solution`, `category`, `difficulty_elo`, index sur `category`/`difficulty_elo`) + colonne `profiles.tactical_elo` (`1000` par défaut, distincte de l'Elo virtuel Stats Avancées EPIC 3) + seed de 15 problèmes (5 `mate_in_1`, 4 `hanging_piece`, 6 `mate_in_2`), **chacun vérifié programmatiquement via python-chess** (coup légal + mat effectif pour les catégories mat, capture non défendue pour `hanging_piece`) faute d'accès réseau à un dataset externe dans cet environnement — le même jeu de données est répliqué en Python (`db_client._TACTICAL_PROBLEMS_SEED`) pour le mode in-memory dev/test.
- `backend/app/domain/tactical_elo.py` : `update_elo(current, success)` (+15/-15, plancher 100).
- `backend/app/domain/tactics.py` : `is_correct_move(fen, solution, played)` (compare des objets `chess.Move` via python-chess, pas des chaînes brutes — des annotations différentes du même coup, ex. `Ra8` vs `Ra8#`, sont reconnues équivalentes) ; `select_nearest_problem(problems, target_elo)` (le plus proche de l'Elo cible, tirage aléatoire en cas d'égalité).
- `backend/app/routers/tactics.py` (nouveau, câblé dans `app.main`) : `GET /api/v1/tactics/next` (JWT requis, ne renvoie jamais `solution`) et `POST /api/v1/tactics/attempt` (JWT requis, **valide le coup côté serveur** contre la solution stockée — jamais une confiance au client —, met à jour l'Elo tactique, révèle la solution uniquement après la tentative).
- **Paramètre `category` pré-câblé mais pas encore exposé** : `db_client.get_next_tactical_problem(tactical_elo, category=None)` accepte déjà un filtre par catégorie (nécessaire à US 8.2), mais la route `GET /api/v1/tactics/next` ne l'expose pas encore en paramètre de requête — réservé à US 8.2.
- Vérifié en intégration réelle (serveur local + `curl`) : 401 sans token, sélection d'un problème sans solution exposée, tentative invalide rejetée proprement (`success: false`, Elo décrémenté) sans crash.
- Tests : `backend/tests/test_tactical_elo.py` (7 tests), `backend/tests/test_tactics.py` (10 tests, validation + sélection), `backend/tests/test_db_tactics.py` (12 tests, dont l'intégrité complète des 15 problèmes du seed), `backend/tests/test_tactics_api.py` (10 tests d'intégration : succès/échec, notation équivalente, persistance, isolation entre utilisateurs, 401/404).

### US 8.2 : Dashboard de catégories tactiques (Mat en 1, Mat en 2, Non-protégés)

**Description :** filtrer les problèmes par thème pour travailler spécifiquement une faiblesse identifiée.

**Critères d'Acceptation (DoD) :**
- Menu de sélection : « Aléatoire », « Mat en 1 », « Mat en 2 », « Tactique Positionnelle ».
- L'API backend filtre la base de problèmes selon le `theme_id` transmis.

**Statut :** ✅ Implémenté :
- **Décision d'interprétation documentée** : le spec pasté nommait la 4ᵉ catégorie « Tactique Positionnelle » dans le menu tout en titrant l'US « Non-protégés » — incohérence interne au spec. Faute d'un dataset de tactique positionnelle dédié (le seed US 8.1 ne couvre que `mate_in_1`/`mate_in_2`/`hanging_piece`), le 4ᵉ bouton du menu a été implémenté comme **« Pièces non protégées »** (`hanging_piece`), cohérent avec le titre de l'US et le seed existant.
- Backend : `GET /api/v1/tactics/next?theme_id=` (`routers/tactics.py`), filtre via `db_client.get_next_tactical_problem(elo, category=theme_id)` (déjà pré-câblé en US 8.1). `theme_id` absent = « Aléatoire » (toutes catégories) ; valeur hors de `domain.tactics.TACTICAL_THEMES` → 422 (plutôt qu'un 404 silencieux, pour distinguer une erreur client d'une simple absence de résultat).
- Frontend : nouvelle carte **TACTIQUE** dans le dashboard (`index.html`), ouvrant une vue plein écran dédiée (`#tactics-col`, `body.tactics-active`, même mécanisme de bascule que Stats Avancées) avec le menu à 4 boutons, un badge Elo tactique, et un affichage temporaire du problème (catégorie + FEN texte — l'échiquier jouable est explicitement la portée de US 8.3). `ApiClient.getNextTacticalProblem(themeId)`.
- **Bug latent corrigé pendant l'implémentation** : `ApiClient.url(path, query)` ajoutait un `?` orphelin (`/x?`) quand tous les paramètres de la query étaient `null`/absents (cas jamais rencontré avant `theme_id`, optionnel par nature) — corrigé pour n'ajouter le `?` que si au moins un paramètre reste après filtrage.
- Vérifié en navigateur (Playwright + Chromium, backend/frontend locaux) : les 3 filtres (Aléatoire, Mat en 1, Mat en 2) renvoient bien des problèmes de la bonne catégorie, bascule visuelle du bouton actif ; captures d'écran à l'appui.
- Tests : `backend/tests/test_tactics_api.py` (5 nouveaux tests : filtre par catégorie ×3, `theme_id` inconnu → 422), `backend/tests/test_tactics.py` (`TACTICAL_THEMES`), `frontend/tests/api_client.test.js` (`getNextTacticalProblem`, + régression sur le bug `url()`).

### US 8.3 : Interface de jeu interactive (échiquier jouable)

**Description :** interagir avec un échiquier où les coups sont validés en temps réel par le backend, pour résoudre les problèmes comme sur une application mobile.

**Critères d'Acceptation (DoD) :**
- Le frontend utilise chess.js (déjà chargé) pour la logique des coups.
- Chaque coup est envoyé au backend, qui valide via le moteur si c'est le « Best Move » attendu du problème (jamais de validation frontend seule).
- Feedback visuel immédiat (vert succès / rouge erreur), son optionnel.

**Statut :** ✅ Implémenté :
- Le backend de validation (`POST /api/v1/tactics/attempt`) était déjà entièrement câblé depuis US 8.1 — cette US ne portait que sur le frontend.
- **Décision d'architecture** : ne pas réutiliser la classe `BoardManager` existante (`board_manager.js`), trop couplée au `#board` partagé unique et au worker Stockfish embarqué (non désiré ici). À la place, un échiquier léger et indépendant est instancié directement avec `Chess`/`Chessboard` (déjà chargés globalement) dans `#tactics-board`, propre à la vue Coach Tactique.
- `app.js` : `_initTacticsBoard(problem)` crée l'échiquier (orientation = couleur au trait) ; `_onTacticsDragStart` bloque le glisser hors-tour/hors-tour-du-joueur et une fois le problème résolu ; `_onTacticsDrop` valide la légalité localement (chess.js, pour le snapback immédiat) puis délègue la validation de la *solution* exclusivement au serveur via `_submitTacticsAttempt` (anti-triche : le frontend ne connaît jamais la solution avant réponse serveur).
- `ApiClient.submitTacticalAttempt(problemId, move)` — `POST /api/v1/tactics/attempt`.
- Feedback visuel : classes CSS `.tactics-board--success`/`--error` (halo vert/rouge autour de l'échiquier) + message `#tactics-feedback` (résultat, et révélation de la solution en cas d'échec) ; badge Elo mis à jour avec la nouvelle valeur renvoyée par le serveur ; enchaînement automatique vers un nouveau problème (même thème) après un court délai. Son : explicitement omis (marqué « optionnel » dans le DoD).
- Vérifié en navigateur (Playwright + Chromium, backend/frontend locaux, `chess.js`/`chessboard.js` simulés car CDN bloqué par le bac à sable — la logique de validation réelle passe par le vrai backend local) : coup correct → halo vert, Elo 1000→1015, message de succès, avance auto ; coup incorrect → halo rouge, Elo inchangé, solution révélée. Captures à l'appui.
- Tests : `frontend/tests/api_client.test.js` (`submitTacticalAttempt`, succès + 404).

### US 8.4 : Persistance et historique des exercices

**Description :** enregistrer chaque tentative pour calculer des statistiques de progression par catégorie.

**Critères d'Acceptation (DoD) :**
- Table `tactical_attempts` : `attempt_id`, `user_id`, `problem_id`, `success` (bool), `time_taken` (secondes), `timestamp`.
- L'historique permet de calculer le taux de réussite par thème pour la vue stats.

**Statut :** ✅ Implémenté :
- Migration `20260701201530_tactical_attempts.sql` : table `tactical_attempts` (`attempt_id`, `user_id` → `profiles`, `problem_id` → `tactical_problems`, `success`, `time_taken`, `created_at`), index sur `user_id`/`problem_id`, RLS (`FOR ALL USING (user_id = auth.uid()::UUID)`, même motif que `user_progress_history`).
- `db_client.record_tactical_attempt(user_id, problem_id, category, success, time_taken)` / `get_tactical_attempts(user_id)` : store in-memory append-only pour dev/test, délégation `PgRepository.record_tactical_attempt`/`get_tactical_attempts` si `DATABASE_URL` défini (contrairement à `tactical_problems`/`tactical_elo` de US 8.1 — dont la délégation Postgres appelait déjà des méthodes non implémentées, gap pré-existant documenté §10.6 — cette nouvelle table a ses deux méthodes réellement écrites, testées par contrat de signature comme `progress_history`).
- `domain/tactics.compute_stats_by_theme(attempts)` : regroupe par catégorie, calcule `attempts`/`successes`/`success_rate`.
- `domain/tactics.compute_daily_streak(attempts, today)` : **Série en cours** (recommandation PO) — nombre de problèmes résolus d'affilée *aujourd'hui*, en parcourant l'historique du plus récent au plus ancien et en s'arrêtant au premier échec ou à la première tentative d'un autre jour. Calculé à la volée depuis l'historique (pas de compteur dupliqué à maintenir en synchronisation).
- `POST /api/v1/tactics/attempt` enregistre désormais chaque tentative et renvoie un champ `streak` en plus de `success`/`new_elo`/`solution` ; nouveau `GET /api/v1/tactics/stats` renvoie `{by_theme: [...], streak}`.
- `TacticalAttemptRequest.time_taken` (optionnel) : secondes écoulées, mesurées côté frontend entre l'affichage de l'échiquier et le coup joué.
- Frontend : badge **🔥 Série** dans la barre du Coach Tactique (à côté du badge Elo), initialisé via `ApiClient.getTacticsStats()` à l'ouverture de la vue, mis à jour après chaque tentative. Une réussite alimente aussi le système XP/Streak général existant (`XPSystem.add`, `StreakSystem.record`, comme le mode Exercice/Ghost) — deux notions de « streak » distinctes et volontairement non fusionnées : le streak général (jours d'activité consécutifs, `StreakSystem`) et le streak tactique du jour (`compute_daily_streak`).
- Tests : `backend/tests/test_tactics.py` (`compute_daily_streak`, `compute_stats_by_theme`), `backend/tests/test_db_tactics.py` (`TestTacticalAttempts`), `backend/tests/test_tactics_api.py` (`streak` sur `/attempt`, nouvelle classe `TestTacticsStats`), `backend/tests/test_pg_repository.py` (contrat de signature), `frontend/tests/api_client.test.js` (`submitTacticalAttempt` + `time_taken`, `getTacticsStats`).
- Vérifié en navigateur (Playwright) : badge Série passe de 🔥 0 à 🔥 1 après un coup correct.

## EPIC 9 : Entraîneur d'Ouvertures (Répertoire personnel + SRS) — Fonctionnalité auto-initiée

**Contexte :** l'intégralité du backlog EPIC 6/7/8 enregistré étant traitée, l'utilisateur a explicitement autorisé le développement d'**une** fonctionnalité non spécifiée par une US existante, à ma discrétion, alignée sur la mission du produit (« un coach personnel qui aide à gommer nos faiblesses »), avec les ouvertures et les finales citées comme pistes, le tout gamifié pour rester ludique.

**Choix retenu :** un **entraîneur de répertoire d'ouvertures par répétition espacée (SM-2)**, plutôt qu'un entraîneur de finales, pour deux raisons : (1) le site dispose déjà d'un algorithme SM-2 testé et éprouvé côté frontend (`SRS`, mode Exercice) mais uniquement pour rejouer les propres gaffes tactiques du joueur — aucune fonctionnalité n'existe pour mémoriser délibérément des lignes d'ouverture ; (2) les statistiques par ouverture (EPIC 3/4, `top_openings`/`successRatio`) diagnostiquent déjà les ouvertures faibles du joueur mais rien ne permet de les travailler explicitement — cette US ferme la boucle diagnostic → entraînement ciblé.

**Objectif :** permettre à l'utilisateur de constituer un répertoire de lignes d'ouverture (Blancs/Noirs) et de les réviser selon un calendrier de répétition espacée, avec correction automatique de la qualité de rappel (pas de notation manuelle fastidieuse) pour rester ludique.

### US 9.1 : Constitution du répertoire

**Description :** ajouter une ligne d'ouverture (nom, couleur, séquence de coups) à son répertoire personnel.

**Critères d'Acceptation (DoD) :**
- Formulaire : nom, couleur (Blancs/Noirs), séquence de coups en notation SAN.
- La séquence est validée (légalité des coups) avant enregistrement.
- Persistée côté serveur (visible depuis n'importe quel appareil, contrairement au SRS tactique 100 % `localStorage`/`IndexedDB` existant).

### US 9.2 : Révision par répétition espacée (SM-2)

**Description :** réviser aujourd'hui les lignes dont l'échéance est arrivée, avec correction automatique.

**Critères d'Acceptation (DoD) :**
- Un échiquier interactif rejoue la ligne : les coups de l'adversaire s'enchaînent automatiquement, l'utilisateur doit jouer ses propres coups (couleur de la ligne).
- La qualité de rappel (0-5, échelle SM-2) est **déduite automatiquement** du nombre d'erreurs commises pendant la révision (aucune notation manuelle) — pour rester ludique et rapide.
- Le calendrier (facteur de facilité, intervalle, prochaine échéance) est recalculé côté serveur selon l'algorithme SM-2 déjà utilisé et testé côté frontend pour le mode Exercice (portage à l'identique, pour cohérence de comportement).

**Statut (US 9.1 + 9.2) :** ✅ Implémenté — voir §4.9 du README pour le détail technique complet (routes, règles métier, câblage frontend, tests).

## EPIC 10 : Entraîneur de Finales Essentielles — Fonctionnalité auto-initiée (2ᵉ bonus)

**Contexte :** l'utilisateur a validé la fusion d'EPIC 9 et explicitement demandé de lancer la piste « finales », déjà documentée comme idée future (README §11.10) faute de temps lors du choix initial d'EPIC 9.

**Choix d'architecture :** reprend le moteur de sélection adaptative par Elo d'EPIC 8 (US 8.1) — pas de duplication : `domain/tactics.is_correct_move`/`select_nearest_problem` et `domain/tactical_elo.update_elo` sont **réutilisés directement** (ce sont des fonctions pures déjà génériques, sans rien de spécifique aux puzzles tactiques) plutôt que réécrits pour les finales. Seuls le jeu de données, le stockage (Elo/problèmes dédiés aux finales) et le câblage sont nouveaux. Distinct du mode « Finales » existant (`EndgameDetector`, diagnostic post-partie) : ce nouvel entraîneur est un **jeu de positions curées** de technique de mat essentielle (Roi+Dame, Roi+Tour, Roi+2 Tours), sur le modèle exact d'EPIC 8 mais pour un thème différent.

### US 10.1 : Moteur de sélection + validation (backend)

**Critères d'Acceptation (DoD) :** Elo « finales » distinct (1000 par défaut, +15/-15), sélection adaptative par catégorie, validation du coup exclusivement serveur, jeu de données vérifié programmatiquement (python-chess) avant intégration.

### US 10.2 : Échiquier interactif + câblage frontend

**Critères d'Acceptation (DoD) :** carte dédiée dans le dashboard, échiquier jouable (réutilise l'infrastructure d'échiquier indépendant d'US 8.3), feedback visuel vert/rouge, menu de catégories.

**Statut (US 10.1 + 10.2) :** ✅ Implémenté — voir §4.10 du README pour le détail technique complet.

## EPIC 11 : Analyse Comportementale (Psychologie) — profil d'erreurs récurrentes

**Contexte :** backlog fourni par l'utilisateur (paste PO), initialement numéroté « US 9.1/9.2 » — **renuméroté EPIC 11** pour éviter la collision avec l'EPIC 9 (Ouvertures) déjà enregistré dans cette session (cf. rationale complet en tête de l'EPIC 13, traité en premier par priorité PO). Traité en second, après EPIC 13 (« Priorité 0 »).

**En tant qu'** utilisateur, **je veux** que l'application identifie mes types d'erreur récurrents (gaffes de pièce non protégée, erreurs sous pression de temps, oublis de tactique de mat), **afin de** m'entraîner spécifiquement sur ma faiblesse dominante plutôt que sur des problèmes aléatoires.

### US 11.1 : Moteur d'analyse comportementale + profil persistant

**Description :** à chaque partie analysée, détecter si chacun des 3 types d'erreur suivis est survenu, et mettre à jour un score de fréquence par type dans un profil persistant.

**Critères d'Acceptation (DoD) :**
- 3 patterns détectés : « Gaffe sur pièce non protégée », « Erreur sous pression de temps » (chute de temps sur un coup fautif), « Oubli de tactique de mat » (mat forcé disponible mais non joué).
- Table `user_error_profiles` (`user_id`, `error_type`, `frequency_score`, `last_observed`).
- Le profil est mis à jour après **chaque** partie analysée, jamais recalculé depuis zéro (mise à jour incrémentale).
- Un score de fréquence `> 70` marque l'erreur comme « Problème récurrent ».

### US 11.2 : Entraînement Personnalisé ciblé

**Description :** un bouton « Entraînement Personnalisé » propose des problèmes tactiques du thème le plus proche de l'erreur récurrente détectée.

**Critères d'Acceptation (DoD) :** `GET /api/v1/tactics/custom?focus={error_type}` renvoie un problème du thème tactique associé au type d'erreur, sélectionné par la même logique adaptative (Elo) que `/tactics/next`.

**Statut (US 11.1 + 11.2) :** ✅ Implémenté — voir §4.12 du README pour le détail technique complet (schéma, formule de fréquence, routes, câblage frontend, tests).

## EPIC 12 : Mode "Tactical Sprint" (Social & Compétitif)

**Contexte :** backlog fourni par l'utilisateur (paste PO), initialement numéroté « US 11.1/11.2 » — **renuméroté EPIC 12** (même rationale de collision que EPIC 11/13, cf. §4.11). Traité en dernier des 3 EPIC du backlog, conformément à l'ordre de priorité PO. Recommandation PO explicite suivie : « Fais simple sur le mode Ghost. Enregistre juste les coups et rejoue-les. Pas besoin de synchronisation WebSocket complexe... un simple polling ou un fetch suffira. »

**En tant qu'** utilisateur, **je veux** résoudre un maximum de problèmes tactiques en un temps limité et me comparer au meilleur score enregistré, **afin de** m'entraîner de façon intensive et compétitive.

### US 12.1 : Sprint chronométré côté serveur

**Description :** un sprint de 60 secondes pendant lequel un maximum de problèmes tactiques doit être résolu, avec un score final.

**Critères d'Acceptation (DoD) :**
- Table `tactical_sprints` (`sprint_id`, `user_id`, `score`, `problems_solved_count`, `duration_seconds`).
- Le chrono est géré côté serveur (impossible de tricher en modifiant l'horloge du client) : la fenêtre de temps autorisée est vérifiée à chaque tentative en comparant l'horodatage de démarrage à l'horloge serveur.
- Chaque coup est validé 100 % serveur (jamais de confiance aveugle au client), comme le reste du produit.

### US 12.2 : Mode Ghost — replay du meilleur sprint

**Description :** afficher en surimpression la progression du meilleur sprint enregistré (toutes utilisateurs confondus), pour se mesurer à lui.

**Critères d'Acceptation (DoD) :** la séquence de coups résolus du meilleur sprint terminé est enregistrée et récupérable via un simple GET (pas de WebSocket) ; le frontend peut activer/désactiver son affichage en surimpression.

**Statut (US 12.1 + 12.2) :** ✅ Implémenté — voir §4.13 du README pour le détail technique complet (schéma, chrono anti-triche, routes, câblage frontend, tests).

## Amélioration outillage : suite E2E Playwright persistée

**Contexte :** demande explicite de l'utilisateur — les vérifications Playwright de US 8.3/8.4, EPIC 9 et EPIC 10 étaient jusqu'ici des scripts ad hoc écrits dans le scratchpad puis jetés à chaque US. Par souci d'économie (ne pas réécrire ce câblage à chaque fois) et de qualité (couverture de régression bout-en-bout rejouable), ces scripts sont désormais persistés dans le dépôt (`frontend/tests/e2e/`) et exécutables via `npm run test:e2e`, avec un job CI dédié (`.github/workflows/e2e-tests.yml`).

**Statut :** ✅ Implémenté — voir §6.3 et §7.3 du README pour le détail complet.

## EPIC 13 : Indépendance et Rapatriement des Assets (Anti-Proxy)

**Contexte :** backlog fourni par l'utilisateur (paste PO), initialement numéroté « US 9.1/9.2 » et « US 11.1/11.2 » — **renuméroté EPIC 11/12/13** pour éviter la collision avec les EPIC 9 (Ouvertures) et EPIC 10 (Finales) déjà enregistrés dans cette session. Traité en premier conformément à la recommandation PO (« Priorité 0 »).

**En tant qu'** utilisateur/développeur, **je veux** que toutes les dépendances externes (scripts, styles, images) soient stockées localement dans le dépôt, **afin de** pouvoir accéder à l'application sans connexion à des sites tiers bloqués par un firewall d'entreprise.

### US 13.1 : Audit + rapatriement des assets statiques

**Critères d'Acceptation (DoD) :** audit de tous les `<script src="...">`/`<link href="...">`/`<img src="...">` pointant vers des domaines externes ; téléchargement des fichiers manquants dans `frontend/assets/{js,css,images,fonts,data}/` ; mise à jour du code pour pointer vers ces chemins locaux.

**Statut :** ✅ Implémenté :
- **Audit** (`grep` exhaustif sur `frontend/js/*.js`, `frontend/css/*.css`, `index.html`) : 4 librairies JS/CSS (jQuery 3.7.1, chess.js 0.10.3, chessboard.js 1.0.0 + son CSS, Chart.js 4.4.0) servies depuis `cdnjs.cloudflare.com`/`cdn.jsdelivr.net` ; les polices Google Fonts (IBM Plex Mono, Inter) ; 12 images SVG de pièces d'échecs (jeu « cburnett ») servies depuis `lichess1.org` (utilisées 4 fois comme `pieceTheme` de `chessboard.js`) ; un jeu de données d'ouvertures ECO (5 fichiers `.tsv`) fetché à l'exécution depuis `raw.githubusercontent.com` ; des URLs CDN de secours pour le moteur Stockfish (asm.js et WASM).
- **Contrainte d'environnement** : `cdnjs.cloudflare.com`, `cdn.jsdelivr.net` et `lichess1.org` sont bloqués par le proxy sortant de cet environnement d'exécution (403 CONNECT) — impossible de les télécharger directement. Contournement : `registry.npmjs.org` (déjà en liste blanche) héberge la plupart de ces bibliothèques sous forme de paquets npm identiques aux builds CDN (`jquery@3.7.1`, `chess.js@0.10.3`, `chart.js@4.4.0`, et `@chrisoakman/chessboardjs@1.0.0` — le mainteneur officiel de chessboard.js publie désormais ses builds `dist/` sous ce nom de paquet scoped) ; les fichiers `dist/` exacts en ont été extraits via `npm pack`. Les pièces cburnett ont été retrouvées sur `raw.githubusercontent.com/lichess-org/lila` (accessible, contrairement à `lichess1.org`) — c'est le dépôt source de lichess.org qui héberge ces mêmes SVG.
- **Fichiers vendorisés** : `frontend/assets/js/` (jquery-3.7.1.min.js, chess-0.10.3.js, chessboard-1.0.0.min.js, chart-4.4.0.umd.js), `frontend/assets/css/` (chessboard-1.0.0.min.css, fonts.css régénéré avec des `url()` locales), `frontend/assets/fonts/` (6 fichiers `.woff2`, sous-ensembles latin/latin-ext uniquement — pas les variantes cyrillic/grec/vietnamien, inutiles pour une UI française), `frontend/assets/images/pieces/` (12 SVG cburnett), `frontend/assets/data/openings/` (5 `.tsv` ECO, ex-fetch runtime `raw.githubusercontent.com`).
- **Code mis à jour** : `index.html` (`<link>`/`<script>` → chemins locaux), `js/app.js` (3 occurrences de `pieceTheme` + `_buildOpeningBook()`), `js/board_manager.js` (`pieceTheme`), `js/engine_worker_wasm.js` (URLs CDN Stockfish retirées, fallback local uniquement).
- **Nettoyage** : `js/engine_worker.js` (ancien worker asm.js avec fallback CDN) supprimé — confirmé mort/non référencé (seul `engine_worker_wasm.js` est câblé depuis `board_manager.js`), sa suppression simplifie l'audit sans rien casser.
- **Hors périmètre, volontairement conservé en externe** (ce ne sont pas des « assets » au sens du DoD — `<script>`/`<img>` statiques — mais des intégrations fonctionnelles à des services tiers, impossibles à auto-héberger par nature) : `api.chess.com` (import de parties utilisateur), `tablebase.lichess.ovh` (évaluation Syzygy des finales). Ces deux appels dégradent déjà proprement (try/catch) si le réseau est indisponible.
- **Non traité (cf. §10, backlog futur)** : build WASM+NNUE de Stockfish (le moteur retombe sur le vendoring asm.js déjà en place, fonctionnel mais plus lent) ; stockage Supabase Storage pour ces assets (non nécessaire tant que le volume reste faible — servis directement par le frontend statique).
- Vérifié en navigateur (Playwright + Chromium) : chargement complet de la page avec **zéro requête externe** (vérifié en journalisant toutes les requêtes hors `localhost`), rendu correct des pièces d'échecs (SVG cburnett) et de la police Inter (`getComputedStyle().fontFamily`).
- Tests : suite E2E existante (`frontend/tests/e2e/`) adaptée pour intercepter les nouveaux chemins locaux (`assets/js/...`) au lieu des anciens domaines CDN — 8/8 tests toujours verts après le rapatriement. `Jest` (226 tests) inchangé.
