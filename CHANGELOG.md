# CHANGELOG

## 2026-10-06 — Étape 2b : migrations, users, audit_logs (tests Python NON exécutés)
- Étape 2a validée et poussée par l'utilisateur (Neon connecté, 34 tests réussis).
- Ajout : Alembic (`alembic.ini`, `app/db/alembic/`), migration `0001` (tables `users` et `audit_logs`), modèles SQLAlchemy, `record_event` / `validate_event`, déclencheurs PostgreSQL « ajout seul » sur `audit_logs`, `session_scope`, guide `docs/ETAPE2B_GUIDE.md`.
- Modification : `app/db.py` devient le paquet `app/db/` (ancien fichier à supprimer) ; `request_id.py` gagne `is_valid_request_id` ; `test_db.py` adapté ; `alembic` ajouté à `requirements.txt`.
- Tests écrits : 37 (26 sans base, 11 sur la vraie base dans un schéma temporaire). Attendu : 71 au total avant la correction ci-dessous (non vérifié).
- Vérifié côté construction : `compileall`, `ruff`, et le SQL de la migration sur PostgreSQL 16.15 local (17 scénarios, retour arrière). Python/Alembic non exécutés.
- Correction des tests de migration : connexion directe Neon (retrait de `-pooler` ou `DATABASE_URL_DIRECT`), garde-fou `current_schema()`, 4 tests de conversion d'adresse (attendu : 75 au total, non vérifié).
- Non fait : mot de passe et authentification (2c), autres tables, pgvector.

## 2026-10-05 — Étape 2a : connexion PostgreSQL (Neon), NON vérifiée par exécution
- Décision utilisateur : Neon (gratuit) comme base de développement.
- Ajout : `DATABASE_URL` (secret) dans la configuration, `app/db.py` (moteur SQLAlchemy, vérification de connexion), commande `python -m app.db_check`, 9 tests (`tests/test_db.py`), guide `docs/ETAPE2A_GUIDE_NEON.md`, règle `*.zip` dans `.gitignore`.
- Vérifié côté construction : `compileall` et `ruff` seulement. Tests et connexion réelle à Neon à exécuter par l'utilisateur.
- Non fait : tables, migrations, authentification, audit_logs.

## 2026-10-04 — Étape 1 : structure initiale et backend minimal (0.1.0)
- Ajout : backend FastAPI (`backend/app`), route réelle `GET /health`, configuration par variables d'environnement, middleware `X-Request-ID`, gestionnaire d'erreur 500 sans fuite de détails.
- Ajout : 25 tests pytest (health, configuration, hygiène des secrets) — exécutés par l'utilisateur dans Codespaces le 2026-10-05 : 25 passed, 1 warning (PyPI inaccessible dans l'environnement de construction).
- Ajout : `.gitignore`, `backend/.env.example` (sans secret), `.devcontainer/devcontainer.json` (non testé), `README.md`, `docs/ETAPE1_GUIDE_TELEPHONE.md`, dossiers `mobile/` et `docs/`.
- Vérifié manuellement : compilation du code, 8 contrôles du middleware (ASGI), `.gitignore` testé avec de faux fichiers sensibles.
- Vérifié chez l'utilisateur (2026-10-05) : `/health` répond dans le navigateur via Codespaces ; dépôt à jour avec `origin/main` ; `ruff` relancé depuis `backend/` signalé OK.
- Dette : requirements non figés (solution temporaire), devcontainer non testé, avertissement httpx/httpx2, version de Python à choisir (3.14.2 constatée, 3.12 visée).

## 2026-10-04 — Cahier des charges sections 40–41 intégrées
- PROJECT_STATE.md §17 : 60 capacités (section 40) et principes 41.1–41.18 intégrés.
- Boucle : étape AUTHORIZE ajoutée ; audit : champs tâche, décision d'autorisation, identifiant de corrélation ; compétences : rollback et compatibilité.
- TODO.md : exigences issues des sections 40–41 ajoutées. Aucun code écrit.

## 2026-10-04 — Étape 0 (v2, validée)
- Architecture v2 validée par l'utilisateur.
- Correction : référence de la sandbox (§12 → §14) ; statuts mis à jour ; décisions techniques ajoutées dans TODO.md ; plan de l'étape 1 préparé (non implémenté).

## 2026-10-04 — Étape 0 (v2)
- Ajout : Policy/Permission Engine déterministe, sandbox d'exécution, Skill Sandbox (DRAFT→ACTIVE), vérification des résultats, human-in-the-loop, kill switch, audit en ajout seul.
- Ajout : séparation noyau / modules spécialisés (dossier modules/), architecture temps réel event-driven.
- Mise à jour : arborescence, roadmap (sandbox + compétences à l'étape 9), risques, décisions restantes.
- Aucun fournisseur choisi : prix et disponibilité à vérifier avant tout paiement.

## 2026-10-04 — Étape 0 (v1)
- Architecture, arborescence, stack, risques et roadmap définis (aucun code).
