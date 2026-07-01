# CLAUDE.md — Règles de développement et comportement de l'Agent (Chess Improver)

## 🤖 Directives d'Exécution de l'Agent
1. **Économie de Contexte** : Ne jamais réécrire un fichier entier si une modification par bloc (`Search/Replace` ou patch ciblé) est possible.
2. **Zéro Tolérance aux Erreurs** : Interdiction de committer du code qui ne valide pas les tests ou le linter.
3. **Précision vs Hallucination** : Si une règle métier ou une API existante est ambiguë, s'arrêter et demander clarification à l'utilisateur plutôt que de présumer.

## 🔄 Protocole de Travail Strict par User Story (US)

### Étape 1 : Synchronisation et Création de l'Environnement (Feature Branching)
- [ ] Revenir sur la branche principale : `git checkout main` (ou `master`).
- [ ] Récupérer les dernières modifications distantes : `git pull origin main` (Obligatoire pour éviter les conflits futurs).
- [ ] Créer et basculer sur une nouvelle branche strictement nommée selon la nomenclature : `git checkout -b feat/US-<numero>-<description-courte>` (ex: `feat/US-12-validation-roque`).
- [ ] Exécuter la suite complète de tests existante (`npm test` et `pytest`) pour valider la stabilité de la base. Si échec, notifier l'utilisateur et stopper.

### Étape 2 : Analyse et Conception des Cas Limites
- [ ] Identifier les impacts de l'US sur la logique globale du jeu (ex: intégrité de l'échiquier, état de la partie).
- [ ] Lister explicitement les cas aux limites (*edge cases*) à couvrir (ex: entrées malformées, coups impossibles).

### Étape 3 : Implémentation TDD (Code & Tests)
- [ ] Écrire les tests unitaires et d'intégration (Jest / pytest) reflétant les spécifications de l'US et les cas limites identifiés.
- [ ] Implémenter le code fonctionnel (JS frontend ou Python backend) jusqu'à ce que les tests passent.
- [ ] Garantir que la couverture globale et locale reste **≥ 80%**.

### Étape 4 : Validation Qualité & Non-Régression
- [ ] Lancer les outils de formatage et de linting du projet (ex: `npm run lint`, `black`, `flake8`). Corriger tout avertissement.
- [ ] Exécuter la suite **complète** des tests du dépôt pour garantir l'absence de régression.

### Étape 5 : Documentation Incrémentale
- [ ] Mettre à jour `UserStory.md` : passer le statut de l'US à `✅ Implémenté`.
- [ ] Mettre à jour `README.md` en appliquant des modifications chirurgicales sur les 12 sections requises (ne pas modifier les sections non impactées).

### Étape 6 : Stratégie de Commit, Push & Fin de cycle
- [ ] **Commit 1 (Fonctionnel)** : Committer uniquement le code et les tests. Message : `feat(US-<X>): <description>` ou `fix(US-<X>): <description>`.
- [ ] **Commit 2 (Documentation)** : Committer les fichiers de documentation séparément. Message : `docs(README): update after US <X>`.
- [ ] Pousser la branche courante sur le dépôt distant : `git push -u origin feat/US-<numero>-<description-courte>`.
- [ ] **Action finale requise** : Notifier l'utilisateur que la branche est prête à être vérifiée et fusionnée (via une Pull Request). **Ne pas démarrer l'US suivante tant que cette branche n'a pas été mergée dans main.**

---

## 📝 Règles de Maintenance du README (12 Sections)
Lors de la mise à jour du `README.md`, appliquer strictement la grille suivante pour éviter la dégradation des informations :

1. **Vue d'ensemble** : Ajuster le diagramme ASCII uniquement si un nouveau module/flux modifie le cycle de vie des données.
2. **Architecture** : Synchroniser le tableau Stack (si ajout/suppression de package) et l'arborescence (uniquement les nouveaux répertoires ou fichiers clés).
3. **Frontend** : Documenter chaque nouveau module JS (Nom, API publique exportée, formule/algo, câblage dans `app.js`).
4. **Backend** : Documenter les nouvelles routes (Méthode, URI, Payload, Réponse, Code HTTP, Règles associées).
5. **Règles métier** : Expliciter toute constante, seuil, ou logique de score. *Code auto-documenté interdit ici : tout doit être écrit en langage naturel.*
6. **Tests & Qualité** : Mettre à jour les métriques (nombres de TUs, taux de couverture exact).
7. **CI/CD** : Documenter les changements de pipelines uniquement si modification des fichiers de workflow.
8. **État du câblage** : Basculer les fonctionnalités de ❌ vers ✅ de manière rigoureuse.
9. **Code mort & non câblé** : Suivre les fonctionnalités implémentées en "background" mais non exposées.
10. **Ce qui reste à développer** : Réévaluer les priorités (🔴🟡🟢) à la lumière des découvertes de l'US.
11. **Backlog & idées futures** : Consigner les suggestions d'amélioration sans démarrer leur code.
12. **Annexes** : Mettre à jour les variables d'environnement (`.env.example`) et les schémas d'initialisation.
