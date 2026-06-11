# FSC LEGAL OS v4 — Guia de Deploy (suas 5 contas + subir tudo)

O código está pronto. O que falta são as contas em nuvem — **só você pode criá-las** (envolvem login e cartão). Para cada uma, depois de logado, eu posso assumir a configuração pelo navegador, como fizemos no Google Cloud.

## Passo 1 — Supabase (banco + auth + storage) · grátis para começar
1. Crie conta em supabase.com → **New Project** → região **South America (São Paulo)**.
2. Me avise logado: eu rodo a migration `supabase/migrations/0001_schema_inicial.sql` no SQL Editor, crio o bucket privado `documentos` e importo suas teses com `seed_teses.py` (cada tese entra no seu GRUPO e o Agente Especialista do grupo é criado).
3. Anotar: `SUPABASE_URL`, `SERVICE_KEY` (Settings → API).

## Passo 2 — GitHub (código) · grátis
1. Crie conta/repos em github.com → repositório privado `fsc-legal-os`.
2. Eu preparo o push do monorepo.

## Passo 3 — VPS DigitalOcean (backend + RPA) · ~US$ 24/mês
1. Crie conta em digitalocean.com → **Droplet Ubuntu 24.04, 4GB/2vCPU**, região NYC ou SP.
2. No Droplet: `curl -sL https://raw.githubusercontent.com/SEU_USUARIO/fsc-legal-os/main/infra/deploy.sh | bash` — instala Docker, Caddy (SSL automático), clona o código e sobe API + worker + Redis.
3. Editar `/opt/fsc-legal-os/backend/.env` (modelo em `.env.example`).

## Passo 4 — Vercel (frontend) · grátis
1. Conta em vercel.com → **Import** do repositório → pasta `frontend/`.
2. Variável `NEXT_PUBLIC_API_URL=https://api.seudominio.com.br`.
3. Domains → adicionar `app.seudominio.com.br`.

## Passo 5 — DNS no seu domínio (5 min, não toca no site atual)
| Registro | Tipo | Valor |
|---|---|---|
| `app` | CNAME | `cname.vercel-dns.com` |
| `api` | A | IP do Droplet |

## Passo 6 — Integrações de negócio
- **Asaas** (asaas.com): conta PJ/advogado → API Key → `.env`. Webhook: `https://api.seudominio.com.br/webhooks/asaas`.
- **ZapSign** (zapsign.com.br): API Token → `.env`. Webhook: `/webhooks/zapsign`.
- **WhatsApp Cloud API** (developers.facebook.com): app Business → número → token → `.env`. Webhook: `/webhooks/whatsapp` (verify token: `fsc-legal-os`).
- **Certificado em nuvem** (BirdID/Safeweb ~R$ 35/mês): contratar A3 em nuvem — usado pelo RPA na assinatura (fase de calibração).
- **Voz do agente** (ElevenLabs ~US$ 5–22/mês): criar conta em elevenlabs.io → **Voices → Add Voice → Instant Voice Clone** → grave 2–3 minutos da sua voz lendo um texto variado → copie o `Voice ID` → `.env` (`ELEVENLABS_API_KEY` e `ELEVENLABS_VOICE_ID`). Para a transcrição dos áudios dos clientes: `OPENAI_API_KEY` (Whisper, ~US$ 0,006/min) ou deixe vazio para usar o Whisper local da VPS (grátis).

> Transparência: o sistema vem com `AVISO_ASSISTENTE=true` — a primeira mensagem informa que o atendimento é do assistente digital do escritório, supervisionado pelo Dr. Fábio. Recomendado manter: clientes ouvindo a sua voz sem saber que é IA pode gerar questionamento ético (OAB) e de consumo.

## A jornada que o sistema executa sozinho
```
Lead (site/WhatsApp)
  → Triagem identifica o GRUPO → AGENTE ESPECIALISTA do grupo assume
  → Qualifica + já demonstra viabilidade citando o entendimento dos tribunais
  → Coleta dados → envia CONTRATO (ZapSign)
  → [webhook: assinou] → envia COBRANÇA (Asaas)
  → [webhook: pagou] → coleta DOCUMENTOS VITAIS da tese, um a um, explicando
  → coleta DEPOIMENTO e provas → Analista gera laudo → Redator gera petição
  → você REVISA no CRM → "APROVAR E PROTOCOLAR" → fila → RPA protocola
  → cliente é notificado com o número do processo
```
Em qualquer ponto: dificuldade, demora nos documentos ou pedido do cliente
→ **escala para você** (alerta no seu WhatsApp) e oferece **agendamento**
com o advogado especialista da demanda (link Cal.com por grupo).

## Ordem recomendada
Supabase → GitHub → VPS → Vercel → DNS → Asaas/ZapSign → WhatsApp → Certificado.
Quando criar cada conta, me chame que eu configuro com você na tela.
