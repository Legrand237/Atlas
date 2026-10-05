# PROJECT_STATE.md — Agent IA personnel (nom de code : « Atlas »)

Dernière mise à jour : 2026-10-05 — Étape 1 livrée et vérifiée par exécution chez l'utilisateur (Codespaces) : 25 tests réussis, /health répond. Quelques vérifications restent à confirmer (voir §18). Cahier des charges et architecture v2 validés par l'utilisateur. Étape 2 non commencée : attend la validation de l'utilisateur.

Règles du projet : pas de faux services, pas de mocks présentés comme fonctionnels, pas de prototype jetable ; application production-ready construite progressivement ; aucun service payant ni clé API avant décision explicite.

## 1. Vision
Application Android (Flutter) + backend cloud (API) + noyau d'agent avec mémoire, compétences versionnées, outils, permissions déterministes, sandbox, modules spécialisés (Trading, Data Science, Android, Jeux). L'agent apprend de nouvelles compétences et résout des problèmes variés (outils, mémoire, recherche, analyse, expérimentation, vérification), tout en restant contrôlé, auditable et sécurisé.

Principe fondamental : INFORMATION ≠ DÉCISION ≠ ACTION.

## 2. Ce qui tourne où
| Partie | Où | Pourquoi |
|---|---|---|
| Interface, voix (STT/TTS), notifications | Téléphone Android | UI native |
| Services Android (Kotlin, Accessibility) | Téléphone Android | Seul endroit possible |
| Agent Core, Policy Engine, outils, mémoire, compétences | Serveur cloud | Clés secrètes, tâches longues |
| Sandbox d'exécution de code | Serveur cloud (conteneur isolé, séparé du backend) | Sécurité |
| Event Bus / temps réel | Serveur cloud | Flux continus |
| Base de données | Cloud (PostgreSQL + pgvector) | Persistance, mémoire sémantique |
| Modèles IA | API externe | Impossible en local sur téléphone |

## 3. Architecture de sécurité (décisions v2)

### 3.1 Orchestrateur de sécurité (Policy / Permission Engine)
Le LLM ne décide jamais seul. Il propose, du code déterministe décide.
```
Utilisateur → Agent Core → LLM → proposition d'action
  → Policy/Permission Engine (code déterministe)
  → autoriser / demander confirmation / refuser
  → Tool Executor → résultat → Agent
```
Aucune réponse du modèle ne peut contourner les permissions. Toute exécution d'outil passe par le Policy Engine, sans exception.

### 3.2 Sandbox d'exécution
Tout code généré par l'agent s'exécute dans un environnement isolé, jamais dans le processus du backend :
- limites CPU et mémoire, timeout
- système de fichiers isolé
- réseau désactivé par défaut
- liste blanche de bibliothèques
- environnement détruit après exécution
- journalisation de chaque exécution
```
Agent → Sandbox isolée → exécution limitée → résultat → Agent
```

### 3.3 Skill Sandbox
Cycle de vie d'une compétence :
`DRAFT → TEST → EVALUATE → APPROVE → ACTIVE → IMPROVE → VERSION suivante`
Chaque compétence a un niveau de confiance et un historique de versions. Une compétence DRAFT ou non approuvée ne s'exécute que dans la sandbox.

### 3.4 Vérification des résultats
Un retour d'outil n'est pas un succès. Chaîne obligatoire :
`ACTION → OBSERVATION → VALIDATION → SUCCESS / FAILURE → RECOVERY`

### 3.5 Human-in-the-loop
Pour les actions sensibles, l'agent demande confirmation : « Je suis prêt à exécuter cette action. Elle nécessite la permission X. Autoriser ? » Choix de l'utilisateur :
- accepter / refuser
- autoriser une seule fois
- autoriser pour une durée
- autoriser définitivement (uniquement si le niveau de risque le permet ; interdit aux niveaux 4 et 5)

### 3.6 Kill switch
Arrêt d'urgence global : stoppe immédiatement les actions de l'agent, les tâches longues, les boucles et toute intégration financière future. Vérifié par le Policy Engine avant chaque action et par la boucle à chaque itération.

### 3.7 Audit
Chaque action importante est tracée : utilisateur, agent, outil, action, permission, résultat, timestamp, erreur éventuelle, tâche, décision d'autorisation, identifiant de corrélation (41.15). Table `audit_logs` en ajout seul (pas de modification ni suppression par l'agent).

