# Rapport Cold Start - Market Insights (11/04/2026)

## Contexte
Analyse réalisée depuis les sorties Docker du VPS OVH pour expliquer le comportement de démarrage de Market Insights côté client.

Services observés:
- `mi-api` (API FastAPI/Uvicorn)
- `mi-frontend` (Nginx)
- `mi-db` (PostgreSQL)

## Données collectées (Docker)

### Etat des conteneurs
- `mi-api`: `Up ... (healthy)` sur `127.0.0.1:18100->8000`
- `mi-frontend`: `Up ...` sur `127.0.0.1:18180->80`
- `mi-db`: `Up ... (healthy)`

### Timeline de démarrage API
Source: `docker inspect mi-api` + health logs

- `StartedAt`: `2026-04-11T14:40:20.316Z`
- Healthcheck en échec (connection refused):
  - `14:41:02.233Z`
  - `14:41:07.479Z`
- Premier healthcheck OK:
  - `14:41:12.736Z`

### Délai observé (cold start)
- Temps entre `StartedAt` et premier `health=OK`: environ **52.4 secondes**.
- Fenêtre d'indisponibilité effective API au redémarrage: environ **45-55 secondes** (selon l'alignement des probes).

### Indices dans les logs applicatifs
Dans `mi-api`:
- Chargement de composants NLP/embedding visible:
  - `Loading weights: 100% ...`
  - `BertModel LOAD REPORT ... sentence-transformers/all-MiniLM-L6-v2`
- Requêtes fonctionnelles ensuite en 200 (`/fundamentals`, `/fair-value`, `/news`, `/insights`).

Dans `mi-frontend`:
- Redémarrage Nginx observé autour de `14:40:25`.
- Le frontend est disponible rapidement, mais dépend de la disponibilité API pour une UX complète.

### Mesure de latence API (état chaud)
Mesures live effectuées après stabilisation:
- sample 1: `ttfb=0.083s`, `total=0.103s`
- sample 2: `ttfb=0.010s`, `total=0.010s`
- sample 3: `ttfb=0.031s`, `total=0.031s`

Conclusion: la performance en régime établi est bonne; le problème est concentré sur la phase de démarrage.

## Diagnostic
Le problème client n'est pas un "simple cold start" au sens banal: c'est un **cold start long et visible** (~52s) qui impacte l'expérience utilisateur au moment des redéploiements/redémarrages.

Causes probables (cumulatives):
1. Initialisation de dépendances lourdes au boot (modèles embedding / NLP).
2. Readiness effective retardée: API non joignable pendant plusieurs probes.
3. Frontend servi avant API complètement prête, donnant une perception de lenteur/instabilité.

## Impact client
- Pendant ~1 minute après redémarrage, l'utilisateur peut voir des écrans partiellement chargés, erreurs de données ou délais élevés.
- L'impact est particulièrement sensible en démonstration commerciale et usage B2B.

## Plan d'action recommandé (orienté client/SLO)

### Priorité P0 (immédiat)
1. Mettre en place un mode "warmup" côté API au démarrage:
- Précharger explicitement les composants lourds avant d'accepter le trafic.
- Exposer un endpoint readiness strict (distinct du health basique) qui ne passe à OK qu'après warmup complet.

2. Ajuster la chaîne de déploiement:
- Router le trafic vers la nouvelle instance uniquement après readiness=OK.
- Eviter de basculer frontend/API tant que readiness n'est pas validé.

3. Dégrader proprement côté frontend:
- Afficher un état "service en initialisation" explicite.
- Retry/backoff progressif côté appels API critiques.

### Priorité P1 (court terme)
1. Mettre en cache local des artefacts modèles (éviter tout fetch dynamique au boot).
2. Introduire des métriques de démarrage:
- `startup_total_seconds`
- `readiness_wait_seconds`
- `first_successful_request_seconds`
3. Définir SLO de redémarrage:
- Exemple cible: readiness < 15s (p95), indisponibilité perçue < 10s.

### Priorité P2 (moyen terme)
1. Stratégie blue/green ou rolling avec overlap.
2. Instance chaude minimale permanente pour supprimer la perception de cold start en production.

## Résumé exécutif
- Cold start mesuré via Docker: **~52s jusqu'à readiness OK**.
- Ce délai est **incompatible avec une expérience client premium** lors de redéploiements.
- La correction doit être traitée comme un sujet de fiabilité produit (SLO/readiness/warmup), pas comme une simple explication technique ponctuelle.
