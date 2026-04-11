# Deployment Production OVH (Apache2 reverse proxy)

Ce guide couvre le deploiement de `market_insights` sur VPS OVH avec Apache2 sur l'hote.

## 1) Architecture cible

- Apache2 (hote): ports publics 80 et 443
- API conteneur: 127.0.0.1:18000
- Frontend conteneur: 127.0.0.1:18080
- PostgreSQL: reseau Docker interne

Option Airflow (nouveau):

- Airflow webserver: `127.0.0.1:8080` (ou IP VPN via `AIRFLOW_WEBSERVER_BIND`)
- Airflow scheduler + metadata DB: reseau Docker interne

Routage public:

- `/` -> frontend React
- `/api/*` -> FastAPI

## 2) Prerequis VPS

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

Configurer un enregistrement A:

- `market-insight.doctumconsilium.com` -> IP publique OVH

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

## 5) Deploiement automatise (recommande)

1. Creer ton fichier de variables OVH:

```bash
cp scripts/deploy/env.ovh.example .env.ovh
```

2. Editer `.env.ovh` avec au minimum:

- `SSH_USER`
- `SSH_HOST`
- `GIT_REPO`
- `APP_DOMAIN`
- `CERTBOT_EMAIL` (si `CERTBOT_AUTOCONFIG=true`)

Pour integrer Airflow en production:

- `COMPOSE_FILES=docker-compose.ovh-apache.yml,docker-compose.airflow.yml`
- variables Airflow (`AIRFLOW_FERNET_KEY`, `AIRFLOW_SECRET_KEY`, `AIRFLOW_ADMIN_PASSWORD`)
- pour VPN uniquement: `AIRFLOW_WEBSERVER_BIND=<IP_VPN_DU_SERVEUR>`

Flags recommandes:

- `SYNC_LOCAL_OVERLAY=true`
- `SYNC_DOTENV=true`
- `ENABLE_APACHE_CONFIG=true`
- `CERTBOT_AUTOCONFIG=true`

3. Lancer le deploiement complet:

```bash
bash scripts/deploy/deploy.ovh.sh deploy .env.ovh
```

Ce mode automatise:

- bootstrap/sync du code sur VPS
- sync du `.env` local vers le VPS (`chmod 600`)
- `docker compose` sur `docker-compose.ovh-apache.yml`
- Certbot (optionnel selon flag)
- generation + activation du vhost Apache

Quand `COMPOSE_FILES` inclut `docker-compose.airflow.yml`, le deploiement lance aussi
`mi-airflow-db`, `mi-airflow-scheduler` et `mi-airflow-webserver`.

## 6) Verification

Depuis le VPS:

```bash
docker compose -f docker-compose.ovh-apache.yml ps
docker compose -f docker-compose.ovh-apache.yml logs -f api
curl -s http://127.0.0.1:18000/health
curl -I http://127.0.0.1:18080

# Si Airflow est active:
docker compose -f docker-compose.ovh-apache.yml -f docker-compose.airflow.yml ps
docker logs --tail=200 mi-airflow-scheduler
docker logs --tail=200 mi-airflow-webserver
```

Depuis ton poste:

```bash
curl -I https://market-insight.doctumconsilium.com
curl -s https://market-insight.doctumconsilium.com/api/health
```

## 7) Reappliquer uniquement le proxy Apache

```bash
bash scripts/deploy/deploy.ovh.sh proxy .env.ovh
```

## 8) Depannage rapide

- Erreur SSH/SCP:
  - verifier `SSH_USER`, `SSH_HOST`, `SSH_PORT`
- Erreur Certbot:
  - verifier DNS du domaine
  - verifier que 80/443 sont atteignables
- Erreur Apache:
  - `sudo apache2ctl configtest`
  - `sudo systemctl status apache2 --no-pager`
- 502 sur `/api`:
  - verifier API locale sur `127.0.0.1:18000`

- Airflow UI inaccessible sur VPN:
  - verifier `AIRFLOW_WEBSERVER_BIND` (doit etre l'IP VPN du serveur)
  - verifier que le client est connecte au VPN
  - verifier les regles firewall VPN sur le port 8080
