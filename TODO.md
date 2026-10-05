# TODO

## Fait
- [x] Architecture v2 validée (2026-10-04)
- [x] Sections 40–41 du cahier des charges intégrées (PROJECT_STATE.md §17) et validées
- [x] Étape 1 écrite : structure, backend FastAPI (/health), tests, .gitignore, .env.example, devcontainer, guide téléphone (PROJECT_STATE.md §18)
- [x] Dépôt GitHub privé créé et projet envoyé dans Codespaces
- [x] `pytest` exécuté par l'utilisateur : 25 passed, 1 warning (2026-10-05)
- [x] Serveur démarré et `/health` appelé dans le navigateur : réponse JSON conforme
- [x] Projet enregistré et envoyé : `git` indique « working tree clean » et « up to date with origin/main »
- [x] `ruff check` relancé depuis `backend/` : signalé OK par l'utilisateur (sortie exacte non transmise)

## À confirmer pour clôturer l'étape 1
- [ ] `git ls-files | grep -E "\.env$|\.venv|\.zip$|__pycache__"` n'affiche rien (aucun fichier sensible suivi)
- [ ] `git log --oneline -3` montre le commit de l'étape 1 (message tel qu'enregistré)
- [ ] Sur github.com : `backend`, `docs`, `mobile` présents et `backend/.env` absent
- [ ] Appliquer dans le dépôt les fichiers de suivi mis à jour (PROJECT_STATE.md, TODO.md, CHANGELOG.md, docs/ETAPE1_GUIDE_TELEPHONE.md), puis commit et push
- [ ] Arrêter le codespace ; vérifier le quota gratuit Codespaces
- [ ] Validation de l'étape 1 par l'utilisateur

## Dette technique de l'étape 1 (à traiter avant ou pendant l'étape 2)
- [ ] Figer les versions dans requirements*.txt (pip freeze) — solution temporaire
- [ ] Choisir et figer la version de Python (3.14.2 constatée dans Codespaces, 3.12 visée par le devcontainer)
- [ ] Avertissement des tests : `httpx` déprécié au profit de `httpx2` dans `starlette.testclient`
- [ ] Tester le devcontainer (Rebuild Container) et vérifier l'image Python
- [ ] Documenter dans le guide que `ruff check .` se lance depuis `backend/`

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
