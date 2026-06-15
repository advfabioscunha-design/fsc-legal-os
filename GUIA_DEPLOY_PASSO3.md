# Passo 3 — SIMPLIFICADO (colocar o robô no ar)

Servidor: **159.69.124.171** · só 3 ações suas. O resto já vem pronto.

---

## AÇÃO 1 — Deixar o repositório acessível (1 clique)
Para o servidor baixar o código. No GitHub (já logado):
repo **fsc-legal-os** → **Settings** → role até o fim (**Danger Zone**) →
**Change visibility** → **Make public** → confirme digitando o nome do repo.
(O código não tem senhas — o `.env` fica fora do GitHub. Depois pode voltar a Private.)

> Eu deixo essa página aberta para você; é só clicar.

---

## AÇÃO 2 — Entrar no servidor
A janela do **Console** do Hetzner já está aberta. Nela:
- `login:` digite **root** e Enter
- `Password:` cole a senha que veio no **e-mail da Hetzner** (no terminal a senha
  fica invisível enquanto digita — é normal) e Enter.

Quando aparecer `root@ubuntu...:~#`, você está dentro.

---

## AÇÃO 3 — Colar 2 blocos

**Bloco 1** (instala tudo, baixa o código e abre o arquivo de chaves) — copie e cole inteiro:
```
apt update && apt install -y docker.io docker-compose-v2 git && \
git clone -b main https://github.com/advfabioscunha-design/fsc-legal-os.git /opt/fsc-legal-os && \
cd /opt/fsc-legal-os/backend && cat > .env <<'EOF'
AMBIENTE=prod
SUPABASE_URL=https://midywtybplbdqmkxfoyj.supabase.co
SUPABASE_SERVICE_KEY=COLE_AQUI_A_SERVICE_KEY
CLAUDE_API_KEY=COLE_AQUI_A_CHAVE_CLAUDE
CLAUDE_MODEL=claude-opus-4-5
CLAUDE_MODEL_RAPIDO=claude-haiku-4-5-20251001
DATAJUD_TRIBUNAIS=tjro,trt14
RADAR_AUTO=true
RADAR_DIA_SEMANA=mon
RADAR_HORA=6
REDIS_URL=redis://redis:6379/0
RPA_HEADLESS=true
AVISO_ASSISTENTE=true
EOF
nano .env
```

Vai abrir um editor (nano) mostrando o arquivo. Troque só 2 linhas:
- Apague `COLE_AQUI_A_SERVICE_KEY` e cole sua **Supabase service_role key**
  (Supabase → Settings → API → `service_role`).
- Apague `COLE_AQUI_A_CHAVE_CLAUDE` e cole sua **chave Claude** (`sk-ant-...`).

Salvar: **Ctrl+O** → Enter → **Ctrl+X**.

**Bloco 2** (sobe o sistema) — cole:
```
cd /opt/fsc-legal-os/backend && docker compose up -d --build
```
Demora alguns minutos na 1ª vez (está montando tudo).

---

## Testar o robô agora
```
docker compose exec -T api python -m jobs.radar_semanal
```
Deve imprimir um JSON com o radar por grupo. A partir daí ele roda **sozinho toda
segunda 06h** e te avisa no WhatsApp (se preencher `HUMANO_WHATSAPP`).

> SSL/domínio público (api.fscadvocaciadigital.com.br) e WhatsApp são opcionais e
> a gente liga depois — não são necessários para o robô funcionar.

---

### Se travar
Me diga em qual ação/linha parou (ou cole a mensagem de erro). Comandos que não
envolvem senha/chave eu posso digitar por você — é só avisar.
