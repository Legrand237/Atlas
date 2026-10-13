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
- [x] Ajouter `*.zip` à .gitignore (fait en 2a)
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
- Étape 2 : hébergeur du backend ; stratégie de migrations (PostgreSQL de dev : Neon, validé le 2026-10-05)
- Étape 3 : fournisseur IA ; modèles par niveau de difficulté ; quotas de coûts
- Étape 5 : fournisseur de recherche Web
- Étape 6 : règles précises des niveaux de permission 0–5
- Étape 9 : technologie de sandbox (conteneur isolé) et où l'héberger
- Étape 12 : source de données de marché ; marchés ciblés
- Étape 13 : distribution Android (APK perso ou Google Play) selon l'usage de l'Accessibility Service
- Nom définitif du projet (« atlas » provisoire pour le dépôt)

## Étape 2a — connexion Neon (écrite, à vérifier par l'utilisateur)
- [x] Étape 2a validée et poussée (2026-10-06) : Neon connecté, db_check OK, 34 tests réussis
- [x] Fournisseur de dev validé : Neon (2026-10-05)
- [x] Code de connexion et 9 tests écrits ; `ruff` OK côté construction
- [ ] L'utilisateur crée le projet Neon, met `DATABASE_URL` dans `backend/.env` (guide `docs/ETAPE2A_GUIDE_NEON.md`)
- [ ] `python -m app.db_check` affiche « OK : connecté à PostgreSQL »
- [ ] `pytest` : 34 passed attendus (non vérifié) ; `ruff` OK
- [ ] Commit et push (sans `.env` ni `.zip`)
- [ ] Revérifier les limites gratuites de Neon avant tout usage réel

## Étape 2b — VÉRIFIÉE par l'utilisateur le 2026-10-13 (guide `docs/ETAPE2B_GUIDE.md`)
- [x] Alembic, tables users et audit_logs (ajout seul), record_event, tests écrits ; SQL vérifié sur PostgreSQL 16 local
- [x] `git pull`, alembic installé ; `backend/app/db.py` supprimé
- [x] `alembic upgrade head` réussi sur Neon
- [x] `pytest` : 75 passed (2026-10-13) ; `ruff` OK
- [ ] Réinitialiser le mot de passe Neon (il est apparu dans une trace de test) et mettre à jour `backend/.env`

## Étape 2c — tests vérifiés 2026-10-13 ; reste le compte et la validation (guide `docs/ETAPE2C_GUIDE.md`)
- [x] `git pull`, `pip install -r requirements-dev.txt`
- [ ] Générer `JWT_SECRET_KEY` dans `backend/.env`
- [x] `alembic upgrade head` : 0001 -> 0002 appliqué sur Neon
- [ ] `python -m app.manage create-user ...` : à lancer SEUL (la 1re tentative a été interrompue, aucun compte créé)
- [x] `pytest` : 121 passed, 1 warning ; `ruff` : All checks passed
- [x] Décisions de conception validées par l'utilisateur le 2026-10-13 (pas d'inscription publique, JWT 60 min sans refresh token, 5 échecs/15 min)

## Après 2c (idées notées)
- Authentification : colonne de mot de passe (migration 0002), hachage, tokens à durée limitée, routes ; premiers événements d'audit réels
- Plus tard : extension pgvector (étape 8), rôle de base INSERT-seul pour l'audit (production), permission_grants, tasks (clé étrangère de audit_logs.task_id)
- Figer les versions des dépendances (dette) pendant 2b

## Étape 3 — en attente du choix de l'utilisateur
- [x] Comparaison des fournisseurs : `docs/ETAPE3_COMPARAISON_IA.md`
- [x] Option A choisie par l'utilisateur le 2026-10-13 : Google Gemini (palier gratuit pour développer, payant plus tard). Règle : aucune donnée personnelle réelle envoyée tant que le palier est gratuit
- [ ] Valider le plan détaillé de l'étape 3 (aucun code avant)
