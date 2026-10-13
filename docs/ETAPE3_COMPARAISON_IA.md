# Étape 3 — Comparaison des fournisseurs d'IA (2026-10-13)

Aucun code, aucune clé, aucun paiement : ce document sert uniquement à choisir. Sources : pages officielles consultées le 2026-10-13 ; les prix changent, à revérifier avant tout paiement.

| Critère | Anthropic (Claude) | Google (Gemini API) | Groq | OpenRouter |
|---|---|---|---|---|
| Disponible au Cameroun | Oui (liste officielle des pays) | Oui (liste officielle des régions) | Non vérifié | Non vérifié |
| Gratuit sans carte | Non (API payante, prépaiement) | Oui (palier gratuit) | Oui (palier gratuit) | Oui, modèles `:free` seulement |
| Limites gratuites | — | Visibles dans AI Studio (non publiées sur la page de doc) | gpt-oss-120b : 30 req/min, 1 000 req/jour, 200 000 jetons/jour | 20 req/min ; 50 req/jour (1 000 si ≥ 10 crédits achetés) |
| Prix payant (par million de jetons, entrée / sortie) | Haiku 5.5 : 0,10 $ / 0,50 $ ; Sonnet 5.5 : 2 $ / 10 $ ; Opus 5.5 : 4 $ / 20 $ | 3.5 Flash-Lite : 0,30 $ / 2,50 $ ; 3.8 Flash : 0,75 $ / 3,75 $ (prix doublés au 1er janvier 2027) ; 2.5 Pro : 1,25 $ / 10 $ | Selon modèle (non détaillé ici) | Prix du modèle choisi + frais |
| Confidentialité | Pas d'entraînement par défaut sur l'API (à confirmer dans les conditions) | Palier gratuit : Google utilise tes requêtes pour améliorer ses produits, relecture humaine possible. Palier payant : non | À vérifier | Dépend du modèle sous-jacent |
| Appels d'outils (indispensable à l'agent) | Oui | Oui | Dépend du modèle | Dépend du modèle |

## Ce qui compte pour Atlas
- Atlas enverra des données personnelles (mémoire, tâches). Le palier gratuit de Google les réutilise : à éviter pour des données réelles, correct pour des essais sans données personnelles.
- Les niveaux de difficulté de l'architecture (petit modèle pour le simple, grand modèle pour le difficile) existent chez Anthropic (Haiku / Sonnet / Opus) et chez Google (Flash-Lite / Flash / Pro).
- L'architecture prévoit une passerelle IA : le fournisseur peut être changé plus tard sans réécrire l'agent.

## Options proposées
- **A. Google Gemini, palier gratuit pour développer, puis palier payant :** 0 € pour construire ; ne mettre aucune donnée personnelle tant qu'on est au palier gratuit.
- **B. Anthropic seul :** meilleure confidentialité et un seul fournisseur, mais il faut un petit prépaiement par carte (à vérifier que ta carte est acceptée) ; Haiku 5.5 coûte très peu.
- **C. Passerelle avec les deux :** Gemini gratuit pour le développement, Anthropic pour l'usage réel avec données personnelles.

Recommandation : C, parce qu'elle respecte « pas de service payant avant décision » (on commence gratuit) sans exposer tes données réelles. Décision à prendre par l'utilisateur ; le paiement et la création des clés se font toujours par lui.
