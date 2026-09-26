# RETOMADA — CONCLUÍDA em 25/09/2026

**Status: operação 100% no ar.**

---

## Infraestrutura atual

| Camada | Onde | Estado |
|---|---|---|
| Site, portal, CRM (Next.js) | Vercel | ✅ no ar · build `Ready` |
| API + robôs + fila (FastAPI/RQ/Redis) | VPS Hostinger KVM 1 · `2.25.248.85` · Ubuntu 24.04 | ✅ containers `api`, `worker`, `redis` Up |
| Banco, autenticação, arquivos | Supabase | ✅ conectado e lendo |
| HTTPS | Caddy + Let's Encrypt | ✅ certificado emitido |
| Domínio | HostGator (pago até 05/2028) | ✅ |

### DNS (zona HostGator)

| Registro | Tipo | Valor |
|---|---|---|
| `app` | CNAME | `cname.vercel-dns.com` |
| `api` | A | `2.25.248.85` |
| `www` | CNAME | `cname.vercel-dns.com` |
| `@` (raiz) | A | `216.198.79.1` (Vercel) |

**Endereço oficial do site: `app.fscadvocaciadigital.com.br`.**
`www.fscadvocaciadigital.com.br` e `fscadvocaciadigital.com.br` (sem www)
fazem redirecionamento permanente **308 → app**, com HTTPS próprio emitido pela
Vercel. Os registros de e-mail (MX, SPF, DKIM da Titan) não foram tocados.

> Os dois registros antigos apontavam para o servidor Hetzner cancelado
> (`159.69.124.171`) — era essa a causa real da queda, não falta de pagamento.

---

## O que foi feito nesta retomada

1. **Servidor novo provisionado**: Docker, Caddy, firewall (ufw) e **swap de 2 GB**
   (protege os 4 GB de RAM do plano).
2. **Código publicado** em `/opt/fsc-legal-os` e serviços no ar.
3. **DNS corrigido** (`app` → Vercel · `api` → VPS novo).
4. **HTTPS automático** ativo em `api.fscadvocaciadigital.com.br`.
5. **`.env` do servidor preenchido** (Supabase + Claude) — chaves nunca expostas em tela.
6. **Variáveis de ambiente criadas na Vercel** e redeploy feito:
   - `NEXT_PUBLIC_API_URL` = `https://api.fscadvocaciadigital.com.br`
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://midywtybplbdqmkxfoyj.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_WHATSAPP_NUMBER` = `5569993225383`
7. **Causa das builds quebradas resolvida**: desde 17/06 *todos* os deploys da
   Vercel falhavam porque as variáveis do Supabase não existiam no projeto — o
   site estava servindo a versão de **14/06**. Com as variáveis criadas, a build
   passou e o site agora roda o código mais recente.

## Testes feitos (com resultado)

| Teste | Resultado |
|---|---|
| `GET https://api.../health` | `{"status":"ok","ambiente":"prod","versao":"4.0"}` |
| `GET /api/v1/teses` | retornou as teses do Supabase |
| `https://app.fscadvocaciadigital.com.br` | HTTP **200**, SSL válido |
| Chamada do site → API (CORS) | **200** a partir do navegador |
| Login/portal | carrega e protege rota (Supabase ok) |
| **Radar Jurimétrico** `POST /api/v1/cerebro/radar-semanal` | **200** — gravou snapshots novos de BANCÁRIO, IMOBILIÁRIO, TRIBUTÁRIO e CONSUMIDOR |
| Agendamento semanal | ligado (`RADAR_AUTO=true`, segunda 06:00 UTC) |

---

## Pontos em aberto (nenhum bloqueia a operação)

1. **Repositório GitHub está PÚBLICO.** Toda a lógica de negócio da plataforma é
   legível por qualquer pessoa. Não há senhas expostas (o `.env` nunca foi
   versionado), mas recomendo voltar a privado — nesse caso gero um token de
   leitura para o servidor.
2. **2FA da Vercel** está desligado (pulei na hora do login para não travar).
   Vale ativar.
3. **Dívida Hetzner** (~US$ 20) segue em aberto, em seu nome.
4. **Cartão internacional recusado** — trocar antes de contratar qualquer coisa
   em dólar de novo.
5. Se `app.fscadvocaciadigital.com.br` não abrir no seu computador, é só cache de
   DNS local (do servidor responde 200). Some sozinho em algumas horas.
