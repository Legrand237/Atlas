# TODO

## Fait
- [x] Architecture v2 validée (2026-10-04)
- [x] Sections 40–41 du cahier des charges intégrées (PROJECT_STATE.md §17) et validées
- [x] Étape 1 écrite : structure, backend FastAPI (/health), tests, .gitignore, .env.example, devcontainer, guide téléphone (PROJECT_STATE.md §18)

## À faire pour clôturer l'étape 1 (par l'utilisateur, voir docs/ETAPE1_GUIDE_TELEPHONE.md)
- [ ] Créer le dépôt GitHub privé `atlas` (avec README initial)
- [ ] Ouvrir Codespaces, envoyer et décompresser `atlas-etape1.zip`
- [ ] Installer les dépendances et lancer `pytest` — noter le résultat (attendu : 25 passed, non vérifié)
- [ ] Lancer le serveur et appeler /health
- [ ] Vérifier que `backend/.env` n'est pas dans `git status`
- [ ] Premier commit et `git push`
- [ ] Arrêter le codespace ; vérifier le quota gratuit Codespaces
- [ ] Lancer `ruff check .` et signaler le résultat

## Dette technique de l'étape 1 (à traiter avant ou pendant l'étape 2)
- [ ] Figer les versions dans requirements*.txt (pip freeze) — solution temporaire
- [ ] Tester le devcontainer (Rebuild Container) et vérifier l'image Python 3.12
- [ ] Valider ou corriger les tests si pytest révèle des échecs

## Exigences issues des sections 40–41 à planifier
- [ ] Étape 6–7 : tracer la raison de chaque autorisation/refus ; étape AUTHORIZE dans la boucle
- [ ] Étape 2 : audit_logs avec identifiant de corrélation (réutiliser X-Request-ID), tâche, décision d'autorisation
- [ ] Étape 9 : skill_versions avec origine, tests, résultats, confiance, compatibilité, rollback
- [ ] Chaque étape : critère 41.18 (implémentation réelle, test, vérification, gestion d'erreurs, documentation minimale, intégration permissions/audit)

## Décisions techniques à prendre avant implémentation (sans payer avant vérification)
- Étape 2 : hébergeur du backend ; fournisseur PostgreSQL (avec pgvector) ; stratégie de migrations
- Étape 3 : fournisseur IA ; modèles par niveau de difficulté ; quotas de coûts
- Étape 5 : fournisseur de recherche Web
- Étape 6 : règles précises des niveaux de permission 0–5
- Étape 9 : technologie de sandbox (conteneur isolé) et où l'héberger
- Étape 12 : source de données de marché ; marchés ciblés
- Étape 13 : distribution Android (APK perso ou Google Play) selon l'usage de l'Accessibility Service
- Nom définitif du projet (« atlas » provisoire pour le dépôt)

## Étape 2 (NON commencée — attend la validation de l'étape 1)
- Base de données, migrations, authentification, audit_logs
