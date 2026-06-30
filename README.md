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
│       └── advanced_stats.test.js      # Tests AdvancedStats (couleurs, deltas, gauge, fallback API)
│
├── backend/
│   ├── requirements.txt                # fastapi, uvicorn, httpx, pydantic, python-chess, bcrypt
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
│       │   └── srs_engine.py           # Algorithme SM-2 côté backend
│       ├── infrastructure/
│       │   ├── chess_com_client.py     # Proxy httpx vers Chess.com API
│       │   ├── engine.py               # EngineProvider (évals client / Stockfish natif) — EPIC 2
│       │   └── db_client.py            # Store in-memory (dev/test) + interface Supabase (US 7)
│       ├── routers/
│       │   ├── auth.py                 # POST /auth/signup /auth/login GET /auth/me (US 7)
│       │   └── sync.py                 # POST /sync — stratégie Client Wins (US 7)
│       ├── tests/
│       │   ├── test_auth.py            # 24 TUs auth : hash, JWT, signup, login, me, sync
│       │   ├── test_analyzer.py
│       │   ├── test_elo.py
│       │   ├── test_phases.py          # US 2.1
│       │   ├── test_acpl.py            # US 2.2
│       │   ├── test_engine.py          # Abstraction moteur
│       │   ├── test_virtual_elo.py     # US 3.1
│       │   ├── test_move_class.py      # US 3.2
│       │   └── test_srs.py
│       └── mutants/                    # Mutation testing mutmut
│
├── supabase/
│   └── migrations/
│       └── 20260630000000_init_auth.sql  # Tables profiles + user_data, RLS, trigger updated_at
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
Auth.syncData(games, srsCards)          // POST /sync → stratégie Client Wins
Auth.isLoggedIn()                       // → boolean
Auth.getToken()                         // → string | null
Auth.getUser()                          // → {id, email, username, chessUsername} | null
```

**Stockage :** `localStorage["ci_jwt"]` (token), `localStorage["ci_user"]` (profil JSON).  
**URL API :** `window.CI_API_URL || "http://localhost:8000"` (configurable).

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
| `renderMatrix/renderDeepDive/renderFinalesTiles/renderTacticsCard/renderAcplChart/renderGaffeDonut/mount` | glue DOM/Chart.js |

**Câblage `app.js` :** `_showAdvStats()` (ajoute la classe + `_loadAdvStats()`), `_loadAdvStats()` (fetch + `renderMatrix/DeepDive/FinalesTiles/TacticsCard` + 2 graphes Chart.js détruits/recréés), onglets de cadence (re-render deep-dive) et sélecteur de période (re-fetch).

> **Câblage données :** ✅ vue + rendu opérationnels ; ⏳ alimentés par `MOCK_SUMMARY` tant que l'endpoint d'agrégation backend (EPIC 1) n'existe pas. La logique pure est testée (`tests/advanced_stats.test.js`, 17 TUs) ; les fonctions `render*` (glue DOM) ne sont pas dans `collectCoverageFrom`, comme `app.js`.

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
| `/auth/me` | GET | — (Bearer token) | 200 `{id, email, username}` | Profil courant |

**Règles métier :**
- Email unique (case-insensitive) → 400 `"Email déjà utilisé"`
- Username unique (case-insensitive) → 400 `"Pseudo déjà pris"`
- Mot de passe haché via bcrypt (salt aléatoire, facteur de coût par défaut ~12)
- Token JWT HS256 (stdlib Python : `hmac` + `hashlib.sha256`), expiration 30 jours
- Payload JWT : `{sub: user_id, email, exp}`

**Dépendance `_current_user` :** FastAPI `HTTPBearer` → `decode_token()` → `find_user_by_id()`. Retourne 401 si token absent, invalide ou expiré.

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

> **Câblage :** ❌ ces modules ne sont pas encore exposés via une route ni appelés par le frontend (voir §9). Ils constituent le socle des US 1.x (ingestion async + persistance `game_moves`) et 4.x (matrice UI) à venir.

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
| `advanced_stats.test.js` | AdvancedStats | cellClass (5 cas), phaseDelta/formatDelta, deepDiveFor (deltas maquette), gaugeAngle (bornes), matrixRows, fetchSummary (succès + 2 fallbacks) — **17 TUs** |

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
| `test_auth.py` | TestPasswordHashing (5), TestJWT (4), TestSignup (4), TestLogin (4), TestMe (3), TestSync (4) | **24 TUs** |
| `test_analyzer.py` | — | Analyse géométrique |
| `test_elo.py` | — | Formules Elo/précision backend |
| `test_phases.py` | Constantes, Material, IsEndgame, OpeningEndPly, SegmentPhases, SegmentPgn | US 2.1 |
| `test_acpl.py` | CentipawnLoss, AverageCpl, AcplByPhase, OverallAcpl | US 2.2 |
| `test_engine.py` | PositionEval, ClientProvidedEngine, NativeStockfishEngine | Abstraction moteur |
| `test_virtual_elo.py` | Anchors, Interpolation, CadenceBonus, AcplToElo | US 3.1 |
| `test_move_class.py` | ClassifyPosition, TacticOutcome, SuccessRatio, TacticalElo, StrategicElo | US 3.2 |
| `test_srs.py` | — | SM-2 backend |

**Couverture backend :** 272 TUs au total, couverture globale **85 %** ; modules du cœur Stats Avancées à 97–100 % (`acpl`, `move_class`, `virtual_elo`, `engine`, `models` à 100 %, `phases` 97 %).

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
| **Vue Statistiques Avancées** (US 4.1/4.2) | `advanced_stats.js` + `index.html` + `app.js` | Plein écran `body.advstats-active` : matrice colorée + gauge Héros + deep-dive + tuiles Finales + carte Tactiques (données `MOCK_SUMMARY`) |

### ❌ Non câblé ou incomplet

| Fonctionnalité | Problème | Priorité |
|---|---|---|
| **Connexion Supabase réelle** (US 7) | `db_client.py` utilise un dict in-memory. La connexion à Supabase via `DATABASE_URL` n'est pas implémentée. | 🔴 Critique |
| **Moteur Stats Avancées (EPIC 2 & 3)** | `phases.py`, `acpl.py`, `virtual_elo.py`, `move_class.py`, `engine.py` sont implémentés et testés mais **non exposés** : aucune route ne les appelle, aucune table `game_moves` ne les persiste, le frontend ne les consomme pas. | 🔴 Critique (prochaine étape) |
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

### 10.1 🔴 CRITIQUE — Connexion Supabase réelle

**Dans `db_client.py` :** implémenter la connexion PostgreSQL via `psycopg2` ou `asyncpg` quand `settings.database_url` est défini. L'interface (`find_user_by_email`, `create_user`, etc.) reste identique — seul le backend de stockage change.

### 10.1bis 🔴 CRITIQUE — Brancher le moteur Stats Avancées (EPIC 1 & 4)

Le cœur algorithmique (EPIC 2 & 3) est prêt et testé mais isolé. Reste à :
- **US 1.1** : `POST /api/v1/games/analyze` → crée une ligne `games` (`status='processing'`), répond `202` + UUID, lance une `BackgroundTask` qui orchestre `segment_phases` → `centipawn_loss`/`acpl_by_phase` → `virtual_elo`/`move_class`.
- **US 1.2** : table Supabase `game_moves` (bulk insert des métriques par coup), passage `status='completed'`.
- **US 4.1** : endpoint d'agrégation `GET /api/v1/stats/summary?period=30d` (zéro calcul client) + matrice UI mobile (lignes Bullet/Blitz/Rapide × colonnes Classement/Ouvertures/Tactique/Stratégie/Finales).
- **US 4.2** : vues détaillées par onglet (Ouvertures top 3 ECO, taux de réussite tactique, taux de conversion/résilience en finale).

### 10.2 🟡 IMPORTANT — Cache du livre d'ouvertures

Sauvegarder le `Set` d'EPD dans IndexedDB (`openings_cache`) avec un TTL de 7 jours. Évite 5 requêtes réseau et ~2s de parsing chess.js à chaque refresh.

### 10.3 🟢 OPTIONNEL — Qualité SRS nuancée

Actuellement `quality=5` ou `quality=1`. Ajouter `quality=3` si le joueur joue un coup différent mais que la position reste avantageuse (`evalCp > 0` après le coup joué).

### 10.4 🟢 OPTIONNEL — Indicateur chargement livre d'ouvertures

L'utilisateur ne voit pas que le livre ECO se télécharge (~2s). Ajouter un spinner ou un message dans l'UI pendant ce chargement.

### 10.5 🟢 OPTIONNEL — Précisions Chess.com dans la carte RÉVISION

L'API Chess.com retourne `g.accuracies.white/black`. Les afficher dans les barres de précision de la `.match-card` au lieu de `null` (les barres restent à 0% si Stockfish n'a pas encore analysé la partie).

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
