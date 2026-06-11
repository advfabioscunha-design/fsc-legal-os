#!/usr/bin/env bash
# Provisiona a VPS (Ubuntu 24.04) do zero — rodar como root na 1ª vez.
set -euo pipefail

echo "[1/5] Pacotes base + firewall"
apt-get update -y && apt-get install -y docker.io docker-compose-v2 git ufw
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

echo "[2/5] Caddy (SSL automático)"
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update -y && apt-get install -y caddy

echo "[3/5] Código"
mkdir -p /opt && cd /opt
[ -d fsc-legal-os ] || git clone https://github.com/advfabioscunha-design/fsc-legal-os.git
cd fsc-legal-os/backend

echo "[4/5] Configuração"
[ -f .env ] || { cp .env.example .env; echo '>>> EDITE /opt/fsc-legal-os/backend/.env antes de subir!'; }
cp ../infra/caddy/Caddyfile /etc/caddy/Caddyfile && systemctl reload caddy

echo "[5/5] Subir serviços"
docker compose up -d --build
echo "API no ar: https://api.seudominio.com.br/health"