## 4. Agent général et modules spécialisés
```
                    ATLAS
                      │
                 AGENT CORE
   (boucle, Policy Engine, Tool Registry, Memory, Skills)
        ┌─────────┬───┴─────┬──────────┐
     GÉNÉRAL   Trading   Android   Data Science / Jeux
```
Le noyau est indépendant des modules. Les modules utilisent uniquement les interfaces communes (Agent Core, Tool Registry, Memory, Permission Engine). Le trading ne modifie jamais le fonctionnement général de l'agent. Un module = un dossier + des outils enregistrés + des compétences.

## 5. Temps réel (event-driven)
```
Data Source → Event Stream (WebSocket si pertinent) → Event Processor
  → Cache → Agent / Event Rules → Analysis → Alert / Action
```
Prévu : reconnexion automatique, déduplication, timestamps, gestion des données manquantes, monitoring. Les « Action » passent par le Policy Engine.

## 6. Boucle autonome
OBSERVE → THINK → PLAN → AUTHORIZE → ACT → OBSERVE → VERIFY → REFLECT → LEARN (l'étape AUTHORIZE ajoutée par la section 40, item 59), avec : nombre maximal d'itérations, timeout, budget, arrêt manuel, arrêt sur erreur, arrêt sur action sensible, kill switch.

## 7. Technologies (choix proposés)
- Mobile : Flutter/Dart, Provider, dio, flutter_secure_storage, speech_to_text, flutter_tts
- Android natif : Kotlin (MethodChannel vers Flutter)
- Backend : Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic
- Base de données : PostgreSQL + pgvector
- Tâches longues : asyncio + table `tasks` d'abord, Redis + worker ensuite
- Event Bus : interne (asyncio) d'abord, Redis Streams ensuite si nécessaire
- Sandbox : conteneur isolé (technologie à choisir, voir §14)
- Tests : pytest, flutter_test
- Auth : JWT court + refresh token, argon2
- Secrets : variables d'environnement côté serveur uniquement
- IA : LLM Gateway abstraite, fournisseur remplaçable, routage par difficulté

## 8. Arborescence finale
```
atlas/
├── PROJECT_STATE.md  CHANGELOG.md  TODO.md
├── backend/
│   ├── app/
│   │   ├── main.py  config.py
│   │   ├── api/            # auth, chat, memory, skills, tools, permissions, tasks, audit, trading, killswitch
│   │   ├── core/           # sécurité, rate limiting, erreurs
│   │   ├── db/             # models, session, alembic/
│   │   ├── agent/          # loop, intent, planner, memory_manager, tool_selector,
│   │   │                   # executor, observer, evaluator (validation), recovery,
│   │   │                   # task_manager, audit_logger
│   │   ├── policy/         # permission_engine, levels, confirmations, killswitch (déterministe)
│   │   ├── sandbox/        # runner, limits, allowlist, cleanup
│   │   ├── llm/            # gateway, providers, router, cache, cost_tracker
│   │   ├── tools/          # base, registry, web, calculator, python_sandbox, files, images, documents, db
│   │   ├── memory/         # short_term, long_term, semantic, episodic, procedural
│   │   ├── skills/         # models, lifecycle (DRAFT→ACTIVE), evaluation, versions
│   │   ├── events/         # bus, streams, processor, cache, rules, monitoring
│   │   └── modules/        # modules spécialisés, indépendants du noyau
│   │       ├── trading/    # data, indicators, backtest, paper, risk, broker (interface, désactivé)
│   │       ├── android/    # côté serveur : commandes vers l'app
│   │       ├── datascience/
│   │       └── games/
│   ├── tests/
│   └── requirements.txt
├── mobile/
│   ├── lib/
│   │   ├── main.dart       # minimal
│   │   ├── presentation/   # 12 écrans + widgets
│   │   ├── state/          # Providers
│   │   ├── domain/  data/  services/  config/
│   ├── android/app/src/main/kotlin/   # services natifs
│   └── test/
└── docs/
```

## 9. Modèle de données
users, conversations, messages, memories, skills, skill_versions, tasks, tool_calls, permissions, audit_logs, experiments, market_data, trading_strategies, backtests, paper_positions. Tables à ajouter en leur temps : permission_grants (une fois / durée / définitif), events, sandbox_runs. Migrations via Alembic.

## 10. Permissions
Niveaux 0–5. Chaque outil déclare son niveau ; le Policy Engine tranche. Niveau 5 : jamais exécuté. Trading réel : désactivé par défaut, aucun retrait possible, limites de montant et de perte, confirmation, kill switch.

## 11. Services externes (à vérifier avant toute intégration : prix, limites, disponibilité Cameroun)
| Besoin | Candidats | Statut |
|---|---|---|
| Modèle IA | à comparer | NON CHOISI |
| Hébergement backend | Render, Railway, Fly.io | NON CHOISI |
| Base de données | Neon, Supabase | NON CHOISI |
| Recherche Web | Tavily, Brave Search API | NON CHOISI |
| Données crypto | Binance API publique, CoinGecko | NON CHOISI |
| Données bourse | Alpha Vantage, Twelve Data | NON CHOISI |
| Dev depuis téléphone | GitHub Codespaces, Termux | à vérifier |
| Compilation APK | GitHub Actions | à vérifier |

Règle : aucun service n'est supposé gratuit ; aucun paiement avant d'avoir vérifié les conditions actuelles.

## 12. Coûts potentiels
Modèle IA (poste principal), hébergement, base de données, recherche Web, données de marché, sandbox. Contrôle : cache, quotas, petit modèle pour tâches simples, suivi de consommation. Objectif : construire d'abord l'architecture et les premières étapes sans dépense importante.

## 13. Risques
1. Dev Flutter/Android sans ordinateur : Codespaces + GitHub Actions.
2. Sandbox : mal isolée, elle devient une faille ; choix technique critique et coûteux à héberger.
3. Accessibility Service : règles Google Play strictes ; usage personnel (APK) plus simple.
4. Boucle autonome : coûts et dérives ; limites obligatoires.
5. Compétences auto-générées non fiables : Skill Sandbox.
6. Trading / jeux d'argent : aucune prédiction garantie ; limites des backtests explicites.
7. Policy Engine contourné par un bug : tests dédiés obligatoires.
8. Anti-triche des jeux : on ne contourne rien.
9. Temps réel : coûts de données et complexité ; en dernier.

## 14. Décisions qui restent à prendre
- Fournisseur IA (après vérification des prix et de la disponibilité)
- Hébergeur backend + base PostgreSQL
- Technologie de la sandbox
- Source des données de marché
- Nom définitif du projet (« Atlas » provisoire)
- (Résolu 2026-10-04) Sections 40–41 reçues et intégrées en §17 ; validation finale du cahier des charges en attente

## 15. Roadmap
- Étape 1 : environnement (GitHub, Codespaces, dépôt, backend minimal + test) — LIVRÉE et vérifiée dans Codespaces (§18), en attente de validation par l'utilisateur
- Étape 2 : backend, base, migrations, authentification
- Étape 3 : LLM Gateway + chat + suivi des coûts
- Étape 4 : app Flutter (connexion + chat)
- Étape 5 : outils (base, registre, calculatrice, web) + audit
- Étape 6 : Policy Engine, permissions, human-in-the-loop, kill switch
- Étape 7 : Agent Core, boucle contrôlée, validation des résultats
- Étape 8 : mémoire
- Étape 9 : sandbox + compétences (Skill Sandbox)
- Étape 10 : les 12 écrans
- Étape 11 : voix
- Étape 12 : module Trading (indicateurs, backtesting, paper trading)
- Étape 13 : Android natif
- Étape 14 : événements temps réel
- Étape 15 : jeux, statistiques, durcissement sécurité, tests complets

## 16. État
Terminé : planification, architecture v2 et cahier des charges validés, étape 1 écrite (voir §18). Tests et /health vérifiés dans Codespaces. En attente : confirmation des dernières vérifications (§18) et validation de l'étape 1 par l'utilisateur. Variables utilisées à l'étape 1 : ENVIRONMENT, LOG_LEVEL (aucun secret). Variables prévues plus tard : DATABASE_URL, JWT_SECRET, LLM_API_KEY, SEARCH_API_KEY, MARKET_DATA_API_KEY. Commandes : voir §18.

## 17. Cahier des charges — sections 40 et 41 (intégrées, exigences fonctionnelles)
Cadre : aucune capacité n'est une promesse irréaliste ; chacune respecte permissions Android, API disponibles, conditions des services externes, limites techniques et règles de sécurité.

### Section 40 — Capacités à terme (60 items, regroupés ; numéros d'origine entre parenthèses)
- Compréhension et résolution : demandes complexes en langage naturel (1), décomposition (2), recherche Web et sources autorisées (3), choix d'outils (4), planification avant exécution (5).
- Cycle d'exécution : exécuter les actions autorisées (6), observer (7), vérifier l'objectif (8), détecter les erreurs et récupérer (9). Cycle complet : OBSERVE → THINK → PLAN → AUTHORIZE → ACT → OBSERVE → VERIFY → REFLECT → LEARN (59).
- Autorisation et sécurité : confirmation utilisateur (10), refus automatique des actions interdites ou dangereuses (11), historique et audit (12, 55), séparation information / décision / action (26), expérimentation sans prendre une hypothèse pour une vérité (25), Policy Engine pour les actions sensibles (51), niveau de permission déclaré par chaque outil (52), l'utilisateur accepte / refuse / limite (53), kill switch global (54), sortie du modèle jamais traitée comme instruction de sécurité ou autorisation (57), « le LLM propose ; le Policy Engine décide ; le Tool Executor exécute » (58).
- Mémoire : court terme (13), long terme (14), sémantique (15), épisodique (16), procédurale (17).
- Compétences : apprentissage par instructions, documentation, exemples, expérimentations contrôlées (18), test avant activation (19), évaluation (20), versionnage avec amélioration ET retour à une version précédente (21), réutilisation automatique quand une tâche correspond (22), plans d'expérimentation et comparaison d'approches (23), conservation des résultats utiles (24), Skill Sandbox avant activation (56).
- Analyse : calcul et données (27), fichiers, documents, tableaux, images (28), code en sandbox (29), rapports et tableaux structurés (30).
- Temps réel : événements (31), surveillance et alertes selon règles (32), tâches longues en arrière-plan quand l'OS et l'infrastructure le permettent (42), notifications (43).
- Modules : Data Science (33) ; Trading — analyse, indicateurs, simulations, backtesting, paper trading (34), gestion stricte du risque et séparation analyse / décision / exécution (35), trading réel désactivé par défaut avec permissions supplémentaires (36), aucun retrait automatique ni action financière non autorisée (37) ; Android avec permissions appropriées (38), permissions officielles, jamais de contournement (39), caméra / micro / notifications / fichiers seulement après permission et si légalement et techniquement disponible (40) ; voix STT/TTS (41) ; jeux vidéo, sans contourner l'anti-cheat (44, 45) ; jeux d'argent et aléatoire : statistiques et simulations, jamais de prédiction présentée comme certitude (46).
- LLM et coûts : plusieurs fournisseurs via couche d'abstraction (47), fournisseur remplaçable sans tout reconstruire (48), suivi des coûts et quotas (49), tâches simples vers modèles moins coûteux (50).
- Objectif final : agent réellement utilisable, extensible, maintenable, pas une démonstration (60).

### Section 41 — Principes obligatoires (toute implémentation future)
- 41.1 Autonomie contrôlée : bornée par permissions, politiques, capacités réelles des outils, limites externes, budgets et quotas, règles utilisateur. Jamais d'accès illimité au téléphone, aux comptes ou à Internet.
- 41.2 INFORMATION (donnée d'une source) ≠ DÉCISION (conclusion ou plan de l'agent) ≠ ACTION (opération réellement exécutée). Une information n'est jamais une autorisation.
- 41.3 Chaîne obligatoire : Utilisateur → Agent Core → Policy/Permission Engine → Tool Executor → Outil/Service externe → Résultat → Verification/Evaluator → Agent Core. Le modèle ne peut pas s'accorder une permission.
- 41.4 Sandbox : contrôle temps CPU, mémoire, système de fichiers, réseau, processus, bibliothèques, taille des fichiers, durée maximale. L'agent ne peut ni désactiver ni modifier ses protections.
- 41.5 Compétences : DRAFT → TEST → EVALUATE → APPROVE → ACTIVE → IMPROVE → VERSION. Une compétence qui échoue aux tests ne devient pas active. Chaque version conserve : origine, changements, tests, résultats, niveau de confiance, date, compatibilité.
- 41.6 Mémoire : 5 catégories ; l'agent décide quoi conserver et évite l'accumulation inutile ; données sensibles protégées selon permissions et confidentialité.
- 41.7 Vérification : ACTION → OBSERVATION → VALIDATION → SUCCESS/FAILURE → RECOVERY.
- 41.8 Erreurs : identifier, juger si récupérable, autre stratégie, réessayer dans les limites, demander l'aide de l'utilisateur, arrêter si continuer est risqué. Boucles infinies impossibles (temps, itérations, budget).
- 41.9 Actions sensibles (modification/suppression de données, actions financières, messages à des tiers, fonctions Android, code à privilèges élevés, opérations irréversibles) : autorisation unique, limitée dans le temps, persistante si approprié, ou refus.
- 41.10 Kill switch : aucune nouvelle action externe, tâches en cours interrompues si techniquement possible, événement enregistré dans l'audit.
- 41.11 Trading : Données → Analyse → Stratégie → Backtest → Paper Trading → Évaluation → Autorisation explicite → éventuellement exécution réelle. Jamais de garantie de profit ; trading réel désactivé par défaut.
- 41.12 Jeux/aléatoire : données, statistiques, simulations, probabilités, comparaison historique ; jamais de certitude.
- 41.13 Android : permissions système, restrictions Android, mécanismes officiels d'accessibilité, règles de distribution ; aucun contournement de sécurité ou d'authentification.
- 41.14 Jeux vidéo : seulement si autorisé ; ni anti-cheat contourné, ni vulnérabilité exploitée, ni client modifié illégalement, ni protections contournées.
- 41.15 Audit append-only : utilisateur, tâche, outil, action, décision d'autorisation, résultat, erreur, timestamp, identifiant de corrélation.
- 41.16 Observabilité : ce que l'agent faisait, tâche en cours, outils, erreurs, durée, coûts, pourquoi une action a été autorisée ou refusée.
- 41.17 Modularité : nouveaux modèles, outils, sources, compétences, modules, interfaces sans réécrire le noyau.
- 41.18 Règle finale (définition de « fonctionnel ») : implémentation réelle + test + vérification + gestion des erreurs + documentation minimale + intégration cohérente avec permissions et audit. Sinon la fonctionnalité n'est pas déclarée fonctionnelle.

### Écarts avec l'architecture v2 relevés lors de l'intégration (tous absorbés)
- Étape AUTHORIZE ajoutée à la boucle (§6).
- Audit : champs tâche, décision d'autorisation et identifiant de corrélation ajoutés (§3.7).
- Compétences : retour à une version précédente (rollback) et champ compatibilité requis dans `skill_versions` (à prévoir à l'étape 9).
- Observabilité : tracer aussi la raison de chaque autorisation ou refus (à prévoir aux étapes 6 et 7).
- Règle 41.18 : critère d'acceptation de chaque étape de la roadmap.
- Points d'attention : tâches en arrière-plan sur Android limitées par l'OS (42) ; fonctions caméra/micro/fichiers dépendantes des permissions (40).

## 18. Étape 1 — état réel (mis à jour le 2026-10-05)

Statut : livrée et vérifiée par exécution chez l'utilisateur, dans Codespaces. L'environnement de construction n'avait pas accès à PyPI (« Host not in allowlist »), donc les tests ont été exécutés par l'utilisateur, pas par l'auteur du code. Résultats rapportés par l'utilisateur (captures d'écran) : `pytest` → 25 passed, 1 warning ; `/health` → réponse JSON `status: ok` via le port 8000 de Codespaces. Les fonctionnalités ci-dessous sont déclarées fonctionnelles au niveau de l'étape 1 ; l'intégration complète aux permissions et à l'audit viendra aux étapes 2 et 6.

### Fichiers créés
- Racine : `.gitignore`, `README.md`, `.devcontainer/devcontainer.json`, `PROJECT_STATE.md`, `TODO.md`, `CHANGELOG.md`
- `backend/` : `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.env.example`
- `backend/app/` : `__init__.py` (version, nom du service), `main.py` (create_app), `config.py` (Settings), `api/health.py` (GET /health), `core/request_id.py` (middleware X-Request-ID), `core/errors.py` (gestionnaire d'erreurs 500)
- `backend/tests/` : `test_health.py` (11 tests), `test_config.py` (4), `test_repo_hygiene.py` (10 tests, dont certains ignorés sans dépôt Git) — 25 tests écrits
- `docs/ETAPE1_GUIDE_TELEPHONE.md` (guide GitHub/Codespaces depuis un téléphone), `mobile/.gitkeep`, `docs/.gitkeep`

### Statut par fonctionnalité (critères 41.18)
| Fonctionnalité | Implémentée | Test écrit | Vérifiée par exécution | Erreurs gérées | Doc minimale | Permissions / audit |
|---|---|---|---|---|---|---|
| GET /health | oui | oui (11) | OUI : 11 tests réussis + appel réel dans le navigateur (JSON `status: ok`, version 0.1.0, environment development) ; la racine `/` répond `{"detail":"Not Found"}` comme attendu | 405/404 par FastAPI, 500 propre | oui | niveau 0 documenté ; audit non applicable avant l'étape 2 |
| X-Request-ID | oui | oui (pytest) | OUI : tests réussis + 8 contrôles ASGI manuels | identifiant client invalide remplacé | oui | base du futur identifiant de corrélation (audit, étape 2) |
| Gestion d'erreur 500 | oui | oui | OUI (test pytest réussi) | pas de fuite de détail interne | oui | — |
| Configuration | oui | oui (4) | OUI (tests réussis) | valeur invalide : échec au démarrage | oui | — |
| Hygiène des secrets | oui | oui (10) | OUI (tests réussis) + `git check-ignore` manuel réussi côté construction. Côté utilisateur : `git status` propre, branche à jour avec `origin/main`, fin de `git ls-files` vue (tests, docs, mobile/.gitkeep). RESTE À CONFIRMER : absence de `.env`, `.venv`, `.zip` dans `git ls-files` (commande `grep` fournie) | — | oui | — |

### Vérifications réellement effectuées
- `python3 -m compileall` sur `app/` et `tests/` : réussi.
- 8 contrôles manuels du middleware RequestIdMiddleware avec un harnais ASGI (identifiant généré, conservé, remplacé si invalide, exception propagée) : 8/8 réussis.
- Test manuel de `.gitignore` avec de faux fichiers sensibles (supprimés ensuite) : tous ignorés, aucun dans l'index.
- Chez l'utilisateur (Codespaces, captures d'écran) : environnement `.venv` créé et dépendances installées ; `pytest` → 25 passed, 1 warning en 0,60 s ; serveur `uvicorn` démarré, `/health` appelé dans le navigateur via le port 8000 (JSON conforme) ; `git commit` → « nothing to commit, working tree clean », branche « up to date with 'origin/main' » (le commit était donc déjà enregistré et envoyé).
- `ruff check` : première exécution depuis la racine du dépôt → 2 erreurs corrigeables (fragment vu : ordre des imports près de `from fastapi.testclient import TestClient`, hypothèse : `ruff` lancé hors de `backend/`). Relancé ensuite depuis `backend/` : l'utilisateur a indiqué « C'est bon » (sortie exacte non transmise).
- NON effectués ou non confirmés : test du devcontainer (non appliqué sur ce premier codespace) ; contenu exact de `git log` ; vérification sur github.com ; arrêt du codespace ; commande `grep` sur `git ls-files`.

### Limites connues
- `requirements*.txt` non figés (versions non vérifiables ici) : « Solution temporaire — à remplacer à l'étape 2 » par un `pip freeze` issu d'une installation réussie.
- Python : `.devcontainer` vise 3.12 ; le Codespaces de l'utilisateur utilisait Python 3.14.2 (le devcontainer n'était pas appliqué) et les tests y passent ; l'environnement de construction avait 3.13. Le code requiert Python >= 3.11 (`datetime.UTC`). Choisir et figer une version de Python à l'étape 2.
- Avertissement de test : `starlette.testclient` signale que l'usage de `httpx` est déprécié au profit de `httpx2` (DeprecationWarning, sans effet sur les résultats). À traiter avec le gel des versions (étape 2).
- `devcontainer.json` (image `mcr.microsoft.com/devcontainers/python:3.12`) non testé.
- /health vérifie uniquement que le processus répond (pas de base de données ni de service externe encore).
- Pas d'audit ni de Policy Engine à ce stade (étapes 2 et 6).
- Livraison du code vers GitHub : par archive `atlas-etape1.zip` envoyée dans Codespaces (le dépôt GitHub de l'utilisateur n'est pas accessible depuis l'environnement de construction).

### Commandes importantes (depuis `backend/`, environnement activé)
- Créer l'environnement : `python3 -m venv .venv && source .venv/bin/activate`
- Installer : `pip install -r requirements-dev.txt`
- Tests : `pytest` (résultat constaté chez l'utilisateur : 25 passed, 1 warning)
- Serveur : `uvicorn app.main:app --reload` puis `curl http://localhost:8000/health`
- Contrôle qualité : `ruff check . --output-format=concise` — à lancer depuis `backend/`, pas depuis la racine du dépôt
