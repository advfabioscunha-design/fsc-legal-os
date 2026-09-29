-- 0031 — balcão de contratos: o pedido do cliente e sua trilha.
--
-- Pedido de contrato NÃO é caso judicial, e tratar os dois na mesma
-- tabela estragaria as duas coisas: o caso tem fases processuais,
-- intimações e prazos; o pedido tem coleta, redação, revisão e
-- assinatura, e morre em semanas. Tabela própria, vida própria.

create table if not exists public.pedidos_contrato (
  id                uuid primary key default gen_random_uuid(),
  cliente_id        uuid references public.clientes(id) on delete set null,
  numero            text,                 -- FSC-C-2026-0001
  tipo              text not null,        -- ver agentes/catalogo_contratos.py
  fase              text not null default 'COLETA',
  dados             jsonb default '{}'::jsonb,   -- o que foi coletado
  observacoes       text,                 -- o combinado, nas palavras do cliente
  com_orientacao    boolean not null default false,
  com_timbre        boolean not null default true,
  valor             numeric(10,2),
  pago_em           timestamptz,
  pix_txid          text,

  minuta            text,
  minuta_anterior   text,
  revisao           jsonb,
  pedidos_alteracao jsonb default '[]'::jsonb,

  redigido_em            timestamptz,
  revisado_em            timestamptz,
  ajustado_em            timestamptz,
  aprovado_advogado_em   timestamptz,
  aprovado_advogado_por  text,
  aprovado_cliente_em    timestamptz,
  assinado_em            timestamptz,
  entregue_em            timestamptz,
  arquivado_em           timestamptz,

  zapsign_token     text,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now()
);

create index if not exists idx_pedidos_contrato_fase on public.pedidos_contrato(fase);
create index if not exists idx_pedidos_contrato_cliente on public.pedidos_contrato(cliente_id);

comment on column public.pedidos_contrato.minuta_anterior is
  'A versão de antes do ajuste. Serve para o advogado ver o que mudou '
  'sem precisar confiar na palavra de ninguém.';

comment on column public.pedidos_contrato.aprovado_advogado_em is
  'Revisão humana. É o único caminho até o cliente: sem esta data, a '
  'minuta não aparece para ele.';


-- Ciência do cliente sobre o que foge da lei.
--
-- Guarda o TEXTO INTEIRO que foi mostrado, não só um "aceitou". O que
-- vale numa discussão futura é o que estava escrito na tela naquele
-- dia — e o texto muda com o tempo.
create table if not exists public.pedidos_ciencias (
  id          uuid primary key default gen_random_uuid(),
  pedido_id   uuid not null references public.pedidos_contrato(id) on delete cascade,
  versao      text not null,
  texto       text not null,
  pontos      jsonb,
  escolha     text not null,          -- PROSSEGUIR | ADEQUAR
  ip          text,
  criado_em   timestamptz not null default now()
);

create index if not exists idx_ciencias_pedido on public.pedidos_ciencias(pedido_id);


-- Numeração do pedido, no mesmo espírito do número de atendimento.
create or replace function public.gerar_numero_pedido()
returns trigger language plpgsql as $$
declare
  ano text := to_char(now(), 'YYYY');
  seq int;
begin
  if new.numero is null then
    select coalesce(max(substring(numero from 12)::int), 0) + 1 into seq
      from public.pedidos_contrato
     where numero like 'FSC-C-' || ano || '-%';
    new.numero := 'FSC-C-' || ano || '-' || lpad(seq::text, 4, '0');
  end if;
  return new;
end $$;

drop trigger if exists trg_numero_pedido on public.pedidos_contrato;
create trigger trg_numero_pedido before insert on public.pedidos_contrato
  for each row execute function public.gerar_numero_pedido();
