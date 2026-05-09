# INFRASTRUCTURE

## Purpose
market_insights provides market-data workflows and analytics services.

## Main Components
- Python application code and orchestration scripts
- Docker runtime via docker-compose files
- Deployment entrypoint: deploy.sh

## Local Run
1. Copy or adjust environment variables as needed.
2. Build and start:
   - docker compose up -d --build
3. Validate running containers:
   - docker compose ps

## Deployment
- Production compose files exist (for example docker-compose.prod.yml).
- Use deploy.sh for controlled deployment steps.

## Operations and Validation
- Check logs with docker compose logs -f.
- Validate API/UI endpoints after each rollout.

## Rollback
- Reapply previous compose configuration and image tags.
- Restart stack with known-good config.
