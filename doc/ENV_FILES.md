# Environment Files - Market Insights

## Authoritative Files

### Local development

- `.env`
  - local/runtime configuration
  - used by local `docker compose` and local development workflows

### OVH production

- `.env.ovh`
  - authoritative production file
  - contains both deploy-control variables and runtime container variables
  - copied to the VPS as `APP_DIR/.env` during deployment

- `scripts/deploy/env.ovh.example`
  - template for `.env.ovh`
  - safe to version

## Variables by role

### Deploy-control variables in `.env.ovh`

- `SSH_USER`, `SSH_HOST`, `SSH_PORT`
- `GIT_REPO`, `GIT_BRANCH`, `APP_DIR`
- `LOCAL_ENV_FILE`
- `COMPOSE_FILES`
- `SYNC_LOCAL_OVERLAY`, `SYNC_DOTENV`
- `ENABLE_APACHE_CONFIG`, `CERTBOT_AUTOCONFIG`, `CERTBOT_EMAIL`
- `APP_DOMAIN`, `SSL_CERT`, `SSL_KEY`
- `API_BIND_PORT`, `FRONTEND_BIND_PORT`

### Runtime variables in `.env.ovh`

- app/database variables: `APP_ENV`, `POSTGRES_*`, `DATABASE_URL`
- provider/LLM variables: `LITELLM_*`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`
- cache/RAG variables: `RAG_*`, `CACHE_TTL_*`
- Airflow variables: `AIRFLOW_DB_*`, `AIRFLOW_FERNET_KEY`, `AIRFLOW_SECRET_KEY`, `AIRFLOW_ADMIN_*`, `AIRFLOW_WEBSERVER_*`, `AIRFLOW_BASE_URL`

## Production Rule

If you change a production value for Market Insights, change `.env.ovh` first.
That file is the exact source used by the OVH deploy pipeline.