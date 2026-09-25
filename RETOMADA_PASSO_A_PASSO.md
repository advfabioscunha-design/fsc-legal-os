# RETOMADA DA OPERAÇÃO — FSC Legal OS
**Plano definido em 10/09/2026** · Decisão: pagar **somente a Hetzner** (sem e-mail Titan)

---

## O que já está PRONTO no código (não precisa refazer)

Sessões anteriores deixaram a plataforma praticamente completa:

**Frontend** (`frontend/app/`): home, landings dos 4 nichos (`/areas/...`), portal de
atendimento, **botão flutuante de WhatsApp**, login (`/entrar`), **área do cliente**
(`/cliente`), **CRM da equipe** (`/crm`, `/processos`, `/agenda`, `/admin`), contrato
online, assistente interno.

**Backend** (`backend/app/`): agentes (triagem, especialista por nicho, contrato,
jurisprudencial, **radar**, relacionamento, ceo), integrações (Asaas, ZapSign,
WhatsApp + omnichannel, áudio/voz, **DataJud/CNJ**, Escavador), workers (fila,
RPA Eproc) e **job `radar_semanal.py`** — busca automática de jurisprudência
toda segunda-feira às 6h (`RADAR_AUTO=true`).

> Ou seja: **falta apenas colocar no ar.** O servidor foi cancelado e o DNS quebrou.

---

## PASSO 1 — Hetzner (você) · ~US$ 20 + US$ ~8/mês

1. Quitar as 3 faturas em aberto: https://accounts.hetzner.com/invoice/088001131295
   (as outras aparecem em *Invoices → Overview*: 088000994701 · 081001049659)
2. **Trocar o cartão** em https://accounts.hetzner.com/account/payment
   — o atual foi recusado 3× e foi isso que derrubou o servidor.
3. Criar o servidor: Cloud → **New Server** → Ubuntu 24.04 · tipo **CX32**
   (4 GB) · região Nuremberg/Falkenstein · autenticação por senha root.
4. Me passar o **IP** que aparecer.

## PASSO 2 — DNS na HostGator (eu faço, com você logado) · R$ 0

Painel → Domínios → `fscadvocaciadigital.com.br` → Editar Zona Avançada de DNS:

| Tipo | Nome | Valor |
|---|---|---|
| CNAME | `app` | `cname.vercel-dns.com` |
| A | `api` | *(IP do servidor novo)* |

> É o que devolve o site ao ar no seu domínio. Sem custo — o domínio está pago até 2028.

## PASSO 3 — Subir o backend na VPS (eu conduzo)

```bash
# no servidor, como root:
curl -sL https://raw.githubusercontent.com/advfabioscunha-design/fsc-legal-os/main/infra/deploy.sh | bash
nano /opt/fsc-legal-os/backend/.env     # preencher chaves (modelo em .env.example)
cd /opt/fsc-legal-os/backend && docker compose up -d --build
```

Chaves mínimas para funcionar: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CLAUDE_API_KEY`.
As demais (Asaas, ZapSign, WhatsApp, ElevenLabs) podem entrar depois, por módulo.

## PASSO 4 — Ligar o frontend ao backend (eu faço)

Vercel → projeto `fsc-legal-os` → Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL         = https://api.fscadvocaciadigital.com.br
NEXT_PUBLIC_SUPABASE_URL    = https://midywtybplbdqmkxfoyj.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY = (Supabase → Settings → API → anon public)
NEXT_PUBLIC_WHATSAPP_NUMBER = 55DDD9XXXXXXXX   ← seu número do escritório
```
→ Redeploy.

## PASSO 5 — Radar de jurisprudência automático (grátis)

Já implementado. A API **DataJud do CNJ é pública e gratuita** (chave já embutida).
Depois do PASSO 3 ele roda sozinho toda segunda às 6h e atualiza teses por nicho.
Teste manual: `POST https://api.fscadvocaciadigital.com.br/api/v1/radar/executar`

---

## Custos da operação depois de retomada

| Item | Custo |
|---|---|
| Servidor Hetzner CX32 | ~R$ 48/mês |
| Domínio | pago até 05/2028 |
| Vercel · Supabase · GitHub · DataJud | R$ 0 |
| Claude API (agentes) | por uso |
| **E-mail profissional** | **não contratado** — usar `adv.fabios.cunha@gmail.com`. Alternativa grátis futura: Zoho Mail Free |

## Pendências que NÃO custam nada (faço quando você quiser)
- Revisar alertas de segurança do Supabase (políticas RLS).
- Publicar as alterações pendentes no GitHub (`SUBIR_GITHUB.bat`).
