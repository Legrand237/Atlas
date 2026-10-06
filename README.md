# Atlas

Agent IA personnel (Android + backend cloud). Projet en construction, étape par étape.
Documents de référence : `PROJECT_STATE.md` (architecture et état), `TODO.md`, `CHANGELOG.md`.

## État actuel (étape 1)

Existe réellement :
- un backend FastAPI minimal (`backend/`) avec une route `GET /health` ;
- un identifiant de requête (`X-Request-ID`) sur chaque réponse ;
- une gestion d'erreur qui ne révèle pas les détails internes ;
- une configuration lue depuis l'environnement (`backend/app/config.py`) ;
- des tests automatisés (`backend/tests/`).

Étape 2a (écrite, à vérifier) : configuration `DATABASE_URL` et commande `python -m app.db_check` pour tester la connexion à PostgreSQL (Neon). Voir `docs/ETAPE2A_GUIDE_NEON.md`.

N'existe pas encore : agent, tables, authentification, permissions, audit, application mobile.
`/health` indique seulement que le processus répond (aucune base ni service externe à tester pour l'instant).

## Lancer le backend

Depuis le dossier `backend/` :

```bash
python3 -m venv .venv                      # crée un environnement Python isolé
source .venv/bin/activate                  # l'active (le terminal affiche (.venv))
pip install -r requirements-dev.txt        # installe les dépendances
cp .env.example .env                       # copie la configuration d'exemple
uvicorn app.main:app --reload              # démarre le serveur sur le port 8000
```

Dans un second terminal : `curl http://localhost:8000/health`

## Lancer les tests

Depuis `backend/`, environnement activé : `pytest`

## Secrets

Aucune clé, aucun mot de passe, aucun token dans Git. La configuration locale va dans `backend/.env`,
ignoré par Git. Seul `backend/.env.example` (sans secret) est versionné.
