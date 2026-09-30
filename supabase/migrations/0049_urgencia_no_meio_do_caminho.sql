-- 0049 — a urgência contratada depois que o trabalho já começou.
--
-- A urgência era uma escolha da negociação e morria ali. Só que a
-- pressa quase nunca nasce junto com o pedido: nasce depois, quando a
-- assinatura foi antecipada, quando a outra parte marcou a entrega das
-- chaves, quando surgiu uma reunião. Quem descobria isso no meio do
-- caminho não tinha caminho nenhum, e o atendimento improvisava,
-- oferecendo o que não existia.
--
-- Agora existe, e em três tempos, com o dinheiro no meio deles:
--
--   urgencia_pedida_em     o orçamento foi apresentado ao cliente
--   urgencia_txid          o cliente disse que pagou, e por qual PIX
--   urgencia_confirmada_em o escritório conferiu o extrato
--
-- O prazo só muda no terceiro. Prazo declarado por quem não conferiu o
-- extrato é prazo que o escritório assume sem ter recebido, e uma vez
-- prometido não se volta atrás sem queimar o cliente.
--
-- O valor fica guardado no momento do orçamento porque a tabela pode
-- mudar entre o orçamento e o pagamento, e quem pagou tem direito ao
-- preço que leu na tela.

alter table public.pedidos_contrato
  add column if not exists urgencia_pedida_em      timestamptz,
  add column if not exists urgencia_valor          numeric(10,2),
  add column if not exists urgencia_txid           text,
  add column if not exists urgencia_confirmada_em  timestamptz,
  add column if not exists urgencia_confirmada_por text;

comment on column public.pedidos_contrato.urgencia_pedida_em is
  'Quando o adicional de urgência foi orçado para este cliente. '
  'Preenchido e o confirmado nulo significa aguardando pagamento.';

comment on column public.pedidos_contrato.urgencia_valor is
  'A diferença orçada, congelada no momento em que foi dita ao '
  'cliente. Quem pagou tem direito ao preço que leu na tela.';

comment on column public.pedidos_contrato.urgencia_confirmada_em is
  'Quando o escritório conferiu o PIX. É só aqui que o prazo passa a '
  '6 horas e a esteira troca para as janelas curtas.';

create index if not exists idx_pedidos_urgencia_aguardando
  on public.pedidos_contrato(urgencia_pedida_em)
  where urgencia_pedida_em is not null
    and urgencia_confirmada_em is null
    and excluido_em is null;
