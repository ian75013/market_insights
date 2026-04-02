#!/usr/bin/env bash
set -euo pipefail

LITELLM_BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
LITELLM_SHARED_NETWORK="${LITELLM_SHARED_NETWORK:-litellm-gateway-vps_llmnet}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-180}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-5}"
DETACH="${DETACH:-false}"
RUN_E2E_CHAT_TEST="${RUN_E2E_CHAT_TEST:-false}"
MARKET_INSIGHTS_HEALTH_URL="${MARKET_INSIGHTS_HEALTH_URL:-http://localhost:8000/health}"
MARKET_INSIGHTS_FRONTEND_URL="${MARKET_INSIGHTS_FRONTEND_URL:-http://localhost:3080}"

if [ ! -f .env ]; then
  echo "Error: .env not found in current directory"
  exit 1
fi

wait_container_ready() {
  local container_name="$1"
  local timeout="$2"
  local interval="$3"
  local elapsed=0
  local status=""

  while true; do
    status=$(docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" "$container_name" 2>/dev/null || true)
    if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
      echo "$container_name status: $status"
      return 0
    fi
    if [ "$elapsed" -ge "$timeout" ]; then
      echo "Timeout waiting for $container_name (last status: ${status:-unknown})"
      return 1
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
}

wait_http_ok() {
  local url="$1"
  local timeout="$2"
  local interval="$3"
  local elapsed=0

  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    if [ "$elapsed" -ge "$timeout" ]; then
      return 1
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
}

echo "Checking shared Docker network: $LITELLM_SHARED_NETWORK"
docker network inspect "$LITELLM_SHARED_NETWORK" >/dev/null

echo "Checking LiteLLM gateway readiness: $LITELLM_BASE_URL/health/readiness"
if ! wait_http_ok "$LITELLM_BASE_URL/health/readiness" "$HEALTH_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS"; then
  echo "Error: LiteLLM gateway is not ready at $LITELLM_BASE_URL"
  echo "Start it first from the litellm-gateway-vps project, for example:"
  echo "  bash scripts/dev_up.sh"
  exit 1
fi

echo "Starting Market Insights with shared LiteLLM gateway..."
if [ "$DETACH" = "true" ]; then
  docker compose up -d --build

  echo "Waiting for Market Insights API..."
  wait_container_ready mi-api-dev "$HEALTH_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS"

  echo "Waiting for Market Insights frontend..."
  wait_container_ready mi-frontend-dev "$HEALTH_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS"

  echo "Checking Market Insights API health: $MARKET_INSIGHTS_HEALTH_URL"
  if ! wait_http_ok "$MARKET_INSIGHTS_HEALTH_URL" "$HEALTH_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS"; then
    echo "Error: Market Insights API is not ready at $MARKET_INSIGHTS_HEALTH_URL"
    exit 1
  fi

  echo "Checking Market Insights frontend: $MARKET_INSIGHTS_FRONTEND_URL"
  if ! wait_http_ok "$MARKET_INSIGHTS_FRONTEND_URL" "$HEALTH_TIMEOUT_SECONDS" "$POLL_INTERVAL_SECONDS"; then
    echo "Error: Market Insights frontend is not reachable at $MARKET_INSIGHTS_FRONTEND_URL"
    exit 1
  fi

  if [ "$RUN_E2E_CHAT_TEST" = "true" ]; then
    echo "Running Market Insights end-to-end chat test..."
    response=$(curl -fsS \
      -H "Content-Type: application/json" \
      -X POST \
      -d '{"ticker":"AAPL","question":"Reponds avec exactement OK","llm_backend":"litellm","llm_model":"local-private","language":"fr","top_k":2}' \
      http://localhost:8000/llm/chat)
    echo "$response" | grep -Eq '"provider"[[:space:]]*:[[:space:]]*"litellm"'
    echo "$response" | grep -Eq '"model"[[:space:]]*:[[:space:]]*"local-private"'
    echo "market_insights_e2e_chat_test: OK"
  fi

  docker compose ps
  echo "Market Insights dev stack is ready with shared LiteLLM gateway."
  exit 0
fi

docker compose up --build