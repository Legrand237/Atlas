# Étape 2b — Migrations Alembic, tables `users` et `audit_logs`

Ce que cette étape ajoute : l'outil de migrations (Alembic), la première migration `0001`, deux tables
(`users`, `audit_logs`) et une fonction `record_event` pour écrire dans l'audit.
Ce qu'elle n'ajoute PAS : mot de passe, connexion, routes d'authentification (étape 2c), autres tables.

Le journal `audit_logs` est « en ajout seul » : PostgreSQL lui-même refuse UPDATE, DELETE et TRUNCATE
(déclencheurs créés par la migration). Limite : le propriétaire de la base pourrait supprimer ces déclencheurs ;
une protection plus forte (un rôle de base qui n'a que le droit d'écrire) viendra avec la mise en production.

## A. Récupérer les fichiers (dans Codespaces, à la racine du dépôt)

Les fichiers de l'étape 2b sont directement dans le dépôt GitHub (plus de zip à envoyer, et `backend/app/db.py`
est déjà remplacé par le dossier `backend/app/db/`). Dans le terminal :

```bash
git pull
```

## B. Installer Alembic

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## C. Créer les tables dans ta base Neon

```bash
alembic upgrade head
alembic current
```

Résultat attendu : des lignes `Running upgrade  -> 0001, ...` puis, avec `alembic current`, `0001 (head)`.
Si tu vois `DatabaseNotConfigured` : `DATABASE_URL` est absente de `backend/.env`.
Pour vérifier dans Neon : console Neon → ton projet → « Tables » : `users`, `audit_logs`, `alembic_version`.

## D. Tests et contrôle qualité

```bash
pytest
ruff check . --output-format=concise
```

Résultat attendu (NON vérifié par l'auteur : à constater chez toi) : 75 tests réussis, 0 skipped
(34 déjà là + 41 nouveaux). Les 11 tests « sur base réelle » créent un schéma temporaire dans ta base Neon
(`test_atlas_...`), y appliquent les migrations, puis le suppriment : ta table `public` n'est pas touchée.
Si ces 11 tests apparaissent « skipped » : `DATABASE_URL` n'est pas lue (lance `pytest` depuis `backend/`).
Les tests utilisent toujours une connexion DIRECTE : si ton adresse est celle du « pooler » (hôte contenant
`-pooler`), le suffixe est retiré automatiquement. Pour imposer une adresse directe précise, ajoute dans
`backend/.env` une ligne `DATABASE_URL_DIRECT=` suivie de cette adresse (ne l'envoie jamais dans le chat).

## E. Vérifier ce qui sera enregistré, puis commit

```bash
cd ..
git status --short
```

Attendu : rien (dossier de travail propre), puisque tout est déjà enregistré. Si tu as modifié quelque chose, ne
l'enchaîne pas : dis-le-moi.

## Ce qui n'est PAS fait à l'étape 2b
Colonne de mot de passe, hachage, connexion, tokens (2c) ; tables conversations, tasks, memories, etc. ;
extension pgvector ; écriture automatique d'audit depuis les requêtes HTTP (aucune route n'écrit encore dans l'audit).
