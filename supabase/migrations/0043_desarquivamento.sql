-- 0043 — o que acontece depois dos sete dias.
--
-- O termo passa a prometer três coisas ao cliente: o documento fica
-- disponível para revisão por sete dias, depois disso a solicitação é
-- arquivada, e para retomá-la ele abre um chamado explicando o motivo.
--
-- As duas primeiras já existiam pela metade. A terceira não existia: o
-- pedido arquivava e acabava ali. Quem quisesse voltar tinha de ligar
-- para o escritório, e a conversa não ficava registrada em lugar
-- nenhum.
--
-- POR QUE O CHAMADO, E NÃO UM BOTÃO QUE REABRE
--
-- Reabertura automática torna o prazo decorativo: quem sabe que basta
-- clicar não se apressa em revisar. E há casos em que a reabertura
-- custa trabalho de verdade, porque o contrato envelheceu, a lei mudou
-- ou a outra parte desistiu. Quem decide isso é o escritório, lendo o
-- motivo, e é por isso que o pedido tem um texto obrigatório.

alter table public.pedidos_contrato
  add column if not exists disponibilizado_em timestamptz;

comment on column public.pedidos_contrato.disponibilizado_em is
  'Quando o documento ficou visível para o cliente revisar. É desta '
  'data que correm os sete dias, e não da entrega: o prazo prometido é '
  'para revisar, e revisar começa aqui.';


create table if not exists public.pedidos_desarquivamento (
  id           uuid primary key default gen_random_uuid(),
  pedido_id    uuid references public.pedidos_contrato(id) on delete cascade,
  caso_id      uuid references public.casos(id) on delete cascade,
  cliente_id   uuid references public.clientes(id) on delete set null,

  motivo       text not null,
  status       text not null default 'PENDENTE',
      -- PENDENTE | APROVADO | RECUSADO
  resposta     text,
  respondido_em  timestamptz,
  respondido_por text,
  criado_em    timestamptz not null default now()
);

-- Um chamado aberto por vez, por pedido. Dois pedidos vivos para a
-- mesma coisa é o escritório respondendo duas vezes à mesma pergunta,
-- e o cliente sem saber qual resposta vale.
create unique index if not exists idx_desarq_pedido_aberto
  on public.pedidos_desarquivamento(pedido_id)
  where status = 'PENDENTE' and pedido_id is not null;

create unique index if not exists idx_desarq_caso_aberto
  on public.pedidos_desarquivamento(caso_id)
  where status = 'PENDENTE' and caso_id is not null;

create index if not exists idx_desarq_fila
  on public.pedidos_desarquivamento(status, criado_em desc);

alter table public.pedidos_desarquivamento enable row level security;

comment on table public.pedidos_desarquivamento is
  'Serve para pedido de contrato e para caso judicial. As duas colunas '
  'de origem existem porque a tabela é a mesma e a fila do escritório '
  'também: o chamado é o mesmo tipo de conversa, mude a demanda que '
  'mudar.';

comment on column public.pedidos_desarquivamento.motivo is
  'Escrito pelo cliente, obrigatório. É o que o escritório lê para '
  'decidir, e é o que explica, meses depois, por que aquele pedido foi '
  'reaberto.';
