# Airflow ETL — Architecture k3s

## Pourquoi les DAGs ont été réécrits

Les DAGs Airflow de ce projet importaient directement le package `market_insights`
(`market_insights.db.session`, `market_insights.services.etl_service`).
Ce pattern fonctionne en local avec Docker Compose (le repo est monté en volume),
mais échoue en k3s car :

- Le package n'est pas pip-installé dans le container `apache/airflow`
- Le hack `sys.path` calculait `../../../` depuis `/opt/airflow/dags/`, ce qui
  donnait `/` (racine FS) — jamais le bon répertoire

## Approche retenue

Les DAGs appellent l'API HTTP interne au lieu d'importer le package :

| Avant | Après |
|---|---|
| `from market_insights.services.etl_service import run_etl` | `httpx.post(f"{MI_API_BASE}/etl/run", params=...)` |
| `from market_insights.db.session import SessionLocal` | supprimé |
| `sys.path.insert(0, _REPO_ROOT)` | supprimé |

L'endpoint `/etl/run` existait déjà dans `market_insights/api/main.py` (ligne 165).

## Configuration k3s

Les DAGs sont embarqués dans le ConfigMap `market-insight-airflow-dags`
défini dans `k3s-fromOVHVps/deploy/platform/10-market-insight.template.yaml`.

Un initContainer `busybox` les copie dans `/opt/airflow/dags/` avant le démarrage
du scheduler et du webserver.

Variable d'environnement clé :
```
MI_API_BASE = http://market-insight-api.market-insight.svc.cluster.local:8000
```
Définie dans le ConfigMap `market-insight-airflow-config`.

## Providers de données (gratuits)

- **Actions** : Yahoo Finance via `yfinance` (provider `yahoo`) — gratuit, rate-limité
- **Crypto** : CoinGecko API publique (provider `coingecko`) — gratuit

Les cooldowns entre tickers (420s stocks, 120s crypto) évitent les rate limits Yahoo.

## Accès Airflow UI

Disponible sur `https://products.doctumconsilium.com/tools/airflow-mi/`
(protégé Keycloak via oauth2-proxy).

## Fichiers DAG

| Fichier | Rôle | Schedule |
|---|---|---|
| `market_insights_dag.py` | ETL quotidien toutes actions | 00:30 UTC |
| `market_insights_full_refresh_dag.py` | Refresh complet ETL+RAG+cache | 05:00 UTC |
| `market_insights_fallback_dags.py` | DAGs manuels par ticker | manuel |
| `mi_airflow_common.py` | Utilitaires partagés | — |
