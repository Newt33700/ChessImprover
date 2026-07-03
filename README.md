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
| Échiquier | chessboard.js v1.0.0 (vendorisé localement, `assets/js/`, EPIC 13) |
| Moteur PGN | chess.js v0.10 (vendorisé localement, `assets/js/`, EPIC 13) |
| Moteur UCI | Stockfish.js v10 asm.js (vendorisé localement — plus de fallback WASM CDN depuis EPIC 13, cf. §10) |
| Graphiques | Chart.js v4.4 (vendorisé localement, `assets/js/`, EPIC 13) |
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
│   ├── serve.py                        # Serveur HTTP dev (python3 serve.py) — bloque si assets pièces manquants (EPIC 18)
│   ├── package.json                    # Jest, fake-indexeddb, Stryker config
│   ├── scripts/
│   │   └── validate_assets.py          # EPIC 18 (US 18.1) : bloque le lancement si un SVG de pièce est manquant
│   ├── js/
│   │   ├── app.js                      # Logique principale (~1450 lignes) — point d'entrée
│   │   ├── board_manager.js            # Échiquier, Worker Stockfish, modes Review/Ghost/Exercice/Sandbox
│   │   ├── engine_worker_wasm.js       # Web Worker UCI : asm.js local (EPIC 13, plus de CDN WASM)
│   │   ├── stockfish.js                # Stockfish.js v10 asm.js (fallback local)
│   │   ├── db.js                       # IndexedDB wrapper (US 0) — tables: games/srs_cards/openings_cache
│   │   ├── wp_chart.js                 # Graphe Win Probability Chart.js (US 1)
│   │   ├── openings_stats.js           # Agrégat W/D/L par ouverture (US 2)
│   │   ├── endgame_detector.js         # Détection finales + Syzygy Lichess (US 3)
│   │   ├── stats_dashboard.js          # Dashboard Elo/Précision lissé (US 5)
│   │   ├── personal_coach.js           # Coach arbre de décision offline (US 6)
│   │   ├── advanced_stats.js           # Stats Avancées : matrice + deep-dive (US 4.1/4.2)
│   │   ├── cognitive_dashboard.js      # EPIC 19 : temps de réflexion par phase + fluidité de décision (US 19.1/19.2)
│   │   ├── coaching_voice.js           # EPIC 14 : alertes tactiques + synthèse vocale (Web Speech API)
│   │   ├── theme_service.js            # EPIC 18 : thème pièces/plateau (chemins SVG, couleurs, résilience JSONB)
│   │   ├── api_client.js               # Client HTTP backend (analyze, stats/summary, salvage EPIC 15, cognitive-load/flashcards EPIC 19/20) — EPIC 1
│   │   └── auth.js                     # Auth JWT frontend (US 7) — chargé dans index.html
│   ├── assets/                         # Dépendances externes rapatriées localement (EPIC 13, §4.11)
│   │   ├── js/                         # jquery-3.7.1.min.js, chess-0.10.3.js, chessboard-1.0.0.min.js, chart-4.4.0.umd.js
│   │   ├── css/                        # chessboard-1.0.0.min.css, fonts.css (Google Fonts vendorisées)
│   │   ├── fonts/                      # 6 .woff2 (IBM Plex Mono 400/600 + Inter variable, subsets latin/latin-ext)
│   │   ├── images/pieces/              # 12 SVG cburnett (ancien emplacement historique, conservé tel quel)
│   │   ├── pieces/                     # EPIC 18 : jeux de pièces par thème — cburnett/ (copie) + cyber-tactics/ (nouveau, 12 SVG)
│   │   ├── boards/presets.json         # EPIC 18 : présets de couleurs de plateau (classic/slate/ocean/cyber)
│   │   └── data/openings/              # a.tsv…e.tsv — référentiel ECO (ex-raw.githubusercontent.com)
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
│       ├── cognitive_dashboard.test.js # EPIC 19 : formatSeconds, insights, fetchReport, render (19 tests)
│       ├── coaching_voice.test.js      # EPIC 14 : alertFor/bestMoveNarration/beep/speak/préférence localStorage
│       ├── theme_service.test.js       # EPIC 18 : chemins SVG/couleurs par thème, résilience JSONB invalide
│       └── api_client.test.js          # Tests ApiClient (base URL, analyze, stats/summary, salvage EPIC 15, cognitive-load/flashcards EPIC 19/20, en-tête Authorization US 6.4)
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
│       │   ├── srs_engine.py           # Algorithme SM-2 côté backend
│       │   ├── error_profile.py        # EPIC 11 : détection patterns + score EMA (US 9.1/9.2)
│       │   ├── tactical_sprint.py      # EPIC 12 : chrono serveur + score + séquence Ghost (US 11.1/11.2)
│       │   ├── cognitive_load.py       # EPIC 19 : temps de réflexion par phase/pression + fluidité de décision (US 19.1/19.2)
│       │   ├── srs_flashcards.py       # EPIC 20 : extraction flashcards depuis les gaffes (US 20.1)
│       │   ├── coaching_voice.py       # EPIC 14 : alerte vocale contextuelle par coup (US 14.1/14.2)
│       │   └── game_salvage.py         # EPIC 15 : pivot de défaite + reconstruction FEN (US 15.1/15.2)
│       ├── infrastructure/
│       │   ├── chess_com_client.py     # Proxy httpx vers Chess.com API
│       │   ├── engine.py               # EngineProvider (évals client / Stockfish natif) — EPIC 2
│       │   ├── pg_repository.py        # Dépôt Postgres/Supabase games+game_moves+progress_history
│       │   └── db_client.py            # Store in-memory + délégation Postgres (EPIC 1 / US 5.1 / US 8.1)
│       ├── routers/
│       │   ├── deps.py                 # get_current_user/get_current_user_id (JWT partagé, US 6.4)
│       │   ├── auth.py                 # POST /auth/signup /auth/login GET+PATCH /auth/me (US 7/6.3), PATCH /auth/me/settings (EPIC 18)
│       │   ├── sync.py                 # POST /sync — stratégie Client Wins (US 7)
│       │   ├── games.py                # POST /games/analyze, GET /games (US 7.1), POST /games/{id}/salvage (EPIC 15), GET stats/summary, GET stats/history, GET stats/cognitive-load (EPIC 19) (JWT requis, US 6.4)
│       │   ├── tactics.py              # GET /tactics/next, /tactics/custom (EPIC 11), POST /tactics/attempt (US 8.1)
│       │   ├── error_profile.py        # EPIC 11 : GET /error-profile (US 9.1)
│       │   ├── tactical_sprint.py      # EPIC 12 : POST /sprints/start /{id}/attempt /{id}/finish, GET /sprints/ghost
│       │   └── srs_flashcards.py       # EPIC 20 : GET /flashcards /flashcards/due, POST /flashcards/{id}/review (US 20.1/20.2)
│       ├── tests/
│       │   ├── test_auth.py            # 45 TUs auth : hash, JWT, signup, login, me, PATCH me, PATCH me/settings (EPIC 18), sync
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
│       │   ├── test_srs.py             # SM-2 backend + sm2_schedule (EPIC 9)
│       │   ├── test_opening_repertoire.py # EPIC 9 : validation séquence + infer_quality
│       │   ├── test_db_opening_repertoire.py # EPIC 9 : store répertoire (CRUD, isolation)
│       │   ├── test_openings_trainer_api.py # EPIC 9 : routes CRUD + révision SM-2
│       │   ├── test_db_endgames.py     # EPIC 10 : store finales + intégrité du seed (python-chess)
│       │   ├── test_endgames_api.py    # EPIC 10 : routes GET next (+ filtre theme_id) / POST attempt
│       │   ├── test_error_profile.py   # EPIC 11 : détection patterns + score EMA
│       │   ├── test_db_error_profile.py # EPIC 11 : store profils d'erreur (CRUD)
│       │   ├── test_error_profile_api.py # EPIC 11 : câblage worker + routes /error-profile, /tactics/custom
│       │   ├── test_tactical_sprint.py # EPIC 12 : chrono serveur + score
│       │   ├── test_db_tactical_sprint.py # EPIC 12 : store sprints (CRUD + meilleur sprint public)
│       │   ├── test_tactical_sprint_api.py # EPIC 12 : cycle start/attempt/finish, expiration, /sprints/ghost
│       │   ├── test_cognitive_load.py  # EPIC 19 : derive_time_spent, pression, temps par phase, fluidité de décision
│       │   ├── test_srs_flashcards.py  # EPIC 20 : extraction flashcards depuis les gaffes (US 20.1)
│       │   ├── test_db_srs_flashcards.py # EPIC 20 : store flashcards (CRUD, isolation, échéance)
│       │   ├── test_srs_flashcards_api.py # EPIC 20 : câblage worker + routes /flashcards, /flashcards/due, /review
│       │   ├── test_coaching_voice.py  # EPIC 14 : build_move_alert (sévérité, pièce en prise) + attach_move_alert
│       │   └── test_game_salvage.py    # EPIC 15 : find_defeat_pivot (filtre couleur, seuil) + reconstruct_position_before_move
│       └── mutants/                    # Mutation testing mutmut (généré à l'exécution, gitignoré depuis l'audit 07/2026)
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
│       ├── 20260701194517_tactics_epic8.sql    # Table tactical_problems + profiles.tactical_elo + seed 15 problèmes (US 8.1)
│       ├── 20260701201530_tactical_attempts.sql # Table tactical_attempts (historique, RLS) (US 8.4)
│       ├── 20260701223519_opening_repertoire.sql # Table opening_repertoire (répertoire + SRS, RLS) (EPIC 9)
│       ├── 20260702051516_endgames_epic10.sql  # Table endgame_problems + profiles.endgame_elo + seed 9 positions (EPIC 10)
│       ├── 20260702064353_user_error_profiles_epic11.sql # Table user_error_profiles (score EMA, RLS) (EPIC 11)
│       ├── 20260702070437_tactical_sprints_epic12.sql # Table tactical_sprints (chrono, moves Ghost, RLS lecture publique) (EPIC 12)
│       ├── 20260702080000_game_moves_voice_alerts_epic14.sql # Colonnes alert_severity/alert_text/tts_text sur game_moves (EPIC 14)
│       ├── 20260702090000_games_pivot_epic15.sql # Colonne pivot_move_index sur games (EPIC 15)
│       ├── 20260702100000_profiles_settings_epic18.sql # Colonne settings (JSONB) sur profiles (EPIC 18)
│       ├── 20260702120000_game_moves_cognitive_load.sql # Colonnes fen/best_move_san/time_spent_seconds sur game_moves (EPIC 19)
│       └── 20260702130000_srs_flashcards_epic20.sql # Table srs_flashcards (calendrier SM-2, RLS) (EPIC 20)
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
_renderAuthState()          // Peuple #current-user : chip username (échappé via escapeHtml) + bouton Déconnexion
_openAuthModal()            // Retire l'attribut hidden sur #auth-modal
_closeAuthModal()           // Cache #auth-modal + réinitialise messages d'erreur
async _submitLogin(event)   // Appelle Auth.login() → _onAuthSuccess() ou affiche l'erreur
async _submitSignup(event)  // Appelle Auth.signup() → _onAuthSuccess() ou affiche l'erreur
_onAuthSuccess(user)        // Ferme modal, toast bienvenue, renderAuthState, auto-connect Chess.com
_onAuthLogout()             // Auth.logout() + renderAuthState()
```

#### Échappement HTML (audit sécurité 07/2026)

`app.js` expose un utilitaire `escapeHtml(value)` (échappe `& < > " '`) appliqué à toute donnée non maîtrisée interpolée dans de l'`innerHTML` : pseudo choisi à l'inscription (`_renderAuthState`), pseudos adverses / `time_class` / PGN renvoyés par l'API Chess.com (`_renderGamesList`, y compris l'attribut `data-pgn`, relu intact via `dataset.pgn` qui décode les entités). Sans cela, un pseudo adverse contenant du HTML s'exécutait dans le dashboard (XSS stocké via données tierces).

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
**URL API :** résolue paresseusement à chaque appel : `window.CI_API_URL` (surcharge E2E) → `window.API_BASE` (production, `config.js`) → `http://localhost:8000` (dev). **Audit 07/2026** : auparavant seul `CI_API_URL` était lu (au chargement du module), si bien qu'en production les appels d'auth partaient silencieusement vers `localhost:8000` au lieu du backend Render.

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

### 3.18 Dashboard de Performance Cognitive & Cimetière des Erreurs (EPIC 19/20)

**Fichiers :** `js/cognitive_dashboard.js`, `js/api_client.js`, `js/app.js` (`#flashcards-col`, `_loadFlashcardsSummary`), `index.html` (cartes « CHARGE COGNITIVE »/« CIMETIÈRE DES ERREURS », `#card-flashcards`)

**Module `CognitiveDashboard` (nouveau, même famille que `stats_dashboard.js`/`advanced_stats.js` — « zéro calcul client », `GET /api/v1/stats/cognitive-load`) :**

| Fonction | Rôle |
|---|---|
| `formatSeconds(seconds)` | libellé lisible (`"1m 20s"`, `"45s"`, `"—"` si inconnu) |
| `buildPhaseChartData(timeAllocation)` | données du graphe barre Chart.js (temps moyen par phase, 3 phases toujours présentes) |
| `buildInsightMessages(report)` | messages en langage naturel (phase dominante ≥ 60 %, écart pression/équilibre, fatigue décisionnelle) — logique pure, testée indépendamment du DOM |
| `fetchReport()` | délègue à `ApiClient.getCognitiveLoad()`, replie sur `EMPTY_REPORT` si non configuré/échec |
| `render(containerId, canvasId)` | glue DOM : insights en `<ul>`, graphe Chart.js |

**Câblage `app.js` :** `CognitiveDashboard.render("cog-dashboard-container", "cog-phase-chart")` appelé depuis `_loadAdvStats()`, indépendamment du résumé `AdvancedStats` (route distincte, jamais bloqué par son état vide).

**Le Cimetière des Erreurs — Recall Training (aucun nouveau module JS, mêmes principes que le Coach Tactique US 8.3) :**
- `ApiClient.getFlashcards()` / `getDueFlashcards()` / `reviewFlashcard(cardId, move)` — nouveaux clients HTTP (`api_client.js`).
- `app.js` : `_showFlashcards()`/`_hideFlashcards()` (toggle `body.flashcards-active`), `_loadFlashcardQueue()` (file du jour), `_loadNextFlashcard()`, `_initFlashcardBoard(card)`/`_onFlashcardDragStart`/`_onFlashcardDrop` (échiquier indépendant, identique en tout point à `_initTacticsBoard` — pas de moteur, pas de couplage au `#board` partagé), `_submitFlashcardAttempt(san)` (validation 100 % serveur, XP + streak sur succès), `_loadFlashcardsSummary()` (compteurs total/à réviser dans la carte Stats Avancées).
- Lancement : carte **CIMETIÈRE DES ERREURS** du dashboard principal (`#card-flashcards`) ou bouton **Rappel Actif →** de la carte Stats Avancées équivalente.

---

### 3.13 bis EPIC 22 — Stabilisation Critique du feedback d'analyse (US 22.1)

**Fichier :** `js/analysis_feedback.js` (nouveau module, testé à 100 %)

