-- 0051 — o quadro começa onde o cliente começa.
--
-- O pedido nascia em PAGAMENTO. Quem estava conversando sobre preço
-- não aparecia em lugar nenhum do quadro: o escritório só via quem já
-- tinha decidido, e nunca via quem desistiu no meio, que é justamente
-- a informação que ensina onde a conversa perde gente.
--
-- Agora o rito tem as duas fases de atendimento na frente:
--
--   QUALIFICACAO  o agente entende o que a pessoa precisa
--   PROPOSTA      o primeiro valor foi dito, e ela está decidindo
--
-- A migração não muda nada do que já existe: pedido em PAGAMENTO
-- continua em PAGAMENTO. As fases novas valem para os próximos.

-- A dúvida que o advogado levanta na conferência final.
--
-- Lendo o documento ele percebe que falta um dado, ou que uma cláusula
-- ficou ambígua porque o cliente descreveu o combinado de um jeito que
-- cabe em duas leituras. Tinha duas saídas ruins: devolver o pedido
-- inteiro para ajuste por causa de uma pergunta, ou perguntar pelo
-- WhatsApp por fora, deixando a resposta fora do registro do pedido.
alter table public.pedidos_contrato
  add column if not exists duvidas_advogado jsonb default '[]'::jsonb;

comment on column public.pedidos_contrato.duvidas_advogado is
  'Perguntas do advogado ao cliente durante a conferência final, com '
  'a hora e quem perguntou. A resposta volta pela conversa do pedido, '
  'por qualquer um dos três canais.';

-- O índice das fases de atendimento, que é o que o quadro abre
-- primeiro e o que a fila de hoje consulta.
create index if not exists idx_pedidos_atendimento
  on public.pedidos_contrato(fase, atualizado_em desc)
  where fase in ('QUALIFICACAO', 'PROPOSTA') and excluido_em is null;
