#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   VPS_USER=ubuntu VPS_HOST=1.2.3.4 DOMAIN=example.com APP_DIR=/opt/app/webapp bash deploy/deploy.sh
#   With password (no SSH keys):
#   VPS_USER=root VPS_HOST=1.2.3.4 DOMAIN=1.2.3.4 PASSWORD='secret' bash deploy/deploy.sh

VPS_USER=${VPS_USER:-}
VPS_HOST=${VPS_HOST:-}
DOMAIN=${DOMAIN:-}
APP_DIR=${APP_DIR:-/opt/app/webapp}
PASSWORD=${PASSWORD:-}

if [[ -z "${VPS_USER}" || -z "${VPS_HOST}" || -z "${DOMAIN}" ]]; then
  echo "Set VPS_USER, VPS_HOST, DOMAIN env vars" >&2
  exit 1
fi

if [[ -n "$PASSWORD" ]]; then
  SSH="sshpass -p '${PASSWORD}' ssh -o StrictHostKeyChecking=accept-new ${VPS_USER}@${VPS_HOST}"
  RSYNC_SSH="sshpass -p '${PASSWORD}' ssh -o StrictHostKeyChecking=accept-new"
else
  SSH="ssh -o StrictHostKeyChecking=accept-new ${VPS_USER}@${VPS_HOST}"
  RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new"
fi

echo "==> Prepare server directories and packages"
$SSH "SUDO=\$(command -v sudo >/dev/null 2>&1 && echo sudo || echo ''); \
      USERNAME=\$(id -un); \
      \$SUDO mkdir -p ${APP_DIR} && \$SUDO chown -R \$USERNAME: \$(dirname ${APP_DIR}); \
      \$SUDO apt update && \$SUDO apt install -y python3-venv python3-pip nginx"

echo "==> Rsync project to server"
rsync -az -e "$RSYNC_SSH" --delete --exclude '.venv' --exclude 'db.sqlite3' --exclude '__pycache__' --exclude '.git' ./ ${VPS_USER}@${VPS_HOST}:${APP_DIR}/

echo "==> Create venv and install requirements"
$SSH "cd ${APP_DIR} && python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

echo "==> Write .env (if not exists)"
$SSH "bash -lc 'set -e; cd ${APP_DIR}; if [[ ! -f .env ]]; then cat > .env <<EOF
DJANGO_SECRET_KEY=$(python3 - <<PY
import secrets
print(secrets.token_urlsafe(50))
PY
)
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=${DOMAIN},${VPS_HOST}
DJANGO_CSRF_TRUSTED_ORIGINS=https://${DOMAIN}
EOF
fi'"

echo "==> Migrate and collectstatic"
$SSH "cd ${APP_DIR} && source .venv/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput"

echo "==> Install systemd unit for gunicorn"
$SSH "sudo bash -lc 'cat > /etc/systemd/system/gunicorn.service <<UNIT
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8001 --workers 3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now gunicorn'"

echo "==> Configure nginx"
$SSH "sudo bash -lc 'cat > /etc/nginx/sites-available/webapp <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} ${VPS_HOST};

    location /static/ { alias ${APP_DIR}/staticfiles/; }
    location /media/  { alias ${APP_DIR}/media/; }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX
ln -sf /etc/nginx/sites-available/webapp /etc/nginx/sites-enabled/webapp && nginx -t && systemctl reload nginx'"

echo "==> Done. Open http://${DOMAIN}"


