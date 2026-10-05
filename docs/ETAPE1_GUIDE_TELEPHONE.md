# Étape 1 — Guide pas à pas depuis un téléphone Android

Conseil : utilise Chrome et active « Site pour ordinateur » (menu ⋮ du navigateur). L'affichage de GitHub et de
Codespaces est bien plus complet. Les noms de boutons peuvent légèrement changer : si quelque chose ne
correspond pas, décris-moi ce que tu vois.

## A. Créer le dépôt privé sur GitHub

1. Va sur github.com et connecte-toi.
2. Touche le « + » en haut à droite, puis « New repository ».
3. Repository name : `atlas`
4. Visibilité : choisis **Private**.
5. Coche **Add a README file** (obligatoire : un dépôt vide ne peut pas ouvrir Codespaces).
6. Ne coche ni .gitignore ni licence (le projet a les siens).
7. Touche « Create repository ».

Résultat attendu : la page de ton dépôt `atlas` avec un cadenas « Private » et un fichier README.md.

## B. Ouvrir Codespaces (l'éditeur dans le navigateur)

1. Sur la page du dépôt, touche le bouton vert « Code ».
2. Onglet « Codespaces », puis « Create codespace on main ».
3. Attends 1 à 2 minutes.

Résultat attendu : un éditeur (VS Code) s'ouvre dans le navigateur, avec une zone de fichiers et un README.md.
Codespaces a un quota gratuit mensuel limité : vérifie-le dans GitHub → Settings → Billing, et pense à arrêter
le codespace quand tu as fini (partie H).

## C. Apporter les fichiers du projet

1. Télécharge `atlas-etape1.zip` depuis la conversation avec Claude.
2. Dans Codespaces, ouvre le panneau des fichiers (icône « Explorer » ou menu ≡).
3. Dans la zone vide du panneau, appuie longuement (ou clic droit) puis « Upload… » et choisis `atlas-etape1.zip`.
4. Ouvre un terminal : menu ≡ → Terminal → New Terminal.
5. Dans le terminal, tape (une ligne à la fois, Entrée après chaque) :

```bash
python3 -m zipfile -e atlas-etape1.zip .
rm atlas-etape1.zip
ls -a
```

Ce que fait chaque ligne : la première décompresse le projet dans le dossier courant, la deuxième supprime le zip,
la troisième liste les fichiers.
Résultat attendu : tu vois notamment `backend`, `docs`, `mobile`, `.gitignore`, `.devcontainer`, `PROJECT_STATE.md`.
Si le message « No such file » apparaît : le zip n'a pas été envoyé au bon endroit, recommence l'envoi (étape 3).

## D. Installer et lancer les tests

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Ce que fait chaque ligne : on entre dans le dossier du backend, on crée un environnement Python isolé, on
l'active (le terminal affiche `(.venv)` au début de la ligne), on installe les outils nécessaires, on lance les tests.
Résultat attendu : `pip` télécharge pendant environ une minute, puis `pytest` affiche une ligne finale
du type `25 passed` (suivi d'un avertissement `httpx` sans conséquence). Ce résultat a été constaté lors de
la première exécution dans Codespaces.
Si des tests échouent ou si une erreur apparaît : copie le texte de l'erreur et envoie-le-moi, ne modifie rien.
Si `pytest: command not found` ou `No module named 'fastapi'` : l'environnement n'est pas activé (ou tu n'es pas
dans `backend/`), refais `cd backend` puis `source .venv/bin/activate`.
Contrôle qualité optionnel : toujours depuis `backend/`, lance `ruff check . --output-format=concise`
(depuis la racine du dépôt, `ruff` peut signaler à tort des erreurs d'ordre d'imports).

## E. Démarrer le serveur et vérifier /health

```bash
cp .env.example .env
uvicorn app.main:app --port 8000 &
sleep 3
curl -i http://localhost:8000/health
kill %1
```

Ce que fait chaque ligne : copie la configuration d'exemple, démarre le serveur en arrière-plan, attend 3 secondes,
appelle la route /health, puis arrête le serveur.
Résultat attendu : une réponse `HTTP/1.1 200 OK`, un en-tête `x-request-id`, et un corps JSON contenant
`"status":"ok"`, `"service":"atlas-backend"`, `"version":"0.1.0"`, `"environment":"development"` et un `timestamp`.

## F. Vérifier qu'aucun secret ne partira sur GitHub

Toujours dans `backend/` :

```bash
git check-ignore -v .env
cd ..
git status --short
```

Résultat attendu : la première commande affiche une règle de `.gitignore` (donc `.env` est ignoré). La liste de
`git status` ne doit contenir ni `backend/.env`, ni `backend/.venv`. Si l'un des deux apparaît : n'enchaîne pas, dis-le-moi.

## G. Premier commit

Depuis la racine du projet (là où se trouve `README.md`) :

```bash
git add .
git status --short
git commit -m "Étape 1 : structure initiale et backend FastAPI minimal (/health)"
git push
```

Résultat attendu : `git status --short` liste uniquement des fichiers du projet (pas de `.env`, pas de `.venv`),
le commit affiche le nombre de fichiers créés, et `git push` se termine par `main -> main`.
Vérifie ensuite sur github.com/ton-compte/atlas que les dossiers `backend`, `docs`, `mobile` sont là
et que le fichier `backend/.env` n'y est pas.

## H. Arrêter Codespaces

Sur github.com/codespaces, touche « … » à côté de ton codespace puis « Stop codespace ».

## Note sur `.devcontainer`

Ce premier codespace a été créé avant que `.devcontainer/devcontainer.json` n'existe : cette configuration ne s'est
donc pas appliquée, d'où les commandes manuelles ci-dessus. Elle n'a pas pu être testée à ce jour. Lors d'une
prochaine ouverture (ou via « Rebuild Container »), elle devrait installer l'environnement automatiquement ;
si une erreur apparaît à ce moment-là, signale-la-moi.
