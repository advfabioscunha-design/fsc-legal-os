# Cadastro do cliente, conversa única e envio de documentos
**Implantado e testado em 26/09/2026 — já está no ar.**

---

## O caminho, do pedido ao retorno à esteira

```
1. ESTEIRA precisa de um documento
       ↓
2. CRM → abrir o caso → "Pedir documento / informação ao cliente"
       ↓  (cria uma SOLICITAÇÃO com status AGUARDANDO)
3. CAIXA DE MENSAGENS DO CLIENTE (dentro do cadastro dele)
   · aviso em destaque na área do cliente
   · mesmo texto dentro do chat de atendimento
       ↓
4. CLIENTE, no próprio chat: 📎 anexar arquivo  ou  📷 tirar foto
   · os arquivos ficam listados para conferência
   · ele confirma no botão ENVIAR DOCUMENTO(S)
       ↓
5. Documento vai para a PASTA DO CASO (Supabase Storage + tabela documentos),
   marcado com a etiqueta CLIENTE
       ↓
6. Solicitação vira ATENDIDA · o registro entra na conversa ·
   se não restou pendência, o caso VOLTA PARA A PRODUÇÃO automaticamente
       ↓
7. CRM mostra o documento na pasta com a etiqueta CLIENTE e o aviso
   "fora da produção" desaparece sozinho
```

## Cadastro do cliente

- O **e-mail passou a ser pedido no atendimento do site**, junto com nome e
  telefone. É ele que liga o cliente ao acesso da plataforma.
- No CRM, o bloco **Cadastro do cliente** agora permite editar nome, e-mail,
  WhatsApp e CPF/CNPJ. Sem e-mail aparece um aviso: o cliente não consegue
  entrar na plataforma para receber pedidos nem enviar documentos.
- O cliente também confere e completa os próprios dados em
  **Meu cadastro e meus documentos**, na área dele.

## Conversa sempre interligada (não pergunta duas vezes)

- Um mesmo cliente é reconhecido por **e-mail, CPF ou WhatsApp**. Se já
  existir cadastro, o sistema **reaproveita** em vez de criar outro registro,
  e completa os campos que faltavam.
- Se o cliente já tem um **caso em andamento**, a nova mensagem **continua
  naquele caso** — o histórico é único, do site ao portal.
- No chat público do site a conversa fica guardada no navegador: ao voltar,
  ela continua de onde parou, sem repetir o formulário.
- O agente especialista recebe o histórico completo e a instrução de nunca
  repetir pergunta já respondida.

## Envio de documentos pelo chat

- Botão **📎** — anexa arquivos do aparelho (imagens, PDF, Word, Excel),
  vários de uma vez.
- Botão **📷** — abre a câmera do celular para fotografar o documento na hora.
- Os anexos ficam em uma lista de conferência (com nome e tamanho) e só sobem
  quando o cliente toca em **Enviar documento(s)**. Dá para remover antes.
- Limite de 25 MB por arquivo.

---

## O que foi publicado

| Camada | Mudança |
|---|---|
| Banco (migração 0013) | tabela `solicitacoes`; `documentos.enviado_por` e `documentos.solicitacao_id`; políticas RLS para o cliente ver só o que é dele |
| API | `/api/v1/cliente/cadastro` (GET/PATCH), `/api/v1/cliente/caso/{id}` (GET), `/api/v1/cliente/caso/{id}/documentos` (POST), `/api/v1/cliente/caso/{id}/mensagens` (POST), `/api/v1/clientes/{id}` (PATCH) |
| Triagem | reaproveitamento de cliente e de caso em aberto |
| Site | campo de e-mail e conversa persistente no chat |
| Área do cliente | caixa de mensagens, anexo/câmera com botão Enviar, "Meu cadastro" |
| CRM | cadastro editável, lista de solicitações com status, etiqueta CLIENTE nos documentos |

## Teste de ponta a ponta executado

| Passo | Resultado |
|---|---|
| CRM pede "RG e comprovante de residência" | solicitação criada · caso saiu da produção |
| Pedido aparece na caixa do cliente | ✅ status AGUARDANDO |
| Cliente envia o arquivo pelo chat | `{"ok":true,"enviados":["rg_teste.txt"],"retomou_producao":true}` |
| Documento na pasta do caso | ✅ etiqueta CLIENTE |
| Solicitação | ✅ ATENDIDA |
| Caso | ✅ voltou para a produção sozinho |

Os dados do teste foram apagados depois (cliente, caso, mensagens, documento,
arquivo no storage e usuário de teste).

---

## Um ponto para você decidir

A base tem **cadastros de clientes duplicados** herdados do início da operação
— inclusive telefones gravados no campo de e-mail:

| Valor no campo e-mail | Registros |
|---|---|
| `69993599001` | 8 |
| `ponteselika05@gmail.com` | 4 |
| `69993225383` | 3 |
| `site` | 2 |

A partir de agora não nascem mais duplicados (a identificação por
e-mail/CPF/WhatsApp reaproveita o cadastro). Mas os antigos continuam lá, e
enquanto existirem não dá para travar o e-mail como chave única no banco.
Se quiser, eu faço a fusão desses cadastros — preciso da sua confirmação
porque isso mexe em casos reais.
