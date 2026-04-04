# Airflow ETL — Market Insights

> Branch: `feature/airflow-etl`

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                   docker compose                        │
│                                                         │
│  docker-compose.prod.yml  +  docker-compose.airflow.yml │
│                                                         │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────────┐ │
│  │  mi-api      │  │ mi-frontend│  │    mi-db         │ │
│  │  (FastAPI)   │  │  (React)   │  │  (Postgres 16)   │ │
│  └──────────────┘  └────────────┘  └─────────────────┘ │
│                                                         │
│  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │  airflow-db  │  │  airflow-scheduler              │  │
│  │ (Postgres 16)│  │  runs DAGs via LocalExecutor   │  │
│  └──────────────┘  │                                │  │
│                    │  ┌──────────────────────────┐  │  │
│                    │  │  market_insights_daily   │  │  │
│                    │  │                          │  │  │
│                    │  │  extract_aapl ──────┐    │  │  │
│                    │  │  extract_msft ──────┤    │  │  │
│                    │  │  extract_nvda ──────┤──► refresh_rag
│                    │  │       …             │    │  │  │
│                    │  │  extract_btc  ──────┘    │  │  │
│                    │  └──────────────────────────┘  │  │
│                    └────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  airflow-webserver  (port 8080)                   │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- `LocalExecutor` — no Celery/Redis overhead for a single VPS node.
- Dedicated `airflow-db` Postgres — keeps Airflow metadata isolated from app data.
- The DAGs folder is mounted **read-only** into the containers → edit DAGs on the host without rebuilding.
- `market_insights` Python package is installed from `deploy/airflow/requirements-airflow.txt` at container init time.
- All 10 extract tasks run **in parallel** (up to 4 at once) then `refresh_rag` waits on all of them.

---

## DAG — `market_insights_daily`

| Field | Value |
|---|---|
| Schedule | `30 0 * * *` (00:30 UTC) |
| Catchup | `False` |
| Max parallel tasks | 4 |
| Retries per task | 3 × 5 min delay |

### Tasks

| Task ID | What it does |
|---|---|
| `extract_aapl` … `extract_btc` | Calls `run_etl(db, ticker, provider)` for one ticker |
| `refresh_rag` | POST `/rag/index/<ticker>` for every ticker via the internal API |

Provider routing: tickers in `_CRYPTO` set → `coingecko`, everything else → `yahoo`.

---

## Prerequisites

- Docker + Docker Compose v2
- The `feature/airflow-etl` branch checked out
- Access to `.env` (or `.env.ovh`) variables described below

---

## Environment Variables

Add these to your `.env` (or `.env.ovh` for VPS) **in addition** to the existing market_insights vars:

```dotenv
# ── Airflow ───────────────────────────────────────────────────────────────────
# Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
AIRFLOW_FERNET_KEY=<base64-fernet-key>

# Random string (32+ chars) used to sign Airflow sessions
AIRFLOW_SECRET_KEY=<random-secret>

# Password for the Airflow admin UI user (username: admin)
AIRFLOW_ADMIN_PASSWORD=<choose-a-password>

# Optional — bind webserver to localhost only (default) or a specific IP
AIRFLOW_WEBSERVER_BIND=127.0.0.1

# ── Passed to Airflow workers so the DAG can reach the app database ───────────
MI_DATABASE_URL=postgresql+psycopg2://mi:mi@mi-db:5432/market_insights
MI_USE_NETWORK=true
```

### Generate a Fernet key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Starting the Full Stack (with Airflow)

```bash
# From the market_insights repo root

# 1. Build the app image (only once, or after code changes)
docker compose -f docker-compose.prod.yml build

# 2. Start app + Airflow together
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.airflow.yml \
  up -d

# 3. Check that all containers are healthy
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.airflow.yml \
  ps
```

Expected containers:

| Name | Port (host-bound) |
|---|---|
| `mi-api` | `127.0.0.1:18100` |
| `mi-frontend` | `127.0.0.1:18180` |
| `mi-db` | internal |
| `airflow-db` | internal |
| `airflow-webserver` | `127.0.0.1:8080` |
| `airflow-scheduler` | — |

### Starting without Airflow (original behaviour)

```bash
docker compose -f docker-compose.prod.yml up -d
```

The API still exposes `/etl/run/{ticker}` endpoints so ETL can be triggered manually.

---

## Accessing the Airflow UI

Forward the webserver port locally (if running on a remote VPS):

```bash
ssh -L 8080:127.0.0.1:8080 yannsmatti@doctumconsilium.com
```

Then open `http://localhost:8080` in your browser.

- **Username:** `admin`
- **Password:** `$AIRFLOW_ADMIN_PASSWORD` (from your `.env`)

---

## Triggering the DAG Manually

### Via the UI

1. Open the Airflow UI → DAGs → `market_insights_daily`
2. Click **▶ Trigger DAG**

### Via the CLI

```bash
docker exec -it airflow-scheduler \
  airflow dags trigger market_insights_daily
```

### Run a single task for debugging

```bash
docker exec -it airflow-scheduler \
  airflow tasks test market_insights_daily extract_aapl 2026-01-01
```

---

## Deploy to VPS

The deploy script (`scripts/deploy/deploy.ovh.sh`) syncs the whole repo including the new files.

```bash
# On your local machine
bash scripts/deploy/deploy.ovh.sh deploy .env.ovh
```

SSH onto the VPS and restart with both compose files:

```bash
ssh yannsmatti@doctumconsilium.com

cd /opt/market_insights   # or wherever it's deployed

docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.airflow.yml \
  up -d --build
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `airflow-init` exits with error | Check `AIRFLOW_FERNET_KEY` and `AIRFLOW_SECRET_KEY` are set |
| DAG import error | Run `docker exec airflow-scheduler airflow dags list-import-errors` |
| `market_insights` module not found | Ensure `requirements-airflow.txt` was installed; check `airflow-init` logs |
| `run_etl` DB error | Verify `MI_DATABASE_URL` matches the `mi-db` service credentials |
| RAG refresh fails | It's best-effort and logs a warning — check `airflow-scheduler` logs |
| Webserver not accessible | Confirm `AIRFLOW_WEBSERVER_BIND` and SSH tunnel are correct |

---

## File Map

```
market_insights/
├── docker-compose.airflow.yml          # Airflow service stack (override)
├── deploy/
│   └── airflow/
│       └── requirements-airflow.txt    # Python deps for Airflow containers
└── market_insights/
    └── etl/
        └── dags/
            └── market_insights_dag.py  # The DAG (auto-loaded by scheduler)
```
