# Étape 2a — Connecter Atlas à une base PostgreSQL (Neon)

Cette étape ne crée AUCUNE table et AUCUNE route nouvelle. Elle ajoute seulement : la lecture de
l'adresse de la base (`DATABASE_URL`), un moteur SQLAlchemy, et une commande qui vérifie la connexion.
Les tables (utilisateurs, audit_logs) et les migrations arrivent à l'étape 2b.

Neon est le fournisseur validé par toi le 2026-10-05 pour le développement (offre gratuite, sans carte
bancaire d'après la documentation de Neon). Les limites gratuites peuvent changer : vérifie-les sur
neon.com avant de t'appuyer dessus.

## A. Créer le projet Neon (sur neon.com)

1. Va sur neon.com, touche « Sign up » et crée un compte (e-mail, GitHub ou Google).
   Si Neon te demande une carte bancaire ou un paiement : ARRÊTE-TOI et dis-le-moi, ne paie rien.
2. Crée un projet. Nom : `atlas`. Garde la version de PostgreSQL proposée par défaut.
   Région : choisis la plus proche de toi dans la liste (le choix n'est pas définitif pour un projet de test).
3. Quand le projet est créé, touche le bouton « Connect ».
4. Dans la fenêtre : désactive l'option « Connection pooling » (on veut la connexion directe, plus simple
   pour les migrations). Le nom d'hôte ne doit alors PAS contenir `-pooler`.
5. Copie l'adresse qui commence par `postgresql://`. Elle contient ton mot de passe.

RÈGLE ABSOLUE : cette adresse est un secret. Ne l'envoie à personne, ne la colle pas dans cette
conversation, ne la mets dans aucun fichier sauf `backend/.env`. Si tu l'as partagée par erreur,
dis-le-moi : on réinitialisera le mot de passe dans Neon.

## B. Mettre l'adresse dans Codespaces (fichier ignoré par Git)

1. Ouvre ton codespace Atlas et un terminal.
2. Récupère la nouvelle version du projet : envoie `atlas-etape2a.zip` dans l'Explorateur
   (clic droit → Upload…), puis, à la racine du dépôt :

```bash
python3 -m zipfile -e atlas-etape2a.zip .
rm atlas-etape2a.zip
```

3. Ouvre le fichier `backend/.env` (il existe depuis l'étape 1 ; sinon : `cp backend/.env.example backend/.env`).
4. Sur la ligne `DATABASE_URL=`, colle l'adresse juste après le signe `=`, sans espace ni guillemets.
5. Enregistre le fichier (Ctrl+S).
6. Vérifie qu'il est ignoré par Git : `git check-ignore -v backend/.env` doit afficher une règle.

## C. Installer les nouvelles dépendances et vérifier la connexion

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.db_check
```

Résultat attendu : `OK : connecté à PostgreSQL (version ...)`.
Si tu vois `ECHEC : DATABASE_URL n'est pas définie` : l'adresse n'est pas dans `backend/.env` (étape B).
Si tu vois `ECHEC : Connexion impossible (...)` : copie ce message et envoie-le-moi (il ne contient jamais
ton mot de passe). Causes possibles : adresse mal copiée, projet Neon en cours de réveil (réessaie
après quelques secondes).

## D. Lancer les tests et le contrôle qualité

```bash
pytest
ruff check . --output-format=concise
```

Résultat attendu (NON encore vérifié : à constater chez toi) : 34 tests réussis (25 de l'étape 1 + 9
nouveaux) ; `ruff` : « All checks passed! ». Les tests ne se connectent pas à ta vraie base Neon : un test
utilise une base SQLite locale (uniquement pour la logique de vérification) et un autre tente une
connexion volontairement impossible pour vérifier qu'aucun mot de passe n'apparaît dans l'erreur.

## E. Enregistrer et envoyer

```bash
cd ..
git add .
git status --short
```

Contrôle : la liste ne doit contenir NI `backend/.env`, NI `backend/.venv`, NI aucun fichier `.zip`.
Si l'un d'eux apparaît : n'enchaîne pas, dis-le-moi. Sinon :

```bash
git commit -m "etape 2a: connexion PostgreSQL (Neon) et verification"
git push
```

Puis arrête le codespace (github.com/codespaces → « … » → Stop codespace).

## Ce qui n'est PAS fait à l'étape 2a
Tables, migrations (Alembic), utilisateurs, authentification, audit_logs, extension pgvector.
