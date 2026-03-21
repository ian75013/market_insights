#!/usr/bin/env bash
set -euo pipefail

DOMAIN="market-insight.doctumconsilium.com"
EMAIL="contact@doctumconsilium.com"
CONF_DIR="deploy/nginx/conf.d"
SSL_CONF="$CONF_DIR/market-insight.conf"
INIT_CONF="$CONF_DIR/market-insight-init.conf.disabled"

cmd=${1:-help}

case $cmd in
  init)
    echo "══ Installation initiale ══"
    [ ! -f .env ] && cp .env.example .env && echo "→ .env créé — éditez-le"
    docker compose build
    echo "→ Build OK. Étapes suivantes :"
    echo "  1. nano .env"
    echo "  2. ./deploy.sh ssl"
    echo "  3. ./deploy.sh up"
    ;;

  ssl)
    echo "══ Obtention du certificat SSL ══"
    [ -f "$SSL_CONF" ] && mv "$SSL_CONF" "${SSL_CONF}.bak"
    cp "$INIT_CONF" "${INIT_CONF%.disabled}"
    docker compose up -d api frontend nginx
    sleep 10
    docker compose run --rm certbot certonly \
      --webroot --webroot-path /var/www/certbot \
      --email "$EMAIL" --agree-tos --no-eff-email \
      -d "$DOMAIN"
    rm -f "${INIT_CONF%.disabled}"
    [ -f "${SSL_CONF}.bak" ] && mv "${SSL_CONF}.bak" "$SSL_CONF"
    docker compose exec nginx nginx -s reload 2>/dev/null || docker compose restart nginx
    echo "══ SSL activé pour $DOMAIN ══"
    ;;

  up)
    docker compose up -d
    echo "→ https://$DOMAIN"
    echo "→ https://$DOMAIN/api/health"
    echo "→ https://$DOMAIN/docs"
    ;;

  down)       docker compose down ;;
  restart)    docker compose restart ;;
  logs)       docker compose logs -f --tail=100 ${2:-} ;;
  update)     git pull && docker compose build && docker compose up -d && echo "→ Mis à jour" ;;
  ssl-renew)  docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload ;;
  status)     docker compose ps ;;
  seed)       docker compose exec api python -m market_insights.scripts.seed_demo_data ;;

  *)
    echo "Usage: ./deploy.sh {init|ssl|up|down|restart|logs|update|ssl-renew|status|seed}"
    ;;
esac
