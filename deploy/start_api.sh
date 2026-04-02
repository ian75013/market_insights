#!/bin/sh
set -eu

echo "[start_api] starting Market Insights API"

# Runtime switches (override from compose env if needed).
: "${MI_RUN_SEED:=false}"
: "${MI_WAIT_DNS:=true}"
: "${MI_DNS_MAX_ATTEMPTS:=8}"
: "${MI_DNS_WAIT_SECONDS:=2}"
: "${MI_DNS_HOSTS:=data.sec.gov news.google.com}"
: "${MI_API_HOST:=0.0.0.0}"
: "${MI_API_PORT:=8000}"
: "${MI_API_WORKERS:=1}"
: "${MI_API_RELOAD:=false}"
: "${MI_API_PROXY_HEADERS:=false}"
: "${MI_API_FORWARDED_ALLOW_IPS:=*}"

if [ "$MI_WAIT_DNS" = "true" ]; then
  echo "[start_api] dns precheck enabled for hosts: $MI_DNS_HOSTS"
  python - "$MI_DNS_MAX_ATTEMPTS" "$MI_DNS_WAIT_SECONDS" $MI_DNS_HOSTS <<'PY'
import socket
import sys
import time

max_attempts = int(sys.argv[1])
wait_s = float(sys.argv[2])
hosts = sys.argv[3:]

for host in hosts:
    ok = False
    for attempt in range(1, max_attempts + 1):
        try:
            socket.getaddrinfo(host, 443)
            print(f"[start_api] dns ok for {host} (attempt {attempt})")
            ok = True
            break
        except OSError as exc:
            print(f"[start_api] dns pending for {host} (attempt {attempt}/{max_attempts}): {exc}")
            if attempt < max_attempts:
                time.sleep(wait_s)
    if not ok:
        print(f"[start_api] dns precheck failed for {host}, continuing startup")
PY
fi

if [ "$MI_RUN_SEED" = "true" ]; then
  echo "[start_api] running demo seed"
  python -m market_insights.scripts.seed_demo_data
fi

if [ "$MI_API_RELOAD" = "true" ]; then
  echo "[start_api] launching uvicorn in reload mode on ${MI_API_HOST}:${MI_API_PORT}"
  if [ "$MI_API_PROXY_HEADERS" = "true" ]; then
    exec uvicorn market_insights.api.main:app \
      --host "$MI_API_HOST" \
      --port "$MI_API_PORT" \
      --proxy-headers \
      --forwarded-allow-ips "$MI_API_FORWARDED_ALLOW_IPS" \
      --reload \
      --reload-dir market_insights
  fi
  exec uvicorn market_insights.api.main:app \
    --host "$MI_API_HOST" \
    --port "$MI_API_PORT" \
    --reload \
    --reload-dir market_insights
fi

echo "[start_api] launching uvicorn with ${MI_API_WORKERS} worker(s) on ${MI_API_HOST}:${MI_API_PORT}"
if [ "$MI_API_PROXY_HEADERS" = "true" ]; then
  exec uvicorn market_insights.api.main:app \
    --host "$MI_API_HOST" \
    --port "$MI_API_PORT" \
    --workers "$MI_API_WORKERS" \
    --proxy-headers \
    --forwarded-allow-ips "$MI_API_FORWARDED_ALLOW_IPS"
fi
exec uvicorn market_insights.api.main:app \
  --host "$MI_API_HOST" \
  --port "$MI_API_PORT" \
  --workers "$MI_API_WORKERS"
