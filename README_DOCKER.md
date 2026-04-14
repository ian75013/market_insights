# README_DOCKER - Market Insights

Ce document liste les commandes Docker utiles pour lancer, verifier et maintenir la stack.

## 1) Development local (SQLite + Vite)

Demarrage:

```bash
docker compose up --build
```

Demarrage detache:

```bash
docker compose up -d --build
```

Arret:

```bash
docker compose down
```

Logs:

```bash
docker compose logs -f api
docker compose logs -f frontend
```

## 2) Development local avec gateway LiteLLM

Depuis `market_insights`:

```bash
bash scripts/dev_up_litellm.sh
```

Mode detache:

```bash
DETACH=true bash scripts/dev_up_litellm.sh
```

Mode detache + test e2e chat:

```bash
DETACH=true RUN_E2E_CHAT_TEST=true bash scripts/dev_up_litellm.sh
```

## 3) Production standard (sans Airflow)

Demarrage:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Etat:

```bash
docker compose -f docker-compose.prod.yml ps
```

Logs:

```bash
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f db
```

Arret:

```bash
docker compose -f docker-compose.prod.yml down
```

## 4) Production avec Airflow

Demarrage:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airflow.yml up -d --build
```

Etat:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airflow.yml ps
```

Logs Airflow:

```bash
docker logs -f mi-airflow-scheduler
docker logs -f mi-airflow-webserver
docker logs -f mi-airflow-init
```

Arret:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.airflow.yml down
```

## 5) OVH Apache (stack locale liee a l'hote)

Demarrage:

```bash
docker compose -f docker-compose.ovh-apache.yml up -d --build
```

Demarrage avec Airflow:

Airflow UI on OVH defaults to port `18089` to avoid conflict with other stacks.

```bash
docker compose -f docker-compose.ovh-apache.yml -f docker-compose.airflow.yml up -d --build
```

Etat:

```bash
docker compose -f docker-compose.ovh-apache.yml ps
docker compose -f docker-compose.ovh-apache.yml -f docker-compose.airflow.yml ps
```

## 6) Commandes Airflow utiles

Lister les DAGs:

```bash
docker exec -it mi-airflow-scheduler airflow dags list
```

Trigger DAG principal:

```bash
docker exec -it mi-airflow-scheduler airflow dags trigger market_insights_daily
```

Tester une task:

```bash
docker exec -it mi-airflow-scheduler airflow tasks test market_insights_daily extract_aapl 2026-01-01
```

Verifier erreurs import DAG:

```bash
docker exec -it mi-airflow-scheduler airflow dags list-import-errors
```

## 7) Maintenance

Rebuild complet:

```bash
docker compose build --no-cache
```

Redemarrer un service:

```bash
docker compose restart api
```

Nettoyage images/volumes non utilises:

```bash
docker system prune -f
docker volume prune -f
```

## 8) Points de config importants

- Les variables shell exportees ont priorite sur `.env`.
- Pour Airflow VPN-only:
  - `AIRFLOW_WEBSERVER_BIND=<IP_VPN_SERVEUR>`
- Pour Airflow localhost-only:
  - `AIRFLOW_WEBSERVER_BIND=127.0.0.1`
  - acces via tunnel SSH: `ssh -L 18089:127.0.0.1:18089 user@vps`