| API publique | Rôle |
|---|---|
| `createState()` | état neuf de dédoublonnage (à recréer à chaque nouvelle review) |
| `shouldDispatch(state, moveIdx, cpLoss, book)` | `true` seulement si le résultat d'analyse du coup a changé depuis la dernière émission (signature `book/mistake + cpLoss arrondi`) — bloque les ~20 messages `info` identiques que Stockfish émet par position |
| `shouldAlert(state, moveIdx, classification)` | `true` UNE SEULE fois par coup, et uniquement pour `blunder`/`mistake` — plus jamais d'alertes Coach empilées |

**Câblage :**
- `board_manager.js` : `this.feedbackState` (réinitialisé dans `startReview`) filtre les dispatchs `move:accuracy` via `shouldDispatch`.
- `app.js:_onMoveAccuracy` : `this._feedbackState` (réinitialisé dans `_enterReviewMode`) filtre l'alerte Coach via `shouldAlert` ; l'alerte s'affiche dans le bandeau `#analysis-alert` du panneau latéral (`_showAnalysisAlert`, contenu REMPLACÉ à chaque alerte), plus jamais en toasts au-dessus de l'échiquier.
- `app.js:_toast` : toast unique — tout nouveau message écrase l'existant (jamais d'empilement).
- US 22.3 : `_renderModulePlaceholders()` synchronise les placeholders des modules protégés (Coach Tactique, Cimetière, Technique de Mat, Ouvertures, Sprint) avec l'état d'authentification réel (loader « Vérification de la session… » pendant `autoConnect`, message prêt si connecté, invite sinon) ; correctif CSS : `body.tactics-active` n'affiche plus que `#tactics-col` (l'ancien sélecteur `.tactics-col` empilait les 4 modules avec leurs faux « Connectez-vous »).
- US 22.4 : `_emptyStateHtml(message, action)` — Empty State standard (message stimulant + bouton `[Analyser une partie]` ou `[Réessayer]`) utilisé par le Cimetière, le Coach Tactique, les Finales et le Sprint à la place des erreurs brutes ; pastilles du bloc EXERCICE libellées (Réussi / À revoir / Échoué + tooltips).

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
| `/games/{username}` | GET | Proxy Chess.com. **Audit sécurité 07/2026** : pseudo validé par regex `[A-Za-z0-9_-]{1,50}` (422 sinon, aucun appel réseau), encodage URL du pseudo dans `ChessComClient` (défense en profondeur), erreurs amont mappées en 404 (joueur inconnu) / 502 générique — le message d'exception interne n'est plus renvoyé au client. | ✅ Fonctionnel mais ⚠ non utilisé |
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
- **Audit sécurité 07/2026** : `decode_token` rejette tout header dont `alg != HS256` (anti « alg confusion » / `alg: none`) ; `POST /auth/login` vérifie un hash bcrypt factice quand l'email est inconnu, pour un temps de réponse constant (anti-énumération de comptes) ; au démarrage hors mode debug, `app.main` **refuse de démarrer** (`RuntimeError`, fail-fast) si `JWT_SECRET` est resté sur sa valeur par défaut — en dev local, définir `DEBUG=true` ou n'importe quel `JWT_SECRET` dans `.env` (le `webServer` Playwright fournit `e2e-test-secret` automatiquement).

**Listes blanches de colonnes SQL (audit sécurité 07/2026) :** `db_client.update_game` / `update_sprint` (et leurs pendants `PgRepository`) n'acceptent plus que des noms de champs figés (`GAME_UPDATABLE_FIELDS`, `SPRINT_UPDATABLE_FIELDS`) et lèvent `ValueError` sinon. Les noms de colonnes ne pouvant pas être paramétrés dans une requête SQL, ils étaient interpolés dans le `SET` — une liste fermée est la seule protection contre une injection via un nom de champ si un appelant futur relaie un jour des clés d'origine client.

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

### 4.8 EPIC 8 — Coaching Tactique Adaptatif (US 8.1-8.4)

**Fichiers :** `routers/tactics.py`, `domain/tactical_elo.py`, `domain/tactics.py`, `infrastructure/db_client.py`, `infrastructure/pg_repository.py`, `supabase/migrations/20260701194517_tactics_epic8.sql`, `supabase/migrations/20260701201530_tactical_attempts.sql`, `js/api_client.js`, `js/app.js`, `index.html` (`#tactics-col`)

> **Distinct du mode Exercice/SRS existant** (`js/app.js`, cartes en `localStorage`/`IndexedDB`) qui rejoue les propres gaffes détectées lors de l'analyse d'une partie du joueur. L'EPIC 8 introduit un **jeu de problèmes tactiques curés côté serveur** (dataset indépendant des parties du joueur), avec sélection adaptative par Elo et validation anti-triche systématiquement côté backend.

