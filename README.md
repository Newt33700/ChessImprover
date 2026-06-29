# Chess Improver — Documentation Complète

> Application d'analyse de parties d'échecs avec estimation Elo, détection d'ouvertures, mode révision, exercices SRS et mode Ghost.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture](#2-architecture)
3. [Frontend — Fonctionnalités développées](#3-frontend--fonctionnalités-développées)
4. [Backend — Fonctionnalités développées](#4-backend--fonctionnalités-développées)
5. [Règles métier](#5-règles-métier)
6. [État du câblage Frontend](#6-état-du-câblage-frontend)
7. [Ce qui reste à développer](#7-ce-qui-reste-à-développer)
8. [Backlog et idées futures](#8-backlog-et-idées-futures)

---

## 1. Vue d'ensemble

Chess Improver est une SPA (Single Page Application) en **mode standalone** : toute l'intelligence est côté navigateur, sans dépendance au backend pour les fonctionnalités principales. Le backend FastAPI existe mais sert principalement de proxy / API d'analyse géométrique et est aujourd'hui peu utilisé par le frontend.

```
Chess.com API  ──► Frontend JS (chess.js + Stockfish Web Worker)
                       │
                       ├── Analyse PGN + horloges
                       ├── Évaluation position (depth 5)
                       ├── Détection ouvertures (ECO GitHub)
                       ├── Classification des coups
                       ├── Mode Review (navigation + badges)
                       ├── Mode Ghost (replay blunder)
                       ├── Mode Exercice (SRS)
                       └── LocalStorage (historique, SRS, XP)
```

---

## 2. Architecture

### 2.1 Stack Frontend

| Élément | Détail |
|---|---|
| Langage | JavaScript ES2022 (pas de bundler, fichiers bruts) |
| Échiquier | [chessboard.js v1.0.0](https://chessboardjs.com/) (CDN) |
| Moteur PGN | [chess.js v0.10](https://github.com/jhlywa/chess.js) (CDN) |
| Moteur UCI | [Stockfish.js v10 Multi-Variant](https://github.com/niklasf/stockfish.js) — **asm.js, pas WASM** |
| Style | CSS custom properties, dark theme, pas de framework CSS |
| Persistance | `localStorage` uniquement |

### 2.2 Stack Backend

| Élément | Détail |
|---|---|
| Framework | FastAPI (Python 3.9) |
| Serveur | uvicorn |
| HTTP client | httpx (async) |
| Venv | `.venv` dans `/backend` |
| Tests | pytest (fichiers dans `tests/` et `mutants/tests/`) |

### 2.3 Structure des fichiers

```
ChessImprover/
├── frontend/
│   ├── index.html          # SPA unique, sections cachées/affichées
│   ├── css/style.css       # Thème sombre, variables CSS, responsive
│   ├── js/
│   │   ├── app.js          # Logique métier principale (~900 lignes)
│   │   └── board_manager.js # Gestion échiquier, Stockfish, modes (~430 lignes)
│   └── serve.py            # Serveur HTTP simple (dev)
└── backend/
    └── app/
        ├── main.py         # Routes FastAPI
        ├── config.py       # Paramètres (CORS, user-agent)
        ├── domain/
        │   ├── analyzer.py       # Analyse géométrique PGN
        │   ├── elo_calculator.py # Formules Elo / précision
        │   ├── srs_engine.py     # Algorithme SM-2
        │   └── models.py         # Pydantic models
        └── infrastructure/
            └── chess_com_client.py # Client Chess.com API
```

---

## 3. Frontend — Fonctionnalités développées

### 3.1 Chargement des parties Chess.com

**Fichier :** `app.js` — `ChessComClient`, `_connectUser()`

- Connexion par pseudo Chess.com
- Récupération des archives mensuelles via `https://api.chess.com/pub/player/{username}/games/{year}/{month}`
- Chargement des 20 dernières parties
- Affichage liste des parties avec : résultat (V/L/½), adversaire, date, cadence, rating
- Clic sur une partie → pré-remplit le PGN dans la zone d'analyse
- Persistance du pseudo en localStorage

**Ce qui n'est pas fait :** Pagination / chargement de plus de parties, filtres par cadence ou période, recherche par adversaire.

---

### 3.2 Parsing PGN et extraction des horloges

**Fichier :** `app.js` — `PGNAnalyzer.analyze(pgn)`

- Parse le PGN via chess.js (history verbose)
- Extrait les headers : `WhiteElo`, `BlackElo`, `TimeControl`, `ECO`, `Opening`
- Extrait les horloges coup par coup depuis les commentaires `[%clk H:MM:SS]`
- Calcule `timeSpent` par coup (différence avec le coup précédent de même couleur)
- Produit un tableau `moves[]` avec pour chaque coup :
  - `san` : notation algébrique
  - `from`, `to` : cases source/destination
  - `color` : "w" ou "b"
  - `fen` : position après le coup
  - `clock` : temps restant en secondes
  - `timeSpent` : temps consommé en secondes
  - `accuracy_score` : null (rempli par Stockfish)
  - `classification` : "unknown" (rempli par Stockfish)
  - `cpLoss` : null (rempli par Stockfish)

---

### 3.3 Moteur Stockfish — Analyse par Web Worker

**Fichier :** `board_manager.js` — `_initWorker()`, `_handleWorkerUCI()`, `_processQueue()`

**Architecture critique :**
- Stockfish.js v10 est asm.js (pas WebAssembly). Il NE répond PAS à `isready` avec `readyok`.
- Séquence d'initialisation : `uci` → `uciok` → `setoption name Hash value 16` + `ucinewgame` → `workerReady = true`
- Analyse **séquentielle** : une position à la fois, via une file d'attente (`analysisQueue[]`)
- Profondeur : `go depth 5` — optimum pour asm.js (vitesse/précision)
- Filtre de stabilité : les infos `depth < 3` sont ignorées

**Protocole UCI implémenté :**
```
→ uci
← uciok              (⚠ pas de readyok ici pour Stockfish.js v10)
→ setoption name Hash value 16
→ ucinewgame
→ position fen <FEN>
→ go depth 5
← info depth N score cp X pv ...
← bestmove <MOVE>    (déclenche la position suivante)
```

**evalCache :** Chaque position analysée est mise en cache (`evalCache[fen]`). L'évaluation est du point de vue du joueur qui doit jouer dans cette position (convention UCI).

---

### 3.4 Détection des coups d'ouverture

**Fichier :** `app.js` — `_buildOpeningBook()`, `_detectBookDepth()`

- Au démarrage de l'app, télécharge les 5 fichiers ECO de [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings) (a.tsv → e.tsv)
- Joue chaque séquence de coups ECO avec chess.js
- Stocke toutes les positions intermédiaires (EPD = FEN sans les compteurs) dans un `Set<string>` (~28 000 positions)
- CORS ouvert : `access-control-allow-origin: *` sur raw.githubusercontent.com
- À chaque revue, `_detectBookDepth()` parcourt les coups du joueur : tant que l'EPD est dans le Set → coup book
- Résultat transmis à `boardMgr.setBookDepth(n)` qui met à jour `bookMoveThreshold`
- Si le réseau est indisponible : fallback → seuil de 15 demi-coups (non reclassifiés)

**Limitation connue :** Pas de cache du livre d'ouvertures entre sessions (recalculé à chaque refresh). L'API Lichess Explorer (`explorer.lichess.ovh`) retourne 401 même côté serveur.

---

### 3.5 Classification des coups

**Fichier :** `app.js` — `EloEngine`, `_onMoveAccuracy()`

Conversion cpLoss → précision du coup :
```
accuracy = 100 × exp(−0.003 × |cpLoss|)
```

**Seuils de classification :**

| Classification | Seuil précision | Symbole badge | Couleur |
|---|---|---|---|
| Brillant | ≥ 95% | ✦ | Teal `#1bada6` |
| Excellent | ≥ 85% | !! | Bleu `#5b8dd9` |
| Bon | ≥ 70% | ! | Vert `#96bc4b` |
| Imprécision | ≥ 50% | ?! | Jaune `#f6af29` |
| Erreur | ≥ 25% | ? | Orange `#e87a14` |
| Gaffe | < 25% | ?? | Rouge `#ca3431` |
| Théorique | (ouverture) | B | Brun `#8b7355` |

**Conversion cpLoss → classification (exemples) :**
- 0 cp → 100% (Brillant si hors book, Théorique si book)
- 30 cp → 91.4% (Excellent)
- 100 cp → 74% (Bon)
- 200 cp → 55% (Imprécision)
- 350 cp → 35% (Erreur)
- 500 cp → 22% (Gaffe)

**Calcul du cpLoss** (dans `_tryUpdateMoveAccuracy`) :
```
cpLoss(blanc) = max(0, evalAvant_blanc - evalAprès_blanc)
cpLoss(noir)  = max(0, evalAprès_blanc - evalAvant_blanc)
```
Les évaluations UCI (point de vue du joueur qui joue) sont converties en avantage blanc absolu avant calcul.

---

### 3.6 Estimation Elo

**Fichier :** `app.js` — `EloEngine.estimateElo()`

```
eloEstimé = max(400, min(2800, précision × 10 + eloAdversaire × 0.3))
```

Calibré sur : 79% de précision + adversaire 1000 Elo ≈ 1090 Elo estimé.

**Limites :** Formule simplifiée, non calibrée sur un grand dataset. Ne tient pas compte de la cadence, de la phase de jeu, ni des erreurs tactiques spécifiques.

---

### 3.7 Mode Review — Navigation et affichage

**Fichier :** `board_manager.js` — `startReview()`, `goToMove()`, `_updateReviewHighlight()`  
**Fichier :** `app.js` — `_enterReviewMode()`, `_onReviewMove()`

**Ce qui est affiché :**

- **Échiquier** : position après chaque coup, navigation ‹ › ou clic sur la liste
- **Liste des coups** (2 colonnes blanc/noir) : classification colorée + icône en bord gauche
- **Badge sur l'échiquier** : cercle coloré animé au coin supérieur-droit de la case de destination
  - Apparaît avec animation "pop" (cubic-bezier rebondissant)
  - Se met à jour en temps réel au fur et à mesure de l'analyse Stockfish
  - Brillant : glow cyan
- **Info-bulle du coup** : classification + notation SAN + précision % + temps consommé
- **Bouton Ghost** : affiché uniquement pour les gaffes et erreurs
- **Horloge** : temps restant de chaque joueur selon les données `[%clk]` du PGN
- **Barre de précision** (accuracy bar) : remplie progressivement au fil de l'analyse
- **Stats** : Précision globale %, Elo estimé, nombre de gaffes

**Orientation du plateau :**
- Le joueur analysé est toujours en bas (auto-flip selon `playerColor` du PGN)
- Bouton de retournement manuel

---

### 3.8 Mode Ghost (replay de gaffe)

**Fichier :** `board_manager.js` — `startGhost()`, `_ghostPlayOpponentMove()`, `_evaluateGhostResult()`  
**Fichier :** `app.js` — `_startGhost()`, `_onGhostResult()`

**Principe :** Permet de rejouer une gaffe depuis 3 coups avant l'erreur, avec les coups historiques de l'adversaire.

**Flux :**
1. Clic sur "Ghost" dans la fiche d'un coup gaffe/erreur
2. Position chargée à `max(0, blunderIndex - 3)`
3. L'adversaire rejoue ses coups historiques automatiquement (avec délai 400ms)
4. Le joueur doit trouver un meilleur coup
5. Évaluation finale via Stockfish (ou cache si déjà calculé)
6. Succès si `playerEval > 0` (position gagnante pour le joueur)
7. Récompense : `XP_PER_EXERCISE × 2` + streak

**Limitation connue :** `playerColor` est hardcodé à "w" dans `_startGhost()`. Le mode ne fonctionne pas correctement si le joueur est noir.

---

### 3.9 Mode Exercice SRS

**Fichier :** `app.js` — `_startExercise()`, `_onExerciseResult()`  
**Fichier :** `app.js` — `const SRS = {...}`

**Algorithme SM-2 implémenté :**
- `EF` (Ease Factor) initial : 2.5, minimum : 1.3
- Qualité 0-5 : 0-2 = raté (réinitialisation), 3-5 = réussi (progression)
- Intervalle : 1j → 6j → `round(interval × EF)` × ...
- Persistance en localStorage via `ci_srs_cards`

**Flux d'exercice :**
1. Charge les cartes SRS dont la date d'échéance ≤ aujourd'hui
2. Affiche la position sur l'échiquier
3. Le joueur joue le coup
4. Succès → `quality=5` → +XP → carte reprogrammée
5. Échec → `quality=1` → intervalle réinitialisé à 1 jour

**⚠ Limitation critique :** `SRS.createCard()` est défini mais **jamais appelé**. Les cartes SRS ne sont **pas créées automatiquement** lors de la détection d'une gaffe. L'exercice ne peut donc fonctionner qu'avec des cartes créées manuellement ou par une autre voie non implémentée.

---

### 3.10 Système XP / Niveaux / Streaks

**Fichier :** `app.js` — `XPSystem`, `StreakSystem`

| Action | XP gagnés |
|---|---|
| Analyser une partie | 50 XP |
| Réussir un exercice | 10 XP |
| Réussir un Ghost | 20 XP |

- **Niveau :** `XP_PER_LEVEL(n) = n × 100` XP requis
- **Streak :** Jours consécutifs d'activité, persisté en localStorage avec date de dernière activité
- Affichage en en-tête : `🔥 N` (streak) + `Niv. X ━━━━ N XP`

---

### 3.11 Tableau de bord (Dashboard)

**Fichier :** `app.js` — `_renderStats()`, `_renderGamesList()`

- Stats agrégées (depuis localStorage) : total parties, précision moyenne, total gaffes
- Liste des parties récentes cliquables
- Bouton "Analyser un PGN" → section saisie PGN

---

## 4. Backend — Fonctionnalités développées

**État : existant mais peu intégré au frontend actuel (mode standalone).**

### Routes disponibles

| Route | Méthode | Description |
|---|---|---|
| `/health` | GET | Statut de santé |
| `/analyze` | POST | Analyse géométrique d'un PGN |
| `/games/{username}` | GET | Dernières parties Chess.com (proxy) |
| `/srs/review` | POST | Erreur 400 (stub, utiliser `/srs/review/full`) |
| `/srs/review/full` | POST | Recalcul carte SRS (SM-2) |

### `/analyze` — Analyse géométrique

**Input :** `{ pgn: string, opponent_elo?: int }`  
**Output :** `GameAnalysis` (précision 70% par défaut, sans Stockfish)

Appelle `analyze_pgn()` qui détecte :
- Gaffes géométriques
- Fourchettes manquées (`missed_forks_count`)
- Paniques temporelles (`time_panic_count`)

**⚠ Non utilisé par le frontend** : le frontend fait toute l'analyse côté client.

### `/games/{username}`

Proxy vers `https://api.chess.com/pub/player/{username}/...`  
**⚠ Non utilisé par le frontend** : le frontend appelle Chess.com directement (CORS autorisé).

### `/srs/review/full`

Implémente SM-2 côté serveur.  
**⚠ Non utilisé par le frontend** : le SRS est entièrement en JS dans `app.js`.

---

## 5. Règles Métier

### 5.1 Formule de précision du coup

```
précision(coup) = 100 × exp(−DECAY × |cpLoss|)
DECAY = 0.003
```

Valeurs de référence :
- 0 cp perdu → 100.0%
- 50 cp → 86.1%
- 100 cp → 74.1%
- 200 cp → 54.9%
- 300 cp → 40.7%

### 5.2 Précision globale de la partie

```
précision(partie) = moyenne(précision_coup) sur tous les coups du joueur
```
Les coups "book" ont une précision de 100% et ne dégradent pas le score.

### 5.3 Estimation Elo

```
eloEstimé = clamp(accuracy × 10 + eloAdversaire × 0.3, 400, 2800)
```

Le rating de l'adversaire est extrait du header PGN (`BlackElo` ou `WhiteElo` selon la couleur du joueur).

### 5.4 Détection des coups théoriques (ouvertures)

1. Au démarrage : téléchargement des fichiers ECO (a.tsv à e.tsv) depuis GitHub
2. Pour chaque ligne ECO : joue la séquence de coups avec chess.js
3. Chaque position intermédiaire (EPD) est ajoutée à un `Set`
4. Pour chaque partie analysée : parcours les coups dans l'ordre jusqu'au premier coup hors du Set
5. Tous les coups avant ce point = "book" (cpLoss=0, précision=100%, aucun badge de classification négatif)

### 5.5 Calcul du cpLoss

Pour le coup à l'index `i` joué par le joueur de couleur `C` :
```
evalBefore_white = evalCache[fen_{i-1}] × (couleur_{i-1} == "w" ? +1 : -1)
evalAfter_white  = evalCache[fen_i]     × (couleur_i     == "w" ? +1 : -1)

si C == "w" : cpLoss = max(0, evalBefore_white − evalAfter_white)
si C == "b" : cpLoss = max(0, evalAfter_white  − evalBefore_white)
```

### 5.6 Algorithme SRS SM-2

```
si qualité < 3 : interval=1, reps=0 (réinitialisation)
sinon :
  delta = 0.1 − (5−q) × (0.08 + (5−q) × 0.02)
  EF_new = max(1.3, EF + delta)
  si reps==1 : interval=1
  si reps==2 : interval=6
  sinon      : interval = round(interval × EF_new)
```

---

## 6. État du câblage Frontend

### ✅ Câblé et fonctionnel

| Fonctionnalité | Fichier(s) | Notes |
|---|---|---|
| Connexion Chess.com | `app.js` | API publique directe |
| Chargement parties (20 dernières) | `app.js` | Avec parsing horloges PGN |
| Analyse PGN (chess.js) | `app.js` | Toutes cadences |
| Analyse Stockfish (depth-5) | `board_manager.js` | Web Worker, séquentiel |
| File d'analyse avec cache | `board_manager.js` | evalCache, pas de re-calcul |
| Détection ouverture (ECO GitHub) | `app.js` | Set EPD, 28k positions |
| Classification des coups (7 niveaux) | `app.js` | book/brilliant/.../blunder |
| Badge sur l'échiquier (animé) | `app.js` | Toutes classifications dont book |
| Liste des coups avec couleurs | `app.js` | Mise à jour temps réel |
| Précision globale | `app.js` | Mise à jour après chaque analyse |
| Estimation Elo | `app.js` | Recalcul à chaque analyse |
| Barre de précision animée | `app.js` | |
| Navigation dans la partie | `board_manager.js` | Flèches + clic liste |
| Horloges temps réel | `app.js` | Depuis `[%clk]` PGN |
| Affichage temps par coup | `app.js` | ⏱ dans l'info-bulle |
| Flip automatique (joueur en bas) | `app.js` | Détecté depuis PGN |
| Flip manuel | `board_manager.js` | Bouton ⇅ |
| Éval moteur en direct | `app.js` | Barre `engine-eval` |
| Mode Ghost | `board_manager.js` + `app.js` | Replay depuis n-3 |
| Mode Exercice SRS | `app.js` | Lecture seule (voir §7) |
| Algorithme SM-2 | `app.js` | Pur JS, localStorage |
| XP + niveaux | `app.js` | Persisté localStorage |
| Streaks | `app.js` | Persisté localStorage |
| Stats dashboard | `app.js` | Agrégat localStorage |
| Historique des parties | `app.js` | 100 parties max, localStorage |

### ❌ Non câblé ou incomplet

| Fonctionnalité | Problème | Priorité |
|---|---|---|
| **Création auto de cartes SRS** | `SRS.createCard()` n'est jamais appelé lors d'une gaffe détectée | 🔴 Critique |
| **Ghost mode côté noir** | `playerColor` hardcodé à "w" dans `_startGhost()` | 🔴 Critique |
| **Cache du livre d'ouvertures** | Re-téléchargé à chaque refresh (~28k positions) | 🟡 Important |
| **Qualité de l'exercice SRS** | Seulement quality=5 (succès) ou quality=1 (raté), pas de nuance | 🟡 Important |
| **Backend integration** | `/analyze`, `/games`, `/srs/review` non utilisés | 🟢 Optionnel |
| **Persistance cross-session** | Tout dans localStorage = perdu si cleared | 🟢 Optionnel |

---

## 7. Ce qui reste à développer

### 7.1 CRITIQUE — Création des cartes SRS depuis les gaffes

**Problème :** Les exercices SRS n'ont aucun contenu. `SRS.createCard()` existe mais n'est jamais appelé.

**Solution à implémenter :**
Dans `_onMoveAccuracy()`, quand `classification === "blunder"` :
```js
if (classification === "blunder") {
  const move = game.moves[moveIdx];
  const prevFen = moveIdx > 0 ? game.moves[moveIdx - 1].fen : startFen;
  const card = SRS.createCard(
    `${game.game_id}_${moveIdx}`,
    prevFen,              // position AVANT la gaffe
    move.to,              // coup correct = bestMove de Stockfish
  );
  SRS.saveCard(card);
}
```
Idéalement utiliser `evalCache[fen].bestMove` comme solution.

### 7.2 CRITIQUE — Ghost mode côté noir

**Fichier :** `app.js`, ligne ~680  
Remplacer le `playerColor = "w"` hardcodé par `this.playerColor`.

### 7.3 Cache du livre d'ouvertures

Sauvegarder le `Set` d'EPD en `localStorage` avec un TTL (ex. 7 jours) pour éviter le retéléchargement à chaque refresh. Représente ~4 Mo en JSON stringifié mais évite 5 requêtes réseau et ~2s de parsing chess.js.

### 7.4 Indicateur de chargement du livre

L'utilisateur ne voit pas que le livre se charge. Ajouter un indicateur visuel ou message "Détection de l'ouverture..." dans l'info-bulle.

### 7.5 Nuances dans la qualité SRS

Actuellement `quality=5` (parfait) ou `quality=1` (raté). Ajouter :
- `quality=4` si le joueur a pris du temps
- `quality=3` si le coup est correct mais pas le meilleur

### 7.6 Persistance back-end

Les données (SRS, historique, XP) sont perdues si localStorage est vidé. Options :
- Sync vers le backend (API `/user/data`)
- Export/import JSON
- IndexedDB pour plus de stockage

---

## 8. Backlog et idées futures

### 8.1 Analyse multi-parties

Actuellement une seule partie analysée à la fois. Idées :
- Analyser les N dernières parties d'un coup
- Identifier les **patterns d'erreur récurrents** (ex. "vous faites souvent des gaffes en phase de milieu de jeu avec les pièces lourdes")
- Graphe de progression Elo estimé dans le temps

### 8.2 Thèmes tactiques automatiques

Classifier chaque gaffe par thème tactique (fourchette, clouage, enfilade, mat en N coups...) via le `bestMove` de Stockfish. Serait la base pour des exercices thématiques SRS.

### 8.3 Répertoire d'ouvertures personnalisé

Identifier les ouvertures que le joueur joue le plus, montrer leurs performances (score, précision moyenne) et recommander des variantes à améliorer.

### 8.4 Analyse d'endgame

Détecter automatiquement la phase de jeu (ouverture / milieu / finale) et calculer des stats séparées par phase.

### 8.5 Puzzles externes

Intégrer les puzzles Lichess API (requiert auth) ou un fichier CSV de puzzles statiques pour enrichir les exercices au-delà des propres gaffes du joueur.

### 8.6 Mode "Devinette du coup"

Avant d'afficher le coup suivant dans la revue, cacher la pièce et demander au joueur de deviner le coup. Transformer la revue passive en revue active.

### 8.7 Analyse de la gestion du temps

Détecter les "paniques temporelles" (coups joués en < 5s) et les mettre en évidence visuellement dans la liste des coups. Un coup précipité est souvent une gaffe.

### 8.8 Export / Partage

- Exporter le rapport d'analyse en PDF
- Partager un lien vers une position spécifique
- Copier le PGN annoté (avec commentaires de classification)

### 8.9 Comparaison chess.com

Récupérer les `accuracies` du JSON chess.com (disponibles dans `g.accuracies.white/black`) et les afficher à côté de l'estimation locale pour calibration.

### 8.10 Mode mobile optimisé

L'interface est responsive mais certains éléments (liste des coups, stats) ne sont pas optimaux sur mobile. Le board est bien adapté mais les interactions tactiles mériteraient des ajustements (swipe pour naviguer, touch targets plus grands).

---

## Annexe — Variables d'environnement Backend

Fichier `.env` à créer dans `/backend/` :
```env
DEBUG=false
USER_AGENT=ChessImprover/0.1 (contact: chess-improver@example.com)
ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

## Annexe — Démarrage en développement

```bash
# Frontend
cd frontend && python3 serve.py
# Accessible sur http://localhost:8080

# Backend (optionnel)
cd backend && .venv/bin/uvicorn app.main:app --port 8000 --reload
# Accessible sur http://localhost:8000
```
