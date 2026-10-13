# Étape 3 — Passerelle IA (Google Gemini) : guide de vérification

Ce que fait cette étape : le backend sait envoyer une conversation à Gemini et rendre la réponse, avec un niveau
(simple / medium / hard) qui choisit le modèle, des plafonds par jour et un audit de chaque appel.
Rien n'est payant : tu utilises le palier gratuit de Google.

**Règle à respecter : au palier gratuit, Google réutilise ce que tu envoies. N'envoie AUCUNE donnée personnelle réelle** (noms, numéros, mots de passe, documents). Que des phrases de test.

Toutes les commandes se lancent dans le terminal de Codespaces, dossier `backend/`, environnement virtuel activé.

## 1. Récupérer le code et lancer les tests
```
cd /workspaces/Atlas && git pull
cd backend
pip install -r requirements-dev.txt
pytest
ruff check .
```
Résultat attendu : `175 passed` (121 avant + 54 nouveaux) et `All checks passed!`.
Colle-moi la dernière ligne de `pytest` (jamais plus : une trace longue peut contenir des secrets).

## 2. Créer ta clé Gemini (gratuite, sans carte)
1. Va sur https://aistudio.google.com/apikey et connecte-toi avec ton compte Google.
2. Clique sur « Create API key » et copie la clé.
3. Dans Codespaces, ouvre le fichier `backend/.env` et ajoute la ligne `GEMINI_API_KEY=` suivie de ta clé. Enregistre (Ctrl+S).
4. **Ne colle jamais cette clé dans le chat, ni dans un fichier suivi par Git.** `backend/.env` est ignoré par Git.

## 3. Choisir les modèles de ton compte
```
python -m app.llm_check models
```
La commande liste les modèles que TA clé peut utiliser. Choisis-en trois : un petit et rapide pour `simple`, un intermédiaire pour `medium`, un plus puissant pour `hard` (au palier gratuit, certains modèles ne sont pas disponibles : la liste fait foi). Les noms de modèles ne sont pas secrets : tu peux me coller cette liste.
Ajoute dans `backend/.env` (exemple de forme, remplace par les noms de la liste, sans le préfixe `models/`) :
```
LLM_MODEL_SIMPLE=nom-du-modele-simple
LLM_MODEL_MEDIUM=nom-du-modele-moyen
LLM_MODEL_HARD=nom-du-modele-puissant
```

## 4. Premier appel réel
```
python -m app.llm_check ping simple
```
Attendu : `Modèle : …`, `Réponse : OK`, puis les nombres de jetons. Si une erreur s'affiche, copie-moi seulement la ligne `Échec (code) : …` (elle ne contient pas la clé).
Codes possibles : `llm_rejected` (clé ou modèle refusé), `llm_rate_limited` (quota gratuit dépassé, attends), `llm_unavailable` / `llm_timeout` (réseau ou Google), `llm_blocked` (filtres de sécurité).

## 5. Essayer la route /llm/chat (serveur + connexion)
Terminal 1 : `uvicorn app.main:app --reload`
Terminal 2 (le compte doit exister : `python -m app.manage create-user ton@email.com --name "Ton nom"`, lancée seule) :
```
read -s -p "Mot de passe : " PW; echo
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d "{\"email\":\"ton@email.com\",\"password\":\"$PW\"}" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -X POST http://localhost:8000/llm/chat -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"Dis bonjour en une phrase."}],"tier":"simple"}'
```
Attendu : un JSON avec `text`, `model`, `tier`, `usage`. Une seconde requête avec `-H` sans `Authorization` doit répondre 401.

## Plafonds et audit
- Par utilisateur, sur 24 h glissantes : 200 requêtes et 200 000 jetons par défaut (`LLM_DAILY_REQUEST_LIMIT`, `LLM_DAILY_TOKEN_LIMIT`). Au-delà : réponse 429, appel refusé et audité. Le plafond de jetons est vérifié avant l'appel : un appel peut le dépasser un peu.
- Réponse limitée à 1 024 jetons par défaut (`LLM_MAX_OUTPUT_TOKENS`).
- Chaque appel ajoute une ligne `llm_chat` à `audit_logs` : modèle, niveau, nombre de jetons, durée, résultat. Jamais le texte envoyé, la réponse ni la clé.

## Limites connues
- L'adaptateur est écrit d'après la documentation de Google et testé avec un transport HTTP de test. Seul `python -m app.llm_check ping simple` prouve que Google répond comme prévu.
- Pas encore de flux de réponse en direct (streaming), d'appels d'outils ni de boucle d'agent : étapes suivantes.
- Le plafond de « coût » est un plafond de requêtes et de jetons ; il n'y a pas de calcul en euros tant que tu restes au palier gratuit.
