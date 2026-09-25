#!/usr/bin/env bash
# =====================================================================
# FSC Legal OS — provisionamento da VPS (Ubuntu 24.04), rodar como root.
#
# Uso:
#   export GITHUB_TOKEN=ghp_xxx      # token de leitura (repo é privado)
#   curl -sL https://raw.githubusercontent.com/advfabioscunha-design/fsc-legal-os/main/infra/deploy.sh | bash
#
# Idempotente: pode rodar de novo sem quebrar nada.
# =====================================================================
set -euo pipefail

REPO="advfabioscunha-design/fsc-legal-os"
DEST="/opt/fsc-legal-os"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

echo "=== [1/6] Pacotes base + firewall ==================================="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io docker-compose-v2 git ufw curl ca-certificates \
                   debian-keyring debian-archive-keyring apt-transport-https
systemctl enable --now docker
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp  >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable

echo "=== [2/6] Swap de 2 GB (protege o plano de 4 GB de RAM) ============="
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "swap criado."
else
  echo "swap já existe — ok."
fi

echo "=== [3/6] Caddy (HTTPS automático) =================================="
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y && apt-get install -y caddy
fi

echo "=== [4/6] Código-fonte ============================================="
mkdir -p /opt && cd /opt
if [ -d "$DEST/.git" ]; then
  echo "repositório já existe — atualizando..."
  git -C "$DEST" pull --ff-only || echo "(pull falhou; seguindo com a cópia local)"
else
  if [ -n "$GITHUB_TOKEN" ]; then
    git clone "https://${GITHUB_TOKEN}@github.com/${REPO}.git" "$DEST"
  else
    echo ">>> Repositório é PRIVADO e GITHUB_TOKEN não foi definido."
    echo ">>> Gere um token em github.com/settings/tokens (escopo: repo → read)"
    echo ">>> e rode:  export GITHUB_TOKEN=xxx  antes deste script."
    git clone "https://github.com/${REPO}.git" "$DEST"   # tenta público
  fi
fi

echo "=== [5/6] Configuração ============================================="
cd "$DEST/backend"
[ -f .env ] || cp .env.example .env
install -d /etc/caddy
cp "$DEST/infra/caddy/Caddyfile" /etc/caddy/Caddyfile
systemctl reload caddy || systemctl restart caddy

echo "=== [6/6] Subindo os serviços ======================================"
docker compose up -d --build

cat <<'FIM'

=====================================================================
 INSTALAÇÃO CONCLUÍDA

 Serviços no ar:  api (FastAPI) · worker (robôs) · redis (fila)
 O site/portal/CRM continuam na Vercel (não consomem este servidor).

 PRÓXIMO PASSO — preencher as chaves:
   nano /opt/fsc-legal-os/backend/.env
   (mínimo: SUPABASE_URL, SUPABASE_SERVICE_KEY, CLAUDE_API_KEY)
   depois:  cd /opt/fsc-legal-os/backend && docker compose up -d

 Testes:
   curl http://localhost:8000/health
   https://api.fscadvocaciadigital.com.br/health   (após apontar o DNS)
=====================================================================
FIM
