#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${1:-deploy}"
DEFAULT_ENV_FILE="$ROOT_DIR/.env.ovh"
if [ ! -f "$DEFAULT_ENV_FILE" ]; then
  DEFAULT_ENV_FILE="$ROOT_DIR/scripts/deploy/env.ovh.example"
fi
ENV_FILE="${2:-$DEFAULT_ENV_FILE}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

case "$MODE" in
  deploy)
    bash "$ROOT_DIR/scripts/deploy/deploy.sh" ovh-apache
    ;;
  proxy)
    bash "$ROOT_DIR/scripts/deploy/deploy.sh" ovh-proxy
    ;;
  *)
    echo "Usage: scripts/deploy/deploy.ovh.sh [deploy|proxy] [env-file]" >&2
    exit 1
    ;;
esac
