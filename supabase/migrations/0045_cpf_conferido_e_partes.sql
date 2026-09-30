-- 0045 — CPF conferido, data de nascimento, e os dados das partes.
--
-- ── O CPF ──────────────────────────────────────────────────────
--
-- O sistema já conferia os dígitos verificadores, o que pega o erro de
-- digitação. Não pega o CPF de outra pessoa, nem o CPF suspenso ou
-- cancelado, e é justamente isso que trava uma assinatura em cartório.
--
-- A consulta à Receita exige data de nascimento. Por isso a coluna: não
-- é dado a mais por capricho, é o que a Receita pede para responder.
--
-- `cpf_conferido_em` guarda quando a Receita confirmou. Nulo significa
-- que só os dígitos foram conferidos, e a tela diz isso ao cliente em
-- vez de afirmar uma conferência que não houve.
--
-- ── AS PARTES DO CONTRATO ──────────────────────────────────────
--
-- Um contrato tem duas partes, e o cliente é uma delas. Os dados da
-- outra ficavam soltos dentro de `dados`, um JSON sem forma, em que
-- cada tipo de contrato usava nomes diferentes de campo. Conferir o que
-- faltava era impossível, e o que faltava só aparecia na hora de
-- redigir, com o redator inventando ou o escritório ligando para
-- perguntar.
--
-- `partes` dá forma a isso: uma lista, cada item com papel, nome, CPF,
-- qualificação e endereço. É o que permite ao atendimento dizer, antes
-- de mandar para a redação, exatamente o que falta e de quem.

alter table public.clientes
  add column if not exists nascimento        date,
  add column if not exists cpf_conferido_em  timestamptz;

comment on column public.clientes.nascimento is
  'Exigida pela consulta de CPF na Receita. Sem ela a consulta não '
  'responde, e o sistema fica só com a conferência dos dígitos.';

comment on column public.clientes.cpf_conferido_em is
  'Quando a Receita confirmou o CPF e o nome. Nulo quer dizer que a '
  'consulta não aconteceu: ou não há credencial configurada, ou faltou '
  'a data de nascimento. A tela nunca escreve "conferido na Receita" '
  'sem esta data preenchida.';


alter table public.pedidos_contrato
  add column if not exists partes           jsonb default '[]'::jsonb,
  add column if not exists partes_completas boolean not null default false;

comment on column public.pedidos_contrato.partes is
  'Lista das partes do contrato, cada uma com papel, nome, CPF ou CNPJ, '
  'qualificação e endereço. O cliente é uma delas, já preenchida a '
  'partir do cadastro dele; as outras ele informa.';

comment on column public.pedidos_contrato.partes_completas is
  'O atendimento conferiu e nada falta. Enquanto for falso, o pedido '
  'não deveria seguir para a redação: contrato com parte mal '
  'qualificada dá trabalho para executar, que é exatamente o problema '
  'que o cliente veio resolver.';
