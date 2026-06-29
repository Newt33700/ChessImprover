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
