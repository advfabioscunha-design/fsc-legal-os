-- ================================================================
-- 0014 — Número de atendimento, nome do caso e central de avisos
--
-- 1) Cada caso ganha um NÚMERO DE ATENDIMENTO (FSC-2026-0001),
--    gerado na criação, em ordem cronológica. É por ele que o
--    cliente identifica o caso quando tem mais de um processo.
-- 2) Cada movimentação relevante vira um AVISO, enviado por
--    e-mail e WhatsApp, com registro de ciência do cliente.
-- ================================================================

-- ── 1. NÚMERO DE ATENDIMENTO ────────────────────────────────────
create sequence if not exists seq_atendimento start 1;

alter table casos add column if not exists numero_atendimento text;
alter table casos add column if not exists titulo text;   -- nome do caso

create unique index if not exists idx_casos_num_atendimento
  on casos (numero_atendimento) where numero_atendimento is not null;

-- Gera FSC-<ano>-<sequência de 4 dígitos> no momento da criação.
create or replace function public.gerar_numero_atendimento()
returns trigger language plpgsql as $$
begin
  if new.numero_atendimento is null or new.numero_atendimento = '' then
    new.numero_atendimento :=
      'FSC-' || to_char(coalesce(new.criado_em, now()), 'YYYY')
             || '-' || lpad(nextval('seq_atendimento')::text, 4, '0');
  end if;
  return new;
end; $$;

drop trigger if exists trg_numero_atendimento on casos;
create trigger trg_numero_atendimento
  before insert on casos
  for each row execute function public.gerar_numero_atendimento();

-- Numera os casos que já existem, respeitando a ordem cronológica.
do $$
declare r record;
begin
  for r in (select id, criado_em from casos
            where numero_atendimento is null order by criado_em) loop
    update casos set numero_atendimento =
      'FSC-' || to_char(r.criado_em, 'YYYY') || '-' ||
      lpad(nextval('seq_atendimento')::text, 4, '0')
    where id = r.id;
  end loop;
end $$;

-- ── 2. AVISOS AO CLIENTE (com ciência) ──────────────────────────
create table if not exists avisos (
  id              uuid primary key default gen_random_uuid(),
  caso_id         uuid not null references casos(id) on delete cascade,
  tipo            text not null,        -- DOCUMENTO | AUDIENCIA | MOVIMENTACAO |
                                        -- PRAZO | PAGAMENTO | CONTRATO | GERAL
  titulo          text not null,
  mensagem        text not null,
  solicitacao_id  uuid references solicitacoes(id),

  -- entrega
  enviado_email      boolean not null default false,
  enviado_whatsapp   boolean not null default false,
  numero_origem      text,              -- número do escritório que enviou (69/48)
  erro_envio         text,

  -- ciência do cliente
  ciencia_em      timestamptz,
  ciencia_canal   text,                 -- PAINEL | WHATSAPP
  lembretes       int not null default 0,
  ultimo_lembrete timestamptz,

  criado_em       timestamptz not null default now()
);
create index if not exists idx_avisos_caso on avisos(caso_id, criado_em desc);
create index if not exists idx_avisos_pendentes
  on avisos(ciencia_em, criado_em) where ciencia_em is null;

-- ── 3. RLS: o cliente vê e dá ciência nos próprios avisos ───────
alter table avisos enable row level security;

drop policy if exists avisos_visiveis on avisos;
create policy avisos_visiveis on avisos for select using (
  public.meu_papel() = 'OPERADOR'
  or caso_id in (
    select c.id from casos c
    where c.cliente_id in (select cliente_id from perfis where id = auth.uid())
  )
);

-- O backend grava com a service_role key (ignora RLS); a política acima
-- protege qualquer leitura feita direto pelo navegador do cliente.
