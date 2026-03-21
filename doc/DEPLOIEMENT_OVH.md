# Deploiement Production - market-insight.doctumconsilium.com

Ce document decrit un deploiement Docker sur un VPS OVH avec:
- Frontend React compile (sans code source de build expose dans l'image runtime)
- Backend FastAPI
- Reverse proxy Nginx en 80/443
- Certificat TLS Let's Encrypt

## 1) Prerequis

- Un VPS OVH Linux (Ubuntu 22.04/24.04 recommande)
- Docker et plugin Docker Compose installes
- Un nom de domaine gerable en DNS
- Acces SSH au VPS

## 2) DNS

Dans votre zone DNS, creer:
- Type: A
- Sous-domaine: market-insight
- Cible: IP publique du VPS
- FQDN final: market-insight.doctumconsilium.com

Verifier la resolution:

```bash
nslookup market-insight.doctumconsilium.com
```

## 3) Installation des dependances sur le VPS

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin certbot curl
sudo systemctl enable --now docker
```

Optionnel (utilisateur non-root):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 4) Pare-feu

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

Creer/adapter le fichier .env a la racine:

```env
APP_ENV=prod
APP_NAME=Market Insights
DATABASE_URL=sqlite:///./market_insights.db

OPENAI_API_KEY=
LLM_BACKEND=fallback

USE_NETWORK=true
DEFAULT_PRICE_PROVIDER=auto

ALPHA_VANTAGE_API_KEY=
FRED_API_KEY=
FMP_API_KEY=

IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=1
```

## 7) Certificat TLS (premiere emission)

Arreter tout service occupant le port 80 (nginx systeme, apache, etc.), puis lancer:

```bash
sudo certbot certonly --standalone \
  -d market-insight.doctumconsilium.com \
  --agree-tos \
  -m votre-email@domaine.com \
  --no-eff-email
```

Certificats attendus:
- /etc/letsencrypt/live/market-insight.doctumconsilium.com/fullchain.pem
- /etc/letsencrypt/live/market-insight.doctumconsilium.com/privkey.pem

## 8) Demarrer l'application

Depuis la racine du repo:

```bash
docker compose up -d --build
```

Verifier:

```bash
docker compose ps
docker compose logs -f nginx
docker compose logs -f api
```

## 9) Verification fonctionnelle

```bash
curl -I http://market-insight.doctumconsilium.com
curl -I https://market-insight.doctumconsilium.com
curl -s https://market-insight.doctumconsilium.com/api/health
```

Resultat attendu:
- HTTP redirige vers HTTPS
- Le frontend charge sur /
- L'API repond via /api/*

## 10) Renouvellement automatique TLS

Configurer cron root:

```bash
sudo crontab -e
```

Ajouter:

```cron
0 3 * * * certbot renew --quiet --deploy-hook "cd /home/ubuntu/market_insights && docker compose restart nginx"
```

Adapter le chemin du repository selon votre serveur.

## 11) Mise a jour applicative

```bash
cd /home/ubuntu/market_insights
git fetch --all
git checkout prod
git pull --ff-only origin prod
docker compose up -d --build
```

## 12) Rollback rapide

Lister les commits:

```bash
git log --oneline -n 10
```

Revenir au commit precedent:

```bash
git checkout prod
git reset --hard <commit_id>
docker compose up -d --build
```

## 13) Depannage

- Erreur TLS au demarrage Nginx:
  - verifier la presence des certificats dans /etc/letsencrypt/live/market-insight.doctumconsilium.com/
- Erreur 502 sur /api:
  - verifier le container api: `docker compose logs -f api`
- Le domaine ne repond pas:
  - verifier DNS (A record), ports 80/443 ouverts, et firewall OVH Cloud
- Conflit de ports 80/443:
  - stopper nginx/apache host avant lancement des containers

## 14) Architecture cible

- nginx (public): 80/443
- frontend (interne): 80
- api (interne): 8000

Le trafic est route ainsi:
- / -> frontend React
- /api/* -> backend FastAPI
