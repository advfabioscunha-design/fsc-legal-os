# Guia — Publicar as telas (Cliente + Operador/CRM) na Vercel

O que foi construído:
- **Botão de WhatsApp** flutuante em todo o site (abre o número oficial → o robô identifica o cliente).
- **/entrar** — login e cadastro (e-mail + senha, Supabase Auth).
- **/cliente** — área do cliente: iniciar contratação + acompanhar as fases do processo.
- **/crm** — área do operador (Kanban completo), protegida: só quem tem papel OPERADOR entra.
- Banco: migration `0004_auth_perfis.sql` (perfis, papéis CLIENTE/OPERADOR, segurança por linha).

## Passo 1 — Rodar a migration de perfis no Supabase
No Supabase → SQL Editor, cole e rode o conteúdo de
`supabase/migrations/0004_auth_perfis.sql`.

## Passo 2 — Ativar HTTPS na API (necessário p/ o site falar com o servidor)
O site na Vercel é HTTPS e o navegador bloqueia chamadas a um endereço HTTP.
Então a API precisa de HTTPS. No servidor (SSH), cole:
```
apt install -y caddy && printf 'api.fscadvocaciadigital.com.br {\n    reverse_proxy localhost:8000\n    encode gzip\n}\n' > /etc/caddy/Caddyfile && systemctl restart caddy
```
Em ~1 min teste no navegador: `https://api.fscadvocaciadigital.com.br/health`
(deve responder `{"status":"ok"}`). O certificado é automático (Let's Encrypt);
o DNS `api` já aponta para o servidor.

## Passo 3 — Publicar o frontend na Vercel
1. Acesse https://vercel.com e entre com a conta **GitHub** (advfabioscunha-design).
2. **Add New → Project** → importe o repositório **fsc-legal-os**.
3. **Root Directory:** selecione a pasta `frontend`.
4. Em **Environment Variables**, adicione:
   - `NEXT_PUBLIC_API_URL` = `https://api.fscadvocaciadigital.com.br`
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://midywtybplbdqmkxfoyj.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = (Supabase → Settings → API → **anon public**)
   - `NEXT_PUBLIC_WHATSAPP_NUMBER` = seu número (ex.: `5569999999999`)
5. **Deploy**. Ao final, a Vercel dá uma URL (ex.: `fsc-legal-os.vercel.app`).
6. (Opcional) Domínio: em **Settings → Domains**, adicionar `app.fscadvocaciadigital.com.br`
   (o DNS `app` já aponta para a Vercel).

## Passo 4 — Criar o primeiro OPERADOR (você)
1. Acesse `/entrar` no site publicado e **cadastre-se** com seu e-mail (vira CLIENTE por padrão).
2. No Supabase → SQL Editor, promova para operador:
   ```sql
   update perfis set papel = 'OPERADOR' where email = 'SEU_EMAIL_AQUI';
   ```
3. Saia e entre de novo: agora você cai direto no **/crm**.

## Como funciona o acesso
- **Cliente** se cadastra em `/entrar` → cai em `/cliente` (inicia contratação e acompanha o processo).
- **Operador** (promovido) entra em `/entrar` → cai em `/crm` (Kanban, fases, aprovar/protocolar).
- O cliente só enxerga os próprios casos (segurança por linha no banco).