**Routes** (JWT requis, comme `games.py` depuis US 6.4) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/tactics/next` | GET | Problème le plus proche de l'Elo tactique de l'utilisateur authentifié (1000 par défaut). Ne renvoie **jamais** `solution`. `?theme_id=` (US 8.2) filtre par catégorie ; absent = « Aléatoire » ; valeur hors `TACTICAL_THEMES` → 422. |
| `/api/v1/tactics/attempt` | POST | Corps `{problem_id, move, time_taken?}` (SAN + secondes optionnelles). Valide le coup **côté serveur** contre la solution stockée, ajuste l'Elo tactique (+15/-15), enregistre la tentative (US 8.4), renvoie `{success, new_elo, solution, streak}` — la solution n'est révélée qu'après la tentative. |
| `/api/v1/tactics/stats` | GET | (US 8.4) Historique agrégé de l'utilisateur authentifié : `{by_theme: [{category, attempts, successes, success_rate}], streak}`. |

**Règles métier :**
- **Elo tactique** (`domain/tactical_elo.py`) : distinct de l'Elo virtuel Stats Avancées (EPIC 3, qualité des coups dans de vraies parties). `update_elo(current, success)` : +15 si réussi, −15 sinon, plancher à 100 (évite une dérive négative absurde après une série d'échecs). Stocké sur `profiles.tactical_elo` (colonne SQL) et répliqué dans le dict utilisateur in-memory (`db_client.create_user`), à l'image de `chess_username` (US 6.2) — le store `users`/`profiles` reste 100 % in-memory quel que soit `DATABASE_URL` (gap connu, §10.1).
- **Validation du coup** (`domain/tactics.is_correct_move`) : compare des objets `chess.Move` (python-chess), pas des chaînes SAN brutes — deux annotations différentes d'un même coup légal (ex. `Ra8` vs `Ra8#`) sont reconnues équivalentes. Toute notation invalide/illégale sur cette position est un échec silencieux (pas d'exception), jamais une confiance au client sur le résultat.
- **Sélection adaptative** (`domain/tactics.select_nearest_problem`) : problème dont `difficulty_elo` est le plus proche de l'Elo tactique du joueur ; tirage aléatoire parmi les problèmes équidistants pour éviter de toujours servir le même. `db_client.get_next_tactical_problem(tactical_elo, category=None)` filtre par catégorie si fourni.
- **Catégories (`domain.tactics.TACTICAL_THEMES`, US 8.2)** : `mate_in_1`, `mate_in_2`, `hanging_piece`. **Décision d'interprétation** : le spec pasté par l'utilisateur nommait le 4ᵉ item du menu « Tactique Positionnelle » tout en titrant l'US « Non-protégés » (incohérence interne) ; en l'absence d'un dataset de tactique positionnelle dédié, le menu expose **« Pièces non protégées »** (`hanging_piece`), cohérent avec le seed existant.
- **Seed de données (MVP)** : 15 problèmes (5 `mate_in_1`, 4 `hanging_piece`, 6 `mate_in_2`, Elo 650-1400), **chacun vérifié programmatiquement par python-chess** avant intégration (coup légal + `board.is_checkmate()` pour les catégories mat — y compris une recherche exhaustive « pour toute réponse adverse, un mat existe » pour `mate_in_2` — et capture d'une pièce sans défenseur pour `hanging_piece`). Choix motivé par l'absence d'accès réseau à un dataset externe (Lichess, etc.) dans cet environnement d'exécution ; le même jeu est répliqué en dur dans `db_client._TACTICAL_PROBLEMS_SEED` pour le mode in-memory dev/test et dans la migration SQL pour Supabase. **Reste à faire** : remplacer/enrichir par un import de dataset externe plus large (cf. §10).

**Frontend (US 8.2) :** carte **TACTIQUE** dans le dashboard → vue plein écran `#tactics-col` (`body.tactics-active`, même mécanisme de bascule que Stats Avancées) : menu de 4 boutons de catégorie, badge Elo tactique.

> **Bug latent corrigé (US 8.2) :** `ApiClient.url(path, query)` ajoutait un `?` orphelin (`/x?`) quand tous les paramètres de la query étaient `null`/absents — jamais rencontré avant `theme_id`, premier paramètre de query entièrement optionnel de l'API. Corrigé pour n'ajouter le `?` que si au moins un paramètre subsiste après filtrage ; couvert par un test de régression.

**Échiquier jouable (US 8.3) :** `app.js:_initTacticsBoard` instancie un échiquier **indépendant** de `BoardManager` (pas de couplage au `#board` partagé, pas de worker Stockfish embarqué) directement avec `Chess`/`Chessboard` (déjà chargés globalement), scopé à `#tactics-board`. Orientation = couleur au trait de la position.
- `_onTacticsDragStart` bloque le glisser hors-tour ou une fois le problème déjà résolu.
- `_onTacticsDrop` valide la légalité du coup localement (chess.js, pour le retour immédiat « snapback » si illégal) mais délègue **exclusivement au serveur** la validation de la *solution* via `ApiClient.submitTacticalAttempt(problemId, moveSan)` (`POST /api/v1/tactics/attempt`, déjà opérationnel depuis US 8.1) — le frontend ne connaît jamais la solution avant la réponse serveur (anti-triche, DoD).
- Feedback visuel : halo vert/rouge autour de l'échiquier (`.tactics-board--success`/`--error`), message de résultat sous l'échiquier (révèle la solution en cas d'échec), badge Elo mis à jour, puis enchaînement automatique vers un nouveau problème (même catégorie) après un court délai. Son : omis (marqué optionnel dans le DoD).

**Persistance et historique (US 8.4) :** table `tactical_attempts` (migration `20260701201530_tactical_attempts.sql` — `attempt_id`, `user_id`, `problem_id`, `success`, `time_taken`, `created_at`, RLS `user_id = auth.uid()::UUID`), avec `db_client.record_tactical_attempt`/`get_tactical_attempts` (in-memory dev/test, délégation `PgRepository` si `DATABASE_URL` — méthodes réellement implémentées cette fois, cf. §10.6).
- **Taux de réussite par thème** (`domain.tactics.compute_stats_by_theme`) : regroupe l'historique par catégorie, calcule `attempts`/`successes`/`success_rate`. Exposé via `GET /api/v1/tactics/stats`.
- **Série en cours du jour** (`domain.tactics.compute_daily_streak`, recommandation PO) : nombre de problèmes résolus d'affilée *aujourd'hui* — calculé à la volée en parcourant l'historique du plus récent au plus ancien, interrompu au premier échec ou à la première tentative d'un jour différent. Pas de compteur dupliqué à maintenir : une seule source de vérité (l'historique).
- Frontend : badge **🔥 Série** dans la topbar du Coach Tactique (à côté du badge Elo), initialisé via `ApiClient.getTacticsStats()` à l'ouverture de la vue et rafraîchi après chaque tentative. Une réussite alimente également le système XP/Streak général déjà existant (`XPSystem`, `StreakSystem` — jours d'activité consécutifs, mode Exercice/Ghost), volontairement **non fusionné** avec le streak tactique quotidien (deux notions différentes : activité générale vs. série de réussites du jour sur les problèmes tactiques).
- `time_taken` (secondes, optionnel) mesuré côté frontend entre l'affichage de l'échiquier et le coup joué, transmis au serveur pour persistance.

### 4.9 EPIC 9 — Entraîneur d'Ouvertures (Répertoire + SRS) — fonctionnalité bonus auto-initiée

**Fichiers :** `routers/openings_trainer.py`, `domain/opening_repertoire.py`, `domain/srs_engine.py` (fonction `sm2_schedule` extraite), `infrastructure/db_client.py` + `pg_repository.py`, `supabase/migrations/20260701223519_opening_repertoire.sql`, `js/api_client.js`, `js/app.js`, `index.html` (`#openings-trainer-col`)

> **Contexte :** une fois l'intégralité du backlog EPIC 6/7/8 traité, l'utilisateur a explicitement autorisé le développement d'**une** fonctionnalité à ma discrétion, non spécifiée par une US existante. Choix retenu : un entraîneur de répertoire d'ouvertures par répétition espacée (SM-2), qui ferme la boucle entre le diagnostic déjà existant (§4.5, `top_openings`/`successRatio` par ouverture) et un entraînement ciblé — jusqu'ici absent du produit malgré un moteur SM-2 déjà présent (mode Exercice tactique, cartes 100 % `localStorage`).

**Routes** (JWT requis) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/openings/repertoire` | POST | Ajoute une ligne `{name, color, moves[]}`. La séquence SAN est rejouée coup par coup côté serveur (`python-chess`) — une ligne illégale est rejetée en 422, jamais de confiance aveugle au client. |
| `/api/v1/openings/repertoire` | GET | Liste tout le répertoire de l'utilisateur authentifié. |
| `/api/v1/openings/repertoire/due` | GET | Lignes dont l'échéance SM-2 est arrivée ou dépassée aujourd'hui. |
| `/api/v1/openings/repertoire/{id}/review` | POST | Corps `{mistake_count}`. Reprogramme la ligne (SM-2) — la qualité (0-5) est **déduite automatiquement** du nombre d'erreurs, jamais notée manuellement. |
| `/api/v1/openings/repertoire/{id}` | DELETE | Retire une ligne (propriétaire uniquement, 404 sinon). |

**Règles métier :**
- **Pas de duplication d'algorithme** : un moteur SM-2 Python testé existait déjà (`domain/srs_engine.py`, utilisé par `/srs/review/full` pour les cartes tactiques du mode Exercice). Plutôt que d'écrire un second portage SM-2, la formule pure a été **extraite** de `review_card` en une fonction réutilisable `sm2_schedule(ease_factor, interval, repetitions, quality, today)` — `review_card` n'est plus qu'un fin wrapper autour de `SRSCard` qui délègue à cette fonction (comportement strictement identique, 31 tests existants inchangés + tests de non-régression d'équivalence ajoutés). L'entraîneur d'ouvertures appelle directement `sm2_schedule`, sans dupliquer la moindre formule.
- **Qualité déduite automatiquement** (`domain/opening_repertoire.infer_quality`) : 0 erreur → 5 (rappel parfait), 1 erreur → 3, 2+ erreurs → 1 — pas de notation manuelle post-révision, pour rester ludique et rapide (contrainte explicite de la demande initiale : gamifier sans rendre l'expérience rébarbative).
- **Validation de la séquence** (`domain/opening_repertoire.validate_move_sequence`) : rejoue chaque coup SAN depuis la position initiale via `python-chess` ; toute notation invalide/illégale est rejetée avant tout enregistrement.
- **Persistance** : table `opening_repertoire` (colonne SQL `line_name` — `name` est un mot réservé sqlfluff/RF04, remappée en `name` côté `PgRepository._line_row` pour ne pas fuiter ce détail dans l'API), RLS scoping par utilisateur. `db_client`/`PgRepository` implémentent la délégation complète (create/list/due/update/delete), sans reproduire le gap `tactical_problems` de US 8.1 (§10.6).

**Frontend :** carte **OUVERTURES** dans le dashboard → vue plein écran `#openings-trainer-col` (`body.openings-trainer-active`, même mécanisme de bascule que Coach Tactique/Stats Avancées).
- **Ajout d'une ligne** : formulaire nom + couleur + coups SAN espacés (ex. `e4 e5 Nf3 Nc6 Bb5`).
- **Révision** : échiquier indépendant (même approche que US 8.3, `Chess`/`Chessboard` directs) qui rejoue la ligne — les coups de la couleur adverse s'enchaînent automatiquement (`_advanceOpeningLine`, boucle de `setTimeout` pilotée par `chess.turn()`, pas par la parité de l'index), l'utilisateur ne joue que les coups de sa propre couleur ; un coup incorrect fait un « snapback » et incrémente le compteur d'erreurs sans bloquer la progression. À la fin de la ligne, la qualité est déduite et soumise automatiquement (`ApiClient.reviewOpeningLine`), puis la ligne suivante due s'enchaîne — ou un message gamifié (« 🎉 Aucune ligne à réviser aujourd'hui ») si le répertoire est à jour. Une révision sans erreur alimente aussi le système XP/Streak général existant.
- **Garde-fou anti-double-soumission** (`_otFinished`) : ajouté après un test Playwright ayant révélé qu'un scénario artificiel (simulation de coups sans attendre les `setTimeout` réels) pouvait déclencher `_finishOpeningReview` plusieurs fois pour la même ligne ; en usage normal humain cela ne se produit pas (un seul `setTimeout` en vol à la fois), mais le garde-fou élimine le risque par construction.
- Vérifié en navigateur (Playwright + Chromium, backend/frontend locaux) : ajout d'une ligne, échiquier de révision monté, ligne rejouée sans erreur → Elo... XP +10, prochaine échéance 2026-07-02 (J+1, cohérent avec un premier succès SM-2), état vide gamifié affiché ensuite. Captures à l'appui.
- Tests : `backend/tests/test_opening_repertoire.py` (validation + `infer_quality`), `backend/tests/test_db_opening_repertoire.py` (CRUD + isolation), `backend/tests/test_openings_trainer_api.py` (17 tests d'intégration : création/liste/due/révision/suppression, 401/404/422, isolation entre utilisateurs), `backend/tests/test_srs.py` (`sm2_schedule` + équivalence avec `review_card`), `backend/tests/test_pg_repository.py` (contrat de signature + mapping `line_name`↔`name`), `frontend/tests/api_client.test.js` (6 nouveaux tests).

### 4.10 EPIC 10 — Entraîneur de Finales Essentielles — 2ᵉ fonctionnalité bonus auto-initiée

**Fichiers :** `routers/endgames.py`, `domain/endgames.py`, `infrastructure/db_client.py`, `supabase/migrations/20260702051516_endgames_epic10.sql`, `js/api_client.js`, `js/app.js`, `index.html` (`#endgame-trainer-col`)

> **Contexte :** une fois EPIC 9 mergée, l'utilisateur a explicitement demandé de lancer la piste « finales », déjà notée comme idée future (ancien §11.10) faute de temps lors du choix initial d'EPIC 9. Distinct du mode **FINALES** existant (`EndgameDetector`, diagnostic post-partie sur les propres parties jouées) : ce nouvel entraîneur est un **jeu de positions curées** de technique de mat essentielle, sur le modèle exact d'EPIC 8 (US 8.1) mais pour un thème différent.

**Pas de duplication d'architecture** : `routers/endgames.py` réutilise **directement** `domain.tactics.is_correct_move`/`select_nearest_problem` et `domain.tactical_elo.update_elo` — ce sont des fonctions pures déjà génériques (elles opèrent sur des dicts `fen`/`solution`/`difficulty_elo`, sans rien de spécifique aux puzzles tactiques). `domain/endgames.py` ne contient donc que la liste des catégories (`ENDGAME_THEMES`) et la justification de ce choix ; aucune formule n'est réécrite.

**Routes** (JWT requis) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/endgames/next` | GET | Position la plus proche de l'Elo « finales » de l'utilisateur (1000 par défaut, distinct de l'Elo tactique EPIC 8). `?theme_id=` filtre par catégorie ; valeur hors `ENDGAME_THEMES` → 422. |
| `/api/v1/endgames/attempt` | POST | Corps `{problem_id, move}`. Valide le coup **côté serveur**, ajuste l'Elo « finales » (+15/-15), révèle la solution après la tentative. |

**Règles métier :**
- **Elo « finales »** (`db_client.get_endgame_elo`/`update_endgame_elo`) : stocké directement dans le dict utilisateur in-memory (`endgame_elo`, 1000 par défaut), comme `tactical_elo` — même gap connu (in-memory quel que soit `DATABASE_URL`, §10.1). Colonne SQL `profiles.endgame_elo` créée par la migration pour la persistance Supabase, sans tentative de délégation Postgres côté `db_client`/`PgRepository` pour la table `endgame_problems` (volontaire : évite de reproduire le piège d'US 8.1 où `tactical_problems` délègue à des méthodes jamais écrites, cf. §10.6 — cette table reste ici honnêtement 100 % in-memory, sans fausse promesse de support Postgres).
- **Catégories (`domain.endgames.ENDGAME_THEMES`)** : `queen_mate` (Roi+Dame vs Roi), `rook_mate` (Roi+Tour vs Roi), `two_rooks_mate` (Roi+2 Tours vs Roi) — trois techniques de mat fondamentales, chacune un thème distinct des catégories tactiques d'EPIC 8 (`mate_in_1`/`mate_in_2`/`hanging_piece`, positions avec plus de matériel où il faut *repérer* un coup, contre ici *exécuter* une technique de mat avec matériel réduit).
- **Seed de données** : 9 positions (3 par catégorie), **chacune vérifiée programmatiquement par python-chess** (recherche exhaustive par force brute des combinaisons Roi/Roi/pièce(s) menant à un mat en 1, même méthodologie que le seed tactique d'US 8.1) avant intégration — verrouillé par `test_db_endgames.py::TestSeedIntegrity`.

**Frontend :** carte **TECHNIQUE DE MAT** dans le dashboard → vue plein écran `#endgame-trainer-col` (`body.endgame-trainer-active`), échiquier indépendant identique en tout point à l'implémentation US 8.3 (`_initEndgameBoard`/`_onEndgameDrop`/`_submitEndgameAttempt`, dupliqué avec des identifiants DOM et endpoints distincts plutôt que factorisé avec le Coach Tactique — cohérent avec le fait qu'aucun des trois échiquiers indépendants du produit, EPIC 8/9/10, ne partage de code de câblage DOM entre eux : trois blocs similaires mais autonomes plutôt qu'une abstraction prématurée). Réutilise les classes CSS génériques `.tactics-board`/`.tactics-feedback`/`.tactics-theme-btn` déjà définies pour EPIC 8.
- Vérifié en navigateur (Playwright + Chromium, backend/frontend locaux) : coup correct → halo vert, Elo 1000→1015, message « Bravo, mat trouvé ! » ; coup incorrect → halo rouge, solution révélée. Captures à l'appui.
- Tests : `backend/tests/test_db_endgames.py` (intégrité du seed + store), `backend/tests/test_endgames_api.py` (13 tests d'intégration), `frontend/tests/api_client.test.js` (5 nouveaux tests).

### 4.11 EPIC 13 — Indépendance et Rapatriement des Assets (Anti-Proxy)

**Fichiers :** `frontend/assets/{js,css,fonts,images/pieces,data/openings}/`, `index.html`, `js/app.js`, `js/board_manager.js`, `js/engine_worker_wasm.js`, `frontend/tests/e2e/helpers.js`

> **Contexte :** demande explicite de l'utilisateur (US 12.1, priorité 0 du PO) — l'application chargeait jusqu'ici jQuery/chess.js/chessboard.js/Chart.js depuis `cdnjs.cloudflare.com`/`cdn.jsdelivr.net`, les polices depuis `fonts.googleapis.com`, les pièces d'échecs depuis `lichess1.org`, et le référentiel d'ouvertures ECO depuis `raw.githubusercontent.com` en direct dans le navigateur de l'utilisateur final. Ces domaines sont fréquemment bloqués par des pare-feux d'entreprise, rendant l'application inutilisable dans ce contexte. Objectif : zéro dépendance réseau tierce au chargement de la page.

**Rapatriement (aucun fichier généré ni build) :**
- `assets/js/` : jQuery 3.7.1, chess.js 0.10.3, chessboard.js 1.0.0, Chart.js 4.4.0 — binaires strictement identiques aux versions CDN utilisées jusqu'ici (mêmes numéros de version), obtenus via les paquets npm officiels des mêmes librairies plutôt que par téléchargement direct depuis le CDN.
- `assets/css/chessboard-1.0.0.min.css` : feuille de style associée à chessboard.js.
- `assets/css/fonts.css` + `assets/fonts/*.woff2` : Google Fonts (IBM Plex Mono 400/600, Inter variable) re-générées avec des `url()` locales ; seuls les sous-ensembles `latin`/`latin-ext` sont conservés (cyrillique/grec/vietnamien supprimés), réduisant le CSS Google d'origine (45 blocs `@font-face`) à 14 blocs pointant vers 6 fichiers `.woff2` uniques.
- `assets/images/pieces/{w,b}{P,N,B,R,Q,K}.svg` : 12 SVG du jeu cburnett, mêmes tracés que ceux servis jusqu'ici par `lichess1.org`.
- `assets/data/openings/{a,b,c,d,e}.tsv` : référentiel ECO (nom d'ouverture ↔ PGN), format TSV inchangé.

**Code applicatif mis à jour :** `index.html` (balises `<script>`/`<link>` pointent vers `assets/js/`/`assets/css/`), `app.js` (`pieceTheme` × 3 échiquiers + `_buildOpeningBook()`), `board_manager.js` (`pieceTheme`) — tous remplacent une URL CDN par un chemin local relatif, sans changement de logique.

**Moteur Stockfish :** `engine_worker_wasm.js` ne tente plus de charger un Stockfish WASM depuis un CDN (`WASM_CDNS = []`) et retombe directement sur le fallback asm.js déjà vendorisé localement (`js/stockfish.js`, `ASM_CDNS = ["stockfish.js"]`). Fonctionnellement identique pour l'utilisateur (le fallback se déclenchait de toute façon dès que le CDN WASM était inaccessible) — perte : pas de WASM+NNUE tant qu'un build auto-hébergé n'est pas ajouté (cf. §10).

**Code mort supprimé :** `frontend/js/engine_worker.js` — confirmé non référencé par aucun fichier du dépôt (seul `engine_worker_wasm.js` est câblé, cf. `board_manager.js:_tryWorker`) ; supprimé plutôt que patché.

**Hors périmètre (volontairement non touché)** : `chess-com-api.js`/`api_client.js` vers `api.chess.com` et `tablebase.lichess.ovh` (Syzygy) restent des appels réseau **applicatifs** (données utilisateur/tablebase en temps réel, pas des « assets » statiques) — l'US 12.1 vise l'indépendance de chargement de l'application, pas la suppression de ses intégrations tierces fonctionnelles. `js/config.js` (`API_BASE`) pointe vers notre propre backend, également hors périmètre.

**Suite E2E Playwright** : les routes de stub CDN (`frontend/tests/e2e/helpers.js`) interceptaient jusqu'ici des domaines externes (`**cdnjs.cloudflare.com**`, etc.) — mises à jour pour intercepter les nouveaux chemins locaux (`**/assets/js/chess-0.10.3.js`, etc.), sans quoi les vraies librairies auraient chargé et cassé les scénarios à cases fixes. Les 8 tests E2E existants repassent inchangés après cette migration.

- Vérifié en navigateur (Playwright + Chromium) : chargement complet + inscription + ouverture du Coach Tactique avec **zéro requête réseau externe** (toutes les requêtes restent sur `localhost`), pièces cburnett et police Inter correctement rendues (capture à l'appui).
- Pas de nouveaux tests unitaires (aucune logique métier modifiée — uniquement des chemins de ressources statiques) ; couverture de régression assurée par la suite E2E existante + vérification manuelle du zéro-appel-externe.

### 4.12 EPIC 11 — Analyse Comportementale (Psychologie) — profil d'erreurs récurrentes

**Fichiers :** `domain/error_profile.py`, `routers/error_profile.py`, `routers/tactics.py` (route `/custom`), `routers/games.py` (câblage worker), `infrastructure/db_client.py` + `pg_repository.py`, `supabase/migrations/20260702064353_user_error_profiles_epic11.sql`, `js/api_client.js`, `js/app.js`, `index.html` (`#tactics-custom-training`)

> **Contexte :** backlog fourni par l'utilisateur, traité juste après EPIC 13 (« Priorité 0 » du PO). Renuméroté EPIC 11 (collision avec EPIC 9 déjà enregistré) — voir rationale complet en tête de §4.11.

**Détection des patterns (`domain/error_profile.detect_error_occurrences`)** — aucune duplication d'algorithme :
- **`hanging_piece`** / **`time_pressure`** : réutilisent directement le moteur géométrique déjà existant (`domain.analyzer.analyze_pgn`, actif depuis les tout premiers US du produit) plutôt que de redétecter une pièce non défendue depuis `game_moves`, qui ne stocke pas l'état de l'échiquier nécessaire à ce calcul. Une gaffe sous forte chute de temps (`time_panic_count > 0`) est classée exclusivement `time_pressure`, jamais aussi `hanging_piece` (différence d'ensemble entre `blunder_moves` et `time_panic_moves`) — pas de double-comptage d'une même erreur.
- **`missed_mate`** : dérivé de `game_moves` (US 1.2) — un coup joué **par l'utilisateur** (`color == user_color`) pour lequel le meilleur coup du moteur menait à un mat forcé (`is_mate=True`) mais dont le coup réellement joué n'était pas ce mat (`cpl > 0`).

**Score de fréquence (`update_frequency_score`)** : moyenne mobile exponentielle (0-100, `alpha=0.3`), même principe de mise à jour incrémentale pure que l'Elo tactique (`domain.tactical_elo.update_elo`, ±15) ou le calendrier SM-2 (`domain.srs_engine.sm2_schedule`) — jamais de recalcul depuis tout l'historique des parties à chaque analyse. Une erreur commise pousse le score vers 100, une partie propre sur ce plan le pousse vers 0 ; 4 occurrences consécutives suffisent à dépasser le seuil de 70 (`RECURRING_THRESHOLD`). `is_recurring` (score > 70) est **calculé à la lecture**, jamais stocké — c'est un état dérivé de `frequency_score`, pas une donnée en soi (cohérent avec le schéma minimal demandé : `user_id`/`error_type`/`frequency_score`/`last_observed`, rien de plus).

**Routes** (JWT requis) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/error-profile` | GET | Liste les profils d'erreur déjà observés de l'utilisateur (un par `error_type`), avec `is_recurring` calculé. |
| `/api/v1/tactics/custom` | GET | Paramètre `focus` = un `error_type` (pas un `theme_id` tactique brut). Le backend fait la correspondance (`ERROR_TYPE_TO_TACTICAL_THEMES` : `hanging_piece`→`hanging_piece`, `time_pressure`→`hanging_piece` (même cause géométrique), `missed_mate`→`mate_in_1`/`mate_in_2`) puis délègue à `select_nearest_problem` (US 8.1, réutilisé sans duplication) sur le pool de thèmes obtenu. `focus` inconnu → 422, comme `theme_id` sur `/tactics/next`. |

**Câblage worker (`routers/games.run_analysis`)** : après chaque analyse de partie réussie, un 3ᵉ bloc `try/except` (même garde-fou que le snapshot de progression US 5.1 juste au-dessus) détecte les occurrences du PGN + des `game_moves` fraîchement persistés, puis met à jour les 3 profils (`ERROR_TYPES`) via `db_client.upsert_error_profile`. Un échec de cette étape ne fait jamais échouer l'analyse déjà persistée.

**Persistance** : table `user_error_profiles` (`error_type` en `TEXT` + `CHECK`, pas un type `ENUM` Postgres natif — cohérence avec `games.status`/`opening_repertoire.color`/`game_moves.phase` qui suivent tous ce même choix), contrainte `UNIQUE(user_id, error_type)` (upsert), RLS scoping par utilisateur. `db_client`/`PgRepository` implémentent la délégation complète (get/list/upsert), sans reproduire le gap `tactical_problems` de US 8.1 (§10.6).

**Frontend :** au moment d'ouvrir le Coach Tactique (`_showTactics`), `_loadErrorProfileHint()` interroge `/error-profile` et affiche un bandeau **« Entraînement Personnalisé »** (`#tactics-custom-training`) si un type d'erreur est récurrent, avec un libellé lisible (`ERROR_TYPE_LABELS`). Cliquer sur le bouton (`_startCustomTraining`) appelle `ApiClient.getCustomTacticalProblem(errorType)` au lieu de `getNextTacticalProblem` ; l'enchaînement automatique après résolution (`_submitTacticsAttempt`, `setTimeout`) préserve le focus personnalisé (`this._customFocus`) tant que l'utilisateur ne sélectionne pas un thème classique.

- Vérifié en navigateur (Playwright + Chromium) : 4 parties avec la même gaffe (pièce non protégée) → bandeau affiché avec le bon libellé ; clic sur le bouton → problème `hanging_piece` chargé ; sans erreur récurrente, bandeau masqué. Captures à l'appui.
- Tests : `backend/tests/test_error_profile.py` (détection + score EMA, 15 tests), `backend/tests/test_db_error_profile.py` (CRUD store, 10 tests), `backend/tests/test_error_profile_api.py` (12 tests d'intégration : câblage worker, isolation entre utilisateurs, `/tactics/custom` 200/422/401), `backend/tests/test_pg_repository.py` (contrat de signature), `frontend/tests/api_client.test.js` (4 nouveaux tests), `frontend/tests/e2e/error_profile.spec.js` (3 tests bout-en-bout).

### 4.13 EPIC 12 — Mode "Tactical Sprint" (Social & Compétitif)

**Fichiers :** `domain/tactical_sprint.py`, `routers/tactical_sprint.py`, `infrastructure/db_client.py` + `pg_repository.py`, `supabase/migrations/20260702070437_tactical_sprints_epic12.sql`, `js/api_client.js`, `js/app.js`, `index.html` (`#sprint-col`)

> **Contexte :** backlog fourni par l'utilisateur, traité en dernier des 3 EPIC (11/12/13) par ordre de priorité PO. Recommandation PO explicite suivie à la lettre : mode Ghost simple (coups enregistrés + rejoués), un fetch/GET plutôt qu'une synchronisation WebSocket.

**Chrono anti-triche 100 % serveur** (`domain.tactical_sprint.is_sprint_active`/`elapsed_seconds`) : contrairement à un minuteur qui bloquerait un worker par sprint actif (`asyncio.sleep`, ne passerait pas à l'échelle), le backend reste stateless entre requêtes — `started_at` est fixé au démarrage, et chaque tentative recalcule le temps écoulé côté serveur (`now() - started_at`) pour décider si le sprint est encore actif. Une tentative reçue hors fenêtre clôture le sprint automatiquement et ne compte jamais, quel que soit ce que le client affiche à cet instant — le décompte visuel côté frontend n'est qu'un affichage, jamais la source de vérité.

**Routes** (JWT requis) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/sprints/start` | POST | Démarre un sprint (`started_at=now()`), renvoie `sprint_id`, la durée autorisée (60s) et le premier problème (sélection adaptative par Elo tactique, réutilise `get_next_tactical_problem` — aucune duplication). |
| `/api/v1/sprints/{id}/attempt` | POST | Valide le coup **côté serveur** (`is_correct_move`, réutilisé de l'US 8.1) ; un coup correct incrémente `problems_solved_count`/`score` et enregistre le coup pour le mode Ghost ; renvoie toujours le problème suivant si le temps restant le permet (correct ou non — un sprint avance quel que soit le résultat, contrairement au Coach Tactique classique). |
| `/api/v1/sprints/{id}/finish` | POST | Clôture le sprint (abandon volontaire ou temps écoulé côté client), fige `duration_seconds`/`score` finaux. Idempotent. |
| `/api/v1/sprints/ghost` | GET | Meilleur sprint **terminé**, toutes utilisateurs confondus — un simple GET, pas de WebSocket (cf. recommandation PO), appelé une seule fois au démarrage d'un sprint (pas de polling continu : le classement ne change qu'à la clôture d'un sprint). |

**Règles métier :**
- **Score** (`domain.tactical_sprint.compute_score`) : 10 points fixes par problème résolu (MVP, pas de bonus de vitesse pour l'instant — cf. §10).
- **Sélection des problèmes** : réutilise `db_client.get_next_tactical_problem`/`select_nearest_problem` (US 8.1) sur l'Elo tactique de l'utilisateur, **jamais modifié par un sprint** (le score de sprint est distinct de l'Elo tactique classique, cohérent avec la séparation déjà en place Elo tactique/Elo finales d'EPIC 10).
- **Séquence Ghost** (`domain.tactical_sprint.record_ghost_move`) : chaque coup **résolu** est ajouté à `moves` (JSONB, `[{problem_id, move, elapsed_ms}]`) — pas de PGN littéral nécessaire, chaque entrée référence sa propre position de départ via `problem_id` (déjà connu du store `tactical_problems`).
- **Persistance** : table `tactical_sprints`, seule table du schéma à RLS **partiellement publique** (`SELECT` ouvert à tous — mode Ghost = fonctionnalité compétitive/sociale par nature, cf. titre EPIC 12 ; `INSERT`/`UPDATE` restent restreints au propriétaire). `db_client`/`PgRepository` implémentent la délégation complète (create/get/update/best), sans reproduire le gap `tactical_problems` de US 8.1 (§10.6).

**Frontend :** carte **SPRINT** dans le dashboard → vue plein écran `#sprint-col` (`body.sprint-active`, même mécanisme que les autres entraîneurs). Timer en haut (`#sprint-timer-badge`, décompte client purement visuel, `setInterval` 1s), compteur de problèmes résolus en bas (`#sprint-solved-count`), échiquier indépendant identique en tout point aux autres entraîneurs (`_initSprintBoard`/`_onSprintDrop`). Case à cocher **Ghost** (`#sprint-ghost-toggle`) : affiche un bandeau (`#sprint-ghost-overlay`) comparant la progression du meilleur sprint enregistré à l'instant courant du sprint en cours (nombre de coups Ghost déjà résolus à ce temps écoulé) — lecture pure du fetch initial (`_startSprint`), aucun appel réseau supplémentaire pendant le sprint.

- Vérifié en navigateur (Playwright + Chromium) : sprint démarré, coup résolu → compteur à jour, sprint clôturé (simulation d'expiration) → message de score final, Ghost affiché avec le score du meilleur sprint précédent. Captures à l'appui.
- Tests : `backend/tests/test_tactical_sprint.py` (chrono + score, 12 tests), `backend/tests/test_db_tactical_sprint.py` (CRUD store + visibilité publique du meilleur sprint, 9 tests), `backend/tests/test_tactical_sprint_api.py` (14 tests d'intégration : cycle complet start/attempt/finish, expiration côté serveur, isolation propriétaire, `/sprints/ghost`), `backend/tests/test_pg_repository.py` (contrat de signature), `frontend/tests/api_client.test.js` (5 nouveaux tests), `frontend/tests/e2e/sprint.spec.js` (3 tests bout-en-bout).

### 4.14 EPIC 14 — Système de "Shadow Coaching" Vocal (Coach Vocal et Feedback Instantané)

**Fichiers :** `domain/coaching_voice.py`, `domain/analysis_pipeline.py` (câblage), `infrastructure/pg_repository.py` (`_MOVE_COLS`), `supabase/migrations/20260702080000_game_moves_voice_alerts_epic14.sql`, `js/coaching_voice.js`, `js/app.js` (`_onMoveAccuracy`), `index.html` (`#btn-voice-coach`)

> **Contexte :** backlog fourni par l'utilisateur (« Idée 3 »), initialement numéroté « EPIC 13 » dans le paste — **renuméroté EPIC 14** pour éviter la collision avec l'EPIC 13 déjà enregistré dans ce dépôt (Indépendance des Assets, §4.11), même rationale que les renumérotations EPIC 11/12/13 précédentes.

**US 14.1 (alertes tactiques) + US 14.2 (TTS)** sont traitées ensemble : la même détection produit à la fois le texte d'alerte affiché et sa variante narrée.

**Détection (`domain.coaching_voice.build_move_alert`)** — aucune duplication de seuils :
- La gravité réutilise directement la classification de précision existante (`elo_calculator.classify_move(elo_calculator.move_accuracy(cpl))`) — mêmes seuils que la coloration Review déjà affichée au joueur (`brilliant`..`blunder`). Seules les classifications `mistake`/`blunder` déclenchent une alerte ; le reste reste silencieux.
- Le message est **contextuel**, pas un simple label : `analyzer.is_piece_hanging` (déjà utilisé par EPIC 11 pour le profil comportemental) identifie, sur la position résultant du coup, la pièce la plus précieuse du joueur laissée en prise et non défendue. Trouvée → « Attention, Qd4 expose ta dame en d4 ! » ; sinon → message générique par gravité (« Gaffe ! … perd un avantage important. » / « … n'était pas le meilleur coup. »).
- `attach_move_alert` enrichit en place un enregistrement `game_moves` (`alert_severity`/`alert_text`/`tts_text`), appelé depuis `analysis_pipeline.analyze_pgn` juste après le calcul du CPL de chaque coup — zéro appel moteur supplémentaire (la position après-coup est déjà disponible dans la boucle d'analyse).

**Persistance :** 3 colonnes nullable ajoutées à `game_moves` (`alert_severity`, `alert_text`, `tts_text`) — absentes du dict si le coup ne déclenche aucune alerte, cohérent avec le reste du schéma (`mate_in`, `eval_before`… déjà optionnels).

**US 14.2 — Synthèse vocale (frontend, `js/coaching_voice.js`) :** branchée sur le flux **temps réel** existant du mode Review (`_onMoveAccuracy`, déclenché à chaque évaluation Stockfish pendant que le joueur navigue/rejoue une partie) plutôt que sur le pipeline batch backEND ci-dessus (qui alimente les parties EPIC 1/Stats Avancées, un système distinct du Bilan client-side, cf. §2) :
- **Zero External Assets** (contrainte EPIC 13/17) : la synthèse vocale utilise l'API **Web Speech** native du navigateur (`speechSynthesis`/`SpeechSynthesisUtterance`, `lang="fr-FR"`) — aucun fichier audio, aucun appel réseau (contrairement à gTTS, qui nécessiterait un aller-retour vers un service Google). Le signal sonore (`CoachingVoice.beep`) est un oscillateur `AudioContext` généré en code (220Hz gaffe / 330Hz erreur), pour la même raison.
- `CoachingVoice.alertFor(classification, san)` reproduit côté client la même logique de gravité (blunder/mistake) que le backend, sur la classification déjà calculée par `EloEngine.classify` (US 5) — pas de duplication de seuils, juste du texte.
- La narration lit l'**idée principale du meilleur coup** (US 14.2) : le premier coup de la PV Stockfish déjà mise en cache par `board_manager.js` (`evalCache[fen].pv`, déjà utilisée pour créer les cartes SRS US 4) est converti UCI → SAN (`_sanFromUci`, chess.js) puis narré (« Le meilleur coup était Nxe5. »).
- Désactivée par défaut (opt-in, persisté `localStorage["ci_voice_coach"]`) — toggle `#btn-voice-coach` dans la barre d'outils Review ; un toast visuel (`_toast`) accompagne systématiquement l'alerte, que la voix soit activée ou non.

- Vérifié en intégration réelle (backend local + `curl`) : un PGN avec une gaffe programmée (cpl=300, pièce en prise construite) renvoie bien `alert_severity: "blunder"`, `alert_text` nommant la pièce et la case, `tts_text`, et `games.pivot_move_index` correctement calculé (cf. §4.15). Vérifié en navigateur (Playwright + Chromium) : bouton `#btn-voice-coach` bascule texte/classe et persiste en `localStorage` après un clic réel.
- Tests : `backend/tests/test_coaching_voice.py` (8 tests : silence sans CPL/bon coup, message générique vs pièce nommée, ignoré si la pièce en prise n'appartient pas au joueur, `attach_move_alert`), `backend/tests/test_analysis_pipeline.py` (existant, toujours vert — le câblage n'altère aucun champ existant), `backend/tests/test_pg_repository.py` (contrat `_MOVE_COLS` étendu), `frontend/tests/coaching_voice.test.js` (19 tests : préférence localStorage, `alertFor`/`bestMoveNarration`, `beep`/`speak` avec/sans API navigateur disponible).

### 4.15 EPIC 15 — Moteur de "Replay Correction" (Game-Salvage / Réparation de Partie)

**Fichiers :** `domain/game_salvage.py`, `routers/games.py` (`run_analysis` + `POST /games/{id}/salvage`), `supabase/migrations/20260702090000_games_pivot_epic15.sql`, `js/board_manager.js` (mode `sandbox`), `js/api_client.js` (`salvageGame`), `js/app.js` (`_startSalvage`), `index.html` (`#btn-salvage`)

> **Contexte :** backlog fourni par l'utilisateur (« Idée 4 »), initialement numéroté « EPIC 14 » dans le paste — **renuméroté EPIC 15** pour la même raison que §4.14 (collision avec l'EPIC 14 déjà attribué au Coach Vocal dans ce dépôt).

**US 15.1 — Pivot de défaite (`domain.game_salvage.find_defeat_pivot`)** : premier coup **joué par le joueur** (filtré par `color == user_color`, pas l'adversaire — sauver la partie signifie réparer sa propre gaffe) dont le CPL atteint le seuil de gaffe déjà défini par `stats_aggregator.BLUNDER_CPL` (200 centipions, réutilisé tel quel plutôt que d'introduire un second seuil de gaffe dans le produit). Calculé une fois à la fin de `run_analysis` (comme `eco`/`opening_name`) et persisté dans une nouvelle colonne `games.pivot_move_index` (nullable — `None` si aucune gaffe de cette ampleur n'a été commise ou si la partie n'a pas été évaluée par un moteur).

**US 15.2 — Reconstruction + Sandbox :**
- `domain.game_salvage.reconstruct_position_before_move(pgn, move_index)` rejoue le PGN (python-chess) jusqu'au coup précédant le pivot et renvoie `{fen, side_to_move, move_number}` — la position **juste avant** la gaffe historique, pour que le joueur puisse tenter un autre coup à la place plutôt que de revivre la même erreur.
- `POST /api/v1/games/{game_id}/salvage` (JWT requis) : 404 si la partie n'existe pas/n'appartient pas à l'utilisateur (même traitement indiscernable que le reste du produit, US 6.4), 409 si l'analyse n'est pas encore terminée (`status != completed`), 404 si aucun pivot n'a été détecté (« Aucun pivot de défaite détecté pour cette partie. »), 422 en dernier recours si le PGN stocké est invalide.
- **Frontend — mode Sandbox** (`board_manager.js:startSandbox`) : nouveau 4ᵉ mode de `BoardManager` (aux côtés de review/exercise/ghost), qui laisse le joueur rejouer librement contre le moteur Stockfish déjà embarqué (`engine_worker_wasm.js`) — après chaque coup joué, le moteur est interrogé (`go depth 15 movetime 500`, déjà en place pour l'analyse) et son `bestmove` est **auto-joué** comme réponse (`_sandboxPlayEngineMove`), contrairement au mode Ghost qui rejoue des coups historiques figés. C'est la première fois que le worker Stockfish du produit joue réellement des coups plutôt que de seulement les évaluer.
- `#btn-salvage` (« 🚑 Sauver la partie ») apparaît dans la barre d'outils Review dès qu'une partie a un pendant serveur connu (`currentGame.serverGameId`, même condition que `#btn-mark-reviewed`, US 7.3) ; un clic échoue proprement (toast) si le backend répond qu'aucun pivot n'existe.

- Vérifié en intégration réelle (backend local + `curl`) : partie soumise avec une gaffe programmée au 3ᵉ demi-coup → `games.pivot_move_index == 2`, `POST /salvage` renvoie la FEN exacte après « 1. e4 e5 » (position avant la gaffe), `side_to_move: "white"`. Vérifié en navigateur (Playwright + Chromium) : `_startSalvage()` appelle bien `ApiClient.salvageGame` puis `boardMgr.startSandbox(fen, "w")` avec la FEN renvoyée par le backend, et `#btn-salvage` bascule visible/masqué selon `currentGame.serverGameId`.
- Tests : `backend/tests/test_game_salvage.py` (11 tests : filtre par couleur, seuil exact, PGN invalide, index hors bornes, position de départ/side-to-move), `backend/tests/test_games_api.py` (6 nouveaux tests d'intégration : 200 avec FEN exacte, 401/404/409/404-sans-pivot), `frontend/tests/api_client.test.js` (2 nouveaux tests `salvageGame`).

### 4.16 EPIC 18 — Système de Personnalisation Visuelle (Theme & Board)

**Fichiers :** `domain/models.py` (`UserSettingsUpdate`, `UserProfile.settings`), `infrastructure/db_client.py` (`update_settings`), `routers/auth.py` (`PATCH /auth/me/settings`), `supabase/migrations/20260702100000_profiles_settings_epic18.sql`, `js/theme_service.js`, `js/board_manager.js` (`refreshTheme`), `js/app.js` (`_openThemeModal`/`_saveThemeSettings`/`_applyServerTheme`), `index.html` (`#theme-modal`, `#btn-open-theme`), `assets/pieces/{cburnett,cyber-tactics}/`, `assets/boards/presets.json`, `scripts/validate_assets.py`, `serve.py`

> **Contexte :** backlog fourni par l'utilisateur (moodboard « Cyber-Tactics » UI Kit + tutoriel CSS glow fourni en exemple). Numérotation EPIC 18 conservée (pas de collision avec les EPIC déjà enregistrés dans ce dépôt).

**US 18.1 — Gestionnaire d'Assets Locaux (Theme Manager) :**
- `js/theme_service.js` résout le chemin d'un jeu de pièces via `getPieceThemePath(themeName)` → `assets/pieces/{theme}/{piece}.svg` (le `{piece}` reste un template résolu par chessboard.js lui-même, comme l'ancien `pieceTheme` codé en dur avant cet EPIC). Un thème inconnu/de mauvais type retombe **toujours** silencieusement sur `cburnett` (`_sanitizeThemeName`), jamais d'exception.
- Deux thèmes livrés : `cburnett` (copie exacte de l'ancien `assets/images/pieces/`, qui reste également en place, inchangé, pour ne rien casser d'existant) et **`cyber-tactics`** (nouveau jeu de 12 SVG angulaires générés — traits épais `#2D3748`, remplissage contrasté clair/slate, accents bleu néon `#3867D6` sur les détails distinctifs de chaque pièce).
- **Effet néon** (US inspirée du tutoriel CSS fourni) : plutôt que de coder la lueur dans le SVG, une classe `body.theme-cyber-tactics` (posée par `ThemeService.applySettings`) cible `.piece-417db` (classe interne de chessboard.js pour les `<img>` de pièces) avec un `filter: drop-shadow(...)` — fonctionne identiquement sur un `<img src="*.svg">` ou un `<svg>` inline, donc applicable sans changer le mode de rendu des pièces de chessboard.js.
- `scripts/validate_assets.py` (US 18.1, astuce PO) : vérifie que les 12 SVG existent pour chaque thème déclaré ; `serve.py` l'exécute et refuse de démarrer (`sys.exit(1)`) si un fichier manque, pour ne jamais découvrir un 404 de pièce après coup. N'affecte pas la suite E2E Playwright, qui démarre le frontend via `python3 -m http.server` directement (pas `serve.py`).

**US 18.2 — Paramétrage du Plateau (Board Settings) :**
- Modale `#theme-modal` (bouton `🎨` toujours visible dans l'en-tête, y compris déconnecté) : sélecteur de jeu de pièces + sélecteur de couleurs de plateau (4 présets `ThemeService` : `classic`/`slate`/`ocean`/`cyber`, dupliqués — volontairement, pour rester synchrones à l'exécution sans dépendre d'un fetch réseau — depuis `assets/boards/presets.json`, la référence documentée).
- Couleurs de plateau appliquées en **variables CSS** (`--board-square-light`/`--board-square-dark`), lues par une règle ajoutée dans `style.css` ciblant les classes chessboard.js `.white-1e1d7`/`.black-3c85d` — chargée après `chessboard-1.0.0.min.css` pour gagner la cascade sans toucher au fichier vendorisé.
- Persistance serveur : `profiles.settings` (JSONB, colonne unique et **permissive** — `UserSettingsUpdate.settings: Dict[str, Any]`, aucun schéma de clés figé) via `PATCH /auth/me/settings` (JWT requis, restreint au profil de l'utilisateur authentifié, sémantique **remplacement** et non fusion — le frontend envoie toujours l'objet `settings` complet qu'il maintient déjà en mémoire). Modularité explicitement visée par le PO : ajouter un futur réglage (son, animation, taille d'échiquier) ne nécessite ni nouvelle migration ni nouveau endpoint, juste une nouvelle clé dans l'objet.

**US 18.3 — Persistance des préférences (anti-flash) :**
- Au tout début du constructeur de `ChessImproverApp` (avant `_initBoard()`, qui lit `ThemeService.getPieceThemePath()` à la construction du premier échiquier), `ThemeService.applySettings(ThemeService.loadLocalCache())` applique l'instantané `localStorage` — le thème correct s'affiche dès le premier échiquier rendu, sans attendre la résolution réseau de `Auth.autoConnect()`.
- Une fois la session serveur résolue (`_onAuthSuccess`, appelé après connexion/inscription **et** après restauration de session silencieuse), `_applyServerTheme(user)` applique les préférences réelles du profil, rafraîchit le cache local, et **reconstruit l'échiquier actuellement affiché** (`BoardManager.refreshTheme()` — chessboard.js 1.0.0 ne permet pas de changer `pieceTheme` après construction, donc `destroy()` + reconstruction à la même position/orientation, sans re-fetch réseau puisque les SVG sont déjà en cache navigateur).
- **Résilience explicitement exigée par le PO** (« une valeur invalide dans le JSONB ne fait pas planter l'échiquier ») : testée à chaque étage — `getPieceThemePath`/`getBoardColors` avec une valeur non-string/inconnue, `applySettings` avec `settings` `null`/`undefined`/de mauvais type, `loadLocalCache` avec du JSON corrompu en `localStorage`, et même `applySettings` appelé alors que `document.documentElement`/`document.body` sont indisponibles — dans tous les cas, repli silencieux sur les valeurs par défaut, aucune exception.

- Vérifié en intégration réelle (backend local + `curl`) : `settings` vide par défaut à l'inscription, `PATCH /auth/me/settings` remplace et persiste (relu par `GET /auth/me`), 422 si `settings` n'est pas un objet JSON.
- Vérifié en navigateur (Playwright + Chromium) : bascule vers `cyber-tactics`/`cyber` → pièces réellement chargées depuis `assets/pieces/cyber-tactics/*.svg` avec la lueur néon visible, variables CSS `--board-square-light`/`--board-square-dark` correctement positionnées, thème toujours actif après un rechargement complet de page (cache local anti-flash confirmé). Capture d'écran à l'appui.
- Tests : `backend/tests/test_auth.py` (classe `TestUpdateSettings`, 8 tests : succès, persistance, remplacement plutôt que fusion, clés arbitraires acceptées, 422 sur valeur non-objet, 401 sans token, isolation entre utilisateurs, défaut `{}` à l'inscription), `frontend/tests/theme_service.test.js` (21 tests : chemins/couleurs par thème incluant repli sur défaut et état courant sans argument, cache local avec JSON corrompu, `applySettings` résilient à toute entrée invalide), `frontend/tests/auth.test.js` (3 nouveaux tests `updateSettings`).

### 4.17 EPIC 19 — Dashboard de Performance Cognitive (Analyse de la Charge Cognitive)

**Fichiers :** `domain/cognitive_load.py`, `domain/cadence.py` (`parse_increment`), `domain/analyzer.py` (`read_mainline_clocks`, rendue publique), `domain/analysis_pipeline.py` (`fen`/`best_move_san`/`time_spent_seconds`), `routers/games.py` (route `/stats/cognitive-load`), `supabase/migrations/20260702120000_game_moves_cognitive_load.sql`, `js/cognitive_dashboard.js`, `js/api_client.js`, `index.html` (carte « CHARGE COGNITIVE »)

> **Contexte :** backlog fourni par l'utilisateur (paste PO), délégué en parallèle d'EPIC 20 avec la directive « moins de temps à jouer, plus de temps à progresser ». Traité en autonomie complète (agent overnight), y compris merge de la PR une fois la CI verte.

**Temps de réflexion par coup (`domain.cognitive_load.derive_time_spent`)** : dérivé des horloges PGN (`[%clk]`) déjà lues par `domain.analyzer` (module désormais public — `read_mainline_clocks` — pour éviter de dupliquer la traversée de l'arbre `chess.pgn`). L'incrément de cadence (`domain.cadence.parse_increment`) est retranché de la chute d'horloge observée : sans cette correction, un coup joué très vite avec un gros incrément peut faire *remonter* l'horloge et biaiser le temps de réflexion vers une valeur trop basse, voire négative — le résultat est toujours plancherisé à 0. Le premier coup de chaque camp n'a pas de référence antérieure (`None`), comme tout le reste du produit lorsqu'une donnée est indisponible plutôt que présumée.

**US 19.1 — Répartition par phase/pression (`build_time_allocation_report`)** : réutilise la segmentation de phase existante (`domain.phases`, US 2.1). Chaque coup du joueur est classé par phase (Ouverture/Milieu/Finale) et par niveau de pression (`classify_pressure`, seuil -150cp — même intensité que `stats_aggregator.ADVANTAGE_CP` pour l'entrée en finale). Le rapport inclut `share_pct` (part du temps total sur cette phase) — c'est ce champ qui permet de révéler qu'un joueur passe 80 % de son temps sur des ouvertures non maîtrisées (valeur métier explicite du backlog).

**US 19.2 — Fluidité de décision (`build_decision_fluidity_report`)** : classe chaque coup joué en `top3` (perte ≤ 50cp) ou `weak` (perte ≥ 100cp), avec une zone intermédiaire volontairement non classée (même principe de bandes disjointes que `domain.move_class`). `is_decision_fatigue` signale un temps moyen sur les coups perdants ≥ 1.3× celui des coups Top 3 — le cas cité par le backlog (« 3 minutes sur un coup perdant ») est directement couvert. **Décision d'architecture documentée dans le code** : le backlog évoquait « le temps moyen de Stockfish » comme référence, or Stockfish n'a pas de temps de réflexion réel dans ce produit (évaluation par profondeur fixe, pas par horloge) — l'indicateur compare donc le joueur à lui-même (coups Top 3 vs perdants), ce qui sert la même valeur métier sans inventer une donnée moteur inexistante.

**Route** (JWT requis) :

| Route | Méthode | Réponse |
|---|---|---|
| `/api/v1/stats/cognitive-load` | GET | `{time_allocation: {by_phase, by_pressure, sample_size}, decision_fluidity: {top3, weak, decision_fatigue}}`. Agrège **toutes** les parties analysées de l'utilisateur, filtrées par couleur *par partie* (comme `/stats/summary` — un joueur peut avoir joué Blancs sur une partie et Noirs sur une autre). Dégrade en rapport vide (200) plutôt qu'un 500 si la base est indisponible. |

**Persistance** : 3 colonnes ajoutées à `game_moves` (`fen`, `best_move_san`, `time_spent_seconds`) — calculées par `analysis_pipeline.analyze_pgn` (nouveau paramètre `time_control`, avec repli sur l'en-tête PGN `TimeControl`) uniquement quand un moteur d'évaluation est disponible pour `fen`/`best_move_san` (sans moteur, `time_spent_seconds` reste calculable dès lors que le PGN contient des horloges).

**Frontend :** `js/cognitive_dashboard.js` — module autonome (même famille que `stats_dashboard.js`/`advanced_stats.js`) : `buildPhaseChartData` (graphe barre Chart.js), `buildInsightMessages` (messages en langage naturel, logique pure testée séparément du rendu DOM). Carte « CHARGE COGNITIVE » dans le dashboard Statistiques Avancées, rendue à chaque ouverture (`_loadAdvStats`), indépendamment du résumé `AdvancedStats` (route distincte).

- Vérifié en navigateur (Playwright + Chromium) : `frontend/tests/e2e/cognitive_flashcards.spec.js` — partie avec gaffe + horloges analysée via l'API réelle → insight visible dans la carte Charge Cognitive.
- Tests : `backend/tests/test_cadence.py` (`parse_increment`, 7 tests), `backend/tests/test_cognitive_load.py` (35 tests), `backend/tests/test_analysis_pipeline.py` (fen/best_move_san/time_spent_seconds), `backend/tests/test_games_api.py::TestStatsCognitiveLoad` (6 tests d'intégration), `frontend/tests/cognitive_dashboard.test.js` (19 tests, 87 % lignes/branches — ajouté à `collectCoverageFrom`).

### 4.18 EPIC 20 — Bibliothèque de Mémoire Tactique (Flashcards SRS auto-générées)

**Fichiers :** `domain/srs_flashcards.py`, `domain/opening_repertoire.py` (`infer_quality`, réutilisée), `domain/tactics.py` (`is_correct_move`, réutilisée), `routers/srs_flashcards.py`, `routers/games.py` (câblage worker), `infrastructure/db_client.py` + `pg_repository.py`, `supabase/migrations/20260702130000_srs_flashcards_epic20.sql`, `js/api_client.js`, `js/app.js` (`#flashcards-col`), `index.html`

> **Contexte :** backlog fourni par l'utilisateur (paste PO), délégué en parallèle d'EPIC 19. Objectif : utiliser la répétition espacée (SRS) sur les erreurs passées du joueur — « construire son propre dictionnaire de patterns » — plutôt que sur des problèmes curés aléatoires (EPIC 8).

**US 20.1 — Extraction automatique (`domain.srs_flashcards.extract_blunder_flashcards`)** : fonction pure qui parcourt les `game_moves` du joueur (déjà enrichis de `fen`/`best_move_san`/`cpl` par EPIC 19) et retient chaque gaffe (perte ≥ 200cp, même seuil que `stats_aggregator.BLUNDER_CPL`) sous la forme `{fen, solution}`. Câblée dans `routers/games.run_analysis` : un bloc `try/except` supplémentaire (même garde-fou que les blocs snapshot/profil d'erreur voisins) crée les flashcards après chaque analyse réussie, sans jamais faire échouer l'analyse déjà persistée.

**Calendrier SM-2 — aucune duplication d'algorithme** : `srs_flashcards.DEFAULT_EASE_FACTOR`/`DEFAULT_INTERVAL_DAYS` (2.5/1) sont la même convention de démarrage que `domain.opening_repertoire`/`domain.srs_engine.create_card` — c'est la **3ᵉ réutilisation** de l'algorithme SM-2 dans le produit (après le SRS tactique JS du mode Exercice et le répertoire d'ouvertures EPIC 9), toujours via `domain.srs_engine.sm2_schedule`.

**US 20.2 — Rappel actif (`routers/srs_flashcards.review_flashcard`)** : le coup tenté est validé par `domain.tactics.is_correct_move` (comparaison de coups `chess.Move`, tolère les variantes de notation, réutilisée telle quelle depuis EPIC 8). La qualité SM-2 est déduite du résultat via `domain.opening_repertoire.infer_quality` — un échec de rappel (tentative unique, contrairement à la révision multi-coups du répertoire d'ouvertures) est mappé sur « 2 erreurs » pour garantir un reset systématique du calendrier plutôt qu'un crédit partiel.

**Routes** (JWT requis) :

| Route | Méthode | Comportement |
|---|---|---|
| `/api/v1/flashcards` | GET | Le Cimetière des Erreurs complet de l'utilisateur — jamais `solution` avant tentative. |
| `/api/v1/flashcards/due` | GET | Flashcards dont l'échéance (`due_date`) est atteinte — alimente la file de Rappel Actif. |
| `/api/v1/flashcards/{id}/review` | POST | Corps `{move}` (SAN). Valide 100 % serveur, recalcule le calendrier SM-2, révèle `solution`. 404 si la carte est inconnue ou n'appartient pas à l'utilisateur authentifié. |

**Persistance** : table `srs_flashcards` — mêmes colonnes de calendrier que `opening_repertoire` (`ease_factor`/`interval_days`/`repetitions`/`due_date`), `game_id` en `ON DELETE SET NULL` (la flashcard survit à la suppression de la partie source), RLS par utilisateur. `db_client`/`PgRepository` implémentent la délégation complète (create/get/get_due/update), sans reproduire le gap `tactical_problems` de US 8.1 (§10.6).

**Frontend :** carte « CIMETIÈRE DES ERREURS » sur le dashboard principal (lancement, `#card-flashcards`) et sur le dashboard Statistiques Avancées (`#flashcards-summary`, compteurs total/à réviser en direct, chargés par `_loadFlashcardsSummary`). Vue plein écran `#flashcards-col` (réutilise le style générique `.tactics-col`) : échiquier indépendant identique en tout point au Coach Tactique (`_initFlashcardBoard`/`_onFlashcardDrop`, US 8.3), feedback vert/rouge, révélation de la solution en cas d'échec, enchaînement automatique sur la carte suivante de la file du jour.

**Note d'architecture (cadence « 3/7/15 jours » du backlog)** : le PO illustrait la répétition espacée par des paliers fixes. Le produit dispose déjà d'un algorithme SM-2 continu, documenté comme source de vérité unique pour toute fonctionnalité de répétition espacée (docstring `domain.srs_engine.sm2_schedule`) ; un second algorithme à paliers fixes dupliquerait cette logique pour un gain marginal. Le calendrier SM-2 produit une cadence croissante (1 jour → 6 jours → ef×intervalle) qui sert la même valeur métier ; les « 3/7/15 jours » sont traités comme une illustration de la cadence attendue, pas une spécification algorithmique stricte.

- Vérifié en navigateur (Playwright + Chromium) : `frontend/tests/e2e/cognitive_flashcards.spec.js` — gaffe analysée → flashcard visible dans le Cimetière → rappel correct (halo vert) et incorrect (halo rouge, solution révélée) via le vrai backend local. 18/18 tests E2E verts.
- Tests : `backend/tests/test_srs_flashcards.py` (9 tests), `backend/tests/test_db_srs_flashcards.py` (12 tests), `backend/tests/test_srs_flashcards_api.py` (10 tests d'intégration), `backend/tests/test_pg_repository.py` (contrat de signature), `frontend/tests/api_client.test.js` (4 nouveaux tests).

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

### 5.17 Alerte Coach Vocal (EPIC 14)

```
classification = classify_move(move_accuracy(cpl))      # seuils US 5.1, inchangés
alerte déclenchée ⟺ classification ∈ {mistake, blunder}  # good/excellent/brilliant/book = silence
pièce nommée     = pièce la + précieuse du joueur en prise ET non défendue
                   sur la position APRÈS le coup (analyzer.is_piece_hanging)
message          = contextuel (pièce + case) si trouvée, générique par gravité sinon
```

### 5.18 Pivot de défaite (EPIC 15)

```
pivot = premier index i (0-based, ligne principale) tel que :
          moves[i].color == user_color  ET  moves[i].cpl >= BLUNDER_CPL (200, §5.16-adjacent stats_aggregator)
None si aucun coup du joueur n'atteint ce seuil (ou partie non évaluée par un moteur)

position de sauvetage = position AVANT que moves[pivot] ne soit joué
                         (rejoue le PGN jusqu'à l'index pivot exclu)
```

### 5.19 Résolution de thème (EPIC 18)

```
getPieceThemePath(theme?) :
  theme_demandé = theme si fourni, sinon dernier thème appliqué (état interne), sinon "cburnett"
  theme_final   = theme_demandé si ∈ {"cburnett","cyber-tactics"}, sinon "cburnett"
  → "assets/pieces/{theme_final}/{piece}.svg"   ({piece} résolu par chessboard.js)

getBoardColors(theme?) : même logique de repli, thèmes valides {classic,slate,ocean,cyber},
                          défaut "classic" → {light, dark} (jamais de valeur invalide renvoyée)

applySettings(settings) : ne lève JAMAIS d'exception, quelle que soit la forme de `settings`
  (null/undefined/non-objet/valeurs de thème de mauvais type) — repli sur les valeurs par
  défaut à chaque étage plutôt que de propager une erreur jusqu'à l'échiquier.
```

### 5.20 Charge Cognitive — temps de réflexion, pression, fluidité (EPIC 19)

```
temps_de_réflexion(coup) = horloge_avant_même_camp − horloge_après + incrément_cadence
                            → plancher 0 ; None si pas d'horloge de référence antérieure
                            → incrément retranché : sinon un coup rapide + gros incrément
                              ferait remonter l'horloge et biaiserait le calcul à la baisse

pression   : UNDER_PRESSURE si éval_avant (POV joueur) ≤ −150 cp, sinon EQUALITY
partage_temps_phase (%) = temps_total(phase) / temps_total(toutes phases) × 100

qualité_coup : TOP3 si cpl ≤ 50 cp ; WEAK si cpl ≥ 100 cp ; sinon non classé (zone neutre)
fatigue_décisionnelle ⟺ temps_moyen(WEAK) > temps_moyen(TOP3) × 1.3
```

### 5.21 Extraction de flashcards depuis les gaffes (EPIC 20, US 20.1)

```
gaffe exploitable ⟺ cpl ≥ 200  ET  fen connu  ET  best_move_san connu  ET  best_move_san ≠ move_san
flashcard générée = {fen, solution: best_move_san}
calendrier initial = ease_factor 2.5, interval_days 1, repetitions 0, due_date = aujourd'hui
                      → identique à domain.opening_repertoire / domain.srs_engine.create_card

révision (US 20.2) : succès ⟹ quality = infer_quality(0)  = 5 (SM-2 avance)
                      échec  ⟹ quality = infer_quality(2)  = 1 (SM-2 réinitialise, jamais de crédit partiel)
```

### 5.22 Fallback de sélection de problèmes — anti-404 (EPIC 22, US 22.2)

Un exercice doit TOUJOURS être servi : l'encadré « Impossible de charger un problème » ne doit plus jamais être causé par le backend.

- Si le dépôt Postgres échoue (méthode non migrée → `AttributeError`, table vide → `None`, erreur SQL), `db_client` retombe silencieusement sur le **set de problèmes par défaut in-memory** (seed tactique 14 problèmes / seed finales 9 positions).
- Si un filtre de catégorie vide le pool de sélection, le pool est **élargi à toutes les catégories** au lieu de renvoyer `None` (qui devenait un 404 côté route et figeait l'interface).
- La sélection par proximité d'Elo (`select_nearest_problem`) est déjà sans plage stricte : le problème le plus proche est servi quel que soit l'écart — l'« élargissement ±200 » du backlog est donc couvert par construction.
- Les `theme_id`/`focus` inconnus restent rejetés en 422 (erreur d'appel, pas un état vide).

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
| `cognitive_dashboard.test.js` (EPIC 19) | CognitiveDashboard | formatSeconds, buildPhaseChartData, buildInsightMessages (phase dominante, pression, fatigue décisionnelle), fetchReport (fallbacks), renderHTML, render |
| `api_client.test.js` | ApiClient | baseUrl/isConfigured (window/localStorage), url (query), analyzeGame (POST + erreur), getStatsSummary, getGame, getStatsHistory, **en-tête `Authorization: Bearer` présent/absent selon `Auth.getToken()` (US 6.4)**, **getGames (US 7.1)**, **updateGameStatus (US 7.3)**, **getNextTacticalProblem + régression bug `?` orphelin (US 8.2)**, **submitTacticalAttempt + time_taken, getTacticsStats (US 8.3/8.4)**, **createOpeningLine/getOpeningLines/getDueOpeningLines/reviewOpeningLine/deleteOpeningLine (EPIC 9)**, **getNextEndgameProblem/submitEndgameAttempt (EPIC 10)**, **salvageGame (EPIC 15)**, **getCognitiveLoad (EPIC 19)**, **getFlashcards/getDueFlashcards/reviewFlashcard (EPIC 20)** |
| `auth.test.js` (US 6.1/6.3) | Auth | signup/login (succès, `detail` chaîne, `detail` liste Pydantic 422 — un ou plusieurs champs, absence de `detail`), `updateChessUsername` (sans token, succès + PATCH + persistance session, format invalide), **`updateSettings` (EPIC 18 : sans token, succès + persistance session, settings absent → objet vide)**, isLoggedIn/logout, **résolution de la base API (audit 07/2026 : fallback dev, `window.API_BASE` prod, priorité `CI_API_URL`, relecture paresseuse à chaque appel)** |
| `coaching_voice.test.js` (EPIC 14) | CoachingVoice | `isSupported`, `setEnabled`/`isEnabled`/`loadPreference` (persistance localStorage), `alertFor` (blunder/mistake/aucune alerte, coup absent), `bestMoveNarration`, `beep` (no-op sans AudioContext, fréquence par gravité), `speak` (no-op désactivé/non supporté, appel réel `speechSynthesis`) |
| `analysis_feedback.test.js` (EPIC 22) | AnalysisFeedback | `createState` (états indépendants), `shouldDispatch` (1er dispatch, 20 ré-émissions identiques bloquées, raffinement cpLoss autorisé, arrondi infra-centipion, bascule book→moteur, coups indépendants, entrées invalides), `shouldAlert` (une seule alerte par coup blunder/mistake, classifications non alertables, reset par nouvelle partie) — **15 TUs, 100 % lignes/branches/fonctions** |
| `theme_service.test.js` (EPIC 18) | ThemeService | `getPieceThemePath`/`getBoardColors` (thème valide/invalide/absent/état courant sans argument), `listPieceThemes`/`listBoardThemes`, `saveLocalCache`/`loadLocalCache` (JSON corrompu, valeur non-objet), `applySettings` (variables CSS, classe `<body>`, résilience totale : `null`/`undefined`/valeurs de mauvais type/`document` indisponible) |

> `advanced_stats.js` n'est pas dans `collectCoverageFrom` (comme `app.js`, `auth.js`, `board_manager.js`) : seules ses fonctions pures sont testées, les `render*` sont de la glue DOM. `cognitive_dashboard.js` y a été ajouté (EPIC 19, 87 % lignes/branches). `analysis_feedback.js` y a été ajouté (EPIC 22, 100 %).

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
| `test_auth.py` | TestPasswordHashing (5), TestJWT (6 — dont **rejet `alg: none` et header `alg` falsifié**, audit 07/2026), TestSignup (4+3 US 6.1+2 US 6.2), TestLogin (4), TestMe (3+1 US 6.2), TestUpdateMe (7, US 6.3), TestUpdateSettings (8, EPIC 18), TestSync (4) | **47 TUs** |
| `test_tactics_fallback.py` (EPIC 22, US 22.2) | TestDbClientFallback (6 — dépôt Postgres cassé/vide → seed in-memory, élargissement de pool tactique/finales), TestApiNeverFreezesUi (5 — `/tactics/next`, `/tactics/custom`, `/tactics/attempt`, `/endgames/next` répondent 200 même avec un dépôt Postgres défaillant) | **11 TUs** |
| `test_main_api.py` (audit 07/2026) | TestHealth, TestGetGamesValidation (pseudo Chess.com : regex, injections de chemin rejetées **sans appel réseau**, bornes `limit`), TestGetGamesErrorMapping (404 joueur inconnu, 502 génériques **sans fuite du message interne**, 503 client absent), **TestJwtSecretFailFast (démarrage refusé avec le secret par défaut hors debug, autorisé en debug ou avec secret custom)**, TestChessComClientSafeEncoding (encodage URL du pseudo) | **18 TUs** |
| `test_analyzer.py` | — | Analyse géométrique |
| `test_elo.py` | — | Formules Elo/précision backend |
| `test_phases.py` | Constantes, Material, IsEndgame, OpeningEndPly, SegmentPhases, SegmentPgn | US 2.1 |
| `test_acpl.py` | CentipawnLoss, AverageCpl, AcplByPhase, OverallAcpl | US 2.2 |
| `test_engine.py` | PositionEval, ClientProvidedEngine, NativeStockfishEngine | Abstraction moteur |
| `test_virtual_elo.py` | Anchors, Interpolation, CadenceBonus, AcplToElo | US 3.1 |
| `test_move_class.py` | ClassifyPosition, TacticOutcome, SuccessRatio, TacticalElo, StrategicElo | US 3.2 |
| `test_cadence.py` | EstimateSeconds, ClassifyCadence (bornes Bullet/Blitz/Rapide/Daily), **ParseIncrement (EPIC 19)** | EPIC 1 |
| `test_db_games.py` | create/get/update/completed games, bulk/clear moves, snapshot/history progression, **pgn_hash (stockage, recherche, isolation par utilisateur)**, **liste blanche `update_game` (rejet de tout champ hors whitelist, audit 07/2026)** | EPIC 1 + US 5.1 + US 7.2 |
| `test_analysis_pipeline.py` | sans moteur (phases/SAN), avec moteur (CPL, plafond, tactique/stratégie), mat, **`compute_pgn_hash` (déterminisme, format SHA-256)**, **`fen`/`best_move_san`/`time_spent_seconds` (EPIC 19/20, incrément de cadence)** | US 1.2 + US 7.2 + EPIC 19/20 |
| `test_stats_aggregator.py` | user_outcome, build_summary (catégories, ratings, couleur), gaffeRate, finales, acplTrend | US 4.1 |
| `test_progress_history.py` | build_snapshot (cadence inconnue, filtre couleur, IDs), filter_history_by_days (bornes, dates invalides/naïves) | US 5.1 |
| `test_games_api.py` | POST analyze (202, 400), worker→completed, réanalyse, GET game (404), stats/summary, snapshot auto, GET stats/history, **401 sans JWT sur les 6 routes, isolation entre 2 utilisateurs (get_game/réanalyse/stats/GET games/PATCH status)**, **GET /games (liste, vide, isolation)**, **dédup PGN par hash (même game_id, pas de doublon, statut réel, isolation par utilisateur, PGN différent → parties distinctes)**, **PATCH /games/{id}/status (marque/démarque, persistance, 404 non-propriétaire, 422 body invalide)**, **`GET /stats/cognitive-load` (EPIC 19 : vide, après analyse avec horloges, isolation, dégradation 200 sur erreur DB)** | US 1.1 + US 5.1 + US 6.4 + US 7.1 + US 7.2 + US 7.3 + EPIC 19 |
| `test_pg_repository.py` | PgRepository (dsn, colonnes, contrat progress_history, `_iso` générique, **contrat `create_game`/`find_game_by_pgn_hash`**, **contrat `record_tactical_attempt`/`get_tactical_attempts` (US 8.4)**, **contrat CRUD `opening_repertoire` + mapping `line_name`↔`name` (EPIC 9)**, **contrat CRUD `srs_flashcards` (EPIC 20)**), délégation db_client (in-memory sans `DATABASE_URL`) | EPIC 1 + US 5.1 + US 7.2 + US 8.4 + EPIC 9 + EPIC 20 |
| `test_tactical_elo.py` | `update_elo` (+15/-15, constantes, plancher, pas de plafond) | US 8.1 |
| `test_tactics.py` | `is_correct_move` (match exact, notation équivalente, coup faux/illégal/invalide), `select_nearest_problem` (vide, exact, plus proche haut/bas, tirage aléatoire équidistant), **`compute_daily_streak` (vide, série du jour, arrêt au premier échec, hier ne compte pas), `compute_stats_by_theme` (regroupement + taux par catégorie)** | US 8.1 + US 8.4 |
| `test_db_tactics.py` | Store tactique (Elo par défaut, persistance), **intégrité des 15 problèmes du seed vérifiée par python-chess** (mat effectif, capture non défendue), sélection/filtre par catégorie, **`TestTacticalAttempts` (enregistrement, isolation entre utilisateurs, reset)** | US 8.1 + US 8.4 |
| `test_tactics_api.py` | `GET /tactics/next` (sans solution, 401, **filtre theme_id ×3 + 422 si inconnu**), `POST /tactics/attempt` (succès/échec ±15, notation équivalente, persistance, 404, 401, isolation entre utilisateurs, **`streak` croissant/remis à zéro, `time_taken` optionnel**), **`GET /tactics/stats` (vide, agrégation par catégorie, 401)** | US 8.1 + US 8.2 + US 8.4 |
| `test_srs.py` | `create_card`/`review_card`/`get_due_cards` (SM-2, toutes branches qualité/EF/intervalle), **`sm2_schedule` (équivalence exacte avec `review_card`, EPIC 9)** | EPIC 9 |
| `test_opening_repertoire.py` | `validate_move_sequence` (ligne valide, vide, coup illégal, entrée invalide), `infer_quality` (0/1/2+ erreurs) | EPIC 9 |
| `test_db_opening_repertoire.py` | Store répertoire : création (calendrier SM-2 initial), liste/isolation par utilisateur, lignes dues (bornes de date), mise à jour de calendrier, suppression (propriétaire/non-propriétaire), reset | EPIC 9 |
| `test_openings_trainer_api.py` | `POST /openings/repertoire` (création, 422 séquence/couleur invalide, 401), `GET` (liste, isolation), `GET /due`, `POST /{id}/review` (planification J+1, échec réinitialise, 404 ligne inconnue/non-propriétaire, 401), `DELETE /{id}` (propriétaire/non-propriétaire, 404, 401) | EPIC 9 |
| `test_db_endgames.py` | Store finales (Elo par défaut, distinct de `tactical_elo`), **intégrité des 9 positions du seed vérifiée par python-chess** (mat en 1 effectif), sélection/filtre par catégorie | EPIC 10 |
| `test_endgames_api.py` | `GET /endgames/next` (sans solution, 401, filtre theme_id ×3 + 422 si inconnu), `POST /endgames/attempt` (succès/échec ±15, persistance, 404, 401, isolation entre utilisateurs, Elo distinct de l'Elo tactique) | EPIC 10 |
| `test_error_profile.py` | `detect_error_occurrences` (hanging_piece/time_pressure mutuellement exclusifs, missed_mate depuis `game_moves`, isolation par couleur), `update_frequency_score` (EMA, bornes 0-100, franchissement du seuil récurrent), `is_recurring` | EPIC 11 |
| `test_db_error_profile.py` | Store profils d'erreur : création/mise à jour (upsert), isolation par utilisateur/type, `get_next_tactical_problem_for_categories` (pool multi-thèmes) | EPIC 11 |
| `test_error_profile_api.py` | Câblage `run_analysis` → profil mis à jour après analyse (blunder, mat manqué via evals), franchissement du seuil récurrent sur 4 parties, isolation entre utilisateurs, `GET /tactics/custom` (200/422 focus inconnu/401, solution jamais renvoyée) | EPIC 11 |
| `test_tactical_sprint.py` | `elapsed_seconds`/`is_sprint_active` (fenêtre exacte, bornes), `compute_score` (pur, déterministe), `record_ghost_move` (immutabilité) | EPIC 12 |
| `test_db_tactical_sprint.py` | Store sprints : création (defaults), mise à jour, **`get_best_sprint` public** (visible entre utilisateurs, ignore les sprints non terminés), **liste blanche `update_sprint` (audit 07/2026)** | EPIC 12 |
| `test_tactical_sprint_api.py` | Cycle complet `POST /start` → `POST /{id}/attempt` (succès/échec, score, problème suivant) → `POST /{id}/finish` (idempotent), **expiration côté serveur** (horloge manipulée directement dans le store, sprint clôturé automatiquement), isolation propriétaire (404), `GET /sprints/ghost` (200/401, meilleur score toutes utilisateurs confondus) | EPIC 12 |
| `test_coaching_voice.py` | `build_move_alert` (silence sans CPL/bon coup, message générique blunder/mistake, pièce en prise nommée par nom+case, pièce adverse ignorée), `attach_move_alert` (ajoute/n'ajoute pas les clés selon le cas) | EPIC 14 |
| `test_game_salvage.py` | `find_defeat_pivot` (pas de pivot sans données moteur/sous le seuil, premier coup du joueur au-dessus du seuil, gaffes adverses ignorées, seuil exact, couleur noire), `reconstruct_position_before_move` (PGN invalide, index hors bornes, position/side-to-move/move_number à chaque index) | EPIC 15 |
| `test_cognitive_load.py` | `derive_time_spent` (incrément, horloge manquante/négative, plancher 0), `classify_pressure`, `build_time_allocation_report` (phase dominante, bucket pression), `move_quality_bucket`, `is_decision_fatigue`, `build_decision_fluidity_report` | EPIC 19 |
| `test_srs_flashcards.py` | `extract_blunder_flashcards` (seuil de gaffe, fen/best_move manquants, solution = coup joué, plusieurs gaffes) | EPIC 20 |
| `test_db_srs_flashcards.py` | Store flashcards : création (calendrier SM-2 initial), liste/isolation par utilisateur, cartes dues (bornes de date), mise à jour de calendrier, reset | EPIC 20 |
| `test_srs_flashcards_api.py` | Génération auto depuis une gaffe analysée (evals moteur), aucune flashcard sur partie propre, isolation entre utilisateurs, `POST /{id}/review` (rappel correct avance le calendrier, rappel incorrect réinitialise + révèle la solution), 404 carte inconnue/non-propriétaire, 401 sans JWT | EPIC 20 |

**Couverture backend :** 794 TUs au total, couverture globale **89 %+** ; cœur Stats Avancées + EPIC 1/5.1/US 4.2/EPIC 19 à 92–100 % (`stats_aggregator`, `cadence`, `progress_history`, `models`, `engine`, `cognitive_load`, `srs_flashcards` à 100 %, `analysis_pipeline` 92 %, `routers/games` 92 %, `db_client` 98 %). Les requêtes SQL réelles de `pg_repository` (nécessitant une base) sont marquées `pragma: no cover`.

**Architecture de test `test_auth.py` :**
- App de test minimale (`FastAPI()` + routers auth/sync uniquement) pour éviter la dépendance `python-chess`
- `@pytest.fixture(autouse=True)` avec `_reset_store()` pour isolation entre tests
- Mock non nécessaire pour la DB (in-memory résetable)

**Mutation testing :**
- Frontend : Stryker JS (`npm run test:mutation`)
- Backend : mutmut (`mutmut run --paths-to-mutate app/domain/auth.py`)

### 6.3 E2E — Playwright (frontend/tests/e2e/)

**Lancer :**
```bash
cd frontend
npx playwright install --with-deps chromium   # une fois, si absent
npm run test:e2e
```

`playwright.config.js` démarre automatiquement le backend (`uvicorn`, port 8006) et le frontend statique (`http.server`, port 8080) — aucune préparation manuelle nécessaire. Chaque test crée son propre compte (`signupFreshUser`) et s'exécute contre le **vrai backend** (store in-memory, réinitialisé au redémarrage du serveur) : ce sont de vrais tests bout-en-bout sur l'API et le câblage `app.js`/`api_client.js`, pas des mocks.

**Stub CDN (`fixtures/stub_chess.js`)** : actif par défaut, partout (local et CI). Les tests pilotent les handlers de coup directement (`window.app._onTacticsDrop(...)`, etc.) avec des cases fixes plutôt que de simuler un vrai glisser-déposer sur `chessboard.js` — objectif : tester le code applicatif et les échanges réseau réels, pas le rendu pixel d'une librairie tierce. `E2E_STUB_CDN=0` reste possible pour un test manuel avec les vraies librairies (nécessite alors d'adapter les scénarios avec des coups réellement légaux).

| Fichier | Couvre |
|---|---|
| `tactics.spec.js` | Coach Tactique (EPIC 8) : résolution correcte (Elo +15, série 🔥1), coup incorrect (Elo −15, solution révélée), enchaînement auto vers le problème suivant |
| `openings.spec.js` | Entraîneur d'Ouvertures (EPIC 9) : ajout + révision complète d'une ligne (calendrier SM-2 avancé à J+1), rejet d'une séquence illégale (422) |
| `endgames.spec.js` | Entraîneur de Finales (EPIC 10) : mat trouvé (Elo +15), coup incorrect (Elo −15), filtre par catégorie |
| `error_profile.spec.js` | Analyse Comportementale (EPIC 11) : 4 gaffes répétées déclenchent le bandeau Entraînement Personnalisé, clic → problème `hanging_piece` chargé, bandeau masqué sans erreur récurrente |
| `sprint.spec.js` | Mode Tactical Sprint (EPIC 12) : coup résolu incrémente le compteur, clôture du sprint affiche le score final, bandeau Ghost affiche le meilleur score une fois activé |
| `cognitive_flashcards.spec.js` | Charge Cognitive (EPIC 19) + Cimetière des Erreurs (EPIC 20) : gaffe analysée (evals + horloges) → insight visible dans le Dashboard Cognitif et flashcard auto-générée, rappel correct (halo vert) et incorrect (halo rouge, solution révélée), Cimetière vide sans gaffe |

> **Origine :** ces 6 specs sont la version persistée des scripts de vérification Playwright ad hoc écrits (puis jetés) pendant le développement d'US 8.3/8.4, EPIC 9, EPIC 10, EPIC 11, EPIC 12, EPIC 19 et EPIC 20. Les garder comme suite rejouable évite de réécrire ce câblage à chaque nouvelle fonctionnalité et donne une vraie couverture de régression bout-en-bout, en plus des TUs Jest/pytest. **18/18 tests E2E verts.**

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

### 7.3 Pipeline E2E → Playwright

**Fichier :** `.github/workflows/e2e-tests.yml`  
**Déclencheur :** push ou PR sur `main` affectant `backend/**` **ou** `frontend/**` (les tests E2E exercent les deux)

```
Job 1 : test-e2e (ubuntu-latest, Python 3.11 + Node 20)
  → pip install -r backend/requirements.txt
  → npm ci (frontend)
  → npx playwright install --with-deps chromium
  → npm run test:e2e   (démarre backend + frontend, cf. §6.3)
  → upload artifact "playwright-report" (si échec)
```

**Secrets requis :** aucun (`JWT_SECRET` retombe sur `ci-test-secret`, comme §7.2)

### 7.4 Pipeline Database → Supabase

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

### 7.5 Migration SQL initiale

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
| **Dashboard de catégories tactiques** (US 8.2) | `index.html:#tactics-col` + `app.js:_showTactics/_loadTacticalProblem` + `api_client.js:getNextTacticalProblem` | Carte TACTIQUE → vue plein écran, menu 4 catégories, badge Elo |
| **Échiquier tactique jouable** (US 8.3) | `app.js:_initTacticsBoard/_onTacticsDrop/_submitTacticsAttempt` + `api_client.js:submitTacticalAttempt` + `index.html`/`style.css` (`.tactics-board`) | Échiquier indépendant (`Chess`/`Chessboard` directs, pas de `BoardManager`), validation de la solution 100 % serveur, feedback vert/rouge, enchaînement auto vers le problème suivant |
| **Persistance + série du jour** (US 8.4) | `tactical_attempts` (migration) + `db_client.record_tactical_attempt`/`get_tactical_attempts` + `domain/tactics.compute_daily_streak`/`compute_stats_by_theme` + `GET /tactics/stats` + `app.js:#tactics-streak-badge` | Chaque tentative est persistée ; badge 🔥 Série (problèmes résolus d'affilée aujourd'hui) mis à jour en direct ; taux de réussite par catégorie calculable via `/tactics/stats` |
| **Entraîneur d'Ouvertures** (EPIC 9, bonus) | `routers/openings_trainer.py` + `domain/opening_repertoire.py` + `domain/srs_engine.sm2_schedule` + `index.html:#openings-trainer-col` + `app.js:_startOpeningReview/_onOtDrop/_finishOpeningReview` | Carte OUVERTURES → vue plein écran : ajout de ligne (validée serveur), révision SRS avec échiquier auto-enchaîné, qualité SM-2 déduite automatiquement (0 notation manuelle), CRUD complet opérationnel et testé |
| **Entraîneur de Finales Essentielles** (EPIC 10, bonus) | `routers/endgames.py` (réutilise `domain/tactics.py` + `domain/tactical_elo.py`) + `index.html:#endgame-trainer-col` + `app.js:_initEndgameBoard/_onEndgameDrop/_submitEndgameAttempt` | Carte TECHNIQUE DE MAT → vue plein écran, 3 catégories (Roi+Dame/Roi+Tour/Roi+2 Tours), Elo « finales » distinct, échiquier jouable avec feedback vert/rouge, opérationnel et testé |
| **Indépendance des assets externes** (EPIC 13, US 12.1) | `frontend/assets/{js,css,fonts,images,data}/` + `index.html` + `app.js`/`board_manager.js` (`pieceTheme`) + `engine_worker_wasm.js` | jQuery/chess.js/chessboard.js/Chart.js/polices/pièces/ouvertures ECO servis depuis le dépôt, zéro appel `cdnjs`/`jsdelivr`/`lichess1.org`/`fonts.googleapis.com` au chargement, vérifié (zéro requête externe) |
| **Analyse Comportementale — profil d'erreurs** (EPIC 11, US 9.1/9.2) | `domain/error_profile.py` + `routers/error_profile.py` + `routers/tactics.py:/custom` + `routers/games.py:run_analysis` + `index.html:#tactics-custom-training` + `app.js:_loadErrorProfileHint/_startCustomTraining` | Profil mis à jour après chaque partie analysée (score EMA par type d'erreur), bandeau « Entraînement Personnalisé » affiché si récurrent (score > 70), bouton chargeant un problème du thème associé, opérationnel et testé |
| **Mode Tactical Sprint** (EPIC 12, US 11.1/11.2) | `domain/tactical_sprint.py` + `routers/tactical_sprint.py` + `index.html:#sprint-col` + `app.js:_startSprint/_onSprintDrop/_submitSprintAttempt/_endSprint/_renderGhostOverlay` | Carte SPRINT → vue plein écran, sprint 60s chronométré côté serveur (anti-triche), score/compteur en direct, mode Ghost (fetch unique, surimpression togglable), opérationnel et testé |
| **Coach Vocal — alertes tactiques + TTS** (EPIC 14, US 14.1/14.2) | `domain/coaching_voice.py` + `analysis_pipeline.py` + `js/coaching_voice.js` + `app.js:_onMoveAccuracy` + `index.html:#btn-voice-coach` | Alerte contextuelle (pièce en prise nommée, ou message générique) sur chaque gaffe/erreur du mode Review, signal sonore `AudioContext`, narration du meilleur coup via `speechSynthesis` (opt-in, 100 % local) |
| **Réparation de Partie — Game-Salvage** (EPIC 15, US 15.1/15.2) | `domain/game_salvage.py` + `routers/games.py:run_analysis`/`POST /games/{id}/salvage` + `board_manager.js` (mode `sandbox`) + `app.js:_startSalvage` + `index.html:#btn-salvage` | Pivot de défaite détecté et persisté (`games.pivot_move_index`) après chaque analyse ; bouton « Sauver la partie » recharge la position juste avant la gaffe et lance un mode Sandbox où le joueur affronte librement le moteur Stockfish déjà embarqué |
| **Personnalisation Visuelle — Thème & Plateau** (EPIC 18, US 18.1/18.2/18.3) | `js/theme_service.js` + `PATCH /auth/me/settings` + `profiles.settings` (JSONB) + `board_manager.js:refreshTheme` + `index.html:#theme-modal`/`#btn-open-theme` + `assets/pieces/{cburnett,cyber-tactics}/` + `scripts/validate_assets.py` | Jeu de pièces (Cburnett/Cyber-Tactics avec lueur néon) + couleurs de plateau (4 présets) sélectionnables via modale, persistés serveur + cache local anti-flash, résilients à toute valeur invalide ; script bloquant le lancement de `serve.py` si un SVG de pièce manque |
| **Dashboard de Performance Cognitive** (EPIC 19, US 19.1/19.2) | `domain/cognitive_load.py` + `routers/games.py:/stats/cognitive-load` + `js/cognitive_dashboard.js` + `index.html:#cog-dashboard-container` + `app.js:_loadAdvStats` | Carte CHARGE COGNITIVE de la vue Stats Avancées : temps de réflexion par phase/pression (graphe barre) + fluidité de décision (alerte fatigue décisionnelle), opérationnel et testé (backend + frontend + E2E) |
| **Le Cimetière des Erreurs — Flashcards SRS** (EPIC 20, US 20.1/20.2) | `domain/srs_flashcards.py` + `routers/srs_flashcards.py` + `routers/games.py:run_analysis` + `index.html:#flashcards-col`/`#card-flashcards` + `app.js:_showFlashcards/_onFlashcardDrop/_submitFlashcardAttempt` | Chaque gaffe (perte ≥ 200cp) devient automatiquement une flashcard SM-2 ; vue plein écran Rappel Actif (échiquier indépendant, validation 100 % serveur, qualité déduite automatiquement) ; opérationnel et testé (backend + frontend + E2E) |
| **Stabilisation Critique — feedback, fallback, auth, empty states** (EPIC 22, US 22.1-22.4) | `js/analysis_feedback.js` + `app.js` (`_toast` unique, `_showAnalysisAlert`, `_renderModulePlaceholders`, `_emptyStateHtml`) + `index.html:#analysis-alert` + `style.css` + `db_client.py` (fallback anti-404) + `auth.js` (`_apiBase` alignée sur ApiClient) | Une seule alerte d'analyse à la fois (bandeau panneau latéral, plus de toasts empilés) ; exercices toujours servis même si Postgres est cassé/vide ; placeholders des modules synchronisés avec la session (loader pendant `autoConnect`) ; Empty States avec CTA `[Analyser une partie]`/`[Réessayer]` ; pastilles EXERCICE libellées |


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

### 10.6 🟢 EPIC 8 — Coaching Tactique Adaptatif (US 8.1-8.4, backlog complet)

**Fait :** moteur de sélection adaptative + validation serveur (US 8.1), filtre par catégorie + dashboard de sélection (US 8.2), échiquier jouable avec feedback visuel et anti-triche serveur (US 8.3), persistance des tentatives + taux de réussite par thème + série du jour (US 8.4), avec un seed de 15 problèmes vérifiés. L'intégralité du backlog EPIC 8 enregistré dans `UserStory.md` est ✅ Implémenté.

**Reste (idées non bloquantes) :** (1) remplacer/enrichir le seed par un dataset externe plus large (ex. export CSV Lichess Puzzle Database) — non fait dans cet environnement d'exécution faute d'accès réseau vers les sources habituelles (proxy sortant restreint) ; (2) exposer `GET /tactics/stats` dans l'UI (ex. une carte dédiée dans Stats Avancées) — l'endpoint existe et est testé, mais aucune vue ne l'affiche encore graphiquement ; (3) **gap Postgres pré-existant (US 8.1, non corrigé ici, hors scope de cette US)** : `db_client.get_tactical_problem`/`get_next_tactical_problem` délèguent à `PgRepository` si `DATABASE_URL` est défini, mais `PgRepository` n'implémente pas ces deux méthodes (contrairement à `tactical_attempts`, dont la délégation US 8.4 est complète et testée) — à corriger avant toute mise en production avec base réelle pour les tables `tactical_problems`/`profiles.tactical_elo`.

### 10.7 🟢 EPIC 13 — Indépendance des assets (reste)

**Fait :** intégralité de l'audit + rapatriement (§4.11) — zéro dépendance CDN au chargement de l'application.

**Reste (idées non bloquantes) :** (1) build WASM+NNUE de Stockfish auto-hébergé — le fallback asm.js local suffit fonctionnellement (mêmes profondeur/temps minimum, `depth 15`/`movetime 500`) mais un futur build `.wasm` vendorisé restaurerait le gain de performance perdu par la suppression du CDN WASM ; (2) bucket Supabase Storage « assets » pour servir ces fichiers statiques (pièces/polices/librairies) via CDN Supabase plutôt que depuis le dépôt git/Vercel, envisageable si le volume d'assets grossit significativement — non nécessaire à ce stade (poids total < 1 Mo).

### 10.8 🟢 EPIC 12 — Mode Tactical Sprint (reste)

**Fait :** cycle complet start/attempt/finish avec chrono anti-triche serveur, score, mode Ghost (fetch unique, surimpression togglable).

**Reste (idées non bloquantes) :** (1) bonus de score à la vitesse de résolution (`compute_score` est actuellement un simple `problems_solved_count × 10`, sans tenir compte du temps mis par coup — l'info existe déjà dans `moves[].elapsed_ms`, prête à être exploitée) ; (2) durée de sprint configurable (actuellement fixe, `SPRINT_DURATION_SECONDS = 60`) ; (3) un vrai classement/leaderboard (le mode Ghost n'expose que le meilleur score, pas un top N) — la RLS de lecture publique de `tactical_sprints` le permettrait sans migration supplémentaire.

### 10.9 🟢 EPIC 19/20 — Dashboard Cognitif & Cimetière des Erreurs (reste)

**Fait :** EPIC 19 (US 19.1/19.2) et EPIC 20 (US 20.1/20.2) intégralement implémentés, testés (backend + frontend + E2E) et câblés — voir §4.14/§4.15.

**Reste (idées non bloquantes) :** (1) `mutmut run --paths-to-mutate app/domain/cognitive_load.py app/domain/srs_flashcards.py` n'a pas été exécuté formellement dans cette session (l'outil n'est câblé dans aucun pipeline CI existant, cf. §6.2) — la couverture 100 % lignes/branches des deux modules et les tests de cas limites explicites (incrément d'horloge, plancher à zéro, bandes disjointes de qualité de coup) visent le même objectif de robustesse, mais une exécution mutmut réelle donnerait une garantie formelle supplémentaire ; (2) le seuil `PRESSURE_THRESHOLD_CP`/`DECISION_FATIGUE_RATIO` sont des constantes fixes (mêmes ordres de grandeur que le reste du produit) — les rendre configurables par utilisateur (ex. joueurs très défensifs vs très agressifs) serait une piste d'affinage future ; (3) pas de suppression manuelle d'une flashcard (le Cimetière ne propose que la révision, pas le retrait volontaire d'une carte jugée non pertinente) — `DELETE /api/v1/flashcards/{id}` serait le complément naturel, sur le modèle de `DELETE /api/v1/openings/repertoire/{id}` (EPIC 9).

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

### 11.5 Analyse de la gestion du temps — ✅ Traité par EPIC 19

Cette idée de backlog a été implémentée par le Dashboard de Performance Cognitive (EPIC 19, §4.14) : temps de réflexion par phase/pression et fluidité de décision, dérivés des horloges PGN pour toutes les parties analysées. La détection de zeitnot pure (< 5s) au sein d'*une* partie reste couverte séparément par `domain.analyzer` (mise en évidence visuelle dans la Review) — hors périmètre d'EPIC 19, qui agrège plutôt sur l'ensemble des parties.

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

> **Volet entraînement implémenté (EPIC 9, §4.9)** : l'entraîneur de répertoire (ajout de lignes + révision SM-2) répond au besoin de mémorisation active. Le volet **diagnostic** décrit ci-dessus (performances par cadence/couleur sur les ouvertures *déjà jouées*, recommandation automatique de variantes à ajouter au répertoire depuis les stats existantes `top_openings`/`successRatio`) reste à faire — connecter les deux fonctionnalités serait la suite naturelle.

### 11.10 Entraîneur de finales essentielles

> **✅ Implémenté (EPIC 10, §4.10).** Technique de mat essentielle (Roi+Dame/Roi+Tour/Roi+2 Tours) sur le modèle exact d'EPIC 8, avec sélection adaptative par Elo. **Reste pour aller plus loin** : les finales de *technique* au sens strict (opposition, Lucena, Philidor, R+P vs R) nécessitent une vérification d'exactitude par tablebase/moteur — non faisables avec seulement `python-chess` (pas d'accès réseau à une tablebase dans cet environnement) contrairement aux positions de mat forcé, vérifiables par recherche exhaustive. Un dataset externe pré-vérifié (Lichess/Syzygy) serait nécessaire pour ce volet.

### 11.11 Coach Vocal & Game-Salvage — pistes d'approfondissement

> **✅ Implémentés (EPIC 14/15, §4.14/§4.15).** **Reste pour aller plus loin :**
> - **Difficulté du Sandbox** (EPIC 15) : le moteur répond toujours à profondeur/temps fixes (`depth 15 movetime 500`, identiques à l'analyse) — pas de niveau de difficulté réglable (ex. profondeur réduite pour un adversaire plus faible que le joueur ne l'affrontait en partie réelle).
> - **Narration TTS enrichie** (EPIC 14) : la synthèse vocale actuelle lit un texte fixe par gravité + le meilleur coup (SAN) ; une narration plus « coach » (expliquer *pourquoi* le coup est mauvais — fourchette, clouage, finale perdue — pas seulement *qu'*il l'est) demanderait de réutiliser la détection de motifs tactiques (`analyzer.find_fork_moves`, EPIC 11) en plus de la pièce en prise déjà couverte.
> - **Persistance des sessions de Sandbox** : contrairement à `tactical_attempts` (EPIC 8), les coups joués en mode Sandbox (Game-Salvage) ne sont pour l'instant pas journalisés côté serveur — aucune statistique de progrès n'est encore tirée du taux de réussite à « sauver » une position (idée : table dédiée `salvage_attempts`, distincte de `tactical_attempts` qui référence des `tactical_problems` curés plutôt que des positions de parties réelles).

### 11.12 Personnalisation Visuelle — pistes d'approfondissement

> **✅ Implémenté (EPIC 18, §4.16).** **Reste pour aller plus loin :**
> - **Plus de thèmes** : l'architecture (`PIECE_THEMES`/`BOARD_THEMES` dans `theme_service.js` + `validate_assets.py`) est conçue pour qu'ajouter un thème se limite à déposer un nouveau dossier `assets/pieces/{nom}/` (12 SVG) et une entrée dans ces deux listes — aucun thème additionnel livré ce soir au-delà de `cburnett`/`cyber-tactics`.
> - **Réglages non visuels** : la colonne `profiles.settings` (JSONB libre) est prête à accueillir des préférences sonores (activer/désactiver les sons de coup), d'animation, ou de taille d'échiquier sans nouvelle migration — non implémentés ce soir, hors du périmètre strict « Theme & Board » de l'US.
> - **Effet néon configurable** : la lueur `body.theme-cyber-tactics` est actuellement une propriété du thème de pièces (tout ou rien) plutôt qu'un réglage indépendant — un curseur d'intensité ou une désactivation séparée de la lueur serait une évolution naturelle.

### 11.13 Suites de l'audit sécurité/optimisation (07/2026) — non bloquantes

Corrigé lors de l'audit : cf. §3 (échappement XSS `app.js`, base API `auth.js`), §4.3 (validation du pseudo Chess.com + non-fuite d'erreurs), §4.4 (durcissement JWT, anti-énumération login, listes blanches de colonnes SQL). **Reste identifié, volontairement non traité ici :**

- **Pool de connexions PostgreSQL** : `PgRepository` ouvre une connexion par appel (simple et correct, documenté dans son docstring). Sous charge réelle, `psycopg_pool.ConnectionPool` réduirait fortement la latence — nécessite d'ajouter la dépendance et un vrai banc d'essai avec base.
- ~~**`JWT_SECRET` par défaut = avertissement, pas d'arrêt**~~ → **✅ traité (PR de suite de l'audit)** : le démarrage échoue désormais (`RuntimeError`) hors debug si le secret n'a pas été changé (cf. §4.4).
- **N+1 sur `/stats/summary` et `/stats/cognitive-load`** : une requête `get_moves_for_game` par partie analysée. Négligeable in-memory, mais en PostgreSQL une jointure unique (`game_moves JOIN games ON ... WHERE user_id = ...`) serait préférable dès que le volume de parties croît.
- ~~**`backend/mutants/`**~~ → **✅ traité (PR de suite de l'audit)** : artefacts mutmut supprimés du dépôt et ajoutés au `.gitignore` (`backend/mutants/`, `.mutmut-cache`) — mutmut les régénère à l'exécution. Le symlink hérité `backend/src → app/domain` (ancien layout, plus référencé nulle part) a également été supprimé.

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
