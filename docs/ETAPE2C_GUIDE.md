# Étape 2c — Authentification (connexion, token, audit)

Ce que cette étape ajoute : la colonne `users.password_hash` (migration `0002`), la connexion `POST /auth/login`
(token à durée limitée), le profil `GET /auth/me`, la limitation des essais, l'audit de chaque tentative et la
commande qui crée un compte. Il n'y a PAS d'inscription publique : un agent personnel ne doit pas accepter
d'inconnus. Les comptes se créent avec la commande ci-dessous.

## A. Mettre à jour le code (Codespaces)

```bash
cd /workspaces/Atlas
git pull
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## B. Créer la clé secrète des tokens (jamais dans Git)

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie la ligne affichée. Ouvre `backend/.env` et, sur la ligne `JWT_SECRET_KEY=` (ajoute-la si elle manque),
colle-la juste après le signe `=`, sans espace ni guillemets. Enregistre (Ctrl+S).
Cette clé est un secret : ne l'envoie à personne et ne la mets dans aucun autre fichier.

## C. Appliquer la migration 0002 sur Neon

```bash
alembic upgrade head
alembic current
```

Attendu : `Running upgrade 0001 -> 0002` puis `0002 (head)`.

## D. Créer ton compte

```bash
python -m app.manage create-user ton@email.com --name "Ton nom"
```

Le mot de passe est demandé au clavier (12 caractères minimum, il ne s'affiche pas). Attendu : `OK : compte créé pour ...`.

## E. Tests et contrôle qualité

```bash
pytest
ruff check . --output-format=concise
```

Résultat attendu (NON vérifié par l'auteur) : 121 tests réussis, 0 skipped (75 déjà là + 46 nouveaux).
Pour lire les erreurs sans risque : envoie seulement les dernières lignes, relues (aucun mot de passe ni clé).

## F. Essayer pour de vrai (facultatif)

```bash
uvicorn app.main:app --port 8000 &
sleep 3
curl -s -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"ton@email.com","password":"TON_MOT_DE_PASSE"}'
kill %1
```

Attendu : un JSON avec `access_token`, `token_type` et `expires_at`. N'envoie JAMAIS ce token ni le mot de passe dans le chat.

## Règles de sécurité de cette étape
- Mots de passe : empreinte argon2 seulement ; 12 à 128 caractères.
- Réponse identique pour « compte inconnu » et « mauvais mot de passe » (même durée de calcul).
- 5 échecs en 15 minutes (réglable) bloquent le compte 15 minutes : réponse 429.
- Chaque tentative est écrite dans `audit_logs` (action `login`, identifiant de corrélation = `X-Request-ID`), sans mot de passe ni e-mail.
- Token HS256, durée 60 minutes (`SESSION_DURATION_MINUTES`), clé `JWT_SECRET_KEY` d'au moins 32 caractères.
  Sans cette clé, `/auth/login` répond 503.

## Ce qui n'est PAS fait à l'étape 2c
Refresh token et déconnexion côté serveur (le token expire seul), changement/oubli de mot de passe, double
authentification, limitation globale des requêtes par adresse IP, inscription publique (volontairement absente).
