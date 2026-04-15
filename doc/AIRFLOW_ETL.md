# Airflow ETL - Market Insights

Ce guide couvre l'orchestration ETL avec Airflow pour Market Insights, en local et en production OVH.

## 1) Architecture actuelle

Stack applicative:

- `db` (`mi-db`) : Postgres applicatif Market Insights
- `api` (`mi-api`) : FastAPI
- `frontend` (`mi-frontend`) : React build

Stack Airflow (override):

- `airflow-db` (`mi-airflow-db`) : Postgres dedie metadata Airflow
- `airflow-init` (`mi-airflow-init`) : migration DB Airflow + creation user admin
- `airflow-scheduler` (`mi-airflow-scheduler`) : planification + execution DAG
- `airflow-webserver` (`mi-airflow-webserver`) : UI Airflow

Le DAG principal historique est dans `market_insights/etl/dags/market_insights_dag.py`:

- DAG: `market_insights_daily`
- Schedule: `30 0 * * *` (00:30 UTC)
- Retry: 3 tentatives avec delai 5 min
- Parallelisme: jusqu'a 4 taches ETL en parallele
- Routage provider: crypto -> `coingecko`, actions -> `yahoo`
- Post-traitement: task `refresh_rag` apres toutes les extractions

Le DAG operations principal pour la production VPS est maintenant `market_insights_full_refresh`:

- Schedule par defaut: `0 5 * * *` (tous les matins a 05:00 UTC)
- Retry par defaut: 7 retries avec delai de 1h, soit 8 tentatives max
- Execution volontairement lisse en serie pour eviter les bursts reseau
- Rechauffe les donnees utiles au site: macro, overview, technique, fondamentaux, news, RAG
- Les chandeliers ne sont PAS precharges: endpoint inline uniquement (a la demande UI)
- Variables optionnelles:
  - `MI_FULL_REFRESH_SCHEDULE`
  - `MI_AIRFLOW_RETRIES`
  - `MI_AIRFLOW_RETRY_DELAY_HOURS`
  - `MI_TICKERS`
  - `MI_STOCK_PROVIDER`
  - `MI_STOCK_ETL_COOLDOWN_SECONDS`
  - `MI_CRYPTO_ETL_COOLDOWN_SECONDS`
  - `MI_POST_RAG_COOLDOWN_SECONDS`
  - `MI_TAB_COOLDOWN_SECONDS`
  - `MI_GLOBAL_COOLDOWN_SECONDS`

Des DAGs de fallback sont aussi generes automatiquement:

- `market_insights_refresh_<ticker>` : relance un ticker complet
- `market_insights_refresh_<ticker>_<onglet>` : relance un ticker sur un onglet cible

Ces DAGs de fallback sont manuels, utiles si Yahoo Finance limite trop fort et qu'il faut decouper les executions.

Ordre pratique recommande:

1. laisser tourner `market_insights_full_refresh`
2. si un ticker bloque ou se fait limiter, lancer `market_insights_refresh_<ticker>`
3. si c'est encore trop lourd, lancer `market_insights_refresh_<ticker>_<onglet>`

## 2) Variables requises

Ajouter ces variables dans `.env` (ou `.env.ovh` en prod):

```dotenv
AIRFLOW_DB_USER=airflow
AIRFLOW_DB_PASSWORD=CHANGE_ME_AIRFLOW_DB
AIRFLOW_DB_NAME=airflow

AIRFLOW_FERNET_KEY=<base64-fernet-key>
AIRFLOW_SECRET_KEY=<random-secret-32+chars>
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=<strong-password>
AIRFLOW_ADMIN_EMAIL=admin@example.com

# Exposition UI Airflow
AIRFLOW_WEBSERVER_BIND=127.0.0.1
AIRFLOW_WEBSERVER_PORT=18089
AIRFLOW_BASE_URL=http://localhost:18089
```

Generation Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 3) Lancement local (prod + airflow)

Depuis la racine du repo `market_insights`:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airflow.yml up -d --build
```

Verifications:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airflow.yml ps
docker logs -f mi-airflow-scheduler
docker logs -f mi-airflow-webserver
```

UI Airflow:

- URL: `http://127.0.0.1:18089`
- User: `AIRFLOW_ADMIN_USER`
- Password: `AIRFLOW_ADMIN_PASSWORD`

## 4) Trigger manuel du DAG

Par UI:

1. Ouvrir Airflow
2. DAGs -> `market_insights_daily`
3. Trigger DAG

Par CLI:

```bash
docker exec -it mi-airflow-scheduler airflow dags trigger market_insights_daily
docker exec -it mi-airflow-scheduler airflow dags trigger market_insights_full_refresh
```

Test d'une tache:

```bash
docker exec -it mi-airflow-scheduler airflow tasks test market_insights_daily extract_aapl 2026-01-01
```

## 5) Integration production OVH

La production OVH applicative utilise `docker-compose.ovh-apache.yml`.

Pour integrer Airflow en prod, lancer avec deux fichiers compose:

```bash
docker compose -f docker-compose.ovh-apache.yml -f docker-compose.airflow.yml up -d --build
```

Important:

- Apache public continue de router uniquement:
  - `/` -> frontend (`127.0.0.1:18080`)
  - `/api/` -> API (`127.0.0.1:18000`)
- Airflow n'est pas route publiquement par Apache par defaut.

## 6) Airflow sur VPN

### Option recommandee: bind direct sur IP VPN

Si le serveur a une IP VPN (ex: `10.8.0.2`), forcer:

```dotenv
AIRFLOW_WEBSERVER_BIND=10.8.0.2
AIRFLOW_WEBSERVER_PORT=18089
AIRFLOW_BASE_URL=http://10.8.0.2:18089
```

Puis relancer la stack compose avec Airflow.

Acces UI depuis client VPN:

```text
http://10.8.0.2:18089
```

### Option stricte: localhost + tunnel

Conserver:

```dotenv
AIRFLOW_WEBSERVER_BIND=127.0.0.1
```

Et utiliser:

```bash
ssh -L 18089:127.0.0.1:18089 user@vps
```

## 7) Deployment script OVH

Le script `scripts/deploy/deploy.ovh.sh` supporte maintenant:

- `COMPOSE_FILE` (historique, fichier unique)
- `COMPOSE_FILES` (nouveau, liste CSV de fichiers compose)

Exemple `.env.ovh` pour prod + Airflow:

```dotenv
COMPOSE_FILES=docker-compose.ovh-apache.yml,docker-compose.airflow.yml
AIRFLOW_WEBSERVER_BIND=10.8.0.2
AIRFLOW_WEBSERVER_PORT=18089
```

Deploiement:

```bash
bash scripts/deploy/deploy.ovh.sh deploy .env.ovh
```

## 8) Troubleshooting

- `mi-airflow-init` fail: verifier `AIRFLOW_FERNET_KEY` et `AIRFLOW_SECRET_KEY`
- DAG absent: `docker exec -it mi-airflow-scheduler airflow dags list`
- Erreurs import DAG: `docker exec -it mi-airflow-scheduler airflow dags list-import-errors`
- UI inaccessible:
  - verifier `AIRFLOW_WEBSERVER_BIND`
  - verifier pare-feu VPN
  - verifier que le client est bien connecte au VPN
- Erreur DB ETL: verifier credentials Postgres app (`POSTGRES_*`) et `MI_DATABASE_URL` injecte par compose
