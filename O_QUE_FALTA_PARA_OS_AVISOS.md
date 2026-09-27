# Comunicação com o cliente — status

**E-MAIL: ✅ NO AR desde 27/09/2026.**
**WhatsApp: aguardando sua decisão sobre os números.**

---

## O que passou a funcionar hoje

A conta `adv.fabios.cunha@gmail.com` está conectada à plataforma por senha de
app (SMTP do Gmail, porta 587). Todo aviso ao cliente sai por e-mail
automaticamente, com o número de atendimento no assunto e o botão de ciência
no corpo.

### Testes reais executados

| Teste | Resultado |
|---|---|
| Envio direto pelo SMTP | ✅ e-mail entregue |
| Pedido de documento pela esteira (`acionar-cliente`) | ✅ `enviado_email: true` |
| Aviso de audiência pelo CRM (`avisar`) | ✅ `enviado_email: true` |
| Roteamento pelo DDD | ✅ cliente com WhatsApp 48 → assinatura do número 48 |
| Número de atendimento | ✅ caso de teste recebeu `FSC-2026-0016` |

Três e-mails reais chegaram na sua caixa de entrada. Os dados de teste
(cliente e caso) foram apagados em seguida.

### Segurança

- A senha de app tem 16 caracteres e está apenas no `.env` do servidor —
  nunca foi versionada no GitHub nem exibida em tela.
- Para revogar: `myaccount.google.com/apppasswords` → excluir `FSC Legal OS`.
  O e-mail para de sair na hora, sem afetar mais nada.
- **A senha da conta Google foi trocada em 27/09** (recomendação atendida,
  após ela ter sido compartilhada por engano).

---

## WhatsApp — a decisão que ficou pendente

Foi verificado no servidor: o WhatsApp **nunca esteve configurado**
(`WHATSAPP_TOKEN` e `WHATSAPP_PHONE_ID` vazios). Até então o sistema dizia
"enviado" mesmo sem enviar — isso já foi corrigido, agora ele informa o motivo
exato da falha.

O código de roteamento está pronto e testado nos sete cenários
(69 → Rondônia, 48 → Santa Catarina, demais → 48). Falta só ligar os números.

**O ponto que trava a decisão:** um número migrado para a API oficial do Meta
**para de funcionar no aplicativo do celular** — passa a ser operado só pela
plataforma.

| Caminho | O que acontece |
|---|---|
| Migrar 69 e 48 | Os dois somem do celular. É o caminho do robô de atendimento. |
| Chip novo só para avisos | 69 e 48 seguem intactos no aparelho. Custo de mais um número. |
| Migrar só o 48 | 48 vira automático, 69 fica humano. Clientes de RO recebem aviso pelo 48. |
| Só e-mail | **Situação atual.** Zero impacto na operação. |

Quando decidir, o que preciso do painel do Meta:
token permanente + **Phone Number ID** de cada número. Aí configuro em minutos.

---

## Como usar agora

**Pedir documento ao cliente:** CRM → abrir o caso → *"Pedir documento /
informação ao cliente"*. Sai e-mail na hora; o cliente anexa ou fotografa pelo
chat do painel e o caso volta sozinho para a produção.

**Avisar sobre audiência, prazo ou movimentação:** CRM → abrir o caso →
*"Avisar o cliente"* → escolher o tipo, escrever título e mensagem.

**Acompanhar a ciência:** dentro do caso, cada aviso mostra se saiu por e-mail,
se o cliente confirmou o recebimento e quantos lembretes já foram enviados.
Quem não confirma recebe lembrete automático a cada 24 h, até 3 vezes.
