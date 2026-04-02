# Deployment Production OVH (Apache2 reverse proxy)

Ce document decrit un deploiement Docker sur VPS OVH dans ton contexte actuel:
- Apache2 deja installe sur l'hote (public 80/443)
- React frontend en conteneur (port local 18080)
- FastAPI backend en conteneur (port local 18000)
- PostgreSQL en conteneur
- TLS gere par Apache2 + Certbot cote hote

## 1) Architecture cible

- Apache2 (hote): 80/443 publics
- frontend container: 127.0.0.1:18080 (non expose Internet)
- api container: 127.0.0.1:18000 (non expose Internet)
- db container: interne Docker uniquement

Routage:
- / -> frontend React
- /api/* -> backend FastAPI

Scripts d automatisation disponibles:
- doc/SCRIPTS_DEPLOIEMENT.md

## 2) Prerequis

- VPS OVH Linux (Ubuntu 22.04/24.04)
- Docker + plugin Compose
- Apache2
- Certbot + plugin Apache
- Domaine pointe vers le VPS

Installation type:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin apache2 certbot python3-certbot-apache curl
sudo systemctl enable --now docker
sudo systemctl enable --now apache2
```

Optionnel (utilisateur non-root):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 3) DNS

Creer un enregistrement A:
- host: market-insight
- cible: IP publique OVH
- FQDN: market-insight.doctumconsilium.com

Verification:

```bash
nslookup market-insight.doctumconsilium.com
```

## 4) Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

## 5) Recuperer le projet

```bash
git clone git@github.com:ian75013/market_insights.git
cd market_insights
```

## 6) Variables d'environnement

Creer/adapter `.env` a la racine (minimum):

```env
POSTGRES_USER=market_insights
POSTGRES_PASSWORD=change-me
POSTGRES_DB=market_insights

USE_NETWORK=true
DEFAULT_PRICE_PROVIDER=auto

LLM_BACKEND=litellm
LLM_MODEL=local-private
LITELLM_BASE_URL=http://litellm:4000
LITELLM_API_KEY=

MI_API_WORKERS=2
MI_RUN_SEED=false
```

## 7) Lancer la stack Docker (mode Apache)

Depuis la racine du repo:

```bash
docker compose -f docker-compose.ovh-apache.yml up -d --build
```

Verifier:

```bash
docker compose -f docker-compose.ovh-apache.yml ps
docker compose -f docker-compose.ovh-apache.yml logs -f api
docker compose -f docker-compose.ovh-apache.yml logs -f frontend
```

Sanity checks locaux sur le VPS:

```bash
curl -s http://127.0.0.1:18000/health
curl -I http://127.0.0.1:18080
```

## 8) Configurer Apache2 reverse proxy

Le template adapte est fourni dans:
- `deploy/apache2/market-insight.ovh.example.conf`

Installation:

```bash
sudo cp deploy/apache2/market-insight.ovh.example.conf /etc/apache2/sites-available/market-insight.conf
```

Editer puis remplacer ces placeholders:
- `__APP_DOMAIN__` -> ton domaine (ex: market-insight.doctumconsilium.com)
- `__SSL_CERT__` -> /etc/letsencrypt/live/<domaine>/fullchain.pem
- `__SSL_KEY__` -> /etc/letsencrypt/live/<domaine>/privkey.pem

Activer modules + site:

```bash
sudo a2enmod proxy proxy_http headers ssl rewrite
sudo a2ensite market-insight.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

## 9) Certificat TLS (Apache)

Si le certificat n'existe pas encore:

```bash
sudo certbot --apache -d market-insight.doctumconsilium.com
```

Puis recharger Apache:

```bash
sudo apache2ctl configtest && sudo systemctl reload apache2
```

## 10) Verification fonctionnelle

```bash
curl -I http://market-insight.doctumconsilium.com
curl -I https://market-insight.doctumconsilium.com
curl -s https://market-insight.doctumconsilium.com/api/health
```

Attendu:
- HTTP redirige vers HTTPS
- frontend disponible sur /
- API disponible sous /api/*

## 11) Renouvellement TLS

Test de renouvellement:

```bash
sudo certbot renew --dry-run
```

Certbot installe normalement un timer systemd. Verification:

```bash
systemctl list-timers | grep certbot
```

## 12) Mise a jour applicative

```bash
cd /home/ubuntu/market_insights
git fetch --all
git checkout prod
git pull --ff-only origin prod
docker compose -f docker-compose.ovh-apache.yml up -d --build
```

## 13) Depannage

- 502 sur /api:
  - verifier l'API: `docker compose -f docker-compose.ovh-apache.yml logs -f api`
  - verifier le proxy Apache cible bien `127.0.0.1:18000`
- frontend inaccessible:
  - verifier `curl -I http://127.0.0.1:18080`
- erreur TLS Apache:
  - verifier chemins cert/key dans le vhost
  - `sudo apache2ctl configtest`
- domaine non resolu:
  - verifier A record OVH + firewall

