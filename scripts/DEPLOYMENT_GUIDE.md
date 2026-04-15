# Market Insights - OVH Deployment Guide

This is the authoritative OVH deployment flow for Market Insights.

## Entry Point

Use the wrapper below for production deployments:

```bash
bash scripts/deploy/deploy.ovh.sh deploy .env.ovh
```

## Files Used

- `.env.ovh`: single source of truth for OVH production
  - deployment control variables (`SSH_*`, `APP_DIR`, `COMPOSE_FILES`, TLS)
  - runtime app variables copied to remote `.env`
  - Airflow runtime variables
- `scripts/deploy/env.ovh.example`: versioned template used to create `.env.ovh`
- `docker-compose.ovh-apache.yml`: OVH app stack
- `docker-compose.airflow.yml`: Airflow override enabled via `COMPOSE_FILES`

## Effective Pipeline

1. Source `.env.ovh`
2. Bootstrap/update the repository on the VPS
3. Sync local workspace overlay if `SYNC_LOCAL_OVERLAY=true`
4. Copy `LOCAL_ENV_FILE` to remote `APP_DIR/.env` if `SYNC_DOTENV=true`
5. Preflight-check host ports (`API_BIND_PORT`, `FRONTEND_BIND_PORT`, `AIRFLOW_WEBSERVER_PORT`)
6. Run `docker compose` with `COMPOSE_FILES`
7. Re-apply Apache and Certbot if enabled

## Production Ports

- API: `127.0.0.1:18100`
- Frontend: `127.0.0.1:18180`
- Airflow: `10.8.0.1:18089`

`18089` is reserved for Market Insights Airflow and must remain distinct from Market Screener Airflow (`18088`).

## Post-Deploy Checks

```bash
docker compose -f docker-compose.ovh-apache.yml -f docker-compose.airflow.yml ps
docker logs --tail=200 mi-airflow-scheduler
docker logs --tail=200 mi-airflow-webserver
curl -I https://market-insight.doctumconsilium.com
curl -s https://market-insight.doctumconsilium.com/api/health
```