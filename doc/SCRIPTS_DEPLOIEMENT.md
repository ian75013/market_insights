# Scripts de deploiement

Ce document explique les scripts ajoutes dans scripts/deploy pour deployer market_insights, en priorite sur OVH derriere Apache2.

## 1) Dossier et role de chaque fichier

- scripts/deploy/deploy.sh
  Orchestrateur principal (cibles de deploiement)

- scripts/deploy/deploy.ovh.sh
  Wrapper OVH, avec 2 modes:
  - deploy : deploiement complet (docker + config Apache)
  - proxy : reconfiguration du reverse proxy Apache uniquement

- scripts/deploy/deploy.aws.sh
- scripts/deploy/deploy.azure.sh
- scripts/deploy/deploy.k3s.sh
  Wrappers de cibles reservees (non cablees completement pour ce repo)

- scripts/deploy/env.ovh.example
  Variables OVH a copier/modifier pour ton VPS

- scripts/deploy/env.ovh.demo.example
  Exemple rempli avec valeurs de demonstration

- scripts/deploy/env.example, env.aws.example, env.azure.example, env.k3s.example
  Exemples de variables pour autres cibles

## 2) Quick start OVH (Apache2 deja installe sur le VPS)

1. Creer ton fichier env local:
   cp scripts/deploy/env.ovh.example .env.ovh

2. Editer .env.ovh et renseigner au minimum:
   - SSH_USER
   - SSH_HOST
   - GIT_REPO
   - APP_DOMAIN
   - SSL_CERT
   - SSL_KEY

3. Lancer le deploiement complet:
   bash scripts/deploy/deploy.ovh.sh deploy .env.ovh

4. Reappliquer seulement le vhost Apache:
   bash scripts/deploy/deploy.ovh.sh proxy .env.ovh

## 3) Ce que fait deploy ovh

Mode deploy:
- Bootstrap du repo sur le VPS (clone ou sync branche)
- Sync overlay local (optionnel)
- Lancement docker compose avec docker-compose.ovh-apache.yml
- Application du template Apache2
  deploy/apache2/market-insight.ovh.example.conf

Mode proxy:
- Regenere le vhost Apache2 depuis le template
- Active modules Apache necessaires
- Reload Apache apres validation config

## 4) Variables importantes (OVH)

- SSH_USER, SSH_HOST, SSH_PORT
  Connexion SSH au VPS

- GIT_REPO, GIT_BRANCH, APP_DIR
  Source Git distante et dossier de deploiement sur VPS

- COMPOSE_FILE
  Fichier compose a lancer sur VPS
  Defaut recommande: docker-compose.ovh-apache.yml

- APP_DOMAIN
  Domaine public frontend/API (avec routage /api)

- SSL_CERT, SSL_KEY
  Chemins certificats pour Apache

- ENABLE_APACHE_CONFIG
  true: applique aussi la config Apache
  false: ne touche pas Apache

- SYNC_LOCAL_OVERLAY
  true: copie les modifications locales non poussees sur le VPS
  false: deploiement strict depuis Git distant

- ASK_SUDO_PASSWORD
  true recommande pour eviter de stocker SUDO_PASSWORD en clair

## 5) Securite et bonnes pratiques

- Preferer ASK_SUDO_PASSWORD=true
- Eviter SUDO_PASSWORD dans les fichiers versionnes
- Utiliser une cle SSH et des permissions minimales
- Garder APP_DOMAIN et certificats coherents avec le DNS

## 6) Verification apres deploiement

Depuis le VPS:
- docker compose -f docker-compose.ovh-apache.yml ps
- docker compose -f docker-compose.ovh-apache.yml logs -f api
- curl -s http://127.0.0.1:18000/health
- curl -I http://127.0.0.1:18080

Depuis ton poste:
- curl -I https://<ton-domaine>
- curl -s https://<ton-domaine>/api/health

## 7) Depannage rapide

- Erreur ssh/scp:
  verifier SSH_USER, SSH_HOST, SSH_PORT, acces cle SSH

- Erreur cert Apache:
  verifier SSL_CERT et SSL_KEY, puis apache2ctl configtest

- 502 sur /api:
  verifier que l API tourne et ecoute sur 127.0.0.1:18000

- Front indisponible:
  verifier 127.0.0.1:18080 et logs frontend

## 8) Lien avec la doc OVH

Pour la procedure infra complete OVH (DNS, firewall, certbot, checks), voir:
- doc/DEPLOIEMENT_OVH.md
