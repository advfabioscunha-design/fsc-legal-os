-- 0037 — o balcão de contratos é outra coisa, e passa a ter rito próprio.
--
-- Até aqui tudo desembocava em `casos`: quem pedia um contrato de aluguel
-- caía no mesmo funil de quem tinha uma ação para propor. São serviços
-- diferentes, com rito, preço, prazo e risco diferentes — e o cliente de
-- um não deve ver a tela do outro. Quem pediu um contrato de locação não
-- precisa (nem deve) ver "meus processos"; quem tem uma ação não deve
-- cair numa tela de compra de documento.
--
-- Três frentes nesta migração:
--   1. o cliente passa a ter tipo, e o tipo decide a porta
--   2. o pedido guarda o preço negociado, não só o de tabela
--   3. o pedido ganha documentos e conversa próprios

-- ── 1. Que porta este cliente enxerga ───────────────────────────
--
-- Default LITIGIOSO porque toda a base existente veio do funil de casos.
-- AMBOS existe porque o cliente de um processo pode, depois, pedir um
-- contrato — e nesse dia ele não pode perder o acesso ao processo.
alter table public.clientes
  add column if not exists tipo text not null default 'LITIGIOSO';

comment on column public.clientes.tipo is
  'LITIGIOSO | CONTRATOS | AMBOS. Decide qual área o cliente vê ao entrar. '
  'Quem chega pelo balcão nasce CONTRATOS; se depois abrir um caso, vira '
  'AMBOS — nunca se troca CONTRATOS por LITIGIOSO apagando o outro lado.';


-- ── 2. O preço que foi negociado ────────────────────────────────
--
-- `valor` sozinho não conta a história: não dá para saber depois se os
-- R$ 200 saíram de desconto, de urgência, ou de alguém ter digitado
-- errado. Guardar a decomposição é o que permite conferir o caixa e
-- entender o que o desconto está fazendo com a margem.
alter table public.pedidos_contrato
  add column if not exists valor_base      numeric(10,2),
  add column if not exists desconto_pct    numeric(5,2) not null default 0,
  add column if not exists urgente         boolean not null default false,
  add column if not exists assinatura_digital boolean not null default true,
  add column if not exists prazo_entrega_horas integer not null default 24,
  add column if not exists negociacao      jsonb default '[]'::jsonb,
  add column if not exists modo_coleta     text,
  add column if not exists clausulas_extras text,
  add column if not exists prazo_alteracao_ate date,
  add column if not exists entrega_link    text;

comment on column public.pedidos_contrato.negociacao is
  'A conversa da proposta, turno a turno, com os descontos oferecidos e o '
  'que o cliente respondeu. É o que mostra, depois, por que este pedido '
  'saiu por este preço.';

comment on column public.pedidos_contrato.prazo_alteracao_ate is
  'Até quando o cliente pode pedir alteração sem custo. Sete dias a '
  'contar da entrega. Passado isso o pedido arquiva sozinho.';

comment on column public.pedidos_contrato.modo_coleta is
  'DOCUMENTOS (mandou PDF/foto) | FORMULARIO (digitou) | MISTO. Serve '
  'para saber onde procurar a informação quando o contrato precisar ser '
  'conferido.';


-- ── 3. Documentos do pedido ─────────────────────────────────────
--
-- Tabela própria, e não a `documentos` dos casos: aquela é peça de
-- processo, com assinatura, protocolo e ciclo de vida de litígio.
-- Aqui é insumo — a foto do RG, a matrícula do imóvel — que morre com o
-- arquivamento do pedido.
create table if not exists public.pedidos_documentos (
  id         uuid primary key default gen_random_uuid(),
  pedido_id  uuid not null references public.pedidos_contrato(id) on delete cascade,
  nome       text not null,
  tipo_mime  text,
  tamanho    integer,
  url        text not null,
  enviado_por text,                       -- CLIENTE | ESCRITORIO
  rotulo     text,                        -- a qual item do rol corresponde
  criado_em  timestamptz not null default now()
);

create index if not exists idx_pedidos_docs on public.pedidos_documentos(pedido_id);


-- ── 4. A conversa do pedido ─────────────────────────────────────
--
-- Separada das `mensagens` dos casos pelo mesmo motivo. Aqui trafegam
-- proposta, pedido de documento e ajuste de minuta; lá, andamento
-- processual. Misturar as duas faria o cliente do balcão receber avisos
-- de processo e vice-versa.
create table if not exists public.pedidos_mensagens (
  id         uuid primary key default gen_random_uuid(),
  pedido_id  uuid not null references public.pedidos_contrato(id) on delete cascade,
  autor      text not null,               -- CLIENTE | AGENTE | ESCRITORIO
  texto      text not null,
  meta       jsonb default '{}'::jsonb,   -- proposta oferecida, desconto, etc.
  lida_em    timestamptz,
  criado_em  timestamptz not null default now()
);

create index if not exists idx_pedidos_msgs on public.pedidos_mensagens(pedido_id, criado_em);


-- ── 5. Pedido órfão ─────────────────────────────────────────────
--
-- A tela do balcão nunca mandou `cliente_id`, e o backend não o derivava
-- do token: todo pedido nasceu sem dono. O join com `clientes` voltava
-- nulo e não havia como o cliente listar "meus pedidos". O código passa
-- a resolver o cliente pelo token; este índice é só para achar os que já
-- ficaram para trás.
create index if not exists idx_pedidos_sem_dono
  on public.pedidos_contrato(criado_em)
  where cliente_id is null;
