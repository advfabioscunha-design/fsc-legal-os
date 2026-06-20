-- 0008 — Motor de Intimações e Monitoramento (Escavador)

create table if not exists monitoramentos (
  id              uuid primary key default gen_random_uuid(),
  caso_id         uuid references casos(id),
  numero_processo text,
  oab             text,
  tribunal        text,
  escavador_id    text,
  ativo           boolean not null default true,
  criado_em       timestamptz not null default now()
);
create index if not exists idx_monitoramentos_proc on monitoramentos (numero_processo);

create table if not exists intimacoes (
  id              uuid primary key default gen_random_uuid(),
  caso_id         uuid references casos(id),
  evento_id       text,                                  -- id do evento no Escavador (idempotência)
  tribunal        text,
  numero_processo text,
  conteudo        text,
  status          text not null default 'A_RESOLVER',    -- A_RESOLVER | RESOLVIDO | PERDA_PRAZO
  prazo_em        date,
  data_movimento  timestamptz,
  lida            boolean not null default false,
  payload         jsonb,
  criado_em       timestamptz not null default now()
);
create index if not exists idx_intimacoes_data on intimacoes (data_movimento desc);
create unique index if not exists idx_intimacoes_evento on intimacoes (evento_id) where evento_id is not null;
