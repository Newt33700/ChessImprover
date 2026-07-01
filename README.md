# Chess Improver — Documentation Complète

> Application web d'analyse de parties d'échecs avec évaluation moteur WASM, visualisation de la Win Probability, profilage des ouvertures, détection de finales, puzzles SRS auto-générés, statistiques de progression et coach personnel offline. Authentification JWT et synchronisation cloud via Supabase.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture](#2-architecture)
3. [Frontend — Fonctionnalités implémentées](#3-frontend--fonctionnalités-implémentées)
4. [Backend — Fonctionnalités implémentées](#4-backend--fonctionnalités-implémentées)
5. [Règles métier](#5-règles-métier)
6. [Tests & Qualité](#6-tests--qualité)
7. [CI/CD](#7-cicd)
8. [État du câblage](#8-état-du-câblage)
9. [Code mort & non câblé](#9-code-mort--non-câblé)
10. [Ce qui reste à développer](#10-ce-qui-reste-à-développer)
11. [Backlog & idées futures](#11-backlog--idées-futures)
12. [Annexes](#12-annexes)

---

## 1. Vue d'ensemble

Chess Improver est une **SPA full-offline** : toute l'intelligence d'analyse est côté navigateur (Stockfish WASM, chess.js, IndexedDB). Le backend FastAPI gère uniquement l'authentification, la synchronisation cloud et un proxy optionnel vers Chess.com.

```
Chess.com API  ──► Frontend JS
                       │
                       ├── US 0  : Stockfish WASM Worker (depth≥15, PV 5 coups)
                       ├── US 0  : IndexedDB (games / srs_cards / openings_cache)
                       ├──        Parsing PGN + horloges [%clk]
                       ├──        Détection ouvertures ECO (28k positions)
                       ├── US 1  : Graphe Win Probability (Chart.js)
                       ├── US 2  : Stats ouvertures W/D/L (jauge tricolore)
                       ├── US 3  : Détection finales + Syzygy Tablebases
                       ├── US 4  : Puzzles SRS auto-générés (SM-2)
                       ├── US 5  : Dashboard Elo/Précision (lissage 5 parties)
                       ├── US 6  : Coach Personnel (arbre de décision offline)
                       ├── US 7  : Auth JWT + sync cloud + modal auth UI câblée
                       ├──        Mode Review (navigation + badges)
                       ├──        Mode Ghost (replay blunder depuis n-3)
                       └──        Mode Exercice SRS + XP/Streaks

Backend FastAPI ──► POST /auth/signup  /auth/login  GET /auth/me
                    POST /sync  (stratégie Client Wins)
                    POST /analyze  GET /games/{username}  (non utilisés par le frontend)
                         │
                    Supabase/PostgreSQL (via db_client.py)
                    Migrations SQL : supabase/migrations/
```

---

## 2. Architecture

### 2.1 Stack Frontend

| Élément | Détail |
|---|---|
| Langage | JavaScript ES2022 (pas de bundler, fichiers bruts) |
| Échiquier | chessboard.js v1.0.0 (CDN) |
| Moteur PGN | chess.js v0.10 (CDN) |
| Moteur UCI | **Stockfish WASM** (primary) + Stockfish.js v10 asm.js (fallback) |
| Graphiques | Chart.js v4.4 (CDN) |
| Persistance locale | **IndexedDB** (ChessDB wrapper) — migration depuis localStorage |
| Style | CSS custom properties, dark theme, pas de framework CSS |
| Tests | Jest 29, fake-indexeddb, coverage V8 |
| Mutation testing | Stryker JS |

### 2.2 Stack Backend

| Élément | Détail |
|---|---|
| Framework | FastAPI (Python 3.11) |
| Serveur | uvicorn |
| HTTP client | httpx (async) |
| Auth | bcrypt + HMAC-SHA256 JWT (stdlib) |
| DB production | Supabase / PostgreSQL via `DATABASE_URL` |
| DB dev/test | dict in-memory (`db_client.py`) |
| Tests | pytest 8, TestClient FastAPI |
| Mutation testing | mutmut |

### 2.3 Structure des fichiers

```
ChessImprover/
├── README.md
├── UserStory.md                        # Spécifications métier US 0→7 + CI/CD
├── .gitignore
│
├── frontend/
│   ├── index.html                      # SPA — dashboard grille 2 cartes/colonne + page Review plein écran, PGN modal overlay, logo SVG
│   ├── css/style.css                   # Thème sombre, variables CSS, responsive
│   ├── serve.py                        # Serveur HTTP dev (python3 serve.py)
│   ├── package.json                    # Jest, fake-indexeddb, Stryker config
│   ├── js/
│   │   ├── app.js                      # Logique principale (~1450 lignes) — point d'entrée
│   │   ├── board_manager.js            # Échiquier, Worker Stockfish, modes Review/Ghost/Exercice
│   │   ├── engine_worker_wasm.js       # Web Worker UCI : WASM primary + asm.js fallback
│   │   ├── stockfish.js                # Stockfish.js v10 asm.js (fallback local)
│   │   ├── db.js                       # IndexedDB wrapper (US 0) — tables: games/srs_cards/openings_cache
│   │   ├── wp_chart.js                 # Graphe Win Probability Chart.js (US 1)
│   │   ├── openings_stats.js           # Agrégat W/D/L par ouverture (US 2)
│   │   ├── endgame_detector.js         # Détection finales + Syzygy Lichess (US 3)
│   │   ├── stats_dashboard.js          # Dashboard Elo/Précision lissé (US 5)
│   │   ├── personal_coach.js           # Coach arbre de décision offline (US 6)
│   │   ├── advanced_stats.js           # Stats Avancées : matrice + deep-dive (US 4.1/4.2)
│   │   ├── api_client.js               # Client HTTP backend (analyze, stats/summary) — EPIC 1
│   │   └── auth.js                     # Auth JWT frontend (US 7) — chargé dans index.html
│   └── tests/
│       ├── setup.js                    # Mocks globaux : IDBFactory, localStorage, Chart, document
│       ├── db.test.js                  # Tests IndexedDB (ChessDB)
│       ├── wp_chart.test.js            # Tests WPChart (formule WP + render Chart.js)
│       ├── openings_stats.test.js      # Tests agrégat ouvertures + renderTable
│       ├── endgame_detector.test.js    # Tests EndgameDetector + mock Syzygy
│       ├── srs_sm2.test.js             # Tests algorithme SM-2
│       ├── stats_dashboard.test.js     # Tests StatsDashboard (Elo logistique + render)
│       ├── personal_coach.test.js      # Tests PersonalCoach (toutes les branches)
│       ├── advanced_stats.test.js      # Tests AdvancedStats (couleurs, deltas, gauge, détails)
│       └── api_client.test.js          # Tests ApiClient (base URL, analyze, stats/summary, en-tête Authorization US 6.4)
│
├── backend/
│   ├── Dockerfile                      # Image Docker + Stockfish natif (Render) — EPIC 2
│   ├── requirements.txt                # fastapi, uvicorn, httpx, pydantic, python-chess, bcrypt, psycopg
│   ├── pyproject.toml / setup.cfg      # Config pytest + mutmut
│   └── app/
│       ├── main.py                     # Routes FastAPI + inclusion routers auth/sync
│       ├── config.py                   # Settings Pydantic (jwt_secret, allowed_origins, etc.)
│       ├── domain/
│       │   ├── models.py               # Pydantic models (Classification, Phase, SRSCard, UserCreate…)
│       │   ├── auth.py                 # hash_password, verify_password, create_token, decode_token (US 7)
│       │   ├── analyzer.py             # Analyse géométrique PGN (blunders, fourchettes, zeitnot)
│       │   ├── elo_calculator.py       # Formules Elo/précision (côté backend)
│       │   ├── phases.py               # US 2.1 : segmentation Ouverture/Milieu/Finale
│       │   ├── acpl.py                 # US 2.2 : perte de centipions (CPL/ACPL) par phase
│       │   ├── virtual_elo.py          # US 3.1 : mapping ACPL → Elo virtuel + bonus cadence
│       │   ├── move_class.py           # US 3.2 : tactique vs stratégie + Elos virtuels
│       │   ├── cadence.py              # time_control Chess.com → TimeClass (EPIC 1)
│       │   ├── analysis_pipeline.py    # Worker : PGN → métriques par coup (US 1.2)
│       │   ├── stats_aggregator.py     # Agrégation → résumé /stats/summary (US 4.1)
│       │   ├── progress_history.py     # Snapshot Elo + fenêtre glissante (US 5.1)
│       │   └── srs_engine.py           # Algorithme SM-2 côté backend
│       ├── infrastructure/
│       │   ├── chess_com_client.py     # Proxy httpx vers Chess.com API
│       │   ├── engine.py               # EngineProvider (évals client / Stockfish natif) — EPIC 2
│       │   ├── pg_repository.py        # Dépôt Postgres/Supabase games+game_moves+progress_history
│       │   └── db_client.py            # Store in-memory + délégation Postgres (EPIC 1 / US 5.1 / US 8.1)
│       ├── routers/
│       │   ├── deps.py                 # get_current_user/get_current_user_id (JWT partagé, US 6.4)
│       │   ├── auth.py                 # POST /auth/signup /auth/login GET+PATCH /auth/me (US 7/6.3)
│       │   ├── sync.py                 # POST /sync — stratégie Client Wins (US 7)
│       │   ├── games.py                # POST /games/analyze, GET /games (US 7.1), GET stats/summary, GET stats/history (JWT requis, US 6.4)
│       │   └── tactics.py              # GET /tactics/next, POST /tactics/attempt (US 8.1)
│       ├── tests/
│       │   ├── test_auth.py            # 37 TUs auth : hash, JWT, signup, login, me, PATCH me, sync
│       │   ├── test_analyzer.py
│       │   ├── test_elo.py
│       │   ├── test_phases.py          # US 2.1
│       │   ├── test_acpl.py            # US 2.2
│       │   ├── test_engine.py          # Abstraction moteur
│       │   ├── test_virtual_elo.py     # US 3.1
│       │   ├── test_move_class.py      # US 3.2
│       │   ├── test_cadence.py         # EPIC 1 : classification cadence
│       │   ├── test_db_games.py        # EPIC 1 + US 5.1 + US 7.2 : store games/moves/progress_history/pgn_hash
│       │   ├── test_analysis_pipeline.py # US 1.2 : worker d'analyse + extraction ECO (US 4.2) + compute_pgn_hash (US 7.2)
│       │   ├── test_stats_aggregator.py  # US 4.1 : agrégation + top_openings/successRatio (US 4.2)
│       │   ├── test_progress_history.py  # US 5.1 : snapshot + fenêtre glissante
│       │   ├── test_games_api.py       # US 1.1 + US 5.1 + US 6.4 + US 7.1/7.2/7.3 : routes JWT + isolation + dédup PGN + is_reviewed + worker async
│       │   ├── test_pg_repository.py   # Adaptateur Postgres + délégation db_client (+ contrat pgn_hash US 7.2)
│       │   ├── test_tactical_elo.py    # US 8.1 : update_elo (+15/-15, plancher)
│       │   ├── test_tactics.py         # US 8.1 : is_correct_move, select_nearest_problem
│       │   ├── test_db_tactics.py      # US 8.1 : store tactique + intégrité du seed (python-chess)
│       │   ├── test_tactics_api.py     # US 8.1/8.2 : routes GET next (+ filtre theme_id) / POST attempt
│       │   └── test_srs.py
│       └── mutants/                    # Mutation testing mutmut
│
├── supabase/
│   └── migrations/
│       ├── 20260630000000_init_auth.sql       # Tables profiles + user_data, RLS (US 7)
│       ├── 20260701000000_advanced_stats.sql  # Tables games + game_moves, RLS (EPIC 1)
│       ├── 20260701120000_progress_history.sql # Table user_progress_history, RLS (US 5.1)
│       ├── 20260701164500_games_eco.sql        # Colonnes eco/opening_name sur games (US 4.2)
│       ├── 20260701172219_profiles_chess_username.sql # Colonne chess_username sur profiles (US 6.2)
│       ├── 20260701185622_games_pgn_hash.sql   # Colonne pgn_hash + index unique (user_id, pgn_hash) (US 7.2)
│       ├── 20260701191149_games_is_reviewed.sql # Colonne is_reviewed (défaut false) sur games (US 7.3)
│       └── 20260701194517_tactics_epic8.sql    # Table tactical_problems + profiles.tactical_elo + seed 15 problèmes (US 8.1)
│
└── .github/
    └── workflows/
        ├── deploy-frontend.yml         # CI/CD 1 : Jest + Vercel (déclenché sur frontend/**)
        ├── deploy-backend.yml          # CI/CD 2 : pytest + Render (déclenché sur backend/**)
        └── deploy-database.yml         # CI/CD 3 : sqlfluff + supabase db push (déclenché sur supabase/migrations/**)
```

---

## 3. Frontend — Fonctionnalités implémentées

### 3.1 US 0 — Moteur WASM & IndexedDB

**Fichiers :** `engine_worker_wasm.js`, `db.js`

#### Moteur Stockfish (Web Worker)

- Worker primaire : Stockfish WASM (NNUE activé, `Use NNUE value true`)
- Fallback automatique : Stockfish.js v10 asm.js si WASM indisponible (timeout 3s)
- Profondeur minimale : **depth 15** + **500ms minimum** (`go depth 15 movetime 500`)
- PV retournée sur les **5 premiers demi-coups** (nécessaire pour l'exercice SRS US 4)
- Conversion scores Mat → `±10000` centipions (évite les cassures dans les calculs)
- Filtre de stabilité : infos `depth < 3` ignorées

**Protocole UCI WASM :**
```
→ uci → setoption name Threads value 1
        setoption name Hash value 32
        setoption name Use NNUE value true
        isready
← readyok  (ou uciok)  → postMessage({ type:"ready" })

→ position fen <FEN>
→ go depth 15 movetime 500
← info depth N score cp X pv e2e4 d7d5 ...   → { type:"info", depth, evaluation, pv }
← bestmove e2e4                               → { type:"bestmove", move, pv }
```

**evalCache** (`board_manager.js`) : chaque FEN analysée → `{ evaluation, bestMove, pv[] }`. Pas de re-calcul si la FEN est déjà en cache.

#### IndexedDB (ChessDB)

**Object stores :**

| Store | Clé primaire | Index | Usage |
|---|---|---|---|
| `games` | `game_id` | `date` | Historique des parties analysées |
| `srs_cards` | `id` | `due` | Cartes de répétition espacée SM-2 |
| `openings_cache` | `epd` | — | Cache du livre d'ouvertures ECO |

**API publique de `ChessDB` :**
```js
ChessDB.open()                   // Ouvre / réutilise la connexion (singleton)
ChessDB.saveGame(game)           // Upsert par game_id
ChessDB.getAllGames()             // Toutes parties triées par date DESC
ChessDB.saveCard(card)           // Upsert par id
ChessDB.getAllCards()             // Toutes cartes SRS
ChessDB.getDueCards()            // Cartes dues (due <= aujourd'hui)
ChessDB.saveOpening(epd, data)   // Cache ECO
ChessDB.getOpening(epd)          // Lookup ECO
ChessDB.migrateFromLocalStorage() // Migration silencieuse au 1er chargement
ChessDB._reset()                 // Réinitialise la connexion (tests)
```

**Migration localStorage → IndexedDB** : au premier chargement, `ci_games` et `ci_srs_cards` sont migrés silencieusement. Flag `ci_idb_migrated` empêche la double migration.

---

### 3.2 US 1 — Graphe Win Probability

**Fichier :** `js/wp_chart.js`  
**Canvas :** `#wp-chart-canvas` dans `#panel-bilan`  
**Câblage :** `app.js` → `_showBilan()` + `WPChart.updateMove()` en temps réel

**Formule WP (du point de vue des Blancs) :**
```
WP(cp) = 50 + 50 × (2 / (1 + exp(−0.003682 × cp)) − 1)
```

Valeurs de référence :
- `cp = 0` → 50% (égalité)
- `cp = +250` → ≈ 71.5% (avantage Blanc)
- `cp = +10000` (mat) → 100%
- `cp = −10000` (mat adverse) → 0%

**API publique :**
```js
WPChart.render(canvasId, moves, onPointClick)   // Crée le graphique Chart.js
WPChart.updateMove(moveIndex, evalCp)           // Mise à jour incrémentale (temps réel)
WPChart.highlightMove(moveIndex)                // Grossit le point correspondant (navigation)
WPChart.destroy()                               // Détruit l'instance Chart.js
WPChart.evalToWP(evalCp)                        // Conversion brute cp → WP%
WPChart.buildDataset(moves)                     // Génère labels[] + data[]
```

**Interactivité :** clic sur un point du graphe → `onPointClick(moveIndex)` → `boardMgr.goToMove(index)`.

**Affichage :**
- Ligne jaune dorée (`#e8c97e`), fill blanc/noir selon côté avantagé
- Points colorés : bleu ≥ 60%, rouge ≤ 40%, gris (égalité)
- Tooltips : `"Blancs : 71.5%"` / `"Égalité"` / `"Noirs : 33.2%"` / `"Calcul…"` (null)
- `spanGaps: true` pour afficher la courbe même en attente d'analyse

---

### 3.3 US 2 — Statistiques Ouvertures

**Fichier :** `js/openings_stats.js`  
**Conteneur :** `#openings-global-container` dans `#tab-openings`  
**Câblage :** `app.js` → `_switchTab("tab-openings")` → `OpeningsStats.render("openings-global-container")`

**Extraction du nom d'ouverture (priorité décroissante) :**
1. Header PGN `[Opening "..."]`
2. Header PGN `[ECO "..."]`
3. Champ `game.opening` (API Chess.com)
4. Fallback : `"Inconnue"`

**Résultat extrait de :**
- `game.white.result` / `game.black.result` selon le `username`
- Valeurs draw : `agreed`, `stalemate`, `repetition`, `insufficient`, `50move`, `timevsinsufficient`, `draw`

**Agrégation :** clé = `"{ouverture}__{couleur}"` (ex. `"Sicilienne, Najdorf__Noir"`)

**Rendu HTML :** tableau avec jauge tricolore `<div class="wdl-gauge">` :
- Vert = Win%, Gris = Draw%, Rouge = Loss%
- Protection XSS via `escapeHtml()` sur le nom d'ouverture

**API publique :**
```js
OpeningsStats.aggregate(games, username)   // → [{opening, color, wins, draws, losses, total}]
OpeningsStats.computeRates(entry)          // → {winPct, drawPct, lossPct}
OpeningsStats.extractOpeningName(game)     // → string
OpeningsStats.getResult(game, username)    // → "win" | "draw" | "loss" | null
OpeningsStats.render(containerId)          // Lit IDB/localStorage et peuple le conteneur
```

---

### 3.4 US 3 — Finales & Syzygy Tablebases

**Fichier :** `js/endgame_detector.js`  
**Câblage :** ✅ `EndgameDetector.analyzeGame()` appelé depuis `app.js:_runEndgameAnalysis()` au démarrage de `_enterReviewMode()`. Résultats peuplent `#panel-endgame` et `#endgame-stats-container` (onglet Finales). `game.endgame_accuracy` sauvegardé dans IndexedDB.

**Détection de la phase de finale :**
```
Material = Σ valeurs pièces (hors Rois et Pions)
Valeurs : Q=9 R=5 B=3 N=3 P=0 K=0
Finale déclenchée si material ≤ 13 pts
```

Exemples : `R(5)+B(3)+N(3)=11` → finale ; `R(5)+R(5)+B(3)=13` → finale ; `Q(9)+R(5)=14` → milieu de jeu.

**API Syzygy (Lichess) :**
- URL : `https://tablebase.lichess.ovh/standard?fen={FEN}`
- Déclenchée si le nombre total de pièces (y compris Rois) ≤ 7
- Catégories retournées : `win | cursed-win | draw | blessed-loss | loss | cursed-loss`
- Classification interne : `win | draw | loss | unknown`
- Gaffe de finale : coup du joueur où `prevCategory === "win"` et `category !== "win"`

**Getter/setter `querySyzygy` :** la fonction interne est exposée via getter/setter pour permettre le remplacement par un mock dans les tests (`EndgameDetector.querySyzygy = jest.fn(...)`).

**API publique :**
```js
EndgameDetector.detectEndgamePhase(fen)           // → boolean
EndgameDetector.isEligibleForSyzygy(fen)          // → boolean (≤7 pièces)
EndgameDetector.countMaterial(fen)                // → {material, totalPieces}
EndgameDetector.classifyCategory(syzygyData)      // → "win"|"draw"|"loss"|"unknown"|null
EndgameDetector.analyzeGame(moves, playerColor, onProgress)  // → {endgameStartIndex, syzygyBlunders[], endgameAvgAccuracy}
EndgameDetector.renderStats(results, containerId) // Peuple #endgame-stats-container
EndgameDetector.querySyzygy                       // getter/setter (remplaçable en tests)
```

---

### 3.5 Chargement des parties Chess.com

**Fichier :** `app.js` — `ChessComClient`, `_connectUser()`

- Connexion par pseudo Chess.com
- Récupération des archives mensuelles : `https://api.chess.com/pub/player/{username}/games/{year}/{month}`
- 20 dernières parties chargées, affichées avec résultat (V/L/½), adversaire, date, cadence, rating
- Clic sur une partie → pré-remplit le PGN dans la zone d'analyse
- Persistance du pseudo en localStorage (`ci_username`)
- Sauvegarde dans IndexedDB (`ChessDB.saveGame()`) après analyse

---

### 3.6 Parsing PGN & extraction des horloges

**Fichier :** `app.js` — `PGNAnalyzer.analyze(pgn)`

- Parsing via chess.js (`history({ verbose: true })`)
- Headers extraits : `WhiteElo`, `BlackElo`, `TimeControl`, `ECO`, `Opening`
- Horloges `[%clk H:MM:SS]` extraites coup par coup depuis les commentaires PGN
- `timeSpent` calculé par différence avec le coup précédent de même couleur

Chaque coup du tableau `moves[]` contient :

| Champ | Type | Rempli par |
|---|---|---|
| `san` | string | chess.js |
| `from`, `to` | string | chess.js |
| `color` | "w"\|"b" | chess.js |
| `fen` | string | chess.js |
| `clock` | number (s) | PGN `[%clk]` |
| `timeSpent` | number (s) | Calcul différentiel |
| `accuracy_score` | number\|null | Stockfish (async) |
| `classification` | string | Stockfish (async) |
| `cpLoss` | number\|null | Stockfish (async) |
| `evalCp` | number\|null | Stockfish — éval absolue Blancs (pour WPChart) |

---

### 3.7 Classification des coups

**Fichier :** `app.js` — `EloEngine`

**Formule de précision du coup :**
```
precision(coup) = 100 × exp(−0.003 × |cpLoss|)
```

**Seuils de classification :**

| Classification | Précision | Badge | Couleur |
|---|---|---|---|
| `book` | — | B | Brun `#8b7355` |
| `brilliant` | ≥ 95% | ✦ | Teal `#1bada6` |
| `excellent` | ≥ 85% | !! | Bleu `#5b8dd9` |
| `good` | ≥ 70% | ! | Vert `#96bc4b` |
| `inaccuracy` | ≥ 50% | ?! | Jaune `#f6af29` |
| `mistake` | ≥ 25% | ? | Orange `#e87a14` |
| `blunder` | < 25% | ?? | Rouge `#ca3431` |

**Calcul du cpLoss** (convention UCI → avantage Blanc absolu) :
```
evalBefore_white = evalCache[fen_{i-1}].evaluation × (color_{i-1} == "w" ? +1 : −1)
evalAfter_white  = evalCache[fen_i].evaluation     × (color_i     == "w" ? +1 : −1)

si joueur == "w" : cpLoss = max(0, evalBefore_white − evalAfter_white)
si joueur == "b" : cpLoss = max(0, evalAfter_white  − evalBefore_white)
```

---

### 3.8 US 4 — Puzzles SRS auto-générés

**Fichiers :** `app.js` — `SRS`, `_onMoveAccuracy()` ; `board_manager.js` — `startExercise()`

#### Création automatique des cartes (câblée ✅)

Dans `_onMoveAccuracy()`, quand `classification === "blunder"` et `moveIdx > 0` :
```js
const prevFen = game.moves[moveIdx - 1].fen;
const pv = this.boardMgr.evalCache[prevFen]?.pv || [];
if (pv.length >= 1) {
  const cardId = `blunder_${game.game_id}_${moveIdx}`;
  if (!SRS.load().find(c => c.id === cardId)) {
    const card = SRS.createCard(cardId, prevFen, pv);
    SRS.saveCard(card);           // localStorage (CI/CD)
    ChessDB.saveCard(card);       // IndexedDB (US 0)
  }
}
```

La PV est la Principal Variation du moteur (jusqu'à 5 demi-coups UCI), convertie en tableau de coups.

#### Algorithme SM-2

```
si quality < 3 : interval=1, reps=0  (réinitialisation)
sinon :
  delta = 0.1 − (5−q) × (0.08 + (5−q) × 0.02)
  EF_new = max(1.3, EF + delta)
  reps==1 → interval=1
  reps==2 → interval=6
  reps≥3  → interval = round(interval × EF_new)
```

- EF initial : 2.5, minimum 1.3
- Persistance : localStorage `ci_srs_cards` + IndexedDB `srs_cards`

#### Mode Exercice (board_manager.js)

```
exercisePV = ["e2e4", "d7d5", "d1h5"]  (tableau UCI)
exerciseMoveStep = 0

Joueur joue coup PV[0] ✓ → board joue PV[1] automatiquement (400ms)
Joueur joue coup PV[2] ✓ → succès complet → quality=5
Joueur joue un coup différent mais position > 0 → quality=3
Joueur se trompe → quality=1
```

---

### 3.9 Mode Ghost (replay de gaffe)

**Fichier :** `board_manager.js` — `startGhost()`, `_ghostPlayOpponentMove()`, `_evaluateGhostResult()`

- Charge la position `max(0, blunderIndex − 3)`
- L'adversaire rejoue ses coups historiques automatiquement (délai 400ms)
- Succès si `playerEval > 0` (position gagnante pour le joueur)
- Récompense : `XP_PER_EXERCISE × 2` + streak

**Correction appliquée :** `playerColor` utilisait `"w"` hardcodé dans `app.js:_startGhost()`. Corrigé en `this.playerColor || "w"` — le mode fonctionne désormais pour les Blancs et les Noirs.

---

### 3.10 Mode Review

**Fichiers :** `board_manager.js` — `startReview()`, `goToMove()` ; `app.js` — `_enterReviewMode()`

- Navigation ‹ › ou clic sur la liste des coups
- Badge animé par classification sur la case de destination
- Mise à jour en temps réel pendant l'analyse Stockfish (badges apparaissent progressivement)
- Horloge des deux joueurs selon données `[%clk]` du PGN
- Flip automatique (joueur analysé en bas), flip manuel

---

### 3.11 US 5 — Dashboard Statistiques

**Fichier :** `js/stats_dashboard.js`  
**Canvas :** `#elo-chart-canvas2` + `#acc-chart-canvas2` dans `#tab-stats`  
**Câblage :** `app.js` → `_switchTab("tab-stats")` + boutons période

**Formule Elo logistique (remplace l'ancienne formule linéaire) :**
```
expectedScore = max(0.001, min(0.999, avgAccuracy / 100))
eloAdvantage  = 400 × log10(expectedScore / (1 − expectedScore))
eloEstimé     = clamp(opponentElo + eloAdvantage, 400, 2800)
```

Calibration : 75% précision + 1000 Elo adverse ≈ 1000 Elo estimé ; 90% ≈ 1573 Elo.

**Lissage :** moyenne mobile sur les **5 dernières parties** (fenêtre glissante). Le graphique affiche la courbe brute (semi-transparente) + la courbe lissée.

**Filtres temporels :** 7 / 30 / 90 jours (filtre sur `game.date` ISO).

**API publique :**
```js
StatsDashboard.wpFromCp(cp)                          // WP% depuis centipions
StatsDashboard.estimateEloLogistic(avgAcc, oppElo)   // Elo logistique
StatsDashboard.movingAverage(values, window=5)       // Lissage
StatsDashboard.filterByDays(games, days)             // Filtre chronologique
StatsDashboard.buildChartData(games, days)           // → {labels, eloData, accData, rawElo, rawAcc}
StatsDashboard.render(days, eloCanvasId, accCanvasId) // Peuple les graphiques
```

---

### 3.12 US 6 — Coach Personnel

**Fichier :** `js/personal_coach.js`  
**Conteneur :** `#coach-diagnosis2` dans `#tab-coach`  
**Câblage :** `app.js` → `_switchTab("tab-coach")` → `PersonalCoach.render("coach-diagnosis2")`

**Métriques calculées (30 dernières parties) :**

| Métrique | Calcul |
|---|---|
| `blunderRate` | `totalBlunders / totalMoves × 100` |
| `earlyBlunderRate` | gaffes dans les 15 premiers coups du joueur / total early moves × 100 |
| `avgAccuracy` | moyenne de `game.accuracy` sur les parties avec données |
| `worstOpening` | ouverture avec winrate le plus bas parmi celles jouées ≥ 5 fois |
| `avgEndgameAcc` | moyenne de `game.endgame_accuracy` |

**Arbre de décision (6 règles, triées par priorité décroissante) :**

| Priorité | Condition | Message | Bouton |
|---|---|---|---|
| 10 | `earlyBlunderRate > 20%` | Trop de gaffes précoces | Réviser mes ouvertures |
| 9 | `worstWinRate < 30%` (≥5 parties) | Ouverture X te coûte des points | Voir mes ouvertures |
| 8 | `blunderRate > 5%` | Taux de gaffes global élevé | Faire mes puzzles SRS |
| 7 | `avgEndgameAcc < 60%` | Technique de finale fragile | Analyser mes finales |
| 5 | `75% ≤ avgAccuracy < 85%` | Bonne précision, cap à franchir | Revoir mes parties |
| 1 | `totalGames < 5` | Manque de données | — |

**Rendu :** cartes HTML avec classes CSS `coach-high` / `coach-mid` / `coach-low`. Les boutons d'action câblent directement vers `app._startExercise()`, `app._enterReviewMode()` ou `app._switchTab(tabId)`.

**API publique :**
```js
PersonalCoach.computeMetrics(games, username)  // → {blunderRate, earlyBlunderRate, avgAccuracy, worstOpening, ...}
PersonalCoach.diagnose(metrics)                // → [{priority, message, action, target}]
PersonalCoach.renderHTML(advices)              // → string HTML
PersonalCoach.render(containerId)             // Lit IDB/localStorage et peuple le conteneur
```

---

### 3.13 US 7 — Auth Frontend + UI Modal

**Fichiers :** `js/auth.js` (logique), `index.html` (modal), `js/app.js` (câblage)  
**Statut :** ✅ chargé dans `index.html`, modal login/signup câblée, auto-connect au boot

#### Modal d'authentification (`index.html`)

- Overlay fixe `#auth-modal.auth-overlay` : apparaît par-dessus toute section
- Deux onglets : **Connexion** (email + mot de passe) et **Inscription** (email + pseudo + pseudo Chess.com optionnel + mot de passe)
- Fermeture : bouton ✕ ou clic sur le fond de l'overlay
- Formulaires : `onsubmit` → `window.app._submitLogin(event)` / `_submitSignup(event)`

#### Méthodes app.js câblées

```js
_renderAuthState()          // Peuple #current-user : chip username + bouton Déconnexion
_openAuthModal()            // Retire l'attribut hidden sur #auth-modal
_closeAuthModal()           // Cache #auth-modal + réinitialise messages d'erreur
async _submitLogin(event)   // Appelle Auth.login() → _onAuthSuccess() ou affiche l'erreur
async _submitSignup(event)  // Appelle Auth.signup() → _onAuthSuccess() ou affiche l'erreur
_onAuthSuccess(user)        // Ferme modal, toast bienvenue, renderAuthState, auto-connect Chess.com
_onAuthLogout()             // Auth.logout() + renderAuthState()
```

#### Auto-connect Chess.com depuis profil

Au démarrage, si `Auth.autoConnect()` retourne un utilisateur avec `chessUsername` enregistré ET que `this.recentGames` est vide, `_onAuthSuccess()` appelle automatiquement `_connectUser(chessUsername)` pour charger les parties sans interaction.

`_connectUser(forceUsername?)` accepte un paramètre optionnel pour les appels programmatiques (contourne l'input DOM).

#### Boot

```js
const user = await Auth.autoConnect();
if (user) window.app._onAuthSuccess(user);
else      window.app._renderAuthState();   // affiche bouton "Connexion"
```

#### API publique `Auth` (`js/auth.js`)

```js
Auth.signup(email, username, password)  // POST /auth/signup → sauvegarde token + user
Auth.login(email, password)             // POST /auth/login  → sauvegarde token + user
Auth.logout()                           // Supprime ci_jwt + ci_user du localStorage
Auth.autoConnect()                      // GET /auth/me → valide le token au rechargement
Auth.updateChessUsername(chessUsername) // PATCH /auth/me → lie/délie le pseudo Chess.com (US 6.3)
Auth.syncData(games, srsCards)          // POST /sync → stratégie Client Wins
Auth.isLoggedIn()                       // → boolean
Auth.getToken()                         // → string | null
Auth.getUser()                          // → {id, email, username, chess_username} | null
```

**Stockage :** `localStorage["ci_jwt"]` (token), `localStorage["ci_user"]` (profil JSON).  
**URL API :** `window.CI_API_URL || "http://localhost:8000"` (configurable).

#### Messages d'erreur exploitables (US 6.1)

`_extractErrorMessage(data)` (interne à `auth.js`) normalise la réponse d'erreur FastAPI avant de la remonter dans `Error.message` : si `detail` est une chaîne (400/401 métier, ex. « Email déjà utilisé »), elle est utilisée telle quelle ; si `detail` est une liste d'erreurs de validation Pydantic (422, un objet `{msg, loc, type}` par champ), les `msg` sont concaténés (`" ; "`) au lieu d'afficher `[object Object]`. `_submitSignup`/`_submitLogin` (`app.js`) affichent ce message dans `#signup-error`/`#login-error`.

#### Modal Profil — liaison Chess.com (US 6.3)

**Fichiers :** `index.html` (`#profile-modal`), `app.js` (`_openProfileModal`/`_closeProfileModal`/`_submitProfile`), `auth.js` (`updateChessUsername`)

Un bouton **Profil** apparaît à côté de **Déconnexion** dans `#current-user` une fois connecté. Il ouvre `#profile-modal` (réutilise les classes `auth-overlay`/`auth-card`/`auth-form`/`auth-error` — même charte graphique que la modal de connexion, plus une classe `.auth-success` pour le message de confirmation), pré-rempli avec `Auth.getUser().chess_username`. La soumission appelle `Auth.updateChessUsername()` (`PATCH /auth/me`) ; en cas de succès, le pseudo est aussi propagé à `Store[STORAGE_KEYS.USERNAME]` pour que le reste du dashboard (chargement Chess.com) l'utilise immédiatement. À l'inscription, si un pseudo Chess.com est saisi dans le formulaire signup, il est désormais persisté côté serveur via ce même appel (`_submitSignup`), remplaçant l'ancien stockage `localStorage` uniquement — un format invalide à cette étape n'empêche jamais la création du compte (l'utilisateur peut corriger ensuite via le profil).

> **Piège évité :** le gestionnaire de bascule d'onglets Connexion/Inscription masquait initialement *tous* les éléments `.auth-form` de la page (`document.querySelectorAll(".auth-form")`), y compris `#profile-form` qui partage cette classe pour la cohérence visuelle — le formulaire de profil restait alors invisible en permanence après le premier clic sur un onglet auth. Détecté par une vérification navigateur (Playwright) et corrigé en scopant le sélecteur à `#auth-modal .auth-form`.

---

### 3.15 Refonte UX — Dashboard grille 2 colonnes & page Review plein écran

**Fichiers :** `index.html`, `css/style.css`, `app.js`

> **Refonte design (juin 2026)** — le dashboard est désormais une **grille de 4 grandes cartes titrées** (REVIEW, EXERCICE, BILAN, FINALES) et la page Review (échiquier + analyse) occupe **toute la largeur** au lieu d'une colonne latérale fixe. Tous les IDs JS sont conservés.

#### Structure de la page

```
<header>  logo SVG patte musclée + gamification bar + auth chip
<main>
  #section-dashboard
    .dash-grid (CSS grid 1fr | 1fr — masquée quand body.board-active)
      .dash-col (gauche)              .dash-col (droite)
        #card-review                    #card-exercise (illustration + médailles)
        .stats-row-db (3 stats)         #card-finales
        #card-bilan (Chart.js)
    .board-col (#board-active) — plein écran, affichée quand body.board-active
  #pgn-modal (overlay fixe)
  #auth-modal (overlay fixe)
```

#### En-têtes de carte (`.db-card-head`)

- Chaque carte affiche un **grand titre** (`.db-card-title`, Inter 800, ~1.55rem, MAJUSCULES) + un **sous-titre** gris (`.db-card-sub`).
- Sous-titres : « Réviser vos parties récentes », « Vos prochains exercices », « Statistiques de progrès », « Maîtrisez les finales ».

#### Carte REVIEW (`#card-review`)

- **Prompt de connexion** (`#connect-prompt`) : affiché par défaut — champ pseudo + bouton "Charger" + lien "Coller un PGN"
- **Aperçu dernière partie** (`#last-game-preview`) :
  - `.match-head` : avatar — nom blanc (`#head-name-white`) — score encadré (`#match-score`) — nom noir (`#head-name-black`) — avatar — chevron `⌄`
  - `.match-precision` : titre « Précision » + 2 lignes `.prec-row` (nom + barre + valeur). Barre blanc = vert (`--green`), barre noir = orange (`--col-inaccuracy`)
  - Bouton "Lancer la Révision" (`.btn--lg`) → `_enterReviewMode(this.currentGame)`
  - Lien "Coller un PGN" → `_openPgnModal()`

#### Carte EXERCICE (`#card-exercise`)

- **Illustration** `.exo-illustration` : mini-échiquier CSS incliné (`.exo-board`) avec pièces ♚♛♞ — décoratif
- `#exercise-preview-card` : badge thème + label + bouton "Résoudre", peuplé par `async _renderExerciseCard()`
- **Médailles** `.exo-medals` : 3 pastilles (or/bronze/argent) décoratives

#### Stats inline (`.stats-row-db`)

- 3 cases : PARTIES / PRÉCISION / GAFFES — IDs `stat-games`, `stat-accuracy`, `stat-blunders`

#### Carte BILAN (`#card-bilan`)

- Toggle **Progrès** / **Elo** → `_renderBilanChart(mode)`
- Progrès : lignes Gaffes (#e04444) + Coups Manqués (#e09a44) sur les 10 dernières parties
- Elo : ligne Elo estimé (#81b64c)
- Instance Chart.js stockée dans `this._bilanChart` (détruite/recréée à chaque rendu)

#### Carte FINALES (`#card-finales`)

- Liste `.finale-list` avec items "Tour vs. Pion" et "Opposition de Rois" → `_showEndgame()`

#### Page Review plein écran (`.board-col` / `#board-active`)

- Masquée par défaut (`display: none`) ; affichée et centrée (`max-width: 1100px`) quand `body.board-active`.
- Contient topbar (back `←` + mode-pills + eval), `board-layout` (échiquier + side-panel), et les `analysis-panel`.
- Le bouton retour `←` (`.board-back-mobile`) est visible **desktop + mobile** et appelle `_goHome()`.
- Boutons « ‹ Précédent » / « Suivant › » élargis (largeur auto).

#### Modal PGN (`#pgn-modal`)

- Overlay fixe (`position: fixed; inset: 0`) remplace `section-pgn`
- `_openPgnModal()` / `_closePgnModal()` — clic sur l'overlay ou `✕` pour fermer
- Après analyse réussie : `_closePgnModal()` + `_enterReviewMode()`

#### Logo SVG (patte musclée)

- SVG inline dans `<header>` : pion vert (#81b64c) avec bras fléchis, base (#4f7128), brillance blanche
- Remplace l'emoji ♞ ; `aria-hidden="true"`, taille 32×36px

#### Bascule dashboard ↔ Review (`body.board-active`)

- `body.board-active` masque `.dash-grid` et affiche `.board-col` (desktop **et** mobile).
- `.dash-grid` passe en une colonne sous `max-width: 900px`.

#### Méthodes app.js

```js
_showBoardActive()        // Affiche #board-active, masque #board-col-empty, add body.board-active
_goHome()                 // Affiche #board-col-empty, masque #board-active, remove body.board-active
_openPgnModal()           // retire hidden sur #pgn-modal
_closePgnModal()          // ajoute hidden sur #pgn-modal
_renderReviewCard(games)  // peuple .match-card (noms top + précision, scores)
async _renderExerciseCard()   // peuple #exercise-preview-card (count SRS)
_renderBilanChart(mode)   // crée Chart.js dans #bilan-canvas (mode 'progress' ou 'elo')
```

`_renderReviewCard` renseigne les noms en double : `#head-name-white/black` (ligne avatars) et `#name-white/black` (lignes précision).

`_showSection(id)` est conservé mais redirige : `"section-board"` → `_showBoardActive()`, `"section-pgn"` → `_openPgnModal()`, `"section-dashboard"` → `_goHome()`.

---

### 3.16 Statistiques Avancées — matrice & deep-dive (US 4.1 / 4.2)

**Fichiers :** `js/advanced_stats.js`, `index.html` (`#advstats-col`), `css/style.css`, `app.js`

Vue plein écran (« type Chess.com Premium ») ouverte depuis la carte BILAN (bouton « Statistiques Avancées → ») via `body.advstats-active` (masque `.dash-grid` et `.board-col`). Retour par `_hideAdvStats()`.

**API publique de `AdvancedStats` (IIFE, exposée en `window.AdvancedStats` + `module.exports`) :**

| Fonction | Rôle |
|---|---|
| `fetchSummary(period, base?)` | `GET {base}/api/v1/stats/summary?period=` ; **fallback `MOCK_SUMMARY`** sur erreur réseau/HTTP (zéro calcul client) |
| `cellClass(elo, current)` | `pos` / `pos-strong` / `neg` / `neg-strong` / `neutral` (seuil fort = 150) |
| `phaseDelta(elo, current)`, `formatDelta(d)` | écart signé + format `+150` / `-50` |
| `deepDiveFor(summary, cadence)` | `{estimated, phases:[{key,label,sub,icon,elo,delta}]}` |
| `gaugeAngle(value, min, max)` | angle d'aiguille −90°…+90° (borné) |
| `matrixRows(summary)` | lignes prêtes au rendu (cadence × 4 catégories classées) |
| `categoryDetailHtml(category, summary)` | vue détaillée (US 4.2) : `tactics` (rating + **gauge circulaire** `successRatio` + thèmes), `endgames` (tuiles + leçons), `openings` (`summary.topOpenings`, `{name, elo}`) |
| `tacticSuccessGaugeHtml(percent)` | SVG circulaire pur (`stroke-dasharray`/`-dashoffset`), clampé `[0,100]`, `undefined`/`null` → 0 % |
| `renderMatrix/renderDeepDive/renderFinalesTiles/renderTacticsCard/renderAcplChart/renderGaffeDonut/mount` | glue DOM/Chart.js |

**Câblage `app.js` :** `_showAdvStats()` (ajoute la classe + `_loadAdvStats()`), `_loadAdvStats()` (fetch + `renderMatrix/DeepDive/FinalesTiles/TacticsCard` + 2 graphes Chart.js détruits/recréés), onglets de cadence (re-render deep-dive) et sélecteur de période (re-fetch).

> **Câblage données :** ✅ vue + rendu opérationnels ; `fetchSummary` **délègue à `ApiClient`** dès qu'une base API est configurée (`window.API_BASE` / `localStorage['apiBase']`) et retombe sur `MOCK_SUMMARY` en cas d'échec. Clic sur une catégorie du deep-dive → vue détaillée (`categoryDetailHtml`, US 4.2). La logique pure est testée (`advanced_stats.test.js` + `api_client.test.js`) ; les `render*` (glue DOM) ne sont pas dans `collectCoverageFrom`, comme `app.js`.

### 3.17 Courbe de progression (US 5.1)

**Fichiers :** `js/advanced_stats.js`, `js/api_client.js`, `index.html` (carte PROGRESSION dans `#advstats-col`), `css/style.css`

Carte **PROGRESSION**, première carte de la colonne principale de la vue Stats Avancées : courbe Chart.js à 4 séries (Ouvertures/Tactique/Stratégie/Finales) + 4 chips à cocher pour masquer/afficher une série sans reconstruire le graphe.

**Fonctions ajoutées à `AdvancedStats` :**

| Fonction | Rôle |
|---|---|
| `fetchHistory(cadence, days, base?)` | délègue à `ApiClient.getStatsHistory` si configuré, sinon `GET {base}/api/v1/stats/history` ; **fallback `MOCK_HISTORY`** |
| `formatShortDate(iso)` | libellé d'axe `"JJ/MM"` ; renvoie les 10 premiers caractères si la date est invalide |
| `buildProgressDatasets(history)` | transforme l'historique en `{labels, series:{openings,tactics,strategy,endgames}}` (pur, sans Chart.js) |
| `renderProgressChart(canvas, history)` | trace la courbe (légende masquée, couleurs `PROGRESS_COLORS`) |
| `toggleProgressSeries(chart, key, visible)` | `chart.setDatasetVisibility` + `update()`, no-op si graphe/clé introuvable |

**`ApiClient.getStatsHistory(cadence, days, userId?)`** → `GET /api/v1/stats/history?cadence=&days=&user_id=`.

**Câblage `app.js` :** `_loadProgressChart()` (fetch + rendu, détruit l'ancien graphe, état vide explicite si `history` vide) appelée depuis `_loadAdvStats()` (chargement initial + changement de période) et depuis le clic sur un onglet de cadence. Toggles délégués sur `#adv-progress-toggles` (`change` → `toggleProgressSeries`). Graphe détruit dans `_hideAdvStats()`.

**UX mobile :** `.adv-progress-wrap { overflow-x: auto }` + largeur minimale du conteneur interne calculée en JS (`Math.max(600, history.length * 46)` px) : au-delà d'un certain nombre de points, l'utilisateur scrolle horizontalement plutôt que de voir une courbe tassée.

---

### 3.14 Système XP / Niveaux / Streaks

**Fichier :** `app.js` — `XPSystem`, `StreakSystem`

| Action | XP |
|---|---|
| Analyser une partie | 50 XP |
| Réussir un exercice SRS | 10 XP |
| Réussir un Ghost | 20 XP |

- Niveau : `XP_PER_LEVEL(n) = n × 100` XP requis
- Streak : jours consécutifs d'activité, persisté avec date de dernière activité
- Affichage en-tête : `🔥 N` (streak) + `Niv. X ━━ N XP`

---

## 4. Backend — Fonctionnalités implémentées

### 4.1 Routes Auth (US 7)

**Fichier :** `backend/app/routers/auth.py`  
**Préfixe :** `/auth`

| Route | Méthode | Corps | Réponse | Description |
|---|---|---|---|---|
| `/auth/signup` | POST | `{email, username, password}` | 201 `{token, user}` | Inscription |
| `/auth/login` | POST | `{email, password}` | 200 `{token, user}` | Connexion |
| `/auth/me` | GET | — (Bearer token) | 200 `{id, email, username, chess_username}` | Profil courant |
| `/auth/me` | PATCH | `{chess_username}` (Bearer token) | 200 `{id, email, username, chess_username}` | Lie/délie le pseudo Chess.com (US 6.3) |

**Règles métier :**
- Email unique (case-insensitive) → 400 `"Email déjà utilisé"`
- Username unique (case-insensitive) → 400 `"Pseudo déjà pris"`
- **Format email validé (US 6.1)** : `UserCreate` (`app/domain/models.py`) rejette (422) toute valeur ne correspondant pas au motif `^[^@\s]+@[^@\s]+\.[^@\s]+$` (au moins un caractère avant `@`, un domaine, un `.` — pas de dépendance externe type `email-validator`, juste une regex stdlib) — avant, seule la longueur minimale (5 caractères) était vérifiée
- Mot de passe haché via bcrypt (salt aléatoire, facteur de coût par défaut ~12), longueur minimale 6 caractères (422 sinon)
- Token JWT HS256 (stdlib Python : `hmac` + `hashlib.sha256`), expiration 30 jours
- Payload JWT : `{sub: user_id, email, exp}`
- **`chess_username` (US 6.2)** : champ distinct du `username` de connexion, initialisé à `None` à la création du profil (`db_client.create_user`), exposé par `UserProfile` dans les réponses `/auth/*`.
- **`PATCH /auth/me` (US 6.3)** : `ChessUsernameUpdate` valide le format (`^[A-Za-z0-9_-]{3,25}$`, chaîne vide autorisée pour délier) → 422 sinon. L'utilisateur ciblé est **toujours** celui du token (`Depends(_current_user)`) — la route n'accepte aucun `user_id` en paramètre, donc structurellement impossible de modifier le profil d'un autre utilisateur.

**Dépendance d'authentification (`app/routers/deps.py`, US 6.4) :** `get_current_user` (FastAPI `HTTPBearer` → `decode_token()` → `find_user_by_id()`, 401 si token absent/invalide/expiré/utilisateur introuvable) et `get_current_user_id` (raccourci `user["id"]`). Factorisée hors de `auth.py` (qui l'importe sous l'alias `_current_user`) pour être réutilisée par `routers/games.py` (§4.6) sans dupliquer la vérification JWT.

### 4.2 Route Sync (US 7)

**Fichier :** `backend/app/routers/sync.py`

| Route | Méthode | Corps | Réponse |
|---|---|---|---|
| `/sync` | POST | `{games:[], srs_cards:[]}` | `{games:[], srs_cards:[]}` |

**Stratégie Client Wins :**
1. Indexer les données serveur par `game_id` / `id`
2. Itérer sur les données client et écraser les entrées existantes
3. Retourner la liste fusionnée

### 4.3 Routes classiques (non utilisées par le frontend)

| Route | Méthode | Description | Statut |
|---|---|---|---|
| `/health` | GET | Statut de santé | ✅ Fonctionnel |
| `/analyze` | POST | Analyse géométrique PGN | ✅ Fonctionnel mais ⚠ non utilisé |
| `/games/{username}` | GET | Proxy Chess.com | ✅ Fonctionnel mais ⚠ non utilisé |
| `/srs/review` | POST | Stub (retourne 400) | ⚠ Stub intentionnel |
| `/srs/review/full` | POST | Recalcul SM-2 côté serveur | ✅ Fonctionnel mais ⚠ non utilisé |

### 4.4 Couche Infrastructure

**`db_client.py` :**
- Mode **dev/test** : deux dicts Python `_users` + `_user_data` (in-memory, resetable via `_reset_store()`)
- Mode **production** : prévu pour Supabase via `DATABASE_URL` (non encore implémenté — la connexion Supabase reste à câbler)
- Interface: `find_user_by_email()`, `find_user_by_username()`, `find_user_by_id()`, `create_user()`, `get_user_data()`, `upsert_user_data()`

**`auth.py` — Implémentation JWT stdlib :**
- Pas de dépendance native (`python-jose`, `cryptography`) pour éviter les problèmes de compatibilité pyo3/cffi
- HMAC-SHA256 via `hmac.new(secret, signing_input, hashlib.sha256)`
- Signature en base64url sans padding (`=`)
- `hmac.compare_digest()` pour la comparaison à temps constant (résistance timing attacks)

### 4.5 Moteur de Statistiques Avancées (EPIC 2 & 3 — cœur algorithmique)

Modules **purs** (couche domaine), entièrement testés, indépendants de l'infrastructure. La source des évaluations Stockfish (profondeur 14) est abstraite : ils consomment des centipions déjà calculés, du point de vue du camp au trait.

**`infrastructure/engine.py` — `EngineProvider` :**
- `MoveScore` (coup + score cp + mat) et `PositionEval` (lignes multipv triées meilleur→pire ; `.best`, `.score_of(uci)`).
- `ClientProvidedEngine(evals)` : relit les évaluations calculées par le Stockfish WASM du navigateur (actif aujourd'hui). `analyse(fen, multipv)` tronque le multipv ; lève `KeyError` si la position est absente.
- `NativeStockfishEngine(binary_path, depth=14)` : appelle un binaire Stockfish natif via `chess.engine` (import paresseux) — branchable sur Render via `STOCKFISH_PATH`.
- `ENGINE_DEPTH = 14`.

**`domain/phases.py` (US 2.1)** — API : `total_material_points(board)`, `is_endgame(board)`, `opening_end_ply(board, moves, in_book=None)`, `segment_phases(board, moves, in_book=None)`, `segment_pgn(pgn, in_book=None)`. Renvoie une `Phase` (`opening`/`middlegame`/`endgame`) par demi-coup.

**`domain/acpl.py` (US 2.2)** — API : `centipawn_loss(best, played)` (plancher 0, plafond `CPL_CAP=400`), `PhasedMove(phase, cpl)`, `average_cpl(list)`, `acpl_by_phase(moves)` (dict des 3 phases, `None` si vide), `overall_acpl(moves)`.

**`domain/virtual_elo.py` (US 3.1)** — API : `acpl_to_elo_base(acpl)` (interpolation des ancres, bornes 600–2800), `cadence_bonus(time_class)`, `acpl_to_elo(acpl, time_class=None)` (bornes finales 600–3000).

**`domain/move_class.py` (US 3.2)** — API : `classify_position(line_scores) → PositionType` (`tactical`/`strategic`/`neutral`), `tactic_outcome(played_cpl) → TacticOutcome`, `tactical_success_ratio(outcomes)`, `tactical_elo(ratio)`, `strategic_elo(calm_cpls, time_class=None)`.

> **Câblage :** ✅ ces modules sont désormais exposés via l'EPIC 1 (cf. §4.6) : le worker `analysis_pipeline` les orchestre, `stats_aggregator` les agrège, et `routers/games.py` les sert. La vue frontend Stats Avancées les consomme via `GET /api/v1/stats/summary`.

### 4.6 EPIC 1 — Ingestion async & persistance (US 1.1 / 1.2)

**Fichiers :** `routers/games.py`, `domain/analysis_pipeline.py`, `domain/stats_aggregator.py`, `domain/cadence.py`, `infrastructure/db_client.py`, `supabase/migrations/20260701000000_advanced_stats.sql`

**Routes** (toutes exigent un JWT valide depuis US 6.4, `Authorization: Bearer <token>`) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/games/analyze` | POST | US 1.1 — crée la partie (`status=processing`), répond **202** + UUID, délègue à une `BackgroundTask`. Corps : `pgn` **ou** `game_ids`, + `user_color`, `time_control`, `evals` (multipv client optionnel). **US 7.2** : si `pgn` correspond au hash SHA-256 d'une partie déjà soumise par cet utilisateur, renvoie son `game_id` et son statut réel sans relancer l'analyse. |
| `/api/v1/games` | GET | US 7.1 — liste des parties déjà soumises/analysées de l'utilisateur authentifié (`{games: [...]}`, réutilise `get_games_for_user`). |
| `/api/v1/games/{game_id}` | GET | Statut de la partie + métriques par coup. `404` si inconnue **ou si elle appartient à un autre utilisateur** (US 6.4). |
| `/api/v1/games/{game_id}/status` | PATCH | US 7.3 — bascule `is_reviewed` (body `{is_reviewed}`), restreint au propriétaire (404 sinon). |
| `/api/v1/stats/summary` | GET | US 4.1 — résumé agrégé de l'utilisateur authentifié (`?period=`). |
| `/api/v1/stats/history` | GET | US 5.1 — historique des snapshots Elo de l'utilisateur authentifié (`?cadence=`, `?days=` 1-365). |

**Isolation par `user_id` (US 6.4) :** `user_id` n'est **jamais** fourni par le client (ni en body, ni en query) — il est dérivé du JWT via `Depends(get_current_user_id)` (`app/routers/deps.py`, dépendance partagée avec `routers/auth.py`). Faille corrigée : ces routes acceptaient auparavant un `user_id` arbitraire non authentifié, exposant les parties/statistiques de n'importe quel utilisateur à quiconque connaissait ou devinait son UUID. La réanalyse par `game_ids` et `GET /games/{id}` ignorent silencieusement (`continue`/404, indiscernable d'une partie inexistante) toute partie n'appartenant pas à l'utilisateur du token.

**Récupération des parties par utilisateur (US 7.1) :** `ApiClient.getGames()` (`api_client.js`) appelle `GET /api/v1/games` ; `app.js:_loadServerGames()` l'invoque depuis `_onAuthSuccess()` (restauration de session au boot **et** juste après connexion/inscription), affiche `_setLoading(true, "Chargement de vos parties…")` pendant l'appel, puis stocke le résultat dans `this.serverGames` (best-effort — un échec réseau n'affecte jamais le reste du chargement du dashboard). Cette liste sert de base à US 7.2 (éviter de re-soumettre un PGN déjà connu) et US 7.3 (statut « déjà étudiée »).

**Hashage PGN et prévention du recalcul (US 7.2) :** `analysis_pipeline.compute_pgn_hash(pgn)` calcule un SHA-256 (`hashlib`, stdlib, aucune dépendance externe). Avant de créer une nouvelle ligne `games` depuis un `pgn` soumis, `routers/games.py` cherche une partie existante de l'utilisateur authentifié avec ce hash (`db_client.find_game_by_pgn_hash`) ; si trouvée, elle est renvoyée telle quelle (`game_id` + statut réel `processing`/`completed`/`failed`) **sans** créer de nouvelle ligne ni relancer Stockfish. La colonne `pgn_hash` porte un index **unique composite `(user_id, pgn_hash)`** (migration `20260701185622_games_pgn_hash.sql`) : l'unicité est scopée par utilisateur, pas globale — deux utilisateurs différents peuvent soumettre le même texte PGN (ex. une partie célèbre) sans collision ni confusion de propriété.

**Table de correspondance « Partie-Étude » (US 7.3) :** colonne `is_reviewed` (`false` par défaut, migration `20260701191149_games_is_reviewed.sql`), bascule via `PATCH /api/v1/games/{game_id}/status`. Frontend : bouton `#btn-mark-reviewed` dans le topbar de la vue Review, masqué tant que la partie en cours n'a pas de pendant serveur connu (`this.currentGame.serverGameId`, capturé par `_syncToBackend` qui appelle ensuite `getGame` pour lire le statut réel — utile après une dédup US 7.2). `app.js:_toggleReviewed()` appelle `ApiClient.updateGameStatus()` et bascule visuellement le bouton (`.is-reviewed`, fond vert `✓ Étudiée`). **Portée volontairement limitée** : la distinction visuelle vit dans la vue Review (bouton), pas dans la liste `#games-list` du dashboard (parties Chess.com) — ces deux listes sont aujourd'hui disjointes, seule une partie passée par la modale « Analyser un PGN » étant synchronisée côté serveur.

**Worker (`run_analysis`)** : choisit la source d'évals (client > Stockfish natif `STOCKFISH_PATH` > aucune), appelle `analysis_pipeline.analyze_pgn`, **bulk-insert** des coups (US 1.2), puis `status=completed` (`failed` sur exception). Depuis US 5.1, enregistre ensuite un **snapshot de progression** (garde-fou séparé : un échec du snapshot n'invalide jamais l'analyse déjà persistée).

**`analysis_pipeline.analyze_pgn(pgn, engine=None)`** → `{result, eco, opening_name, moves:[…]}` : pour chaque coup, `phase` (US 2.1), `eval_before`/`eval_after`/`score_cp`, `cpl` plafonné (US 2.2), `is_mate`/`mate_in`, `position_type` (US 3.2). `build_client_engine(evals)` adapte les évals navigateur (`{fen: [[uci, cp, is_mate?, mate_in?], …]}`). **`_extract_opening(headers)`** (US 4.2) lit les en-têtes PGN `ECO`/`Opening`/`ECOUrl` (format Chess.com) ; `(None, None)` si absents (PGN non issu de Chess.com).

**`stats_aggregator.build_summary(entries, ratings=None, period)`** → résumé attendu par le frontend : matrice `rows` (Elo virtuel par cadence × catégorie, défaut 1200), `acplTrend`, `gaffeRate` par phase, `finales` (conversion/résilience), `tactics` (+ `successRatio` %, US 4.2), `topOpenings` (US 4.2). **`category_elos(moves, tc)`** (ex-`_category_elos`, promue publique en US 5.1) : cœur du calcul, partagé avec `progress_history.build_snapshot`. **`top_openings(entries, limit=3)`** groupe par `eco`, trie par nombre de parties, Elo **sans bonus de cadence** (un groupe ECO peut mélanger les cadences).

> **Persistance :** en dev/test, `db_client` stocke `games`/`game_moves`/`user_progress_history` en mémoire (resetable). L'adaptateur Postgres (`pg_repository.py`, §10.1) est prêt côté code.

### 4.7 US 5.1 — Historisation de la progression

**Fichiers :** `domain/progress_history.py`, `infrastructure/db_client.py` + `pg_repository.py`, `routers/games.py`, `supabase/migrations/20260701120000_progress_history.sql`

**`progress_history.build_snapshot(moves, time_control, user_color="white", game_id=None, user_id=None)`** → `{user_id, game_id, cadence, elos:{openings,tactics,strategy,endgames}}`, ou **`None` si la cadence est inconnue** (aucun snapshot enregistré dans ce cas). Filtre d'abord `moves` par `user_color`, puis délègue à `stats_aggregator.category_elos`.

**`progress_history.filter_history_by_days(history, days=30, now=None)`** → sous-ensemble de `history` dont `recorded_at` est dans la fenêtre `[now - days, now]` ; `days ≤ 0` renvoie `[]` ; les lignes sans date valide (absente/malformée) sont exclues plutôt que de faire planter le tri. `now` est injectable pour des tests déterministes.

**`db_client.create_progress_snapshot(user_id, game_id, cadence, elos)`** / **`get_progress_history(user_id, cadence)`** : CRUD in-memory (append-only, triés par `recorded_at`) ou délégation `pg_repository` si `DATABASE_URL` défini. Même précaution SQL que `get_completed_games` (§10.1) : pas de paramètre `IS NULL` non typé, cast `::uuid` explicite.

**`GET /api/v1/stats/history`** : dégrade en `history: []` (200) si l'accès aux données échoue (log de la trace), plutôt qu'un 500 — même pattern défensif que `/stats/summary`.

### 4.8 EPIC 8 — Coaching Tactique Adaptatif (US 8.1/8.2)

**Fichiers :** `routers/tactics.py`, `domain/tactical_elo.py`, `domain/tactics.py`, `infrastructure/db_client.py`, `supabase/migrations/20260701194517_tactics_epic8.sql`, `js/api_client.js`, `js/app.js`, `index.html` (`#tactics-col`)

> **Distinct du mode Exercice/SRS existant** (`js/app.js`, cartes en `localStorage`/`IndexedDB`) qui rejoue les propres gaffes détectées lors de l'analyse d'une partie du joueur. L'EPIC 8 introduit un **jeu de problèmes tactiques curés côté serveur** (dataset indépendant des parties du joueur), avec sélection adaptative par Elo et validation anti-triche systématiquement côté backend.

**Routes** (JWT requis, comme `games.py` depuis US 6.4) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/tactics/next` | GET | Problème le plus proche de l'Elo tactique de l'utilisateur authentifié (1000 par défaut). Ne renvoie **jamais** `solution`. `?theme_id=` (US 8.2) filtre par catégorie ; absent = « Aléatoire » ; valeur hors `TACTICAL_THEMES` → 422. |
| `/api/v1/tactics/attempt` | POST | Corps `{problem_id, move}` (SAN). Valide le coup **côté serveur** contre la solution stockée, ajuste l'Elo tactique (+15/-15), renvoie `{success, new_elo, solution}` — la solution n'est révélée qu'après la tentative. |

**Règles métier :**
- **Elo tactique** (`domain/tactical_elo.py`) : distinct de l'Elo virtuel Stats Avancées (EPIC 3, qualité des coups dans de vraies parties). `update_elo(current, success)` : +15 si réussi, −15 sinon, plancher à 100 (évite une dérive négative absurde après une série d'échecs). Stocké sur `profiles.tactical_elo` (colonne SQL) et répliqué dans le dict utilisateur in-memory (`db_client.create_user`), à l'image de `chess_username` (US 6.2) — le store `users`/`profiles` reste 100 % in-memory quel que soit `DATABASE_URL` (gap connu, §10.1).
- **Validation du coup** (`domain/tactics.is_correct_move`) : compare des objets `chess.Move` (python-chess), pas des chaînes SAN brutes — deux annotations différentes d'un même coup légal (ex. `Ra8` vs `Ra8#`) sont reconnues équivalentes. Toute notation invalide/illégale sur cette position est un échec silencieux (pas d'exception), jamais une confiance au client sur le résultat.
- **Sélection adaptative** (`domain/tactics.select_nearest_problem`) : problème dont `difficulty_elo` est le plus proche de l'Elo tactique du joueur ; tirage aléatoire parmi les problèmes équidistants pour éviter de toujours servir le même. `db_client.get_next_tactical_problem(tactical_elo, category=None)` filtre par catégorie si fourni.
- **Catégories (`domain.tactics.TACTICAL_THEMES`, US 8.2)** : `mate_in_1`, `mate_in_2`, `hanging_piece`. **Décision d'interprétation** : le spec pasté par l'utilisateur nommait le 4ᵉ item du menu « Tactique Positionnelle » tout en titrant l'US « Non-protégés » (incohérence interne) ; en l'absence d'un dataset de tactique positionnelle dédié, le menu expose **« Pièces non protégées »** (`hanging_piece`), cohérent avec le seed existant.
- **Seed de données (MVP)** : 15 problèmes (5 `mate_in_1`, 4 `hanging_piece`, 6 `mate_in_2`, Elo 650-1400), **chacun vérifié programmatiquement par python-chess** avant intégration (coup légal + `board.is_checkmate()` pour les catégories mat — y compris une recherche exhaustive « pour toute réponse adverse, un mat existe » pour `mate_in_2` — et capture d'une pièce sans défenseur pour `hanging_piece`). Choix motivé par l'absence d'accès réseau à un dataset externe (Lichess, etc.) dans cet environnement d'exécution ; le même jeu est répliqué en dur dans `db_client._TACTICAL_PROBLEMS_SEED` pour le mode in-memory dev/test et dans la migration SQL pour Supabase. **Reste à faire** : remplacer/enrichir par un import de dataset externe plus large (cf. §10).

**Frontend (US 8.2) :** carte **TACTIQUE** dans le dashboard → vue plein écran `#tactics-col` (`body.tactics-active`, même mécanisme de bascule que Stats Avancées) : menu de 4 boutons de catégorie, badge Elo tactique, et un affichage temporaire du problème sélectionné (catégorie + FEN texte — l'échiquier jouable est la portée de US 8.3). `ApiClient.getNextTacticalProblem(themeId)` ; nécessite d'être connecté (message explicite sinon, comme les autres fonctionnalités liées au compte).

> **Bug latent corrigé (US 8.2) :** `ApiClient.url(path, query)` ajoutait un `?` orphelin (`/x?`) quand tous les paramètres de la query étaient `null`/absents — jamais rencontré avant `theme_id`, premier paramètre de query entièrement optionnel de l'API. Corrigé pour n'ajouter le `?` que si au moins un paramètre subsiste après filtrage ; couvert par un test de régression.

---

## 5. Règles métier

### 5.1 Précision d'un coup

```
precision(coup) = 100 × exp(−0.003 × |cpLoss|)
```

| cpLoss | Précision | Classification |
|---|---|---|
| 0 | 100.0% | Brillant / Book |
| 30 | 91.4% | Excellent |
| 50 | 86.1% | Excellent |
| 100 | 74.1% | Bon |
| 200 | 54.9% | Imprécision |
| 300 | 40.7% | Erreur |
| 400 | 30.1% | Erreur |
| 500 | 22.3% | Gaffe |

### 5.2 Précision globale d'une partie

```
accuracy(partie) = moyenne(precision_coup) sur tous les coups du joueur
```
Les coups `book` ont une précision de 100% et n'abaissent pas le score.

### 5.3 Win Probability

```
WP(cp) = 50 + 50 × (2 / (1 + exp(−0.003682 × cp)) − 1)
```
- `cp` est toujours du point de vue des **Blancs** (positif = avantage Blanc)
- Caps : `cp ≥ 10000` → 100% ; `cp ≤ −10000` → 0%

### 5.4 Estimation Elo (logistique — remplace l'ancienne formule linéaire)

```
es = clamp(accuracy / 100, 0.001, 0.999)
eloAvantage = 400 × log10(es / (1 − es))
eloEstimé   = clamp(opponentElo + eloAvantage, 400, 2800)
```

L'ancienne formule `accuracy × 10 + eloAdv × 0.3` a été abandonnée (non calibrée).

### 5.5 Détection des coups théoriques (Ouvertures)

1. Téléchargement des fichiers ECO a→e (lichess-org/chess-openings sur raw.githubusercontent.com)
2. Jeu de chaque séquence ECO avec chess.js, stockage de chaque EPD intermédiaire dans un `Set`
3. Pour chaque partie : parcours les coups jusqu'au premier coup hors du Set → seuil book
4. Tous les coups avant ce seuil : `classification = "book"`, `cpLoss = 0`, `accuracy = 100%`

### 5.6 Détection de la phase de finale

```
Material = Σ valeur_pièce (hors Rois, hors Pions)
valeurs : Q=9 R=5 B=3 N=3 P=0 K=0

Finale si Material ≤ 13 pts
```

### 5.7 Algorithme SM-2

```
si quality (0-2) : interval=1, reps=0, EF inchangé
sinon (quality 3-5) :
  delta = 0.1 − (5 − quality) × (0.08 + (5 − quality) × 0.02)
  EF_new = max(1.3, EF + delta)
  si reps==1  → interval=1
  si reps==2  → interval=6
  si reps≥3   → interval = round(interval × EF_new)
  reps++
```

EF initial : 2.5. EF minimum : 1.3.  
`quality=5` : delta = +0.1 → EF monte, intervalles s'allongent rapidement.  
`quality=3` : delta = −0.14 → EF baisse légèrement, progression freinée.

### 5.8 JWT (HS256 stdlib)

```
header  = base64url({ "alg": "HS256", "typ": "JWT" })
payload = base64url({ "sub": user_id, "email": email, "exp": now() + 30×86400 })
sig     = HMAC-SHA256(secret, f"{header}.{payload}")
token   = f"{header}.{payload}.{base64url(sig)}"
```

Validation : vérification signature en temps constant (`compare_digest`) + vérification `exp`.

### 5.9 Segmentation des phases (US 2.1)

Valeurs matérielles (points, Rois exclus) : Pion=1, Cavalier=3, Fou=3, Tour=5, Dame=9.

```
Ouverture  : plies [0, fin_ouverture[  où fin_ouverture = min(sortie_du_livre, 30)
Finale     : (aucune Dame ET matériel_total ≤ 16)
             OU (Dames présentes ET chaque camp ≤ 1 pièce lourde/mineure hors Dame)
             → verrouillée (latch) une fois déclenchée
Milieu     : tout le reste, entre ouverture et finale
```

### 5.10 Perte de centipions / ACPL (US 2.2)

```
CPL  = clamp(Eval_meilleurCoup − Eval_coupJoué, 0, 400)   # POV camp au trait
ACPL = moyenne(CPL), calculée séparément par phase
```

Le plafond à 400 cp empêche une gaffe massive de ruiner la moyenne.

### 5.11 Mapping ACPL → Elo virtuel (US 3.1)

Interpolation linéaire des ancres empiriques, puis bonus de cadence :

| ACPL | ≤10 | 20 | 35 | 50 | 75 | ≥110 |
|------|-----|-----|-----|-----|-----|------|
| Elo  | 2800 | 2400 | 1900 | 1500 | 1100 | 600 |

```
Elo_virtuel = clamp( base(ACPL) + bonus_cadence , 600 , 3000 )
bonus_cadence : Bullet +200 · Blitz +100 · Rapide/Daily +0
```

### 5.12 Tactique vs Stratégie (US 3.2)

```
Tactique   : (best − 2e) > 150 cp        # un seul coup critique
   → joué = best        → Réussie
   → perte > 100 cp     → Loupée
   → sinon              → Partielle
   Elo_tactique = clamp(600 + ratio_réussite × 2400, 600, 3000)

Stratégie  : (best − 3e) < 40 cp         # position calme
   Elo_stratégie = mapping_US3.1( ACPL des positions calmes )
```

### 5.13 Classification de cadence (EPIC 1)

```
temps_estimé = base + 40 × incrément           # "180+2" → 260 s
daily ("1/…")              → DAILY
temps_estimé < 180 s       → BULLET
180 s ≤ temps_estimé < 600 → BLITZ
≥ 600 s                    → RAPID
```

### 5.14 Agrégation Stats (EPIC 1 / US 4.1)

```
catégorie Elo : openings/endgames = mapping_US3.1(ACPL de la phase, cadence)
                strategy           = Elo_stratégie ; tactics = Elo_tactique
current        = classement réel fourni, sinon moyenne des catégories (défaut 1200)
gaffe          = cpl ≥ 200 ;  coup manqué = 100 ≤ cpl < 200
Finales : conversion = % victoires si entrée en finale avec éval ≥ +150
          résilience = % nulles/victoires si entrée en finale avec éval ≤ −150
```

### 5.15 Historisation de la progression (US 5.1)

```
snapshot enregistré ⟺ classify_cadence(time_control) ≠ None   (sinon : rien)
elos du snapshot     = category_elos(coups du joueur, cadence)   — identique à la matrice US 4.1
fenêtre affichée      = { lignes | now - days ≤ recorded_at ≤ now }
days ≤ 0               → fenêtre vide (aucune ligne)
```

### 5.16 Top ouvertures & taux de réussite tactique (US 4.2)

```
eco/opening_name = en-têtes PGN ECO / Opening / ECOUrl (Chess.com) — None si absents
top_openings     : groupe par eco, exclut les parties sans eco,
                   trie par nb de parties décroissant, garde les 3 premières
Elo par ouverture = acpl_to_elo(ACPL des coups d'ouverture du groupe, cadence=None)
                    → PAS de bonus de cadence (un groupe ECO mélange les cadences)
successRatio (%) = tactical_success_ratio(tous les coups tactiques, toutes cadences confondues) × 100
                    → 0.0 si aucune position tactique (pas de None exposé au frontend)
```

---

## 6. Tests & Qualité

### 6.1 Frontend — Jest (js/tests/)

**Lancer :**
```bash
cd frontend
npm ci
npm test              # Jest + coverage
npm run test:mutation # Stryker
```

**Configuration Jest (`package.json`) :**
- Environnement : `node` (pas JSDOM) + mocks globaux dans `tests/setup.js`
- Coverage provider : V8
- Seuils de couverture : **lignes ≥ 80%, fonctions ≥ 80%, branches ≥ 70%, statements ≥ 80%**

**Fichiers couverts :**

| Fichier | Tests | Couvre |
|---|---|---|
| `db.test.js` | ChessDB | open, saveGame, getAllGames, saveCard, getDueCards, saveOpening, migrateFromLocalStorage |
| `wp_chart.test.js` | WPChart | cpToWP, evalToWP, buildDataset, render (Chart mock), updateMove, highlightMove, destroy |
| `openings_stats.test.js` | OpeningsStats | aggregate, computeRates, extractOpeningName, getResult, _renderTable (vide + données), _escapeHtml, render |
| `endgame_detector.test.js` | EndgameDetector | countMaterial, detectEndgamePhase, isEligibleForSyzygy, classifyCategory (tous cas), querySyzygy (erreur API), analyzeGame (+ onProgress), renderStats |
| `srs_sm2.test.js` | SRS (extrait de app.js) | createCard, SM-2 quality=5/3/1, EF clamp, due date |
| `stats_dashboard.test.js` | StatsDashboard | wpFromCp, estimateEloLogistic, movingAverage, filterByDays, buildChartData, render (Chart mock) |
| `personal_coach.test.js` | PersonalCoach | computeMetrics, diagnose (toutes les 6 branches), renderHTML, _detectResult, _detectUserColor, _extractOpening |
| `advanced_stats.test.js` | AdvancedStats | cellClass, deltas, deepDiveFor, gaugeAngle, matrixRows, `categoryDetailHtml` (tactics/endgames/openings/strategy), `tacticSuccessGaugeHtml` (bornes, clamp, NaN-safe), fetchSummary (fallbacks), `formatShortDate`, `buildProgressDatasets`, `toggleProgressSeries`, `fetchHistory` (fallbacks) |
| `api_client.test.js` | ApiClient | baseUrl/isConfigured (window/localStorage), url (query), analyzeGame (POST + erreur), getStatsSummary, getGame, getStatsHistory, **en-tête `Authorization: Bearer` présent/absent selon `Auth.getToken()` (US 6.4)**, **getGames (US 7.1)**, **updateGameStatus (US 7.3)**, **getNextTacticalProblem + régression bug `?` orphelin (US 8.2)** |
| `auth.test.js` (US 6.1/6.3) | Auth | signup/login (succès, `detail` chaîne, `detail` liste Pydantic 422 — un ou plusieurs champs, absence de `detail`), `updateChessUsername` (sans token, succès + PATCH + persistance session, format invalide), isLoggedIn/logout |

> `advanced_stats.js` n'est pas dans `collectCoverageFrom` (comme `app.js`, `auth.js`, `board_manager.js`) : seules ses fonctions pures sont testées, les `render*` sont de la glue DOM.

**Mocks globaux (`tests/setup.js`) :**
- `global.indexedDB = new IDBFactory()` (fake-indexeddb, réinitialisé dans `beforeEach`)
- `global.localStorage` : dict in-memory avec `getItem/setItem/removeItem`
- `global.Chart` : `jest.fn()` retournant `{ data, update, destroy }`
- `global.document.getElementById` : retourne un mock element avec `getContext`, `innerHTML`, `querySelectorAll`, `addEventListener`

### 6.2 Backend — pytest (backend/tests/)

**Lancer :**
```bash
cd backend
pip install -r requirements.txt
JWT_SECRET=ci-test-secret pytest tests/ -v
```

**Fichiers de tests :**

| Fichier | Classes | TUs |
|---|---|---|
| `test_auth.py` | TestPasswordHashing (5), TestJWT (4), TestSignup (4+3 US 6.1+2 US 6.2), TestLogin (4), TestMe (3+1 US 6.2), TestUpdateMe (7, US 6.3), TestSync (4) | **37 TUs** |
| `test_analyzer.py` | — | Analyse géométrique |
| `test_elo.py` | — | Formules Elo/précision backend |
| `test_phases.py` | Constantes, Material, IsEndgame, OpeningEndPly, SegmentPhases, SegmentPgn | US 2.1 |
| `test_acpl.py` | CentipawnLoss, AverageCpl, AcplByPhase, OverallAcpl | US 2.2 |
| `test_engine.py` | PositionEval, ClientProvidedEngine, NativeStockfishEngine | Abstraction moteur |
| `test_virtual_elo.py` | Anchors, Interpolation, CadenceBonus, AcplToElo | US 3.1 |
| `test_move_class.py` | ClassifyPosition, TacticOutcome, SuccessRatio, TacticalElo, StrategicElo | US 3.2 |
| `test_cadence.py` | EstimateSeconds, ClassifyCadence (bornes Bullet/Blitz/Rapide/Daily) | EPIC 1 |
| `test_db_games.py` | create/get/update/completed games, bulk/clear moves, snapshot/history progression, **pgn_hash (stockage, recherche, isolation par utilisateur)** | EPIC 1 + US 5.1 + US 7.2 |
| `test_analysis_pipeline.py` | sans moteur (phases/SAN), avec moteur (CPL, plafond, tactique/stratégie), mat, **`compute_pgn_hash` (déterminisme, format SHA-256)** | US 1.2 + US 7.2 |
| `test_stats_aggregator.py` | user_outcome, build_summary (catégories, ratings, couleur), gaffeRate, finales, acplTrend | US 4.1 |
| `test_progress_history.py` | build_snapshot (cadence inconnue, filtre couleur, IDs), filter_history_by_days (bornes, dates invalides/naïves) | US 5.1 |
| `test_games_api.py` | POST analyze (202, 400), worker→completed, réanalyse, GET game (404), stats/summary, snapshot auto, GET stats/history, **401 sans JWT sur les 6 routes, isolation entre 2 utilisateurs (get_game/réanalyse/stats/GET games/PATCH status)**, **GET /games (liste, vide, isolation)**, **dédup PGN par hash (même game_id, pas de doublon, statut réel, isolation par utilisateur, PGN différent → parties distinctes)**, **PATCH /games/{id}/status (marque/démarque, persistance, 404 non-propriétaire, 422 body invalide)** | US 1.1 + US 5.1 + US 6.4 + US 7.1 + US 7.2 + US 7.3 |
| `test_pg_repository.py` | PgRepository (dsn, colonnes, contrat progress_history, `_iso` générique, **contrat `create_game`/`find_game_by_pgn_hash`**), délégation db_client (in-memory sans `DATABASE_URL`) | EPIC 1 + US 5.1 + US 7.2 |
| `test_tactical_elo.py` | `update_elo` (+15/-15, constantes, plancher, pas de plafond) | US 8.1 |
| `test_tactics.py` | `is_correct_move` (match exact, notation équivalente, coup faux/illégal/invalide), `select_nearest_problem` (vide, exact, plus proche haut/bas, tirage aléatoire équidistant) | US 8.1 |
| `test_db_tactics.py` | Store tactique (Elo par défaut, persistance), **intégrité des 15 problèmes du seed vérifiée par python-chess** (mat effectif, capture non défendue), sélection/filtre par catégorie | US 8.1 |
| `test_tactics_api.py` | `GET /tactics/next` (sans solution, 401, **filtre theme_id ×3 + 422 si inconnu**), `POST /tactics/attempt` (succès/échec ±15, notation équivalente, persistance, 404, 401, isolation entre utilisateurs) | US 8.1 + US 8.2 |
| `test_srs.py` | — | SM-2 backend |

**Couverture backend :** 480 TUs au total, couverture globale **89 %** ; cœur Stats Avancées + EPIC 1/5.1/US 4.2 à 92–100 % (`stats_aggregator`, `cadence`, `progress_history`, `models`, `engine` à 100 %, `analysis_pipeline` 92 %, `routers/games` 92 %, `db_client` 98 %). Les requêtes SQL réelles de `pg_repository` (nécessitant une base) sont marquées `pragma: no cover`.

**Architecture de test `test_auth.py` :**
- App de test minimale (`FastAPI()` + routers auth/sync uniquement) pour éviter la dépendance `python-chess`
- `@pytest.fixture(autouse=True)` avec `_reset_store()` pour isolation entre tests
- Mock non nécessaire pour la DB (in-memory résetable)

**Mutation testing :**
- Frontend : Stryker JS (`npm run test:mutation`)
- Backend : mutmut (`mutmut run --paths-to-mutate app/domain/auth.py`)

---

## 7. CI/CD

### 7.1 Pipeline Frontend → Vercel

**Fichier :** `.github/workflows/deploy-frontend.yml`  
**Déclencheur :** push ou PR sur `main` affectant `frontend/**`

```
Job 1 : test-frontend (ubuntu-latest, Node 20)
  → npm ci
  → npm test -- --coverage --coverageReporters=text --coverageReporters=lcov
  → upload artifact "frontend-coverage"
```

**Note déploiement :** le déploiement Vercel est géré par **l'intégration GitHub App Vercel** (configurée côté Vercel), pas par la CI GitHub Actions. Le job `deploy-frontend` a été supprimé car il nécessitait `VERCEL_TOKEN` non configuré — l'intégration native Vercel déclenche le déploiement directement sur push vers `main`.

**Secrets requis :** aucun (tests uniquement)

### 7.2 Pipeline Backend → Render

**Fichier :** `.github/workflows/deploy-backend.yml`  
**Déclencheur :** push ou PR sur `main` affectant `backend/**`

```
Job 1 : test-backend (ubuntu-latest, Python 3.11)
  → pip install -r requirements.txt
  → JWT_SECRET=ci-test-secret pytest tests/ -v --tb=short

Job 2 : deploy-backend (main seulement, dépend de test-backend)
  → curl -fsSL -X POST "$RENDER_DEPLOY_HOOK"
```

**Secrets requis :** `RENDER_DEPLOY_HOOK`, `JWT_SECRET`

### 7.3 Pipeline Database → Supabase

**Fichier :** `.github/workflows/deploy-database.yml`  
**Déclencheur :** push ou PR sur `main` affectant `supabase/migrations/**`

```
Job 1 : lint-migrations (ubuntu-latest)
  → pip install sqlfluff
  → sqlfluff lint supabase/migrations/ --dialect postgres --exclude-rules LT12,AM06

Job 2 : push-migrations (main seulement, dépend de lint-migrations)
  → supabase/setup-cli@v1
  → supabase link --project-ref "$SUPABASE_PROJECT_ID"
  → supabase db push --password "$SUPABASE_DB_PASSWORD"
```

**Secrets requis :** `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`, `SUPABASE_PROJECT_ID`

### 7.4 Migration SQL initiale

**Fichier :** `supabase/migrations/20260630000000_init_auth.sql`

```sql
-- Table profiles
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
email TEXT UNIQUE NOT NULL
username TEXT UNIQUE NOT NULL
password_hash TEXT NOT NULL
created_at TIMESTAMPTZ DEFAULT now()
chess_username TEXT                          -- ajoutée par 20260701172219 (US 6.2), nullable

-- Table user_data
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE
games JSONB NOT NULL DEFAULT '[]'
srs_cards JSONB NOT NULL DEFAULT '[]'
updated_at TIMESTAMPTZ DEFAULT now()
UNIQUE (user_id)

-- Index : idx_user_data_user_id
-- RLS : profiles_own_row, user_data_own_row (auth.uid())
-- Trigger : set_updated_at() sur user_data BEFORE UPDATE
```

---

## 8. État du câblage

### ✅ Fonctionnel et câblé

| Fonctionnalité | Fichier(s) | Notes |
|---|---|---|
| Connexion Chess.com | `app.js` | API publique directe, CORS ok |
| Chargement 20 dernières parties | `app.js` | Parsing horloges PGN |
| Analyse Stockfish WASM | `engine_worker_wasm.js` + `board_manager.js` | depth≥15, PV 5 coups, fallback asm.js |
| evalCache | `board_manager.js` | Pas de re-calcul si FEN en cache |
| IndexedDB (ChessDB) | `db.js` | Tables games/srs_cards/openings_cache |
| Migration localStorage → IDB | `db.js` | Au 1er chargement (flag `ci_idb_migrated`) |
| Sauvegarde partie en IDB | `app.js` | Après analyse complète |
| Détection ouverture (ECO) | `app.js` | Set EPD ~28k positions |
| Classification coups (7 niveaux) | `app.js` | book/brilliant/.../blunder |
| Badges échiquier (animés) | `app.js` + CSS | Mise à jour temps réel |
| **Graphe WP** (US 1) | `wp_chart.js` | Câblé dans `_showBilan()` + `updateMove()` |
| **Stats Ouvertures** (US 2) | `openings_stats.js` | Câblé dans `_switchTab("tab-openings")` |
| **Création auto SRS depuis gaffes** (US 4) | `app.js:_onMoveAccuracy()` | Câblé depuis la dernière session |
| Mode Exercice SRS (PV multi-coups) | `board_manager.js` | `startExercise(fen, pv[])` |
| **Dashboard Stats Elo/Précision** (US 5) | `stats_dashboard.js` | Câblé dans `_switchTab("tab-stats")` |
| **Coach Personnel** (US 6) | `personal_coach.js` | Câblé dans `_switchTab("tab-coach")` |
| Backend auth/sync (US 7) | `routers/auth.py` + `routers/sync.py` | API opérationnelle |
| **Backend EPIC 1 — analyse async + stats** | `routers/games.py` + `analysis_pipeline.py` + `stats_aggregator.py` | `POST /api/v1/games/analyze` (202 + BackgroundTask), `GET /api/v1/stats/summary`. Persistance in-memory (adaptateur Postgres prêt, §10.1). |
| **Historisation de la progression** (US 5.1) | `progress_history.py` + `routers/games.py` + `advanced_stats.js` | Snapshot Elo auto après analyse (`user_progress_history`), `GET /api/v1/stats/history`, carte PROGRESSION (courbe + toggles) |
| **Analyse Finale** (US 3) | `endgame_detector.js` + `app.js` | Câblé via `_runEndgameAnalysis()` dans `_enterReviewMode()` |
| **UI Auth — Modal login/signup** (US 7) | `auth.js` + `index.html` + `app.js` | Modal overlay câblée, `Auth.autoConnect()` au boot |
| **Auto-connect Chess.com depuis profil** (US 7) | `app.js:_onAuthSuccess()` | Appelle `_connectUser(username)` après login |
| **Ghost playerColor** | `app.js:_startGhost()` | Corrigé : `this.playerColor \|\| "w"` au lieu de `"w"` hardcodé |
| Mode Ghost | `board_manager.js` + `app.js` | Replay depuis n-3 (fonctionne Blancs + Noirs) |
| Mode Review | `board_manager.js` + `app.js` | Navigation + badges temps réel |
| XP + niveaux + streaks | `app.js` | Persisté localStorage |
| Stats dashboard basique | `app.js:_renderStats()` | Total parties, précision, gaffes |
| Flip auto/manuel | `board_manager.js` | Joueur analysé en bas |
| **Refonte UX — layout deux colonnes** | `index.html` + `style.css` + `app.js` | Dashboard gauche + board droit sticky |
| **Logo SVG pion musclé** | `index.html` | SVG inline vert #81b64c |
| **Carte RÉVISION + match card** | `app.js:_renderReviewCard()` | Dernière partie avec barres de précision |
| **Carte EXERCICE SRS** | `app.js:_renderExerciseCard()` | Count révisions en attente + bouton |
| **Bilan Chart dashboard** | `app.js:_renderBilanChart()` | Graphe Progrès/Elo sur les 10 dernières parties |
| **Modal PGN overlay** | `index.html` + `app.js` | Remplace section-pgn ; `_openPgnModal()/_closePgnModal()` |
| **Mobile / bascule Review** | CSS `body.board-active` | `.dash-grid` masquée / `.board-col` plein écran via classe `body` |
| **Vue Statistiques Avancées** (US 4.1/4.2) | `advanced_stats.js` + `index.html` + `app.js` | Plein écran `body.advstats-active` : matrice colorée + gauge Héros + deep-dive + tuiles Finales + carte Tactiques (gauge circulaire `successRatio`) + top 3 ouvertures ECO (données réelles via `/stats/summary`, `MOCK_SUMMARY` en secours) |
| **Validation email + erreurs UI inscription** (US 6.1) | `models.py:UserCreate` + `auth.js:_extractErrorMessage` | Format email validé (regex) en plus de la longueur ; erreurs 422 Pydantic (liste) affichées lisiblement au lieu de `[object Object]` |
| **Colonne `chess_username` sur le profil** (US 6.2) | Migration `20260701172219_profiles_chess_username.sql` + `db_client.create_user` + `UserProfile` | Initialisée à `None` à l'inscription, exposée par `/auth/signup`/`/auth/login`/`/auth/me` |
| **Modal Profil — liaison Chess.com** (US 6.3) | `PATCH /auth/me` + `auth.js:updateChessUsername` + `index.html:#profile-modal` + `app.js` | Édition du pseudo Chess.com depuis un bouton « Profil » ; validation format (regex) ; persisté serveur dès l'inscription si renseigné |
| **Isolation par user_id — routes games/stats** (US 6.4) | `routers/deps.py` + `routers/games.py` + `api_client.js` | `POST /games/analyze`, `GET /games/{id}`, `GET /stats/summary`, `GET /stats/history` exigent un JWT et dérivent `user_id` du token (plus de `user_id` client) ; `api_client.js` attache `Authorization: Bearer` ; `app.js:_syncToBackend` no-op si non connecté |
| **Liste des parties par utilisateur** (US 7.1) | `GET /api/v1/games` + `api_client.js:getGames` + `app.js:_loadServerGames` | Appelée depuis `_onAuthSuccess()` (boot + après connexion), loader `_setLoading` pendant l'appel, résultat dans `this.serverGames` |
| **Hashage PGN et prévention du recalcul** (US 7.2) | `analysis_pipeline.compute_pgn_hash` + `db_client.find_game_by_pgn_hash` + `routers/games.py` | Une 2ᵉ soumission du même PGN par le même utilisateur renvoie la partie existante (statut réel) au lieu de relancer Stockfish ; index unique `(user_id, pgn_hash)` |
| **Table « Partie-Étude » — bouton Marquer étudiée** (US 7.3) | `PATCH /games/{id}/status` + `api_client.js:updateGameStatus` + `index.html:#btn-mark-reviewed` + `app.js:_toggleReviewed` | Bouton du topbar Review, masqué sans `serverGameId` connu ; bascule visuelle (texte + fond vert) après clic |
| **Moteur de sélection adaptative tactique** (US 8.1) | `routers/tactics.py` + `domain/tactical_elo.py` + `domain/tactics.py` | Backend : `GET /tactics/next` + `POST /tactics/attempt` opérationnels et testés (curl/pytest) |
| **Dashboard de catégories tactiques** (US 8.2) | `index.html:#tactics-col` + `app.js:_showTactics/_loadTacticalProblem` + `api_client.js:getNextTacticalProblem` | Carte TACTIQUE → vue plein écran, menu 4 catégories, badge Elo ; affichage FEN texte en attendant l'échiquier jouable (US 8.3) |

### ❌ Non câblé ou incomplet

| Fonctionnalité | Problème | Priorité |
|---|---|---|
| **Connexion Supabase réelle pour l'auth** (US 7) | `find_user_by_email`/`create_user`/`get_user_data`/`upsert_user_data` restent en dict in-memory. Seuls `games`/`game_moves`/`user_progress_history` ont un adaptateur Postgres (§10.1) ; les tables `profiles`/`user_data` (US 7) ne sont pas encore migrées. | 🟡 Important |
| **Cache livre d'ouvertures** | Re-téléchargé à chaque refresh (~5 req. réseau, ~2s de parsing) | 🟡 Important |
| **Qualité SRS nuancée** | Seul `quality=5` (succès) et `quality=1` (raté) sont utilisés. `quality=3` (correct mais non optimal) n'est jamais émis. | 🟢 Optionnel |

---

## 9. Code mort & non câblé

### 9.1 `/analyze`, `/games/{username}`, `/srs/review/full` — backend non utilisé

Le frontend appelle Chess.com directement (CORS autorisé). L'analyse Stockfish est côté client. Ces routes backend fonctionnent mais ne sont jamais appelées par le frontend actuel.

### 9.2 `game.endgame_accuracy` — alimentation différée

Le `PersonalCoach` lit `game.endgame_accuracy` pour évaluer la technique de finale. Ce champ est désormais calculé par `_runEndgameAnalysis()` et sauvegardé dans IndexedDB, mais uniquement pour les parties analysées *après* le câblage de l'EndgameDetector (commit `96e223c`). Les parties déjà sauvegardées avant ce commit auront `endgame_accuracy = undefined` et la règle coach `avgEndgameAcc < 60%` ne se déclenchera pas pour elles.

---

## 10. Ce qui reste à développer

### 10.1 🟢 Connexion Supabase réelle — en production

**Fait :** `infrastructure/pg_repository.py` implémente les tables `games`/`game_moves`/`user_progress_history` en PostgreSQL (`psycopg` v3), `db_client` **délègue automatiquement** dès que `DATABASE_URL` est défini, et le backend est **déployé sur Render avec `DATABASE_URL`/`JWT_SECRET` configurés**. Un bug réel (`psycopg.errors.IndeterminateDatatype` sur `get_completed_games`, paramètre `IS NULL` non typé) a été trouvé en production et corrigé (branchement de requête + cast `::uuid` explicite, cf. commit de fix EPIC 1).

**Reste :** (1) migrer aussi `users`/`user_data` (US 7) vers Postgres — encore in-memory (perdu au redémarrage Render) ; (2) ajouter un pool de connexions (actuellement une connexion par requête) ; (3) valider `create_progress_snapshot`/`get_progress_history` (US 5.1) contre l'instance Supabase de prod, par analogie avec le bug déjà corrigé sur `games`.

### 10.1bis 🟢 Chaîne Stats Avancées — bout-à-bout en production

EPIC 1 à 4 et US 5.1 sont implémentés, testés, **déployés** (backend Render Docker + Stockfish natif, frontend Vercel, Supabase). US 4.2 est désormais **complète** (top 3 ouvertures ECO + gauge circulaire tactique). Reste :
- **Source d'évals** : le frontend ne poste pas encore le PGN + évals de son Stockfish WASM vers `POST /api/v1/games/analyze` (champ `evals`) — Stockfish natif Render (`STOCKFISH_PATH=/usr/games/stockfish`, Docker) est la source active actuellement.
- **US 4.2 — ECO en prod** : l'extraction ECO ne peuple `topOpenings` que pour les parties analysées **après** ce déploiement (les parties déjà en base ont `eco = NULL`, exclues du classement jusqu'à réanalyse via `game_ids`).
- **US 5.1 (reste)** : aucune vue de progression n'existe encore pour un utilisateur avec 0 ou 1 seul snapshot (le graphe affiche alors 0 ou 1 point ; pas de message pédagogique intermédiaire entre l'état vide et une vraie courbe).

### 10.2 🟡 IMPORTANT — Cache du livre d'ouvertures

Sauvegarder le `Set` d'EPD dans IndexedDB (`openings_cache`) avec un TTL de 7 jours. Évite 5 requêtes réseau et ~2s de parsing chess.js à chaque refresh.

### 10.3 🟢 OPTIONNEL — Qualité SRS nuancée

Actuellement `quality=5` ou `quality=1`. Ajouter `quality=3` si le joueur joue un coup différent mais que la position reste avantageuse (`evalCp > 0` après le coup joué).

### 10.4 🟢 OPTIONNEL — Indicateur chargement livre d'ouvertures

L'utilisateur ne voit pas que le livre ECO se télécharge (~2s). Ajouter un spinner ou un message dans l'UI pendant ce chargement.

### 10.5 🟢 OPTIONNEL — Précisions Chess.com dans la carte RÉVISION

L'API Chess.com retourne `g.accuracies.white/black`. Les afficher dans les barres de précision de la `.match-card` au lieu de `null` (les barres restent à 0% si Stockfish n'a pas encore analysé la partie).

### 10.6 🟡 IMPORTANT — EPIC 8, jeu de données tactiques (US 8.1/8.2)

**Fait :** moteur de sélection adaptative + validation serveur (US 8.1), filtre par catégorie + dashboard de sélection (US 8.2), avec un seed de 15 problèmes vérifiés.

**Reste :** (1) remplacer/enrichir le seed par un dataset externe plus large (ex. export CSV Lichess Puzzle Database) — non fait dans cet environnement d'exécution faute d'accès réseau vers les sources habituelles (proxy sortant restreint) ; (2) échiquier jouable côté client (US 8.3) — la vue Coach Tactique affiche pour l'instant la position en FEN texte, sans board interactif ni soumission de coup depuis l'UI ; (3) persistance/historique des tentatives (US 8.4).

---

## 11. Backlog & idées futures

### 11.1 Analyse multi-parties

Analyser les N dernières parties d'un coup, identifier les patterns d'erreur récurrents (phase de jeu, type de pièce, cadence), graphe de progression Elo dans le temps.

### 11.2 Thèmes tactiques automatiques

Classifier chaque gaffe par thème (fourchette, clouage, enfilade, mat en N coups) via la PV de Stockfish. Base pour des exercices thématiques SRS.

### 11.3 Puzzles externes

Intégrer les puzzles Lichess API (CSV statique ou endpoint) pour enrichir les exercices au-delà des propres gaffes du joueur.

### 11.4 Mode "Devinette du coup"

Avant d'afficher le coup suivant en mode Review, cacher la pièce et demander au joueur de deviner le coup. Transformer la revue passive en revue active.

### 11.5 Analyse de la gestion du temps

Détecter les coups joués en < 5s (zeitnot), les mettre en évidence visuellement. Un coup précipité est souvent une gaffe.

### 11.6 Export / Partage

- PGN annoté (commentaires de classification)
- Export rapport en JSON ou PDF
- Lien vers position spécifique

### 11.7 Comparaison Chess.com

Récupérer les `accuracies` du JSON Chess.com (`g.accuracies.white/black`) et les afficher à côté de l'estimation locale pour calibration.

### 11.8 Mode mobile optimisé

Swipe pour naviguer entre coups, touch targets plus grands, layout vertical pour les panels d'analyse.

### 11.9 Répertoire d'ouvertures personnalisé

Identifier les ouvertures jouées le plus souvent, montrer leurs performances par cadence et couleur, recommander des variantes à améliorer.

---

## 12. Annexes

### 12.1 Variables d'environnement Backend

Fichier `.env` à créer dans `backend/` :

```env
DEBUG=false
USER_AGENT=ChessImprover/0.1 (contact: chess-improver@example.com)
ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080

# US 7 — Auth
JWT_SECRET=change-moi-en-production-min-32-chars
JWT_EXPIRY_DAYS=30

# US 7 — Database (laisser vide pour mode in-memory)
DATABASE_URL=postgresql://user:password@host:5432/db
```

### 12.2 Démarrage en développement

```bash
# Frontend (SPA standalone)
cd frontend
python3 serve.py
# → http://localhost:8080

# Backend (optionnel — requis pour auth/sync)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
# → http://localhost:8000
# → http://localhost:8000/docs (Swagger UI)
```

### 12.3 Lancer les tests

```bash
# Frontend
cd frontend && npm ci && npm test

# Backend
cd backend
JWT_SECRET=ci-test-secret pytest tests/ -v --tb=short

# Mutation testing frontend
cd frontend && npm run test:mutation

# Mutation testing backend
cd backend && mutmut run --paths-to-mutate app/domain/auth.py
```

### 12.4 Schéma SQL Supabase

```sql
-- profiles
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
email TEXT UNIQUE NOT NULL
username TEXT UNIQUE NOT NULL
password_hash TEXT NOT NULL
created_at TIMESTAMPTZ DEFAULT now()
chess_username TEXT  -- US 6.2, nullable, distinct du username de connexion

-- user_data
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE
games JSONB NOT NULL DEFAULT '[]'
srs_cards JSONB NOT NULL DEFAULT '[]'
updated_at TIMESTAMPTZ DEFAULT now()  -- mis à jour par trigger
UNIQUE (user_id)

-- RLS : chaque utilisateur ne voit que ses propres lignes
-- via auth.uid()::UUID = id (profiles) ou user_id (user_data)
```

### 12.5 Branche de développement active

```
Branche : claude/chess-app-user-stories-4umz42
Repo    : Newt33700/ChessImprover
```
