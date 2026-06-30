# CLAUDE.md — Règles de développement Chess Improver

## Mise à jour du README après chaque US

**Règle obligatoire :** à chaque fois qu'une User Story (US) est implémentée, commitée et poussée, mettre à jour `README.md` pour refléter l'état exact du dépôt.

La mise à jour doit respecter les **12 sections** définies dans le README :

1. **Vue d'ensemble** — Mettre à jour le diagramme ASCII si de nouveaux flux apparaissent (nouveau module, nouveau endpoint, nouvelle source de données).
2. **Architecture** — Mettre à jour le tableau Stack si une dépendance change, et l'arborescence des fichiers si un fichier est créé, renommé ou supprimé.
3. **Frontend — Fonctionnalités implémentées** — Ajouter une sous-section pour chaque nouveau module JS : formule ou algorithme exact, API publique (toutes les fonctions exportées), comportement du câblage dans `app.js`.
4. **Backend — Fonctionnalités implémentées** — Documenter chaque nouvelle route (méthode, corps, réponse, règles métier). Mettre à jour le tableau des routes classiques si leur statut change.
5. **Règles métier** — Ajouter toute formule, seuil, constante ou règle de décision nouvelle. Ne jamais laisser une règle implicite dans le code sans l'expliquer ici.
6. **Tests & Qualité** — Mettre à jour la liste des fichiers de tests, le nombre de TUs, les seuils de couverture et les mocks globaux ajoutés.
7. **CI/CD** — Documenter tout nouveau pipeline ou modification d'un pipeline existant (jobs, secrets, déclencheurs).
8. **État du câblage** — Déplacer une fonctionnalité de ❌ vers ✅ dès qu'elle est câblée. Ajouter les nouvelles fonctionnalités dans la bonne colonne dès leur création.
9. **Code mort & non câblé** — Ajouter toute fonctionnalité implémentée mais pas encore intégrée dans l'UI ou dans `app.js`. Supprimer les entrées résolues.
10. **Ce qui reste à développer** — Mettre à jour les priorités (🔴🟡🟢) au fil des US. Supprimer les points traités, ajouter les nouveaux bloquants découverts.
11. **Backlog & idées futures** — Ajouter les idées qui émergent pendant le développement, sans les implémenter.
12. **Annexes** — Mettre à jour les variables d'environnement, commandes, schémas SQL si nécessaire.

### Ordre de travail pour chaque US

1. Implémenter le code (JS frontend ou Python backend).
2. Écrire les tests (Jest ou pytest), vérifier que la couverture ≥ 80%.
3. Mettre à jour `UserStory.md` : passer le statut à `✅ Implémenté`.
4. Mettre à jour `README.md` en respectant les 12 sections ci-dessus.
5. Committer les fichiers de code et de tests dans un commit séparé du README.
6. Committer le README dans un commit dédié avec le message `docs(README): update after US X`.
7. Pousser sur la branche `claude/chess-app-user-stories-4umz42`.
