# Pendências para retomar a operação — FSC Legal OS
**Levantamento em 10/09/2026** (fonte: faturas no e-mail adv.fabios.cunha@gmail.com)

---

## 🔴 1. HETZNER — servidor do backend/robôs · CONTRATO CANCELADO

O servidor foi **cancelado em 04/08/2026** após 3 faturas recusadas no cartão.
É por isso que a API/robôs não existem mais.

| Fatura | Data | Valor | Status |
|---|---|---|---|
| 088000994701 | 01/07/2026 | US$ 6,22 | cartão recusado |
| 081001049659 | 01/08/2026 | US$ 10,09 | cartão recusado |
| 088001131295 | 01/09/2026 | US$ 3,87 | cartão recusado |
| **TOTAL** | | **≈ US$ 20,18 (~R$ 110)** | em aberto |

- Conta: **K0626409726** · Painel: https://accounts.hetzner.com
- Ação: quitar as faturas + atualizar cartão (o anterior recusou 3x seguidas).
- Servidor novo depois: CX32 (4 GB) ≈ **€ 7,52/mês (~R$ 48)**.

## 🟠 2. HOSTGATOR — e-mail profissional contato@ · FATURA VENCIDA

| Fatura | Serviço | Valor | Venceu |
|---|---|---|---|
| 57190823 | Plano de E-mail Essentials (1 caixa) | **R$ 9,99** | 17/07/2026 |

- Pagar em: https://cliente.hostgator.com.br/faturas/pendentes/57190823
- **O domínio `fscadvocaciadigital.com.br` está PAGO até 11/05/2028** — não corre risco.

## 🟢 3. ANTHROPIC (Claude) — regularizado
- Cobrança de R$ 110 falhou em 20/08 (acesso pausado), mas há recibo pago em 21/08 (#2416-4229-1773) e o acesso está ativo.

## 🟢 4. Serviços gratuitos ativos — nada a pagar
- **Vercel** (site): no ar em https://fsc-legal-os.vercel.app
- **Supabase** (banco/documentos): ativo — só há alertas de segurança RLS a revisar
- **GitHub**: repositório privado ativo

---

## ⚡ O SITE VOLTA AO AR SEM PAGAR NADA

O site **não caiu por falta de pagamento** — ele está no ar e funcionando na Vercel.
O que quebrou foi o **DNS**: `app.fscadvocaciadigital.com.br` deixou de resolver
(a Vercel vem avisando "1 domain needs configuration" desde 28/06).

**Correção (5 minutos, custo zero):** recriar na Zona DNS da HostGator o registro
`CNAME app → cname.vercel-dns.com` — provavelmente foi perdido quando o plano de
e-mail venceu e a zona foi alterada.

---

## Ordem recomendada de gastos

| Prioridade | Item | Custo | Resultado |
|---|---|---|---|
| 1 | Corrigir DNS (não é pagamento) | R$ 0 | Site no ar no domínio próprio |
| 2 | HostGator e-mail | R$ 9,99 | contato@ funcionando p/ cadastros |
| 3 | Hetzner: quitar + novo servidor | ~R$ 110 + R$ 48/mês | Backend, agentes IA e RPA de volta |

**Custo mensal da operação completa depois de regularizada:** ~R$ 50/mês de servidor
+ R$ 10/mês de e-mail + consumo de API (Claude/WhatsApp, conforme uso).
