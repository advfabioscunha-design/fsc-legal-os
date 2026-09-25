# Trocar de servidor: é viável? Perco o que foi produzido?
**Análise de 25/09/2026** — motivo: cartão internacional recusado na Hetzner

---

## RESPOSTA CURTA

**É totalmente viável e você NÃO perde nada.** O servidor é a peça mais
descartável do projeto: ele só *executa* o backend. Nenhum dado seu morava
nele. Trocar leva ~30 minutos e é o mesmo comando de instalação.

### Onde o seu patrimônio digital está guardado (tudo intacto)

| O que | Onde está | Situação |
|---|---|---|
| Código completo da plataforma | GitHub (repositório privado) | ✅ intacto |
| Banco: clientes, casos, teses, mensagens | Supabase (nuvem) | ✅ intacto |
| Documentos e petições | Supabase Storage | ✅ intacto |
| Site, portal, CRM (frontend) | Vercel | ✅ **no ar agora** |
| Domínio fscadvocaciadigital.com.br | HostGator | ✅ pago até 05/2028 |
| Servidor (executor do backend/robôs) | Hetzner — cancelado | ❌ o único item perdido |

> O que se perdeu foi só a "máquina vazia". Como o deploy é automatizado
> (`infra/deploy.sh`), reconstruí-la em outro provedor é rotina.

---

## RECOMENDAÇÃO: Hostinger VPS (Brasil)

Além de resolver o pagamento, a troca traz **vantagem técnica real**:

| Critério | Hetzner (Alemanha) | **Hostinger (São Paulo)** |
|---|---|---|
| Pagamento | cartão internacional ❌ | **PIX, boleto, cartão nacional** ✅ |
| Cobrança | dólar/euro | **em reais** |
| Datacenter | Alemanha | **São Paulo** |
| RPA nos tribunais (PJe/Eproc) | IP estrangeiro — risco de bloqueio/lentidão | **IP brasileiro — acesso natural** ✅ |
| Suporte | inglês | português |

**O ponto do IP brasileiro importa muito para o seu caso**: sistemas de
tribunal com frequência tratam acesso estrangeiro como suspeito. Com servidor
em São Paulo, o robô de protocolo trabalha como se fosse seu escritório.

### Planos (preços de 2026)

| Plano | Recursos | 1º ciclo (24 meses) | Renovação mensal |
|---|---|---|---|
| **KVM 1** | 1 vCPU · 4 GB RAM · 50 GB | R$ 29,99/mês | R$ 59,99 |
| **KVM 2** ⭐ | 2 vCPU · 8 GB RAM · 100 GB | ~R$ 39–49/mês | ~R$ 89 |

⭐ **Recomendo o KVM 2**: o robô Playwright + FastAPI + Redis rodando juntos
pedem 2 vCPU. O KVM 1 funciona, mas fica apertado no protocolo automático.

⚠️ **Atenção ao preço promocional**: R$ 29,99/mês só vale pagando os **24 meses
adiantados** (~R$ 720 à vista). No plano de 12 meses fica por volta de
R$ 40–50/mês. Vale conferir na hora da contratação e escolher o ciclo que
couber no caixa — o sistema funciona igual em qualquer um.

### Alternativas avaliadas

- **Contabo** (~€ 6): barato, mas paga em euro/PayPal — mesmo problema.
- **HostGator VPS**: você já tem conta e paga em reais, porém ~R$ 150/mês.
- **Oracle Cloud Free** (grátis): exige cartão internacional no cadastro e é
  ARM — complica o Playwright. Descartada pelos mesmos motivos.
- **Render/Railway free**: dormem por inatividade e não suportam o RPA.

---

## Como fica a migração (30 min, eu conduzo)

1. Você contrata a VPS (Ubuntu 24.04) e me passa **IP + senha root**.
2. Rodo o instalador: Docker, Caddy (HTTPS automático), código do GitHub.
3. Preencho o `.env` com as chaves (Supabase, Claude).
4. Ajusto o DNS: `api` → novo IP · `app` → Vercel (isso já devolve o site ao ar).
5. Subo os serviços e ativo o radar semanal de jurisprudência.

Nada no código precisa mudar — `deploy.sh`, `docker-compose.yml` e o Caddyfile
são agnósticos de provedor.

## E a dívida da Hetzner?

Continua em aberto (~US$ 20) e é dívida em seu nome, então vale quitar quando
puder — inclusive para não sujar seu cadastro num provedor que talvez você
queira usar no futuro. Mas **não bloqueia nada**: podemos subir na Hostinger
sem depender disso.
