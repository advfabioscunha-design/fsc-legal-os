-- 0038 — a última saída antes de perder o cliente.
--
-- O atendimento tem dois degraus de desconto e para ali. Quando o
-- cliente diz que não consegue pagar nem o último valor, hoje a
-- conversa morre: ele fecha a página e ninguém no escritório fica
-- sabendo que existiu.
--
-- Isso é informação jogada fora. Saber que três pessoas ofereceram
-- R$ 150 pelo mesmo tipo de contrato na mesma semana vale mais do que
-- qualquer palpite sobre preço, e quem decide se aceita é o advogado,
-- não o atendimento.
--
-- A proposta fica no próprio pedido, e não numa tabela à parte, porque
-- ela é um estado do pedido: o mesmo pedido que segue para coleta se
-- for aceita, e que fica parado se não for.

alter table public.pedidos_contrato
  add column if not exists proposta_valor      numeric(10,2),
  add column if not exists proposta_motivo     text,
  add column if not exists proposta_em         timestamptz,
  add column if not exists proposta_status     text,
      -- PENDENTE | ACEITA | RECUSADA | CONTRAPROPOSTA
  add column if not exists proposta_resposta   text,
  add column if not exists proposta_contra     numeric(10,2),
  add column if not exists proposta_respondida_em timestamptz,
  add column if not exists proposta_respondida_por text;

-- O painel abre por esta consulta toda vez. Sem índice, ela varre a
-- tabela inteira para achar meia dúzia de linhas.
create index if not exists idx_pedidos_proposta
  on public.pedidos_contrato(proposta_em)
  where proposta_status = 'PENDENTE';

comment on column public.pedidos_contrato.proposta_valor is
  'Quanto o cliente se dispõe a pagar. Registrado apenas depois que os '
  'dois degraus de desconto foram usados: antes disso o atendimento '
  'ainda tem o que oferecer, e pedir contraproposta cedo demais é '
  'ensinar o cliente a pechinchar.';

comment on column public.pedidos_contrato.proposta_motivo is
  'Por que aquele valor. É a parte mais útil: "é o que sobra do aluguel '
  'deste mês" e "achei caro" levam a decisões diferentes.';
