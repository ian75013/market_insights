#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="${APP_NAME:-market-insights}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

log() {
  echo "[deploy] $*"
}

die() {
  echo "[deploy][error] $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

remote_sudo_mode() {
  if [ "${ASK_SUDO_PASSWORD:-false}" = "true" ]; then
    printf '%s' "prompt"
  elif [ -n "${SUDO_PASSWORD:-}" ]; then
    printf '%s' "stdin"
  else
    printf '%s' "plain"
  fi
}

write_remote_sudo_helpers() {
  local mode="$1"
  cat <<EOF
run_sudo() {
  if [ "$mode" = "prompt" ]; then
    sudo -v
    sudo "\$@"
  elif [ "$mode" = "stdin" ]; then
    printf '%s\\n' "\${SUDO_PASSWORD}" | sudo -S -p '' "\$@"
  else
    sudo "\$@"
  fi
}
EOF
}

remote_sync_workspace_overlay() {
  local ssh_target="$1"
  local ssh_port="$2"
  local app_dir="$3"

  tar \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    --exclude='market_insights.db' \
    --exclude='deploy copy' \
    --exclude='deploy copy 2' \
    -czf - \
    -C "$ROOT_DIR" . | ssh -p "$ssh_port" "$ssh_target" "mkdir -p $(printf %q "$app_dir") && tar -xzf - -C $(printf %q "$app_dir")"
}

remote_sync_dotenv() {
  local ssh_target="$1"
  local ssh_port="$2"
  local app_dir="$3"
  local local_env="${LOCAL_ENV_FILE:-$ROOT_DIR/.env}"

  if [[ "$local_env" != /* ]]; then
    local_env="$ROOT_DIR/$local_env"
  fi

  [ -f "$local_env" ] || die "Missing local .env at $local_env"

  scp -P "$ssh_port" "$local_env" "$ssh_target:$app_dir/.env" >/dev/null
  ssh -p "$ssh_port" "$ssh_target" "chmod 600 $(printf %q "$app_dir/.env")"
}

remote_bootstrap_repo() {
  local ssh_target="$1"
  local ssh_port="$2"
  local app_dir="$3"
  local git_repo="$4"
  local git_branch="$5"
  local sudo_password="${SUDO_PASSWORD:-}"
  local remote_user="${ssh_target%@*}"
  local sudo_mode
  sudo_mode="$(remote_sudo_mode)"
  local ssh_tty_args=()
  local tmp_local_script
  local tmp_remote_script

  if [ "$sudo_mode" = "prompt" ]; then
    ssh_tty_args=(-tt)
  fi

  tmp_local_script="$(mktemp)"
  tmp_remote_script="/tmp/${APP_NAME}-bootstrap-repo.sh"

  cat > "$tmp_local_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

$(write_remote_sudo_helpers "$sudo_mode")

if ! command -v git >/dev/null 2>&1; then
  run_sudo apt-get update
  run_sudo apt-get install -y git
fi
run_sudo mkdir -p "${app_dir}"
run_sudo chown -R "${remote_user}:${remote_user}" "${app_dir}"
if [ ! -d "${app_dir}/.git" ]; then
  git clone "${git_repo}" "${app_dir}"
fi
cd "${app_dir}"
git remote set-url origin "${git_repo}"
git fetch --all --prune
git reset --hard HEAD
git clean -fd
git checkout -B "${git_branch}" "origin/${git_branch}"
EOF

  chmod +x "$tmp_local_script"
  scp -P "$ssh_port" "$tmp_local_script" "${ssh_target}:${tmp_remote_script}" >/dev/null
  ssh "${ssh_tty_args[@]}" -p "$ssh_port" "$ssh_target" "SUDO_PASSWORD=$(printf %q "$sudo_password") bash ${tmp_remote_script}"
  rm -f "$tmp_local_script"
}

run_remote_ovh_deploy() {
  local ssh_target="$1"
  local ssh_port="$2"
  local app_dir="$3"
  local compose_file="$4"
  local compose_files="$5"
  local sudo_mode="$6"
  local api_bind_port="$7"
  local frontend_bind_port="$8"
  local airflow_webserver_bind="$9"
  local airflow_webserver_port="${10}"
  local sudo_password="${SUDO_PASSWORD:-}"
  local ssh_tty_args=()
  local tmp_local_script
  local tmp_remote_script

  if [ "$sudo_mode" = "prompt" ]; then
    ssh_tty_args=(-tt)
  fi

  tmp_local_script="$(mktemp)"
  tmp_remote_script="/tmp/${APP_NAME}-ovh-docker.sh"

  cat > "$tmp_local_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

$(write_remote_sudo_helpers "$sudo_mode")

cd "${app_dir}"

IMAGE_TAG=$(printf '%q' "$IMAGE_TAG")
COMPOSE_FILE=$(printf '%q' "$compose_file")
COMPOSE_FILES=$(printf '%q' "$compose_files")
API_BIND_PORT=$(printf '%q' "$api_bind_port")
FRONTEND_BIND_PORT=$(printf '%q' "$frontend_bind_port")
AIRFLOW_WEBSERVER_BIND=$(printf '%q' "$airflow_webserver_bind")
AIRFLOW_WEBSERVER_PORT=$(printf '%q' "$airflow_webserver_port")

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  run_sudo usermod -aG docker "${ssh_target%@*}" || true
fi

if ! run_sudo docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required" >&2
  exit 1
fi

compose_files_str="\${COMPOSE_FILES}"
if [ -z "\${compose_files_str}" ]; then
  compose_files_str="\${COMPOSE_FILE}"
fi

IFS=',' read -r -a compose_files_arr <<< "\${compose_files_str}"
compose_args=()
for f in "\${compose_files_arr[@]}"; do
  [ -n "\$f" ] || continue
  if [ ! -f "\$f" ]; then
    echo "Missing compose file: \$f" >&2
    exit 1
  fi
  compose_args+=( -f "\$f" )
done

if [ "\${#compose_args[@]}" -eq 0 ]; then
  echo "No compose files resolved. Set COMPOSE_FILE or COMPOSE_FILES." >&2
  exit 1
fi

if ! command -v ss >/dev/null 2>&1; then
  run_sudo apt-get update
  run_sudo apt-get install -y iproute2
fi

port_in_use() {
  local p="$1"
  ss -ltn "sport = :\${p}" | awk 'NR>1 {print}' | grep -q .
}

docker_owns_port() {
  local p="$1"
  run_sudo docker ps --format '{{.Ports}}' | grep -qE "(^|[ ,])[^,]*:\${p}->"
}

resolve_port() {
  local name="$1"
  local wanted="$2"

  if ! port_in_use "\${wanted}"; then
    printf '%s' "\${wanted}"
    return 0
  fi

  if docker_owns_port "\${wanted}"; then
    printf '%s' "\${wanted}"
    return 0
  fi

  echo "[deploy][error] Host port \${wanted} is already in use on VPS (\${name})." >&2
  echo "[deploy][error] Stop now and choose a free port before deploying." >&2
  ss -ltnp "sport = :\${wanted}" || true
  exit 1
}

airflow_enabled=false
for f in "\${compose_files_arr[@]}"; do
  if [ "\$f" = "docker-compose.airflow.yml" ]; then
    airflow_enabled=true
    break
  fi
done

API_BIND_PORT="\$(resolve_port API_BIND_PORT "\${API_BIND_PORT:-18000}")"
FRONTEND_BIND_PORT="\$(resolve_port FRONTEND_BIND_PORT "\${FRONTEND_BIND_PORT:-18080}")"

if [ "\$airflow_enabled" = true ]; then
  AIRFLOW_WEBSERVER_PORT="\$(resolve_port AIRFLOW_WEBSERVER_PORT "\${AIRFLOW_WEBSERVER_PORT:-18089}")"
  if [ "\${AIRFLOW_WEBSERVER_BIND:-127.0.0.1}" != "127.0.0.1" ] && ! ip -o addr show | grep -q " \${AIRFLOW_WEBSERVER_BIND}/"; then
    echo "[deploy][error] AIRFLOW_WEBSERVER_BIND=\${AIRFLOW_WEBSERVER_BIND} is not configured on the VPS." >&2
    exit 1
  fi
fi

run_sudo env \
  IMAGE_TAG="\${IMAGE_TAG}" \
  API_BIND_PORT="\${API_BIND_PORT:-18000}" \
  FRONTEND_BIND_PORT="\${FRONTEND_BIND_PORT:-18080}" \
  AIRFLOW_WEBSERVER_BIND="\${AIRFLOW_WEBSERVER_BIND:-127.0.0.1}" \
  AIRFLOW_WEBSERVER_PORT="\${AIRFLOW_WEBSERVER_PORT:-18089}" \
  docker compose "\${compose_args[@]}" up -d --build --remove-orphans
run_sudo env \
  IMAGE_TAG="\${IMAGE_TAG}" \
  API_BIND_PORT="\${API_BIND_PORT:-18000}" \
  FRONTEND_BIND_PORT="\${FRONTEND_BIND_PORT:-18080}" \
  AIRFLOW_WEBSERVER_BIND="\${AIRFLOW_WEBSERVER_BIND:-127.0.0.1}" \
  AIRFLOW_WEBSERVER_PORT="\${AIRFLOW_WEBSERVER_PORT:-18089}" \
  docker compose "\${compose_args[@]}" ps
EOF

  chmod +x "$tmp_local_script"
  scp -P "$ssh_port" "$tmp_local_script" "${ssh_target}:${tmp_remote_script}" >/dev/null
  ssh "${ssh_tty_args[@]}" -p "$ssh_port" "$ssh_target" "SUDO_PASSWORD=$(printf %q "$sudo_password") bash ${tmp_remote_script}"
  rm -f "$tmp_local_script"
}

run_remote_apache_config() {
  local ssh_target="$1"
  local ssh_port="$2"
  local app_dir="$3"
  local app_domain="$4"
  local ssl_cert="$5"
  local ssl_key="$6"
  local api_bind_port="$7"
  local frontend_bind_port="$8"
  local sudo_mode="$9"
  local sudo_password="${SUDO_PASSWORD:-}"
  local ssh_tty_args=()
  local tmp_local_script
  local tmp_remote_script

  if [ "$sudo_mode" = "prompt" ]; then
    ssh_tty_args=(-tt)
  fi

  tmp_local_script="$(mktemp)"
  tmp_remote_script="/tmp/${APP_NAME}-apache-proxy.sh"

  cat > "$tmp_local_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

$(write_remote_sudo_helpers "$sudo_mode")

cd "${app_dir}"

if ! command -v apache2ctl >/dev/null 2>&1; then
  run_sudo apt-get update
  run_sudo apt-get install -y apache2
fi

template="deploy/apache2/market-insight.ovh.example.conf"
if [ ! -f "\$template" ]; then
  echo "Missing Apache template: \$template" >&2
  exit 1
fi

tmp_conf="/tmp/market-insight.conf"
sed \
  -e "s|__APP_DOMAIN__|${app_domain}|g" \
  -e "s|__SSL_CERT__|${ssl_cert}|g" \
  -e "s|__SSL_KEY__|${ssl_key}|g" \
  -e "s|__API_BIND_PORT__|${api_bind_port}|g" \
  -e "s|__FRONTEND_BIND_PORT__|${frontend_bind_port}|g" \
  "\$template" > "\$tmp_conf"

run_sudo install -m 644 "\$tmp_conf" /etc/apache2/sites-available/market-insight.conf
run_sudo a2enmod proxy proxy_http headers ssl rewrite >/dev/null
run_sudo a2ensite market-insight.conf >/dev/null
run_sudo apache2ctl configtest
run_sudo systemctl reload apache2
EOF

  chmod +x "$tmp_local_script"
  scp -P "$ssh_port" "$tmp_local_script" "${ssh_target}:${tmp_remote_script}" >/dev/null
  ssh "${ssh_tty_args[@]}" -p "$ssh_port" "$ssh_target" "SUDO_PASSWORD=$(printf %q "$sudo_password") bash ${tmp_remote_script}"
  rm -f "$tmp_local_script"
}

run_remote_certbot() {
  local ssh_target="$1"
  local ssh_port="$2"
  local app_domain="$3"
  local certbot_email="$4"
  local sudo_mode="$5"
  local sudo_password="${SUDO_PASSWORD:-}"
  local ssh_tty_args=()
  local tmp_local_script
  local tmp_remote_script

  if [ "$sudo_mode" = "prompt" ]; then
    ssh_tty_args=(-tt)
  fi

  tmp_local_script="$(mktemp)"
  tmp_remote_script="/tmp/${APP_NAME}-certbot.sh"

  cat > "$tmp_local_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

$(write_remote_sudo_helpers "$sudo_mode")

if ! command -v certbot >/dev/null 2>&1; then
  run_sudo apt-get update
  run_sudo apt-get install -y certbot python3-certbot-apache
fi

# Prevent apache plugin failures if an old vhost references missing cert files.
if [ -f /etc/apache2/sites-enabled/market-insight.conf ]; then
  run_sudo a2dissite market-insight.conf >/dev/null || true
  run_sudo systemctl reload apache2 || true
fi

run_sudo certbot certonly --apache \
  --non-interactive \
  --agree-tos \
  --keep-until-expiring \
  --cert-name "${app_domain}" \
  --email "${certbot_email}" \
  -d "${app_domain}"
EOF

  chmod +x "$tmp_local_script"
  scp -P "$ssh_port" "$tmp_local_script" "${ssh_target}:${tmp_remote_script}" >/dev/null
  ssh "${ssh_tty_args[@]}" -p "$ssh_port" "$ssh_target" "SUDO_PASSWORD=$(printf %q "$sudo_password") bash ${tmp_remote_script}"
  rm -f "$tmp_local_script"
}

deploy_ovh_apache() {
  require_cmd ssh
  require_cmd scp

  local ssh_user="${SSH_USER:-}"
  local ssh_host="${SSH_HOST:-}"
  local ssh_port="${SSH_PORT:-22}"
  local app_dir="${APP_DIR:-/opt/market_insights}"
  local git_repo="${GIT_REPO:-}"
  local git_branch="${GIT_BRANCH:-main}"
  local compose_file="${COMPOSE_FILE:-docker-compose.ovh-apache.yml}"
  local compose_files="${COMPOSE_FILES:-}"
  local sync_overlay="${SYNC_LOCAL_OVERLAY:-true}"
  local sync_dotenv="${SYNC_DOTENV:-true}"
  local enable_apache="${ENABLE_APACHE_CONFIG:-true}"
  local certbot_autoconfig="${CERTBOT_AUTOCONFIG:-false}"
  local certbot_email="${CERTBOT_EMAIL:-}"
  local app_domain="${APP_DOMAIN:-}"
  local ssl_cert="${SSL_CERT:-/etc/letsencrypt/live/${APP_DOMAIN}/fullchain.pem}"
  local ssl_key="${SSL_KEY:-/etc/letsencrypt/live/${APP_DOMAIN}/privkey.pem}"
  local api_bind_port="${API_BIND_PORT:-18000}"
  local frontend_bind_port="${FRONTEND_BIND_PORT:-18080}"
  local airflow_webserver_bind="${AIRFLOW_WEBSERVER_BIND:-127.0.0.1}"
  local airflow_webserver_port="${AIRFLOW_WEBSERVER_PORT:-18089}"
  local sudo_mode

  [ -n "$ssh_user" ] || die "SSH_USER is required"
  [ -n "$ssh_host" ] || die "SSH_HOST is required"
  [ -n "$git_repo" ] || die "GIT_REPO is required"

  sudo_mode="$(remote_sudo_mode)"
  local ssh_target="${ssh_user}@${ssh_host}"

  log "Syncing repository on VPS"
  remote_bootstrap_repo "$ssh_target" "$ssh_port" "$app_dir" "$git_repo" "$git_branch"

  if [ "$sync_overlay" = "true" ]; then
    log "Syncing local workspace overlay to VPS"
    remote_sync_workspace_overlay "$ssh_target" "$ssh_port" "$app_dir"
  fi

  if [ "$sync_dotenv" = "true" ]; then
    log "Syncing local env file to VPS with secure permissions"
    remote_sync_dotenv "$ssh_target" "$ssh_port" "$app_dir"
  fi

  log "Starting Docker stack on VPS"
  run_remote_ovh_deploy "$ssh_target" "$ssh_port" "$app_dir" "$compose_file" "$compose_files" "$sudo_mode" "$api_bind_port" "$frontend_bind_port" "$airflow_webserver_bind" "$airflow_webserver_port"

  if [ "$enable_apache" = "true" ]; then
    [ -n "$app_domain" ] || die "APP_DOMAIN is required when ENABLE_APACHE_CONFIG=true"

    if [ "$certbot_autoconfig" = "true" ]; then
      [ -n "$certbot_email" ] || die "CERTBOT_EMAIL is required when CERTBOT_AUTOCONFIG=true"
      log "Issuing/renewing TLS certificate with Certbot"
      run_remote_certbot "$ssh_target" "$ssh_port" "$app_domain" "$certbot_email" "$sudo_mode"
      ssl_cert="/etc/letsencrypt/live/${app_domain}/fullchain.pem"
      ssl_key="/etc/letsencrypt/live/${app_domain}/privkey.pem"
    fi

    log "Applying Apache reverse proxy config on VPS"
    run_remote_apache_config "$ssh_target" "$ssh_port" "$app_dir" "$app_domain" "$ssl_cert" "$ssl_key" "$api_bind_port" "$frontend_bind_port" "$sudo_mode"
  fi

  log "OVH Apache deployment completed"
}

deploy_ovh_proxy_only() {
  require_cmd ssh
  require_cmd scp

  local ssh_user="${SSH_USER:-}"
  local ssh_host="${SSH_HOST:-}"
  local ssh_port="${SSH_PORT:-22}"
  local app_dir="${APP_DIR:-/opt/market_insights}"
  local app_domain="${APP_DOMAIN:-}"
  local ssl_cert="${SSL_CERT:-/etc/letsencrypt/live/${APP_DOMAIN}/fullchain.pem}"
  local ssl_key="${SSL_KEY:-/etc/letsencrypt/live/${APP_DOMAIN}/privkey.pem}"
  local api_bind_port="${API_BIND_PORT:-18000}"
  local frontend_bind_port="${FRONTEND_BIND_PORT:-18080}"
  local sudo_mode

  [ -n "$ssh_user" ] || die "SSH_USER is required"
  [ -n "$ssh_host" ] || die "SSH_HOST is required"
  [ -n "$app_domain" ] || die "APP_DOMAIN is required"

  sudo_mode="$(remote_sudo_mode)"
  run_remote_apache_config "${ssh_user}@${ssh_host}" "$ssh_port" "$app_dir" "$app_domain" "$ssl_cert" "$ssl_key" "$api_bind_port" "$frontend_bind_port" "$sudo_mode"

  log "OVH Apache proxy configuration applied"
}

deploy_aws_apprunner() {
  die "AWS App Runner adapter is not wired yet for this repository."
}

deploy_azure_containerapps() {
  die "Azure Container Apps adapter is not wired yet for this repository."
}

deploy_k3s() {
  die "k3s adapter is not wired yet for this repository."
}

usage() {
  cat <<'EOF'
Usage:
  scripts/deploy/deploy.sh <target>

Targets:
  ovh-apache         Deploy this project on OVH VPS behind host Apache2
  ovh-proxy          Re-apply Apache2 reverse proxy vhost only
  aws-apprunner      Reserved adapter target
  azure-containerapps Reserved adapter target
  k3s                Reserved adapter target

Important env vars:
  SSH_USER, SSH_HOST, SSH_PORT=22
  GIT_REPO, GIT_BRANCH=main, APP_DIR=/opt/market_insights
  COMPOSE_FILE=docker-compose.ovh-apache.yml
  COMPOSE_FILES=docker-compose.ovh-apache.yml,docker-compose.airflow.yml
  APP_DOMAIN, SSL_CERT, SSL_KEY
  API_BIND_PORT=18000, FRONTEND_BIND_PORT=18080
  AIRFLOW_WEBSERVER_BIND=127.0.0.1|<vpn-ip>, AIRFLOW_WEBSERVER_PORT=18089
  SYNC_LOCAL_OVERLAY=true|false
  SYNC_DOTENV=true|false
  ENABLE_APACHE_CONFIG=true|false
  CERTBOT_AUTOCONFIG=true|false
  CERTBOT_EMAIL=you@example.com

Security:
  Prefer ASK_SUDO_PASSWORD=true over SUDO_PASSWORD in env files.
EOF
}

main() {
  local target="${1:-}"
  case "$target" in
    ovh-apache)
      deploy_ovh_apache
      ;;
    ovh-proxy)
      deploy_ovh_proxy_only
      ;;
    aws-apprunner)
      deploy_aws_apprunner
      ;;
    azure-containerapps)
      deploy_azure_containerapps
      ;;
    k3s)
      deploy_k3s
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      die "Unknown target: $target"
      ;;
  esac
}

main "$@"
